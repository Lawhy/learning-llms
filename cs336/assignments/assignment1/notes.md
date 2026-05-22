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

All BPE work<sup class="margin-marker"><a href="#note-7">7</a></sup><span class="margin-note" id="note-7"><span class="margin-note__label">Note 7</span>For the comprehensive distilled writeup &mdash; mental model, worked example, and engineering choices &mdash; see <a href="https://yuanhe.wiki/posts/technical/bpe/">Byte-Pair Encoding (BPE)</a> on the blog. These notes stay focused on the assignment deliverables.</span> lives in a single class, `cs336_basics.bpe.BPETokenizer`. Training is a classmethod (`BPETokenizer.train`) that returns a constructed instance; the same class exposes `encode` / `encode_iterable` / `decode`. Adapters in `tests/adapters.py` are glue — `run_train_bpe` calls `BPETokenizer.train` and unpacks `tok.vocab, tok.merges`; `get_tokenizer` just constructs `BPETokenizer(vocab, merges, special_tokens)`.

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

---

## Problem `linear` — Implementing the Linear Module

<span class="heading-meta">1 point</span>

**Question:** Implement a biasless `Linear` module subclassing `nn.Module` with interface `(in_features, out_features, device=None, dtype=None)`. Store the weight as $W$ of shape `(out_features, in_features)` (not $W^\top$), initialize with truncated normal $\mathcal{N}(0, \sigma^2 = \frac{2}{d_\text{in} + d_\text{out}})$ clipped to $[-3\sigma, 3\sigma]$.

**Verifying test:** `uv run pytest -k test_linear` &mdash; **passes (1/1)**.

### Storage shape vs. math shape

The handout's math is column-vector ($y = Wx$ with $W$ of shape `(d_out, d_in)`), but PyTorch tensors are row-major and we batch by adding leading dims, not by stacking columns. The parameter is stored in the column-vector shape `(out_features, in_features)` and `forward` contracts the trailing axis of `x` against the trailing axis of `W` — equivalent to $Y = X W^\top$ for the row-vector convention.

### einops vs. torch native

The primary `forward` uses `einops.einsum` with named multi-character axes:

```
einsum(x, self.weight, "... d_in, d_out d_in -> ... d_out")
```

The names make the contraction self-documenting at the cost of one extra dependency. For a single matmul this is overkill, but it's worth practising the notation here so the multi-head attention shapes later don't become unreadable.<sup class="margin-marker"><a href="#note-8">8</a></sup><span class="margin-note" id="note-8"><span class="margin-note__label">Note 8</span>`torch.einsum` only supports single-character labels, e.g. `"...i,oi->...o"` — terse but cryptic past 3–4 axes. `einops` dispatches to the same underlying primitive, so the performance is identical; the difference is purely ergonomic.</span>

`_forward` documents the torch-native equivalent (`x @ self.weight.T` or `torch.einsum("...i,oi->...o", x, self.weight)`) — kept for reference, not called by the test.

### Initialization — σ vs. σ²

The handout gives the *variance* $\sigma^2 = \frac{2}{d_\text{in} + d_\text{out}}$, but `trunc_normal_(std=...)` takes the *standard deviation*, so the code computes $\sigma = \sqrt{2/(d_\text{in} + d_\text{out})}$. The truncation bounds `a`, `b` must also be passed explicitly as $\pm 3\sigma$ — the function's defaults are $[-2, 2]$, which would not clip this very narrow distribution at all.<sup class="margin-marker"><a href="#note-9">9</a></sup><span class="margin-note" id="note-9"><span class="margin-note__label">Note 9</span>This is the Xavier/Glorot scheme with the gain factor of 2 used by GPT-2 / Llama. Truncating at $\pm 3\sigma$ rejects ≈0.27% of samples in the tails — enough to prevent rare extreme inits from kicking off exploding/vanishing activations in deep stacks.</span>

### Device/dtype plumbing

`device` and `dtype` flow straight into `torch.empty(...)` so the `Parameter` lands on the right device with the right precision the moment it's constructed. This pattern repeats for every module that holds learned weights; getting the shape of the constructor right once propagates through `Embedding`, `RMSNorm`, the FFN, attention, and the full Transformer block.

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/linear.py::Linear }}

---

## Problem `embedding` — Implementing the Embedding Module

<span class="heading-meta">1 point</span>

