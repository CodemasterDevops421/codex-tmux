from __future__ import annotations

import math

try:
  import tiktoken  # type: ignore
except Exception:  # pragma: no cover
  tiktoken = None


def estimate_tokens(text: str) -> int:
  if not text:
    return 0
  if tiktoken is not None:
    try:
      enc = tiktoken.get_encoding("cl100k_base")
      return len(enc.encode(text))
    except Exception:
      pass
  return int(math.ceil(len(text) / 4))
