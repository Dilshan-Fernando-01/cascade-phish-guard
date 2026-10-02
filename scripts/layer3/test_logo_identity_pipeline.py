import os
import sys

from playwright.sync_api import sync_playwright

from logo_candidates import crop_candidate, find_logo_candidates
from logo_identity import check_domain_brand_mismatch, load_model, load_reference_cache

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "backend", "app"))

WEIGHTS_PATH = "../../data/external/phishpedia/resnetv2_rgb_new.pth.tar"
CACHE_PATH = "../../data/external/phishpedia/logo_reference_embeddings.pkl"
DOMAIN_MAP_PATH = "../../data/external/phishpedia/domain_map.pkl"
CROP_DIR = "../../temp/backups/logo_identity_test_crops"

TEST_SITES = [
    "https://www.paypal.com",
    "https://www.apple.com",
    "https://www.microsoft.com",
]

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def main():
    import pickle

    with open(DOMAIN_MAP_PATH, "rb") as f:
        domain_map = pickle.load(f)

    print("Loading model + reference embeddings...")
    model = load_model(WEIGHTS_PATH)
    ref_embeddings, ref_file_paths = load_reference_cache(CACHE_PATH)
    print(f"Loaded {len(ref_file_paths)} reference logo embeddings.")

    os.makedirs(CROP_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for url in TEST_SITES:
            domain = url.split("//")[1]
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            try:
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
            except Exception as exc:
                check(f"{domain}: page loaded", False)
                print(f"  error: {exc}")
                page.close()
                continue

            candidates = find_logo_candidates(page, top_n=1, min_score=1)
            if not candidates:
                check(f"{domain}: found a logo candidate", False)
                page.close()
                continue

            crop_path = os.path.join(CROP_DIR, f"{domain}.png")
            cropped_ok = crop_candidate(page, candidates[0], crop_path)
            check(f"{domain}: cropped logo candidate", cropped_ok)
            page.close()

            if not cropped_ok:
                continue

            real_result = check_domain_brand_mismatch(crop_path, url, model, ref_embeddings, ref_file_paths, domain_map)
            print(f"  real-domain result: {real_result}")
            check(f"{domain}: own real domain is NOT flagged as mismatch", real_result["mismatch"] is False)

            fake_url = f"https://{domain.replace('.', '-')}-account-verify-secure.tk/login"
            fake_result = check_domain_brand_mismatch(crop_path, fake_url, model, ref_embeddings, ref_file_paths, domain_map)
            print(f"  fake-domain result:  {fake_result}")
            if real_result["identified_brand"]:
                check(f"{domain}: fabricated domain IS flagged as mismatch", fake_result["mismatch"] is True)
            else:
                print(f"  (skipped mismatch assertion -- brand not confidently identified for {domain})")

        browser.close()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