**Question:** Implement a custom `Embedding` module subclassing `nn.Module` with interface `(num_embeddings, embedding_dim, device=None, dtype=None)`. Store the embedding matrix as a `Parameter` of shape `(num_embeddings, embedding_dim)`. `forward(token_ids)` returns the embedding vectors for the given integer IDs (with any leading batch shape preserved).

**Verifying test:** `uv run pytest -k test_embedding` &mdash; **passes (1/1)**.

### An embedding is a one-hot times a weight matrix — implemented as a gather

Mathematically, the embedding for token $t$ is $e_t^\top W$, where $e_t$ is the one-hot vector with a 1 at index $t$. The whole forward could in principle be written as an einsum `"... v, v d -> ... d"` on the one-hot representation — and that's exactly the dual of what the **output projection** at the top of the Transformer will do (`logits = hidden @ W^\top`), which is why weight-tying between input embedding and output projection is sometimes used.<sup class="margin-marker"><a href="#note-10">10</a></sup><span class="margin-note" id="note-10"><span class="margin-note__label">Note 10</span>Materializing a one-hot tensor of shape `(batch, seq, vocab_size)` wastes O(V) memory and FLOPs per token to return a result identical to a single memory read. Modern GPUs have fast gather instructions; integer indexing routes straight to them.</span>

In practice the forward is a one-liner that exploits PyTorch's advanced indexing — `self.weight[token_ids]` broadcasts the lookup across any leading shape, so input of shape `(batch, seq)` returns output of shape `(batch, seq, embedding_dim)`.

### Initialization — different from Linear

The handout (§3.3.1) gives each module type a different init. `Linear` uses Xavier $\sigma^2 = 2/(d_\text{in}+d_\text{out})$; `Embedding` uses **plain $\sigma=1$ truncated at $\pm 3$**. The narrow Xavier σ that's correct for Linear would push embedding vectors to essentially zero for a 50 000-token vocab, which would starve the downstream RMSNorm and attention layers calibrated for unit-variance inputs.

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/embedding.py::Embedding }}

---

## Problem `rmsnorm` — Root Mean Square Layer Normalization

<span class="heading-meta">1 point</span>

**Question:** Implement `RMSNorm` as a `torch.nn.Module` with interface `(d_model, eps=1e-5, device=None, dtype=None)`. `forward(x)` rescales each activation by $\text{RMSNorm}(a_i) = \frac{a_i}{\text{RMS}(a)} g_i$ where $\text{RMS}(a) = \sqrt{\tfrac{1}{d_\text{model}}\sum_i a_i^2 + \varepsilon}$. Upcast to `float32` before computing RMS to avoid overflow when squaring, then downcast the result to the input dtype.

**Verifying test:** `uv run pytest -k test_rmsnorm` &mdash; **passes (1/1)**.

### Why RMS as the normalizing term

> Normalize like L2, but with a zero-mean assumption and a $\sqrt{d}$ rescale so each component lands at $\mathcal{O}(1)$.

Three observations packed into one formula. **(1) Like L2** — Euclidean / rotation-invariant magnitude is the only kind that's basis-independent, which matters because linear layers freely rotate features through the residual stream. **(2) Zero-mean assumption** — LayerNorm subtracts the mean first; RMSNorm skips it because trained residual streams have $\mu \approx 0$ anyway, and any leftover constant offset gets absorbed by the next layer's bias. **(3) Per-component $\mathcal{O}(1)$** — pure L2 normalization would put each component at $\mathcal{O}(1/\sqrt{d})$, which downstream attention/FFN layers aren't calibrated for; dividing by RMS (which already has the $1/\sqrt{d}$ baked in) restores unit per-component scale.

### RMSNorm is element-wise; only the RMS itself reduces

The shape story is the whole problem: the normalization is element-wise across `d_model`, but the RMS *scalar* is computed by reducing across `d_model`. So the forward has three shape regimes layered on top of each other:

| quantity | shape | computed by |
|----------|-------|-------------|
| sum-of-squares | `(...,)` | einsum `"... d_model, ... d_model -> ..."` (drops `d_model`) |
| RMS | `(..., 1)` | sqrt of mean + eps, then `.unsqueeze(-1)` to restore the broadcast slot |
| `x / RMS` | `(..., d_model)` | broadcast over the size-1 trailing axis |
| `(x / RMS) * weight` | `(..., d_model)` | broadcast `(d_model,)` against `(..., d_model)` |

