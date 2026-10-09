"""Provenance manifest for cached F1 data.

Every file under data/cache/jolpica and data/cache/openf1 is listed in
data/cache/MANIFEST.json with the URL it came from, when it was fetched and its
SHA-256. The fetchers record each write here; tests/check_data_integrity.py fails
when a file's content no longer matches its entry, so a hand edit or a generated
file can't slip into the dataset unnoticed.

CLI:
  python -m app.tools.data_manifest --rebuild    # record every file currently on disk
  python -m app.tools.data_manifest --check      # list files that differ from the manifest
"""
import argparse
import datetime as _dt
import glob
import hashlib
import json
import os
import threading
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE_ROOT = os.path.join(ROOT, "data", "cache")
MANIFEST = os.path.join(CACHE_ROOT, "MANIFEST.json")
_lock = threading.Lock()


def _rel(path: str) -> str:
    return os.path.relpath(os.path.abspath(path), CACHE_ROOT).replace(os.sep, "/")


def _sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _load() -> dict:
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    return {"description": "Provenance of every cached data file. Written by the fetchers; do not edit by hand.",
            "files": {}}


def _save(man: dict) -> None:
    man["files"] = dict(sorted(man["files"].items()))
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=1, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, MANIFEST)


def record(path: str, source: str, note: Optional[str] = None) -> None:
    """Record (or refresh) a cached file after the fetcher wrote it."""
    if not os.path.exists(path):
        return
    with _lock:
        man = _load()
        entry = {"source": source, "sha256": _sha256(path),
                 "fetched_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        if note:
            entry["note"] = note
        man["files"][_rel(path)] = entry
        _save(man)


def forget(path: str) -> None:
    """Drop a file the fetcher deleted (e.g. a 'not raced yet' placeholder)."""
    with _lock:
        man = _load()
        if man["files"].pop(_rel(path), None) is not None:
            _save(man)


def _guess_source(path: str) -> str:
    """Source URL for a file being registered by --rebuild."""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        return "unknown"
    if isinstance(doc, dict) and "MRData" in doc:
        return doc["MRData"].get("url", "https://api.jolpi.ca")
    name = os.path.basename(path)
    if "/openf1/" in path.replace(os.sep, "/"):
        meta_path = os.path.join(CACHE_ROOT, "openf1", "sprint_qualifying_meta.json")
        if name.endswith("_sprint_qualifying.json") and os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f).get(name.replace("_sprint_qualifying.json", ""), {})
            if meta.get("source_url"):
                return meta["source_url"]
        return "https://api.openf1.org/v1/sessions"
    if name.endswith("_laps_all.json"):
        y, rnd = name.split("_")[:2]
        return f"https://api.jolpi.ca/ergast/f1/{y}/{rnd}/laps.json (all pages merged)"
    return "unknown"


def all_data_files():
    return sorted(glob.glob(os.path.join(CACHE_ROOT, "jolpica", "*.json")) +
                  glob.glob(os.path.join(CACHE_ROOT, "openf1", "*.json")))


def rebuild(note: str) -> int:
    with _lock:
        man = _load()
        now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        old, man["files"] = man.get("files", {}), {}
        for p in all_data_files():
            rel, sha = _rel(p), _sha256(p)
            if old.get(rel, {}).get("sha256") == sha:
                man["files"][rel] = old[rel]  # unchanged since the fetcher recorded it
            else:
                man["files"][rel] = {"source": _guess_source(p), "sha256": sha, "fetched_at": now, "note": note}
        _save(man)
        return len(man["files"])


def changed_files():
    man = _load()["files"]
    out = []
    for p in all_data_files():
        rel = _rel(p)
        if rel not in man:
            out.append((rel, "not in manifest"))
        elif man[rel]["sha256"] != _sha256(p):
            out.append((rel, "content differs"))
    for rel in man:
        if not os.path.exists(os.path.join(CACHE_ROOT, rel)):
            out.append((rel, "missing on disk"))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--note", default="registered by --rebuild")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.rebuild:
        print(f"recorded {rebuild(a.note)} files in {MANIFEST}")
    if a.check:
        diffs = changed_files()
        for rel, why in diffs:
            print(f"{why:16s} {rel}")
        print(f"{len(diffs)} file(s) differ from the manifest")
        raise SystemExit(1 if diffs else 0)
