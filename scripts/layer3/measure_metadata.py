import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend", "app"))
from features.metadata_identity import metadata_identity  # noqa: E402
from features.url_brand_hint import url_brand_hints  # noqa: E402


def host_from_filename(name):
    stem = name[: -len(".html")]
    for scheme in ("https_", "http_"):
        if stem.startswith(scheme):
            stem = stem[len(scheme):]
            break
    return stem.split("_")[0]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("legit", "phishing"):
        print(__doc__)
        return
    folder = os.path.join(ROOT, "data", "layer3", "html_test", sys.argv[1])
    files = [f for f in os.listdir(folder) if f.endswith(".html")]
    with_meta = strong = tight = 0
    for name in files:
        host = host_from_filename(name)
        html = open(os.path.join(folder, name), encoding="utf-8", errors="ignore").read()
        result = metadata_identity(html, f"https://{host}/")
        if result is None:
            continue
        with_meta += 1
        if result["strong"]:
            strong += 1
            if url_brand_hints(host):
                tight += 1
    total = len(files)
    print(f"set: {sys.argv[1]}  pages saved: {total}")
    print(f"  declares metadata: {with_meta} ({100 * with_meta / max(total, 1):.1f}%)")
    print(f"  strong alone:      {strong} ({100 * strong / max(with_meta, 1):.1f}% of those with metadata)")
    print(f"  strong + brand in address: {tight} ({100 * tight / max(with_meta, 1):.1f}% of those with metadata)")


if __name__ == "__main__":
    main()