The `.unsqueeze(-1)` matters because PyTorch broadcasting aligns from the right — without it, `(B, T) / (B, T, D)` would try to match `T` against `D` and error.<sup class="margin-marker"><a href="#note-11">11</a></sup><span class="margin-note" id="note-11"><span class="margin-note__label">Note 11</span>Equivalent alternative: `(x ** 2).mean(dim=-1, keepdim=True)` — the `keepdim=True` flag preserves a size-1 axis at the reduction position, accomplishing the same broadcasting setup without an explicit `unsqueeze`. Einsum has no `keepdim` knob, so the unsqueeze is the einsum-friendly path.</span>

### Why upcast to float32

If `x` is float16 with values near $\pm 1$, squaring gives ${\sim}1$ — fine. But if any activation has magnitude $\gg 1$ (which happens early in training before RMSNorm has stabilized things), squaring can overflow float16's $\pm 65504$ range and produce `inf`, which then poisons the sum, the sqrt, and every downstream activation. Promoting to float32 for the RMS computation costs negligible compute and avoids a class of silent training divergences.<sup class="margin-marker"><a href="#note-12">12</a></sup><span class="margin-note" id="note-12"><span class="margin-note__label">Note 12</span>RMSNorm is one of three places where the standard advice is "upcast then downcast" — the others are the softmax inside attention (denominator overflow) and the final logits (cross-entropy expects float32 for numerical stability). The pattern is the same: localize the float32 calculation, restore the caller's dtype on return.</span>

### Why the gain is initialized to 1

The handout (§3.3.1) lists `RMSNorm: 1` — the gain vector starts at all ones, not Xavier-scaled. At initialization, RMSNorm is the identity map (scaled by unit RMS), so signal passes through untouched. The `g_i` parameters only deviate from 1 if training discovers per-dimension scale corrections actually help — which in practice they barely do, so the gain stays close to 1 throughout. This is a common pattern for normalization layers: a learnable rescaler that defaults to "no rescaling" and rarely strays far.

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/rms_norm.py::RMSNorm }}

---

## Problem `positionwise_feedforward` — SwiGLU FFN

<span class="heading-meta">2 points</span>

**Question:** Implement the position-wise feed-forward network as SwiGLU:

$$\text{FFN}(x) = W_2\big(\text{SiLU}(W_1 x) \odot W_3 x\big), \qquad \text{SiLU}(x) = x \cdot \sigma(x)$$

with $W_1, W_3 \in \mathbb{R}^{d_\text{ff} \times d_\text{model}}$, $W_2 \in \mathbb{R}^{d_\text{model} \times d_\text{ff}}$, no biases, and $d_\text{ff} \approx \tfrac{8}{3} d_\text{model}$ rounded to a multiple of 64.

**Verifying test:** `uv run pytest -k test_swiglu` &mdash; **passes (1/1)**. (And the standalone `test_silu_matches_pytorch` also passes via the `silu` helper.)

### Design intuition

The original Transformer FFN was a single stream — *up-project, ReLU, down-project*. SwiGLU restructures this into two **parallel** up-projections that combine *multiplicatively* before being projected back down:

| | Vanilla FFN | SwiGLU |
|--|--|--|
| Functional form | $W_2 \cdot \text{ReLU}(W_1 x)$ | $W_2 \cdot (\text{SiLU}(W_1 x) \odot W_3 x)$ |
| Per-feature computation | Pointwise nonlinear | Bilinear (gate × value) |
| Matrices | 2 | 3 |

The extra matrix isn't free expressiveness — it's a *structural change* in how features combine. Each output feature is now a sum of `d_ff` terms of the form $(\text{gated activation}) \cdot (\text{linear value})$ rather than just $\text{nonlinear}(\text{linear})$.

### The gating lens

The Hadamard product $\text{SiLU}(W_1 x) \odot W_3 x$ implements **conditional computation**: the gate ($\text{SiLU}(W_1 x)$, roughly sigmoid-shaped) decides *whether* each value-stream feature is relevant in this context, and the value ($W_3 x$) provides the *magnitude/direction*. This decouples "is this pattern present?" from "with what strength?" — a vanilla ReLU FFN has to encode both signals in one scalar per neuron.

