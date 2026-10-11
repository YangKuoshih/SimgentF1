"""Static sentence embeddings (model2vec "potion" models) with only numpy.

A static embedding model is a table with one vector per token. A text's vector is the mean of
its token vectors, normalised to unit length. This module reads the table from
model.safetensors and tokenises with a pure-Python BERT WordPiece tokenizer driven by the
model's tokenizer.json, so no tokenizer or ML library is needed (verified id-for-id against the
reference `tokenizers` library, see tests/test_router.py).

Model files are fetched by scripts/fetch_models.py (pinned revision, SHA-256 checked) into
models/<name>/. When they are missing, `StaticEmbedder.load` returns None and callers fall back
to lexical matching.
"""

import json
import os
import struct
import unicodedata
from typing import Dict, List, Optional

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_DIR = os.environ.get("SIMGENT_EMBEDDING_MODEL", os.path.join(ROOT, "models", "potion-base-8M"))


class WordPiece:
    """BERT uncased tokenisation: clean text, lowercase, strip accents, split on whitespace and
    punctuation (with spaces around CJK characters), then greedy longest-match WordPiece."""

    def __init__(self, vocab: Dict[str, int], unk: str = "[UNK]", prefix: str = "##", max_chars: int = 100):
        self.vocab, self.unk_id, self.prefix, self.max_chars = vocab, vocab.get(unk), prefix, max_chars

    @classmethod
    def from_tokenizer_json(cls, path: str) -> "WordPiece":
        with open(path, encoding="utf-8") as f:
            model = json.load(f)["model"]
        if model.get("type") != "WordPiece":
            raise ValueError(f"unsupported tokenizer model {model.get('type')!r}")
        return cls(model["vocab"], model.get("unk_token", "[UNK]"),
                   model.get("continuing_subword_prefix", "##"), model.get("max_input_chars_per_word", 100))

    @staticmethod
    def _is_punct(ch: str) -> bool:
        cp = ord(ch)
        if 33 <= cp <= 47 or 58 <= cp <= 64 or 91 <= cp <= 96 or 123 <= cp <= 126:
            return True
        return unicodedata.category(ch).startswith("P")

    @staticmethod
    def _is_cjk(cp: int) -> bool:
        return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF
                or 0x2A700 <= cp <= 0x2B73F or 0x2B740 <= cp <= 0x2B81F or 0x2B820 <= cp <= 0x2CEAF
                or 0xF900 <= cp <= 0xFAFF or 0x2F800 <= cp <= 0x2FA1F)

    def _normalise(self, text: str) -> str:
        out = []
        for ch in text:
            cp = ord(ch)
            if cp == 0 or cp == 0xFFFD or (unicodedata.category(ch).startswith("C") and ch not in "\t\n\r"):
                continue
            if ch in "\t\n\r" or unicodedata.category(ch) == "Zs":
                out.append(" ")
            elif self._is_cjk(cp):
                out.append(f" {ch} ")
            else:
                out.append(ch)
        text = unicodedata.normalize("NFD", "".join(out).lower())
        return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")

    def _words(self, text: str) -> List[str]:
        words = []
        for chunk in text.split():
            word = ""
            for ch in chunk:
                if self._is_punct(ch):
                    if word:
                        words.append(word)
                        word = ""
                    words.append(ch)
                else:
                    word += ch
            if word:
                words.append(word)
        return words

    def encode(self, text: str) -> List[int]:
        ids = []
        for word in self._words(self._normalise(text)):
            if len(word) > self.max_chars:
                ids.append(self.unk_id)
                continue
            start, pieces = 0, []
            while start < len(word):
                end, piece = len(word), None
                while start < end:
                    sub = word[start:end] if start == 0 else self.prefix + word[start:end]
                    if sub in self.vocab:
                        piece = self.vocab[sub]
                        break
                    end -= 1
                if piece is None:
                    pieces = [self.unk_id]
                    break
                pieces.append(piece)
                start = end
            ids.extend(pieces)
        return ids


def _read_safetensors(path: str) -> np.ndarray:
    """The single embedding table from a safetensors file (F32 or F16), as float32."""
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
    tensors = {k: v for k, v in header.items() if k != "__metadata__"}
    if len(tensors) != 1:
        raise ValueError(f"expected one tensor in {path}, found {list(tensors)}")
    meta = next(iter(tensors.values()))
    dtype = {"F32": np.float32, "F16": np.float16}[meta["dtype"]]
    begin, end = meta["data_offsets"]
    raw = np.fromfile(path, dtype=np.uint8, count=end - begin, offset=8 + n + begin)
    return raw.view(dtype).reshape(meta["shape"]).astype(np.float32)


class StaticEmbedder:
    def __init__(self, tokenizer: WordPiece, table: np.ndarray):
        self.tokenizer, self.table = tokenizer, table
        self.dim = table.shape[1]

    @classmethod
    def load(cls, model_dir: str = MODEL_DIR) -> Optional["StaticEmbedder"]:
        tok, weights = os.path.join(model_dir, "tokenizer.json"), os.path.join(model_dir, "model.safetensors")
        if not (os.path.exists(tok) and os.path.exists(weights)):
            return None
        return cls(WordPiece.from_tokenizer_json(tok), _read_safetensors(weights))

    def embed(self, texts: List[str]) -> np.ndarray:
        """Unit-length vectors, one row per text (zeros for a text with no known tokens)."""
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            ids = [t for t in self.tokenizer.encode(text) if t != self.tokenizer.unk_id]
            if ids:
                v = self.table[ids].mean(axis=0)
                norm = float(np.linalg.norm(v))
                out[i] = v / norm if norm else v
        return out
