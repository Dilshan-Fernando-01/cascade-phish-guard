import os
import pickle
from collections import OrderedDict

import numpy as np
import torch
from PIL import Image, ImageOps
from tldextract import tldextract
from torchvision import transforms

from resnetv2 import bit_m_r50x1

NUM_CLASSES = 277
IMG_SIZE = 128
MEAN = [0.5, 0.5, 0.5]
STD = [0.5, 0.5, 0.5]
SIMILARITY_THRESHOLD = 0.87  # Phishpedia's own published MATCH_THRE

SKIP_FILENAME_PREFIXES = ("loginpage", "homepage")
VALID_EXTENSIONS = (".png", ".PNG", ".jpeg", ".jpg", ".JPG", ".JPEG")

COUNTRY_TLDS = {
    "af", "ax", "al", "dz", "as", "ad", "ao", "ai", "aq", "ag", "ar", "am", "aw", "ac", "au", "at",
    "az", "bs", "bh", "bd", "bb", "eus", "by", "be", "bz", "bj", "bm", "bt", "bo", "bq", "an", "nl",
    "ba", "bw", "bv", "br", "io", "vg", "bn", "bg", "bf", "mm", "bi", "kh", "cm", "ca", "cv", "cat",
    "ky", "cf", "td", "cl", "cn", "cx", "cc", "co", "km", "cd", "cg", "ck", "cr", "ci", "hr", "cu",
    "cw", "cy", "cz", "dk", "dj", "dm", "do", "tl", "tp", "ec", "eg", "sv", "gq", "er", "ee", "et",
    "eu", "fk", "fo", "fm", "fj", "fi", "fr", "gf", "pf", "tf", "ga", "gal", "gm", "ps", "ge", "de",
    "gh", "gi", "gr", "gl", "gd", "gp", "gu", "gt", "gg", "gn", "gw", "gy", "ht", "hm", "hn", "hk",
    "hu", "is", "in", "id", "ir", "iq", "ie", "im", "il", "it", "jm", "jp", "je", "jo", "kz", "ke",
    "ki", "kw", "kg", "la", "lv", "lb", "ls", "lr", "ly", "li", "lt", "lu", "mo", "mk", "mg", "mw",
    "my", "mv", "ml", "mt", "mh", "mq", "mr", "mu", "yt", "mx", "md", "mc", "mn", "me", "ms", "ma",
    "mz", "na", "nr", "np", "nc", "nz", "ni", "ne", "ng", "nu", "nf", "tr", "kp", "mp", "no", "om",
    "pk", "pw", "pa", "pg", "py", "pe", "ph", "pn", "pl", "pt", "pr", "qa", "ro", "ru", "rw", "re",
    "bl", "sh", "kn", "lc", "mf", "pm", "vc", "ws", "sm", "st", "sa", "sn", "rs", "sc", "sl", "sg",
    "sx", "sk", "si", "sb", "so", "za", "gs", "kr", "ss", "es", "lk", "sd", "sr", "sj", "sz", "se",
    "ch", "sy", "tw", "tj", "tz", "th", "tg", "tk", "to", "tt", "tn", "tm", "tc", "tv", "ug", "ua",
    "ae", "uk", "us", "vi", "uy", "uz", "vu", "va", "ve", "vn", "wf", "eh", "ye", "zm", "zw",
}


def load_model(weights_path, num_classes=NUM_CLASSES):
    model = bit_m_r50x1(head_size=num_classes, zero_head=True)
    weights = torch.load(weights_path, map_location="cpu")
    weights = weights["model"] if "model" in weights else weights
    new_state_dict = OrderedDict()
    for k, v in weights.items():
        name = k.split("module.")[1] if "module." in k else k
        new_state_dict[name] = v
    model.load_state_dict(new_state_dict)
    model.eval()
    return model


def l2_norm(x):
    x = x.reshape((x.shape[0], -1))
    return torch.nn.functional.normalize(x, p=2, dim=1)


