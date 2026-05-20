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

---

All BPE work lives in a single class, `cs336_basics.bpe.BPETokenizer`. Training is a classmethod (`BPETokenizer.train`) that returns a constructed instance; the same class exposes `encode` / `encode_iterable` / `decode`. Adapters in `tests/adapters.py` are glue — `run_train_bpe` calls `BPETokenizer.train` and unpacks `tok.vocab, tok.merges`; `get_tokenizer` just constructs `BPETokenizer(vocab, merges, special_tokens)`.

## Problem `train_bpe` — BPE Tokenizer Training

<span class="heading-meta">15 points</span>

**Question:** Train a byte-level BPE tokenizer following §2.4–§2.5: initialize the vocab with the 256 single-byte tokens plus the special tokens, pre-tokenize the corpus with the GPT-2 regex (splitting on special tokens first so merges can't span document boundaries), then iteratively merge the most frequent adjacent byte pair until the vocab reaches `vocab_size`. Break frequency ties by preferring the *lexicographically greater* pair.

**Verifying test:** `uv run pytest tests/test_train_bpe.py` &mdash; **passes (3/3)**.

### Pre-tokenization (parallel)

The corpus is split into byte-aligned chunks on occurrences of the first special token (so no chunk slices a document and no merge can span a join), then each chunk is pre-tokenized in its own worker process. Inside a chunk we further split on every special token via `re.split` with `re.escape` to neutralize the regex-meta `|` inside `<|endoftext|>`<sup class="margin-marker"><a href="#note-1">1</a></sup><span class="margin-note" id="note-1"><span class="margin-note__label">Note 1</span>Chunk boundaries only guarantee the chunk *starts* at a special token — a single chunk still contains thousands of them inside it, so the inner `re.split` over the full special-token list is still required.</span>, then iterate the GPT-2 regex over each segment.

Each pre-token is represented as a tuple of **single-byte** `bytes` objects — `tuple(bytes([b]) for b in match.group(0).encode("utf-8"))` — so that every atom exists in the initial 256-byte vocab and merges can build them up.<sup class="margin-marker"><a href="#note-2">2</a></sup><span class="margin-note" id="note-2"><span class="margin-note__label">Note 2</span>The tempting bug is `tuple(c.encode("utf-8") for c in match.group(0))` — but iterating a `str` yields characters, and a non-ASCII char encodes to multiple bytes, producing an atom that doesn't exist in vocab and can never be built from merges.</span>

`_pretokenize_chunk` runs in a worker subprocess and must be **picklable** (it gets shipped to workers via `ProcessPoolExecutor.submit`), so it's a `@staticmethod` rather than a nested function.<sup class="margin-marker"><a href="#note-3">3</a></sup><span class="margin-note" id="note-3"><span class="margin-note__label">Note 3</span>Multiprocessing — not threading or asyncio — is necessary because pre-tokenization is CPU-bound Python (regex scanning + dict updates). Python's GIL serializes threaded CPU work; `asyncio.to_thread` would inherit the same limitation since it dispatches to a thread pool under the hood.</span>

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/bpe.py::BPETokenizer._pretokenize_chunk }}

### Merge loop — incremental pair counts

The merge step maintains **two indices** across iterations rather than recomputing pair statistics from scratch each round:

- `pair_counts[(a, b)]` — current frequency of pair `(a, b)` across the corpus.
- `pair_to_pretokens[(a, b)]` — set of pre-tokens currently containing `(a, b)`. This reverse index makes "which pre-tokens are affected by this merge?" an O(1) lookup.

Each merge iteration follows three phases per affected pre-token: **withdraw → rewrite → register**. Withdraw the old shape's contributions from `pair_counts` and `pair_to_pretokens`; rewrite the pre-token via `_apply_merge`; register the new shape's contributions.

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/bpe.py::BPETokenizer._apply_merge }}

The single-pass scan in `_apply_merge` handles `(b'a', b'b', b'a', b'b')` correctly when merging `(b'a', b'b')`: both occurrences collapse in one pass, instead of producing two competing "merged at one position" variants.

