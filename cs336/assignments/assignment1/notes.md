---
title: Assignment 1 — Basics
ready: true
---

<span class="margin-note" id="resources"><span class="margin-note__label">Resources</span><span class="icon-list"><a href="./cs336_assignment1_basics.pdf"><svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="15" y2="17"/></svg><span>Assignment PDF</span></a><br><a href="./assignment1-basics/"><svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.55v-2.13c-3.2.69-3.87-1.34-3.87-1.34-.52-1.31-1.27-1.66-1.27-1.66-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.75 2.68 1.24 3.34.95.1-.74.4-1.24.72-1.53-2.55-.29-5.23-1.28-5.23-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.79 0c2.21-1.49 3.18-1.18 3.18-1.18.62 1.58.23 2.75.11 3.04.73.81 1.18 1.84 1.18 3.1 0 4.42-2.69 5.4-5.25 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.66.8.55C20.71 21.39 24 17.08 24 12 24 5.65 18.85.5 12 .5z"/></svg><span>Code Base</span></a></span></span>

## Problem `unicode1` — Understanding Unicode

<span class="heading-meta">1 point total</span>

### (a) `chr(0)`

**Question:** What Unicode character does `chr(0)` return?

**Answer:** The null character, U+0000 (NUL) — Python represents it as the single-character string `'\x00'`.

### (b) `__repr__()` vs printed form

**Question:** How does this character's string representation (`__repr__()`) differ from its printed representation?

**Answer:** `__repr__()` returns the escape-sequence form `'\x00'` (printable, unambiguous, suitable for eval-roundtripping), while `print(chr(0))` emits the actual NUL control byte, which is non-printing and therefore invisible in the output.

### (c) NUL inside a string

**Question:** What happens when this character occurs in text? (e.g., `"this is a test" + chr(0) + "string"` and `print(...)` of the same.)

**Answer:** The null character is a **single** regular character within the Python string (it does not terminate the string as in C), but because it is a non-printing control character it is silently invisible when printed.

---

## Problem `unicode2` — Unicode Encodings

<span class="heading-meta">3 points total</span>

### (a) Why UTF-8 over UTF-16 / UTF-32

**Question:** What are some reasons to prefer training our tokenizer on UTF-8 encoded bytes, rather than UTF-16 or UTF-32?

**Answer:** UTF-8 uses fewer bytes (one byte per ASCII character, vs. 2 or 4 in UTF-16/UTF-32) and avoids the wasted null-padding bytes that those wider encodings produce; otherwise a BPE tokenizer would spend extra time and vocabulary "merges" on those noisy, redundant null-byte patterns.

### (b) Why per-byte decoding is incorrect

**Question:** Why is `decode_utf8_bytes_to_str_wrong` (which decodes each byte individually) incorrect? Provide an example input that breaks it.

**Example input:** `"こんにちは".encode("utf-8")` → `b'\xe3\x81\x93\xe3\x82\x93\xe3\x81\xab\xe3\x81\xa1\xe3\x81\xaf'`.

**Answer:** Decoding each byte individually fails because multi-byte UTF-8 characters can't be split — each constituent byte (a leading byte like `\xe3` or a continuation byte like `\x81`) is not itself a valid UTF-8 character, so `bytes([b]).decode("utf-8")` raises `UnicodeDecodeError`.

### (c) A two-byte sequence that does not decode

**Question:** Give a two-byte sequence that does not decode to any Unicode character(s).

**Example:** `b"\xc0\xaf"`.

**Answer:** Structurally this looks like a 2-byte lead (`\xc0` = `110 00000`) followed by a continuation byte (`\xaf` = `10 101111`), but stripping the framing bits yields codepoint `0x2F` (`/`), which is ASCII and must be encoded in a single byte; UTF-8 forbids such *overlong encodings*, so the decoder rejects `\xc0` outright as an invalid start byte.
