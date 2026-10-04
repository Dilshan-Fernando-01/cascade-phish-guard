import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from services.layer3_rule import (  # noqa: E402
    SUSPICIOUS_FLOOR,
    apply_layer3_rule,
    html_has_credential_signal,
)

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def l3(level):
    return {"identity_note": {"level": level, "text": "", "disclaimer": ""}}


PASSWORD_HTML = '<form><input type="password" name="pw"></form>'
SIGNIN_LINK_HTML = '<a href="/account/signin">Sign in</a>'
PLAIN_HTML = "<p>Welcome to our shop. Browse the catalogue.</p>"


check("password field is a credential signal", html_has_credential_signal(PASSWORD_HTML))
check("sign-in link text is a credential signal", html_has_credential_signal(SIGNIN_LINK_HTML))
check("sign-up link by href is a credential signal",
      html_has_credential_signal('<a href="https://x.example/register">Join</a>'))
check("plain page has no credential signal", not html_has_credential_signal(PLAIN_HTML))
check("missing html has no credential signal", not html_has_credential_signal(None))


score, comb = apply_layer3_rule(0.10, l3("closely resembles"), {"password_input_count": 1}, None)
check("mismatch + password field raises a low score to the floor", score == SUSPICIOUS_FLOOR)
check("raise is recorded", comb["raised"] is True and comb["notice"] is False)

score, comb = apply_layer3_rule(0.30, l3("may be imitating"), {}, SIGNIN_LINK_HTML)
check("mismatch + sign-in link raises the score", score == SUSPICIOUS_FLOOR and comb["raised"])


score, comb = apply_layer3_rule(0.90, l3("closely resembles"), {"password_input_count": 1}, None)
check("a score already above the floor is not lowered", score == 0.90 and comb["raised"] is False)
check("the rule never pushes a score into the phishing band", score <= 0.8 or score == 0.90)
score, comb = apply_layer3_rule(0.45, l3("closely resembles"), {"password_input_count": 1}, None)
check("a score just under the floor is raised only to the floor", score == SUSPICIOUS_FLOOR)
check("the rule result never exceeds the floor on its own", apply_layer3_rule(0.05, l3("closely resembles"), {"password_input_count": 2}, None)[0] == SUSPICIOUS_FLOOR)


score, comb = apply_layer3_rule(0.10, l3("closely resembles"), {"password_input_count": 0}, PLAIN_HTML)
check("mismatch without credential signal leaves the score", score == 0.10)
check("mismatch without credential signal sets the notice", comb["notice"] is True and comb["raised"] is False)


score, comb = apply_layer3_rule(0.10, l3("matches"), {"password_input_count": 1}, None)
check("a matching brand does not raise the score", score == 0.10 and comb["brand_mismatch"] is False)
score, comb = apply_layer3_rule(0.10, None, {"password_input_count": 1}, None)
check("no Layer 3 result changes nothing", score == 0.10 and comb["brand_mismatch"] is False)
score, comb = apply_layer3_rule(0.10, {"error": "could not run"}, {"password_input_count": 1}, None)
check("a Layer 3 error changes nothing", score == 0.10 and comb["brand_mismatch"] is False)
score, comb = apply_layer3_rule(0.10, l3("could not confirm"), {"password_input_count": 1}, None)
check("could not confirm is not a mismatch", score == 0.10 and comb["brand_mismatch"] is False)

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