The same gating principle appears in LSTM forget gates, attention's softmax weighting, mixture-of-experts routing, and highway networks.<sup class="margin-marker"><a href="#note-13">13</a></sup><span class="margin-note" id="note-13"><span class="margin-note__label">Note 13</span>One mechanistic interpretability lens: each FFN neuron acts like a key-value memory. Vanilla FFN gives each neuron *one* key (the ReLU detector). SwiGLU gives each neuron *two* keys — a gate detector and a value detector — so detection and magnitude can be encoded independently. This is hand-wavy but matches the empirical observation that gated FFNs reliably outperform non-gated ones by 1–2% on perplexity.</span> SwiGLU is the smallest version of "compute something AND decide how much it matters" applied inside a feedforward block.

### Why the magic 8/3

Total parameter counts in the two FFN forms:

- **Vanilla**, $d_\text{ff} = 4 d_\text{model}$: two matrices of size $4 d_\text{model}^2$ → **$8 d_\text{model}^2$ total**.
- **SwiGLU**, $d_\text{ff} = \tfrac{8}{3} d_\text{model}$: three matrices of size $\tfrac{8}{3} d_\text{model}^2$ → **$8 d_\text{model}^2$ total**.

The factor $\tfrac{8}{3}$ is the unique rescaling that swaps a ReLU FFN for SwiGLU at **identical parameter cost**.<sup class="margin-marker"><a href="#note-14">14</a></sup><span class="margin-note" id="note-14"><span class="margin-note__label">Note 14</span>Rounding to a multiple of 64 aligns with GPU tensor-core preferences — e.g. $\tfrac{8}{3} \cdot 4096 = 10923$ rounded becomes $10944 = 171 \cdot 64$. This is a hardware optimization, not a learning argument; the model trains fine at the unrounded value, just slightly slower.</span> No extra capacity, but reshaped into the gate-value-down structure.

### Why SiLU over ReLU

Three properties: (1) **smooth at 0** — differentiable everywhere, no kink → smoother loss landscape; (2) **non-monotonic** — small negative dip around $x = -1$ that the network can use; (3) **self-gating** — $x \cdot \sigma(x)$ already has a gate-like shape built in, so SwiGLU effectively stacks gates within gates. GELU (BERT/GPT-2's choice) is qualitatively similar; SiLU is slightly cheaper.

### What the network gains, empirically

The headline result from Shazeer's original paper: SwiGLU outperforms ReLU FFN by ~1–2% on language modeling perplexity at matched parameter count, across model scales. Llama, PaLM, Gemma, Mistral all use it. The improvement is small but reliable — large enough to justify the structural complexity, small enough that Shazeer himself wrote:

> "We offer no explanation as to why these architectures seem to work; we attribute their success, as all else, to divine benevolence."

The architecture works; the precise reason is still debated.

### Implementation notes

`SwiGLU` is composed from three of our existing `Linear` submodules — no manual `nn.Parameter` plumbing needed. The init formula falls out automatically: each `Linear` sees its own `(in_features, out_features)` pair and applies the truncated Xavier the handout prescribes, with $\sigma$ identical across all three matrices (they share the same $d_\text{in} + d_\text{out} = d_\text{model} + d_\text{ff}$).

`SiLU` is a top-level function rather than an `nn.Module` because it has no parameters and isn't reused as a sub-component anywhere else; making it a Module would add ceremony without benefit. `torch.sigmoid` is used directly per the handout's note (numerical stability — don't roll your own).<sup class="margin-marker"><a href="#note-15">15</a></sup><span class="margin-note" id="note-15"><span class="margin-note__label">Note 15</span>Two structural symmetries make the forward a one-liner: (1) both gate ($W_1 x$) and value ($W_3 x$) branches produce tensors of identical shape `(..., d_ff)`, so the Hadamard product is direct; (2) `d_ff` is the caller's responsibility — the module takes it as a constructor arg rather than computing $\tfrac{8}{3} d_\text{model}$ internally, which keeps the "round to a multiple of 64" hardware tweak out of the model code.</span>

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/swiglu.py::SwiGLU }}

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/swiglu.py::silu }}

---

## Problem `rope` — Rotary Position Embeddings

<span class="heading-meta">2 points</span>

**Question:** Implement `RotaryPositionalEmbedding` that injects positional information by *rotating* each query/key vector in pre-computed 2D subspaces. The rotation angle per subspace depends on the token's position and a frequency schedule $\theta_{i,k} = i / \Theta^{(2k-2)/d_k}$. Layer has **no learnable parameters** — cosines/sines are precomputed as buffers.

Interface:

