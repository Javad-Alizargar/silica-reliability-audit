"""Acquire the original published nanosilica workbook and companion code archive."""
from pathlib import Path
from urllib.request import urlopen, Request
import hashlib
import json
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 2_000_000_000

def get(url):
    return urlopen(Request(url, headers={"User-Agent": "NanosilicaResearch/0.1"}), timeout=90)

def main():
    (ROOT / 'download').mkdir(parents=True, exist_ok=True)
    (ROOT / 'literature/raw').mkdir(parents=True, exist_ok=True)
    records = []
    for article_id, destination in [(23112038, "download"), (23112032, "literature/raw")]:
        url = f"https://api.figshare.com/v2/articles/{article_id}"
        with get(url) as r:
            meta = json.load(r)
        (ROOT / "literature/raw" / f"figshare_{article_id}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        for item in meta["files"]:
            if item["size"] >= LIMIT:
                raise RuntimeError("User consultation required for download >= 2 GB")
            name = Path(item["name"]).name
            path = ROOT / destination / name
            if not path.exists():
                with get(item["download_url"]) as r, path.open("wb") as out:
                    size = 0
                    while chunk := r.read(1024 * 1024):
                        size += len(chunk)
                        if size >= LIMIT:
                            raise RuntimeError("Download crossed automatic size threshold")
                        out.write(chunk)
            data = path.read_bytes()
            assert len(data) == item["size"], "Size mismatch"
            assert hashlib.md5(data).hexdigest() == item["computed_md5"], "Repository checksum mismatch"
            records.append({"path": path.relative_to(ROOT).as_posix(), "bytes": len(data),
                            "sha256": hashlib.sha256(data).hexdigest(), "md5": item["computed_md5"],
                            "source": url, "download_url": item["download_url"], "doi": meta["doi"],
                            "license": meta["license"], "retrieved_utc": datetime.now(timezone.utc).isoformat()})
            print(name, len(data), "bytes; repository checksum verified")
    (ROOT / "download/data_manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
