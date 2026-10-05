import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "app"))
from services.layer3_rule import (  # noqa: E402
    STRONG_FLOOR,
    SUSPICIOUS_FLOOR,
    apply_layer3_rule,
    html_has_user_input,
)

FAILURES = []


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


def l3(level):
    return {"identity_note": {"level": level, "text": "", "disclaimer": ""}}


def run(score, level, features, layer2_score, html):
    return apply_layer3_rule(score, l3(level) if level else None, features, layer2_score, html)


PASSWORD_HTML = '<form><input type="password" name="pw"></form>'
TEXT_HTML = '<form><input type="text" name="card"></form>'
TEXTAREA_HTML = "<textarea></textarea>"
FILE_HTML = '<input type="file" name="upload">'
HIDDEN_ONLY_HTML = '<input type="hidden" name="t"><input type="submit" value="Go"><input type="checkbox">'
SIGNIN_LINK_HTML = '<a href="/account/signin">Sign in</a>'
PLAIN_HTML = "<p>Welcome to our shop. Browse the catalogue.</p>"

# What counts as user input
check("password field counts", html_has_user_input(PASSWORD_HTML))
check("text box counts", html_has_user_input(TEXT_HTML))
check("text area counts", html_has_user_input(TEXTAREA_HTML))
check("file upload counts", html_has_user_input(FILE_HTML))
check("sign-in link counts", html_has_user_input(SIGNIN_LINK_HTML))
check("hidden, submit and checkbox do not count", not html_has_user_input(HIDDEN_ONLY_HTML))
check("plain page with no input does not count", not html_has_user_input(PLAIN_HTML))
check("missing html does not count", not html_has_user_input(None))

# Mismatch + input, Layer 2 not in the suspicious band -> suspicious floor
score, comb = run(0.10, "closely resembles", {"password_input_count": 1}, None, None)
check("mismatch + password (no Layer 2) raises to the suspicious floor", score == SUSPICIOUS_FLOOR)
check("strength is suspicious", comb["strength"] == "suspicious" and comb["raised"] is True)
score, comb = run(0.10, "closely resembles", {}, 0.10, TEXT_HTML)
check("mismatch + text box, Layer 2 safe -> suspicious floor", score == SUSPICIOUS_FLOOR)
score, comb = run(0.10, "may be imitating", {}, 0.05, FILE_HTML)
check("mismatch + file upload, Layer 2 safe -> suspicious floor", score == SUSPICIOUS_FLOOR)

# Mismatch + input, Layer 2 in the suspicious band -> strong suspicion
score, comb = run(0.40, "closely resembles", {}, 0.40, TEXT_HTML)
check("mismatch + input + Layer 2 suspicious -> strong floor", score == STRONG_FLOOR)
check("strength is strong", comb["strength"] == "strong")
score, comb = run(0.40, "closely resembles", {"password_input_count": 1}, 0.25, None)
check("strong floor also applies at the low edge of the band", score == STRONG_FLOOR)

# Never lowers, never reaches phishing from Layer 3
score, comb = run(0.90, "closely resembles", {"password_input_count": 1}, 0.90, None)
check("a phishing score is not lowered", score == 0.90 and comb["raised"] is False)
score, comb = run(0.75, "closely resembles", {}, 0.75, TEXT_HTML)
check("a score already above the strong floor is not lowered", score == 0.75 and comb["raised"] is False)
score, comb = run(0.85, "closely resembles", {}, 0.85, TEXT_HTML)
check("Layer 3 never pushes a score into the phishing band", score == 0.85)

# Mismatch without input -> no change, notice flag set
score, comb = run(0.10, "closely resembles", {}, 0.10, PLAIN_HTML)
check("mismatch without input leaves the score", score == 0.10)
check("mismatch without input sets the notice", comb["notice"] is True and comb["raised"] is False)

# Match, unknown, error, or no Layer 3 result -> nothing
score, comb = run(0.10, "matches", {"password_input_count": 1}, 0.10, TEXT_HTML)
check("a matching brand does not change the score", score == 0.10 and comb["brand_mismatch"] is False)
score, comb = run(0.10, "could not confirm", {"password_input_count": 1}, 0.10, TEXT_HTML)
check("could not confirm is not a mismatch", score == 0.10 and comb["brand_mismatch"] is False)
score, comb = run(0.10, None, {"password_input_count": 1}, 0.10, TEXT_HTML)
check("no Layer 3 result changes nothing", score == 0.10 and comb["brand_mismatch"] is False)
score, comb = apply_layer3_rule(0.10, {"error": "could not run"}, {"password_input_count": 1}, 0.10, TEXT_HTML)
check("a Layer 3 error changes nothing", score == 0.10 and comb["brand_mismatch"] is False)

print()
if FAILURES:
    print(f"{len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("All checks passed.")
