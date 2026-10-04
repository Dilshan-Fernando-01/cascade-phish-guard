import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from features.url_brand_hint import url_brand_hints  # noqa: E402
from services.layer3_analyzer import analyze_layer3  # noqa: E402

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def brands(host):
    return [h["brand"] for h in url_brand_hints(host)]


def main():
    check("real brand homepage gets no hint", brands("www.paypal.com") == [])
    check("real brand subdomain gets no hint", brands("login.paypal.com") == [])
    check("small spelling change is hinted", "paypal.com" in brands("paypa1.com"))
    check("brand name inside a longer address is hinted", "paypal.com" in brands("paypal-secure-login.tk"))
    check("brand name with a suffix is hinted", "microsoft.com" in brands("microsoft-account-verify.xyz"))
    check("unrelated local site gets no hint", brands("nibm.ac.lk") == [])
    check("ordinary search site gets no hint", brands("google.com") == [])

    no_logo = analyze_layer3("https://paypa1.com/login", b"")["identity_note"]
    check("no logo plus hint gives 'may be imitating'", no_logo["level"] == "may be imitating")
    check("imitating note never says phishing", "phishing" not in no_logo["text"].lower())

    local = analyze_layer3("https://nibm.ac.lk/", b"")["identity_note"]
    check("local site with no logo and no hint is 'could not confirm'", local["level"] == "could not confirm")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
