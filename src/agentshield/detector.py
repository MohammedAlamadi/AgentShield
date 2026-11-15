"""Layer 1 - prompt-injection detector (D1 Section III-C-1).

protectai/deberta-v3-base-prompt-injection-v2, used as released (no training or fine-tuning),
on CPU, pinned to a fixed Hugging Face revision. Labels verified on 13 Nov 2026:
{0: "SAFE", 1: "INJECTION"}.

Long inputs (our own addition, D1): the model has 512 position embeddings, but the
tokenizer sets no length limit, so an un-truncated pipeline would silently score text past
the trained length. Each output is therefore tokenised once and split into consecutive
windows of 510 content tokens (+[CLS]/[SEP] = 512), with a 128-token overlap so an
instruction that straddles a boundary still appears whole in at least one window. The
output is flagged if ANY window has P(INJECTION) >= threshold; the whole output is then
quarantined by the agent loop.
"""

from __future__ import annotations

import os
import time

from .agent import DetectorResult

MODEL_ID = "protectai/deberta-v3-base-prompt-injection-v2"
REVISION = "90c9989b1a342275dd0d1a95aad283c04e075671"
INJECTION_LABEL = "INJECTION"
MAX_TOKENS = 512
WINDOW = MAX_TOKENS - 2  # room for [CLS] and [SEP]
OVERLAP = 128


def chunk_token_ids(ids: list[int], window: int = WINDOW, overlap: int = OVERLAP) -> list[list[int]]:
    """Split token ids into consecutive overlapping windows. Empty input gives one empty window."""
    if window <= overlap:
        raise ValueError("window must be larger than overlap")
    if len(ids) <= window:
        return [ids]
    step = window - overlap
    chunks = []
    start = 0
    while True:
        chunks.append(ids[start : start + window])
        if start + window >= len(ids):
            return chunks
        start += step


class InjectionDetector:
    def __init__(self, threshold: float = 0.5, batch_size: int = 8) -> None:
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.threshold = threshold
        self.batch_size = batch_size
        self._torch = torch
        load = dict(revision=REVISION)
        try:  # prefer the local cache so demos work offline
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, local_files_only=True, **load)
            self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, local_files_only=True, **load)
        except OSError:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, **load)
            self.model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, **load)
        self.model.to("cpu").eval()
        labels = {v.upper(): k for k, v in self.model.config.id2label.items()}
        if INJECTION_LABEL not in labels:
            raise RuntimeError(f"unexpected detector labels {self.model.config.id2label}")
        self.injection_index = labels[INJECTION_LABEL]
        if self.model.config.max_position_embeddings != MAX_TOKENS:
            raise RuntimeError("detector max_position_embeddings changed; re-check the chunking strategy")
        self.screen("warm-up")  # first call is slower; keep it out of measurements

    def info(self) -> dict:
        return {"model": MODEL_ID, "revision": REVISION, "threshold": self.threshold, "device": "cpu",
                "window_tokens": WINDOW, "overlap_tokens": OVERLAP, "labels": self.model.config.id2label}

    def injection_probabilities(self, text: str) -> list[float]:
        torch = self._torch
        ids = self.tokenizer(text, add_special_tokens=False)["input_ids"]
        chunks = chunk_token_ids(ids)
        cls, sep, pad = self.tokenizer.cls_token_id, self.tokenizer.sep_token_id, self.tokenizer.pad_token_id
        probs: list[float] = []
        for i in range(0, len(chunks), self.batch_size):
            batch = [[cls, *c, sep] for c in chunks[i : i + self.batch_size]]
            width = max(len(b) for b in batch)
            input_ids = torch.tensor([b + [pad] * (width - len(b)) for b in batch])
            attention = torch.tensor([[1] * len(b) + [0] * (width - len(b)) for b in batch])
            with torch.no_grad():
                logits = self.model(input_ids=input_ids, attention_mask=attention).logits
            probs.extend(torch.softmax(logits, dim=-1)[:, self.injection_index].tolist())
        return probs

    def screen(self, text: str) -> DetectorResult:
        t0 = time.perf_counter()
        probs = self.injection_probabilities(text)
        seconds = time.perf_counter() - t0
        top = max(probs)
        flagged = top >= self.threshold
        return DetectorResult(
            flagged=flagged,
            max_score=round(top, 6),
            chunk_scores=[round(p, 6) for p in probs],
            n_chunks=len(probs),
            seconds=round(seconds, 4),
            label=INJECTION_LABEL if flagged else "SAFE",
        )
