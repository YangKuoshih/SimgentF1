"""Download the embedding model used by the Pit Wall Agent router (pinned and verified).

  python scripts/fetch_models.py           # into models/potion-base-8M/
  python scripts/fetch_models.py --check   # verify files already present

minishlab/potion-base-8M (MIT licence, https://huggingface.co/minishlab/potion-base-8M):
static embeddings, about 30 MB. Files come from one pinned revision and must match the SHA-256
hashes below; anything else is rejected. The Docker build runs this script, and CI runs it
before the router tests. Without the files the router falls back to lexical matching.
"""

import hashlib
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "minishlab/potion-base-8M"
REVISION = "bf8b056651a2c21b8d2565580b8569da283cab23"
DEST = os.path.join(ROOT, "models", "potion-base-8M")
FILES = {
    "model.safetensors": "f65d0f325faadc1e121c319e2faa41170d3fa07d8c89abd48ca5358d9a223de2",
    "tokenizer.json": "e67e803f624fb4d67dea1c730d06e1067e1b14d830e2c2202569e3ef0f70bb50",
    "config.json": "2a6ac0e9aaa356a68a5688070db78fc3a464fefe85d2f06a1905ce3718687553",
}
# Hugging Face serves large files from its CDN after a redirect.
ALLOWED_HOSTS = ("huggingface.co", "cdn-lfs.huggingface.co", "cdn-lfs-us-1.hf.co", "cas-bridge.xethub.hf.co")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class _Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = urllib.parse.urlsplit(newurl).hostname or ""
        if urllib.parse.urlsplit(newurl).scheme != "https" or not (
                host in ALLOWED_HOSTS or host.endswith(".hf.co") or host.endswith(".huggingface.co")):
            raise urllib.error.URLError(f"refusing redirect to {host}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(check_only: bool = False) -> bool:
    os.makedirs(DEST, exist_ok=True)
    opener = urllib.request.build_opener(_Redirects)
    ok = True
    for name, digest in FILES.items():
        path = os.path.join(DEST, name)
        if os.path.exists(path) and _sha256(path) == digest:
            print(f"  ok      {name}")
            continue
        if check_only:
            print(f"  MISSING {name}")
            ok = False
            continue
        url = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}"
        tmp = path + ".part"
        req = urllib.request.Request(url, headers={"User-Agent": "SimgentF1-fetch-models/1.0"})
        with opener.open(req, timeout=120) as r, open(tmp, "wb") as f:
            while chunk := r.read(1 << 20):
                f.write(chunk)
        got = _sha256(tmp)
        if got != digest:
            os.remove(tmp)
            print(f"  REJECTED {name}: sha256 {got} != {digest}")
            ok = False
            continue
        os.replace(tmp, path)
        print(f"  fetched {name}")
    return ok


if __name__ == "__main__":
    print(f"{REPO}@{REVISION[:12]} -> {os.path.relpath(DEST, ROOT)}")
    sys.exit(0 if fetch(check_only="--check" in sys.argv) else 1)
