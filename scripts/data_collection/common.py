import json
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


def fetch_text(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "cascade-phish-guard-research/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def save_snapshot(source, url, lines, timestamp):
    source_dir = RAW_DIR / source
    source_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = source_dir / f"{timestamp}.txt"
    snapshot_path.write_text("\n".join(lines), encoding="utf-8")

    manifest_path = source_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    manifest.append({
        "source": source,
        "url": url,
        "timestamp": timestamp,
        "count": len(lines),
        "file": snapshot_path.name,
    })
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return snapshot_path, len(lines)