```python
def __init__(self, theta: float, d_k: int, max_seq_len: int, device=None)
def forward(self, x: Float[Tensor, "... seq_len d_k"], token_positions: Int[Tensor, "... seq_len"]) -> Float[Tensor, "... seq_len d_k"]
```

**Verifying test:** `uv run pytest -k test_rope` &mdash; **passes (1/1)**.

### The problem RoPE solves

Self-attention is **permutation-invariant by default**: $\text{Attention}(QKV)$ on $[\text{cat}, \text{sat}, \text{on}]$ gives the same scores as on $[\text{sat}, \text{on}, \text{cat}]$ if you reorder consistently. Language is *not* permutation-invariant — "the dog bit the man" $\neq$ "the man bit the dog." So we need to inject **token positions** somewhere into the computation.

The original Transformer added a positional encoding to the embeddings ($x_i \leftarrow x_i + p_i$). That works but has two issues:
1. The position information has to *survive* every layer, while being slowly overwritten by the residual stream's content updates.
2. The model has to learn that "$p_3 - p_1$ means 2 positions apart" — relative position is encoded *implicitly* and indirectly.

RoPE's trick: **apply position as a rotation, not as an addition**, and apply it inside attention's $Q$ and $K$ specifically (not to the residual stream at all). The geometry makes the attention dot product depend *only on the relative position* between query and key — which is exactly what language modeling wants.

### Worked example: the simplest possible case ($d_k = 2$)

Take the smallest interesting query/key dim: $d_k = 2$. Suppose two tokens have *identical* content vectors but live at different positions:

$$q = \begin{bmatrix} 1 \\ 0 \end{bmatrix} \text{ at position } i = 1, \qquad k = \begin{bmatrix} 1 \\ 0 \end{bmatrix} \text{ at position } j = 3.$$

**Without positional encoding**, $q^\top k = 1$ — attention can't tell these tokens apart by position.

**With RoPE**, rotate each vector by an angle proportional to its position. Use $\theta = 30°$ per position step (so position 1 → $30°$, position 3 → $90°$). The 2D rotation matrix is:

