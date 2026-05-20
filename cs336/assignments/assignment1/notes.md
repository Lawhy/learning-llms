---
title: Assignment 1 — Basics
ready: true
---

Implement a BPE tokenizer and the core transformer building blocks from scratch. Code lives in the [`assignment1-basics`](./assignment1-basics/) submodule; assignment PDF is [`cs336_assignment1_basics.pdf`](./assignment1-basics/cs336_assignment1_basics.pdf).

Tracks the conceptual ground from [[cs336/lectures/lecture_01_overview_tokenization|Lecture 1]] and the engineering primitives from [[cs336/lectures/lecture_02_pytorch_einops_resource_accounting|Lecture 2]].

## Problem 1 — Pre-tokenization chunking

**Question:** Given a large training file, how do we split it across workers without crossing a special-token boundary (e.g., `<|endoftext|>`)?

**Answer:** Pick uniformly-spaced byte offsets as initial chunk boundaries, then nudge each boundary forward to the next occurrence of the special token. The assignment provides a reference implementation:

{{ include: cs336/assignments/assignment1/assignment1-basics/cs336_basics/pretokenization_example.py::find_chunk_boundaries }}

The key invariant: every chunk starts immediately after a special token (or at byte 0), so per-worker pre-tokenization can run independently without re-tokenizing across boundaries.

## Problem 2 — BPE training [stub]

*Not yet attempted. The deliverable is a working `train(corpus, vocab_size) → (vocab, merges)` plus pass `uv run pytest tests/test_train_bpe.py`.*

## Notes

- Tests run with `uv run pytest` inside the submodule directory.