Tie-breaks fall out of Python's tuple comparison: `max(pair_counts, key=lambda p: (pair_counts[p], p))` automatically prefers the lexicographically greater pair when counts are equal, because `bytes` compare lexicographically and tuples compare element-wise.<sup class="margin-marker"><a href="#note-4">4</a></sup><span class="margin-note" id="note-4"><span class="margin-note__label">Note 4</span>Workspace data (`pair_counts`, `pair_to_pretokens`, `pretoken_counts`) lives as locals inside `train()` and is discarded when training finishes — only `vocab` and `merges` make it onto the returned `BPETokenizer` instance. The training scratch is several MB; the durable tokenizer state is a few hundred KB.</span>

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/bpe.py::BPETokenizer.train }}

---

## Problem `train_bpe_tinystories` — BPE Training on TinyStories

<span class="heading-meta">2 points</span>

### (a) Train on TinyStories, vocab 10000

**Question:** Train on TinyStories with `vocab_size=10000`, report time + memory, identify the longest token, and judge whether it makes sense.

**Answer:**

| metric             | value                                  |
|--------------------|----------------------------------------|
| wall time          | **~700 s (11 min 41 s)** on 4 workers  |
| peak process RSS   | **~125 MiB**                            |
| final vocab size   | 10 000 (= 256 bytes + 1 special + 9 743 merges) |
| longest token      | `b' accomplishment'` (15 bytes)         |

The longest token is `' accomplishment'` (with a leading space). It makes sense: TinyStories is moralistic children's stories where words like *accomplishment*, *adventure*, *somewhere*, *important* recur often. The leading space comes from the GPT-2 regex's ` ?\p{L}+` branch, which absorbs the preceding space into each word's pre-token — so most "long" word tokens carry that space prefix.

### (b) Profile: what dominates training time?

**Question:** Profile your code. What part of the tokenizer training process takes the most time?

**Answer:** With the naive merge loop (recount-all-pairs every iteration), the merge loop was 95%+ of wall time and grew as O(N·V) where N = total atom slots and V = vocab_size. After switching to **incremental pair-count updates** with the `pair_to_pretokens` reverse index, the merge loop scales with *affected pre-tokens only* (typically <5% of the corpus per iteration). On the optimized run, pre-tokenization (parallel across 4 workers, ~5 s on the valid set) and the merge loop are roughly comparable; pre-tokenization edges out on small inputs while the merge loop has the larger absolute cost on the full train.<sup class="margin-marker"><a href="#note-5">5</a></sup><span class="margin-note" id="note-5"><span class="margin-note__label">Note 5</span>Structurally, pre-tokenization is embarrassingly parallel (just add workers) while the merge loop is inherently sequential — each merge depends on the previous. So the merge loop is the scaling ceiling for very large vocabs even after the incremental optimization, since multiprocessing can't speed it up.</span>

---

## Problem `train_bpe_expts_owt` — Deferred

<span class="heading-meta">2 points · not yet attempted</span>

Training a vocab-32 000 BPE on OpenWebText (~11 GB corpus) is estimated at ~60–70 min wall-clock with the current implementation — well within the 12-hour budget, but not a priority right now. The speedup work (incremental pair counts, multiprocessing pre-tokenization) is already validated by the TinyStories run, so the marginal *learning* return on this sub-problem is low. The qualitative output difference — what the longest token looks like on internet-scale text vs. children's stories — is the main thing left to observe.

**Plan to revisit** after finishing the TinyStories end-to-end pipeline (transformer training, sampling, perplexity). At that point an OWT-trained tokenizer also becomes the input for any leaderboard submission, which would supply a separate motivation.

---

## Problem `tokenizer` — Implementing the Tokenizer

<span class="heading-meta">15 points</span>

**Question:** Implement a `BPETokenizer` class with `__init__(vocab, merges, special_tokens)`, `encode(text) -> list[int]`, `encode_iterable(stream) -> Iterator[int]`, and `decode(ids) -> str`. Special tokens must be preserved as single units; encoding must produce the canonical priority-based sequence (the one training would have produced).

