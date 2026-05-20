---
title: Lecture 1 — Overview & Tokenization
ready: true
---

Course intro + the tokenization problem: how do we turn a byte stream into the discrete units a transformer consumes?

Slides: [`slides.pdf`](./slides.pdf)

## Why tokenization is non-trivial

Bytes are too fine-grained (long sequences, wasted compute on common prefixes); words are too coarse (open vocabulary, brittle to morphology and non-Latin scripts). The compromise is **subword tokenization** — units that are common-substring-frequent in the training corpus.

The standard choice in modern LLMs is **Byte-Pair Encoding (BPE)**, which greedily merges the most frequent adjacent token pair until a target vocabulary size is reached.

## A bit of math: compression ratio

Given a corpus of $N$ bytes encoded into $T$ tokens by a tokenizer, the **compression ratio** is

$$ r = \frac{N}{T} $$

Higher $r$ means a token "carries" more bytes on average — a proxy for vocabulary efficiency. Typical BPE vocabularies achieve $r \approx 4$ on English text.

## Where this connects

- The next lecture, [[cs336/lectures/lecture_02_pytorch_einops_resource_accounting]], grounds these abstractions in PyTorch and starts the resource-accounting habit (FLOPs, bytes, latency).
- The first hands-on is [[cs336/assignments/assignment1|Assignment 1]], which has you implement a BPE tokenizer from scratch.

## Open questions

- How sensitive are downstream metrics to tokenizer choice when vocabulary size is held constant?
- What does tokenizer-induced bias look like for multilingual corpora — and can it be measured without training a full model?
