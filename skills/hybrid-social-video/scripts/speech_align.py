"""speech_align.py - shared helpers: normalise text to spoken tokens, align a transcript to a script.

Used by voice_check.py and host_assemble.py. Stdlib only. English number words are handled for 0-999
(digits in a script are spoken as words, and a transcriber may return either); other languages compare
their tokens as written, so a language with its own digit words should pass `numbers=False` and list its
number words in the beat map (`meta.number_words`).
"""
from __future__ import annotations

import difflib
import re

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def number_words(n: int) -> list[str]:
    if n < 20:
        return [_ONES[n]]
    if n < 100:
        return [_TENS[n // 10]] + ([_ONES[n % 10]] if n % 10 else [])
    if n < 1000:
        return [_ONES[n // 100], "hundred"] + (number_words(n % 100) if n % 100 else [])
    return [str(n)]


def tokens(text: str, numbers: bool = True) -> list[str]:
    """Lower-cased spoken tokens: hyphens and punctuation split words, digits become words (0-999)."""
    out: list[str] = []
    for w in re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE):
        if numbers and w.isdigit() and int(w) < 1000:
            out += number_words(int(w))
        else:
            out.append(w)
    return out


def display_tokens(word: str, numbers: bool = True) -> list[str]:
    return tokens(word, numbers)


def align(expected: list[str], heard: list[str]) -> dict[int, int]:
    """Map index in `expected` -> index in `heard` for the tokens that match, in order."""
    sm = difflib.SequenceMatcher(None, expected, heard, autojunk=False)
    return {blk.a + i: blk.b + i for blk in sm.get_matching_blocks() for i in range(blk.size)}


def wer(expected: list[str], heard: list[str]) -> float:
    """Word error rate by Levenshtein distance over tokens (0 = identical)."""
    n, m = len(expected), len(heard)
    if n == 0:
        return 0.0 if m == 0 else 1.0
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (expected[i - 1] != heard[j - 1]))
        prev = cur
    return prev[m] / n