$$R(\theta) = \begin{bmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{bmatrix}$$

Rotate $q$ by $30°$ and $k$ by $90°$:

$$R(30°) q = \begin{bmatrix} 0.866 \\ 0.5 \end{bmatrix}, \qquad R(90°) k = \begin{bmatrix} 0 \\ 1 \end{bmatrix}.$$

Their dot product:

$$\big(R(30°) q\big)^\top \big(R(90°) k\big) = 0.866 \cdot 0 + 0.5 \cdot 1 = 0.5 = \cos(60°).$$

**The result is $\cos$ of the relative angle** — and $60° = 90° - 30°$ is determined entirely by the position *difference* $j - i = 2$ steps. The absolute positions $i = 1$ and $j = 3$ never appear in the answer.

### Why the dot product is purely relative

The algebra behind the example. For any rotation matrices, $R(\alpha)^\top R(\beta) = R(\beta - \alpha)$. So:

$$\big(R(\theta_i) q\big)^\top \big(R(\theta_j) k\big) = q^\top R(\theta_i)^\top R(\theta_j) k = q^\top R(\theta_j - \theta_i) k.$$

The post-rotation dot product equals $q^\top \cdot (\text{rotation by relative angle}) \cdot k$. Absolute angles cancel. This is the **single mathematical property** that makes RoPE work as a positional encoding.

A nice consequence: $\|R(\theta) v\| = \|v\|$ for any $\theta$ — rotations preserve magnitude. So RoPE doesn't change the scale of $q$ or $k$, which means it doesn't perturb attention's scaling assumptions ($\sqrt{d_k}$ denominator).<sup class="margin-marker"><a href="#note-16">16</a></sup><span class="margin-note" id="note-16"><span class="margin-note__label">Note 16</span>Compare to the additive sinusoidal scheme: adding $p_i$ to $x_i$ changes the magnitude of $x_i$ unpredictably (sometimes amplifying, sometimes cancelling), and the relative-position property only holds approximately. RoPE's magnitude-preserving rotation is structurally cleaner.</span>

### Extending to $d_k > 2$: block-diagonal rotation

Real query/key vectors are much wider — typically $d_k = 64$ or $128$. The trick is to **decompose the $d_k$-dim vector into $d_k/2$ independent 2D pairs**, each rotated in its own 2D subspace by its own angle:

$$R^i = \begin{pmatrix} R^i_1 & 0 & \cdots & 0 \\ 0 & R^i_2 & \cdots & 0 \\ \vdots & & \ddots & \vdots \\ 0 & 0 & \cdots & R^i_{d/2} \end{pmatrix}$$

Each $R^i_k$ is a 2D rotation block of the form shown above, applied to the $k$-th pair of consecutive dimensions $(x_{2k-1}, x_{2k})$. The relative-angle dot-product property holds **per pair** and therefore for the sum over all pairs — so the full $d_k$-dim dot product also depends only on relative position (linearly combined across $d_k/2$ frequencies).

### The frequency schedule: why each pair gets a different rate

Each pair $k$ uses a different angular speed:

$$\theta_{i,k} = \frac{i}{\Theta^{(2k-2)/d_k}}, \qquad \text{where } \Theta = 10\,000 \text{ typically}.$$

For pair $k = 1$ the denominator is $\Theta^0 = 1$, so the angle is just $i$ — **one full revolution every $2\pi$ position steps** (fast rotation, captures *local* position).

For pair $k = d_k/2$ the denominator is $\Theta^{(d_k - 2)/d_k} \approx \Theta$, so the angle is $i / \Theta \approx i / 10000$ — **one full revolution every $20\,000 \cdot \pi$ position steps** (slow rotation, captures *long-range* position).

#### Worked frequency example ($d_k = 4$, $\Theta = 10\,000$)

Two pairs, two frequencies. Let's tabulate angles at a few positions:

| position $i$ | pair 1 angle ($\Theta^0 = 1$) | pair 2 angle ($\Theta^{1} \approx 100$) |
|---|---|---|
| 1 | 1 rad ≈ 57° | 0.01 rad ≈ 0.57° |
| 10 | 10 rad ≈ 573° (almost 2 revolutions) | 0.1 rad ≈ 5.7° |
| 100 | 100 rad (≈ 16 full revolutions) | 1 rad ≈ 57° |
| 1000 | 1000 rad (essentially scrambled) | 10 rad ≈ 573° |

Pair 1 rotates so fast that it's already "wrapping around" at position 10. Pair 2 rotates slowly enough that even at position 100 it has only made one revolution. The model gets **multi-scale positional information**: high-frequency pairs distinguish close neighbors, low-frequency pairs distinguish far-apart tokens.

This is identical in spirit to the original sinusoidal positional encoding — a Fourier-like basis over position — but applied as a *rotation* rather than an *addition*.<sup class="margin-marker"><a href="#note-17">17</a></sup><span class="margin-note" id="note-17"><span class="margin-note__label">Note 17</span>The base $\Theta = 10\,000$ is tunable. Llama 1/2 used 10 000; long-context Llama 3 raised it (sometimes to 500 000+) to spread the low-frequency pairs across a wider position range, which is the simplest "context extension" trick. Larger $\Theta$ → longer effective context.</span>

#### Why this gives *multi-scale* position resolution

The previous table looks at absolute angles, but attention reads position information through the *dot product* $q_i^\top R(\Delta\theta) k_j$ — what actually matters is the **angle difference** $\Delta\theta_{i \to j, k} = (j - i) \cdot \text{freq}_k$, not the absolute angle of either token. So each pair encodes a particular **range of position differences**, and its informativeness drops off outside that range:

| $\Delta\theta$ value | What attention sees |
|---|---|
| Near 0 ($\Delta\theta \ll 1$) | $\cos\Delta\theta \approx 1$ — looks like no position offset |
| Around 1 to $\pi$ rad | Informative — distinguishable signal |
| Past $\pi$, wrapping toward $2\pi$ | Aliasing — distant positions collide with closer ones |

The "sweet spot" for each pair is where $\Delta\theta$ lands in the middle range. For $d_k = 8$, $\Theta = 10\,000$ (frequencies $[1, 0.1, 0.01, 0.001]$):

| $\|j - i\|$ | pair 1 (freq 1) | pair 2 (freq 0.1) | pair 3 (freq 0.01) | pair 4 (freq 0.001) |
|---|---|---|---|---|
| 1 | **clear** (1 rad) | small (0.1) | tiny | invisible |
| 10 | wrapped — noisy | **clear** (1 rad) | small | tiny |
| 100 | noise | wrapped — noisy | **clear** (1 rad) | small |
| 1000 | noise | noise | wrapped — noisy | **clear** (1 rad) |

Each pair's sweet spot sits one decade slower than the previous: pair 1 distinguishes immediate neighbors, pair 4 distinguishes positions roughly a thousand apart. Combined, the $d_k/2$ pairs give a **logarithmically spaced Fourier basis over position differences** — fine resolution locally, coarse resolution at long range, with each frequency band handling its own scale.<sup class="margin-marker"><a href="#note-18">18</a></sup><span class="margin-note" id="note-18"><span class="margin-note__label">Note 18</span>This is why "smaller angle diff per position step" enables longer-range encoding: it lets the slow pair's sweet spot extend out to position differences in the thousands without wrapping. Raising $\Theta$ slides every pair's sweet spot further out, which is the geometric reason the $\Theta$ trick extends usable context length.</span>

### Implementation strategy

Three pieces:

1. **Precompute** the $\cos$ and $\sin$ tables of shape $(\text{max\_seq\_len}, d_k/2)$ in `__init__`. Each entry is $\cos\theta_{i,k}$ / $\sin\theta_{i,k}$ for token position $i$, pair index $k$. Store with `self.register_buffer("cos", ..., persistent=False)` — buffers are part of the module's device/dtype tree but **not** parameters and **not** saved to state_dict.

2. **Look up** by `token_positions` in `forward`. The input `x` has shape `(..., seq_len, d_k)`. Split the last dim into pairs (shape `(..., seq_len, d_k/2, 2)` if reshape, or grab even/odd entries directly), then index the precomputed cos/sin tables by `token_positions` to get rotation factors of matching shape.

3. **Apply the 2D rotation pairwise**:
   $$\begin{aligned} x'_{2k-1} &= x_{2k-1} \cos\theta_{i,k} - x_{2k} \sin\theta_{i,k} \\ x'_{2k} &= x_{2k-1} \sin\theta_{i,k} + x_{2k} \cos\theta_{i,k} \end{aligned}$$

   This is just the 2D rotation matrix multiplication applied element-wise across all pairs and positions. No `nn.Parameter` anywhere.

### Why precompute, why a buffer

- **No learnable params** — the rotation angles are *deterministic functions of position*, not learned. The PDF is explicit: don't use `nn.Parameter`, use `register_buffer(persistent=False)`.
- **`persistent=False`** — the buffer doesn't get saved/loaded by `state_dict`. Since it's fully reconstructible from `theta`, `d_k`, and `max_seq_len`, there's no point persisting it. (It would also blow up checkpoint size for long context.)
- **Single RoPE module shared across all layers** — every Transformer block applies the same rotation rules to its $Q$ and $K$. The PDF suggests a single module referenced by all layers, which makes the precompute amortize across the whole model.

### Convention gotcha: adjacent-pair vs. halved-pair layout

A subtle bug worth knowing about: the *math* of RoPE is layout-agnostic at the attention dot-product level (Q^⊤K is just $\sum_i Q_i K_i$, which doesn't care how pair components are arranged in $d_k$), but the *element-wise output tensor* is layout-specific. Two valid conventions in the literature:

| Convention | Pair $k$ contains... | Output assembly |
|---|---|---|
| **Adjacent-pair** (PDF, Su et al. original) | $(x_{2k}, x_{2k+1})$ — consecutive dims | Interleave rotated halves: `stack(..., dim=-1).flatten(-2)` |
| **Halved-pair** (Llama, GPU-friendly) | $(x_k, x_{k+d_k/2})$ — first half + second half | Concatenate rotated halves: `cat(..., dim=-1)` |

The implementation here uses adjacent-pair (matching the PDF). A *consistent* halved-pair implementation would also work — and would produce identical attention scores in a self-contained model — but it would fail this assignment's test (which compares element-by-element against an adjacent-pair reference) and break compatibility with Llama-format pretrained weights.<sup class="margin-marker"><a href="#note-19">19</a></sup><span class="margin-note" id="note-19"><span class="margin-note__label">Note 19</span>The trap: splitting with adjacent indexing (`::2`, `1::2`) but assembling with halved concatenation (`torch.cat`) produces a *hybrid* layout that matches neither standard. The rotations are mathematically correct but the output ordering is non-standard — element-wise wrong, but dot-product correct if used end-to-end. The lesson: tensor layout is part of the contract between modules. Two equivalent maths produce different bytes; the test enforces canonical bytes.</span>

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/rope.py::RoPE }}