**Verifying test:** `uv run pytest tests/test_tokenizer.py` &mdash; **passes (24/24 + 1 xpassed)**.

### Splitting on special tokens — two regex recipes for two jobs

`re.split` has two behaviors depending on whether the pattern contains capturing groups:

- **No capturing group** — delimiters are *discarded*. This is what training-time pretokenization wants (special tokens act as hard segmentation boundaries but don't contribute to pair counts).
- **With outer parens** — delimiters are *preserved* as their own elements in the result, interleaved between text segments. This is what `encode` needs, because each special token in the input must emit its own pre-assigned vocab ID.

`BPETokenizer.__init__` builds the encoding-side pattern by wrapping the alternation in `(...)`, and `encode` then checks `if segment in self.special_tokens` to emit the special-token ID directly, bypassing merges.

Special tokens are also **sorted by length descending** before joining. Regex alternation is *leftmost-wins* (not longest-wins), so without sorting a shorter prefix could match before its longer overlapping cousin — e.g. `<|endoftext|>` would eat into `<|endoftext|><|endoftext|>` and produce two separate single-token matches instead of one double-token match. Sorting descending guarantees the longer alternative is tried first.

### Priority-based merge selection

The core of `encode` is a single nested loop. At each step it scans the current sequence's adjacent pairs and applies **the one with the smallest `merge_priorities` value** (= earliest learned during training), not the first one encountered left-to-right. The left-to-right greedy variant is wrong in general — for input `[a, b, c]` with merges `[(b, c), (a, b)]`, greedy yields `[ab, c]` but the priority-based encoder yields `[a, bc]`, which is the sequence training would have produced.<sup class="margin-marker"><a href="#note-6">6</a></sup><span class="margin-note" id="note-6"><span class="margin-note__label">Note 6</span>Priority is by training-iteration order — index 0 in `merges` means "learned first," and that merge must fire first at encode time. Subsequent merges may *depend on* earlier ones (e.g. merge `(ab, c)` can only fire after `(a, b) → ab` has created the atom `ab`). Replaying training order at encode time is the contract between training-time data prep and inference-time input prep — the model only knows the token sequences its tokenizer emits.</span>

The loop terminates at a **fixed point**: when no adjacent pair in the current sequence has a learned merge, we stop. The number of iterations is input-dependent (typically 0–10 for short pretokens), which is why it's a `while True` rather than a fixed-count loop.

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/bpe.py::BPETokenizer.encode }}

### Streaming via `encode_iterable`

`encode_iterable` is a one-liner: `for chunk in iterable: yield from self.encode(chunk)`. Memory-efficient for large files because only one chunk is held at a time. The corresponding memory test (`test_encode_iterable_memory_usage`, ≤1 MB budget) passes; the analogous test for non-streaming `encode` is marked `xfail` in the suite because plain `encode` materializes the whole text in memory.

### Decoding

`decode` is also a one-liner: concatenate the vocab bytes for each id and `.decode("utf-8", errors="replace")`. The `errors="replace"` is necessary because a user can construct arbitrary ID sequences whose bytes don't form valid UTF-8 — those positions become `U+FFFD` instead of raising.

---

## Problem `tokenizer_experiments` — Deferred

<span class="heading-meta">4 points · not yet attempted</span>

The four sub-parts ask for compression ratios on TinyStories and OWT samples, a cross-tokenizer "what happens if you tokenize OWT with the TinyStories tokenizer?" experiment, a throughput estimate (bytes/sec → Pile extrapolation), and encoding the TinyStories+OWT train/dev datasets to integer-ID files. Three of the four depend on having both tokenizers trained; with OWT [deferred](#problem-train_bpe_expts_owt-deferred), this whole problem rides along.

**Plan to revisit** alongside the OWT BPE training. The throughput estimate (c) and the cross-tokenizer (b) sub-parts are quick once OWT exists.
