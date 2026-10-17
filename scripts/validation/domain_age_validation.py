import sys
from datetime import datetime, timezone

import requests


def try_rdap(host):
    try:
        resp = requests.get(f"https://rdap.org/domain/{host}", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            for event in data.get("events", []):
                if event.get("eventAction") == "registration":
                    reg_date = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
                    days = (datetime.now(timezone.utc) - reg_date).days
                    return days, reg_date.date().isoformat()
        return None, f"RDAP responded {resp.status_code}, no registration event"
    except Exception as exc:
        return None, f"RDAP failed: {exc}"


def try_whois(host):
    import threading

    try:
        import whois
    except ImportError:
        return None, "whois library not installed"

    box = {}

    def _lookup():
        try:
            box["result"] = whois.whois(host, timeout=5)
        except Exception as exc:
            box["error"] = exc

    t = threading.Thread(target=_lookup, daemon=True)
    t.start()
    t.join(timeout=6)
    if t.is_alive():
        return None, "WHOIS timed out (>6s)"
    if "result" not in box:
        return None, f"WHOIS failed: {box.get('error')}"

    creation = box["result"].creation_date
    if isinstance(creation, list):
        creation = creation[0]
    if not creation:
        return None, "WHOIS returned no creation_date"
    if creation.tzinfo is None:
        creation = creation.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - creation).days
    return days, creation.date().isoformat()


def try_wayback(host):
    try:
        resp = requests.get(
            "http://web.archive.org/cdx/search/cdx",
            params={
                "url": host,
                "output": "json",
                "limit": 1,
                "fl": "timestamp",
                "filter": "statuscode:200",
            },
            timeout=20,
        )
        if resp.status_code != 200:
            return None, f"Wayback CDX responded {resp.status_code}"
        rows = resp.json()
        if len(rows) <= 1:
            return None, "Wayback has no archived snapshot for this host"
        timestamp = rows[1][0]
        first_seen = datetime.strptime(timestamp[:8], "%Y%m%d").replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - first_seen).days
        return days, first_seen.date().isoformat()
    except Exception as exc:
        return None, f"Wayback failed: {exc}"


def resolve_domain_age(host):
    print(f"=== {host} ===")

    days, detail = try_rdap(host)
    print(f"  1. RDAP      -> {detail}")
    if days is not None:
        print(f"     RESULT: {days} days (~{days/365:.1f} years), source=RDAP")
        return days, "RDAP"

    days, detail = try_whois(host)
    print(f"  2. WHOIS     -> {detail}")
    if days is not None:
        print(f"     RESULT: {days} days (~{days/365:.1f} years), source=WHOIS")
        return days, "WHOIS"

    days, detail = try_wayback(host)
    print(f"  3. Wayback   -> {detail}")
    if days is not None:
        print(f"     RESULT: {days} days (~{days/365:.1f} years, LOWER BOUND), source=Wayback")
        return days, "Wayback"

    print("     RESULT: no age could be determined from any source")
    return None, None


if __name__ == "__main__":
    hosts = sys.argv[1:] or ["sampath.lk", "nibm.ac.lk", "circuito.nibm.lk", "lolcfinance.com"]
    for h in hosts:
        resolve_domain_age(h)
        print()