@torch.no_grad()
def get_embedding(img, model):
    """img: a file path or a PIL.Image. Returns a (2048,) L2-normalized numpy vector."""
    img = Image.open(img) if isinstance(img, str) else img
    img = img.convert("RGB")

    pad_color = (255, 255, 255)
    w, h = img.size
    img = ImageOps.expand(
        img,
        ((max(w, h) - w) // 2, (max(w, h) - h) // 2, (max(w, h) - w) // 2, (max(w, h) - h) // 2),
        fill=pad_color,
    )
    img = img.resize((IMG_SIZE, IMG_SIZE))

    tensor = transforms.Compose([transforms.ToTensor(), transforms.Normalize(mean=MEAN, std=STD)])(img)
    tensor = tensor[None, ...]
    feat = model.features(tensor)
    return l2_norm(feat).squeeze(0).numpy()


def build_reference_embeddings(targetlist_path, model, progress=True):
    """One-time (cacheable) pass over every real brand logo image, producing
    (embeddings, file_paths) -- file_paths[i]'s parent folder name identifies
    the brand for embeddings[i]."""
    embeddings, file_paths = [], []
    brands = sorted(d for d in os.listdir(targetlist_path) if not d.startswith("."))
    for bi, brand in enumerate(brands):
        brand_dir = os.path.join(targetlist_path, brand)
        if not os.path.isdir(brand_dir):
            continue
        for fname in os.listdir(brand_dir):
            if not fname.endswith(VALID_EXTENSIONS):
                continue
            if fname.startswith(SKIP_FILENAME_PREFIXES):
                continue
            path = os.path.join(brand_dir, fname)
            try:
                embeddings.append(get_embedding(path, model))
                file_paths.append(path)
            except Exception:
                continue
        if progress and (bi + 1) % 25 == 0:
            print(f"[reference embeddings] {bi + 1}/{len(brands)} brand folders processed")
    return np.array(embeddings), file_paths


def save_reference_cache(path, embeddings, file_paths):
    with open(path, "wb") as f:
        pickle.dump({"embeddings": embeddings, "file_paths": file_paths}, f)


def load_reference_cache(path):
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["embeddings"], data["file_paths"]



BRAND_NAME_ALIASES = {
    "Adobe Inc.": "Adobe", "Adobe Inc": "Adobe",
    "ADP, LLC": "ADP", "ADP, LLC.": "ADP",
    "Amazon.com Inc.": "Amazon", "Amazon.com Inc": "Amazon",
    "Americanas.com S,A Comercio Electrnico": "Americanas.com S",
    "AOL Inc.": "AOL", "AOL Inc": "AOL",
    "Apple Inc.": "Apple", "Apple Inc": "Apple",
    "AT&T Inc.": "AT&T", "AT&T Inc": "AT&T",
    "Banco do Brasil S.A.": "Banco do Brasil S.A",
    "Credit Agricole S.A.": "Credit Agricole S.A",
    "DGI (French Tax Authority)": "DGI French Tax Authority",
    "DHL Airways, Inc.": "DHL Airways", "DHL Airways, Inc": "DHL Airways", "DHL": "DHL Airways",
    "Dropbox, Inc.": "Dropbox", "Dropbox, Inc": "Dropbox",
    "eBay Inc.": "eBay", "eBay Inc": "eBay",
    "Facebook, Inc.": "Facebook", "Facebook, Inc": "Facebook",
    "Free (ISP)": "Free ISP",
    "Google Inc.": "Google", "Google Inc": "Google",
    "Mastercard International Incorporated": "Mastercard International",
    "Netflix Inc.": "Netflix", "Netflix Inc": "Netflix",
    "PayPal Inc.": "PayPal", "PayPal Inc": "PayPal",
    "Royal KPN N.V.": "Royal KPN N.V",
    "SF Express Co.": "SF Express Co",
    "SNS Bank N.V.": "SNS Bank N.V",
    "Square, Inc.": "Square", "Square, Inc": "Square",
    "Webmail Providers": "Webmail Provider",
    "Yahoo! Inc": "Yahoo!", "Yahoo! Inc.": "Yahoo!",
    "Microsoft OneDrive": "Microsoft", "Office365": "Microsoft", "Outlook": "Microsoft",
    "Global Sources (HK)": "Global Sources HK",
    "T-Online": "Deutsche Telekom",
    "Airbnb, Inc": "Airbnb, Inc.",
    "azul": "Azul",
    "Raiffeisen Bank S.A": "Raiffeisen Bank S.A.",
    "Twitter, Inc": "Twitter, Inc.", "Twitter": "Twitter, Inc.",
    "capital_one": "Capital One Financial Corporation",
    "la_banque_postale": "La Banque postale",
    "db": "Deutsche Bank AG",
    "Swiss Post": "PostFinance", "PostFinance": "PostFinance",
    "grupo_bancolombia": "Bancolombia",
    "barclays": "Barclays Bank Plc",
    "gov_uk": "Government of the United Kingdom",
    "Aruba S.p.A": "Aruba S.p.A.",
    "TSB Bank Plc": "TSB Bank Limited",
    "strato": "Strato AG",
    "cogeco": "Cogeco",
    "Canada Revenue Agency": "Government of Canada",
    "UniCredit Bulbank": "UniCredit Bank Aktiengesellschaft",
    "ameli_fr": "French Health Insurance",
    "Banco de Credito del Peru": "bcp",
}


def brand_converter(folder_name):
    return BRAND_NAME_ALIASES.get(folder_name, folder_name)


def _brand_of(file_path):
    return brand_converter(os.path.basename(os.path.dirname(file_path)))


def predict_brand(crop_img, model, ref_embeddings, ref_file_paths, domain_map, similarity_threshold=SIMILARITY_THRESHOLD):
    """Given a cropped candidate logo image, returns (brand, known_domains, similarity)
    or (None, None, top1_similarity) if no confident match."""
    img_feat = get_embedding(crop_img, model)
    sims = ref_embeddings.dot(img_feat)

    top_idx = np.argsort(sims)[::-1][:3]
    top_brands = [_brand_of(ref_file_paths[i]) for i in top_idx]
    top_sims = sims[top_idx]

    for j in range(len(top_idx)):
        if top_brands[j] != top_brands[0]:
            continue
        if top_sims[j] >= similarity_threshold:
            brand = top_brands[j]
            return brand, domain_map.get(brand, []), float(top_sims[j])

    return None, None, float(top_sims[0]) if len(top_sims) else 0.0


def check_domain_brand_mismatch(crop_img, page_url, model, ref_embeddings, ref_file_paths, domain_map,
                                 similarity_threshold=SIMILARITY_THRESHOLD):
    brand, known_domains, similarity = predict_brand(
        crop_img, model, ref_embeddings, ref_file_paths, domain_map, similarity_threshold
    )

    result = {
        "identified_brand": brand,
        "known_domains": known_domains,
        "similarity": similarity,
        "page_domain": None,
        "mismatch": False,
    }

    if not brand or not known_domains:
        return result

    extracted = tldextract.extract(page_url)
    page_domain = f"{extracted.domain}.{extracted.suffix}"
    result["page_domain"] = page_domain

    if page_domain in known_domains:
        return result  # exact match -- benign

    page_2nd_level = extracted.domain
    known_2nd_levels = [tldextract.extract(d).domain for d in known_domains]
    if page_2nd_level in known_2nd_levels and extracted.suffix.split(".")[-1] in COUNTRY_TLDS:
        return result  # same brand, regional TLD variant -- benign, not flagged

    result["mismatch"] = True
    return result
