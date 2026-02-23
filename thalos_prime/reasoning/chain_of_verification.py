"""Chain of Verification engine — Data Plane component.

Implements the three-step verification protocol:
  1. Decompose candidate answer into atomic claims (sentences).
  2. Verify each claim against the knowledge graph.
  3. Retract unverified claims and reassemble the final answer.
"""

from __future__ import annotations

import json
import re
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

from thalos_prime.graph_rag.knowledge_graph import KnowledgeGraph
from thalos_prime.reasoning.schema import (
    REASONING_SCHEMA_VERSION,
    VerificationClaim,
    VerificationResult,
)

# Sentence boundary pattern
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.?!])\s+")

# Simple tokenizer for key-entity extraction
_TOKEN_RE = re.compile(r"\b([a-z]{3,})\b")


def _compute_claim_id(answer_id: str, index: int) -> str:
    return sha256(f"{answer_id}:{index}".encode()).hexdigest()


def _answer_id(answer_text: str) -> str:
    return sha256(answer_text.encode("utf-8")).hexdigest()


def _key_tokens(text: str) -> set[str]:
    """Return lowercase word tokens of length ≥ 4 (content words)."""
    return {m.group(1) for m in _TOKEN_RE.finditer(text.lower()) if len(m.group(1)) >= 4}


class ChainOfVerification:
    """Data Plane engine implementing Chain of Verification.

    Given a candidate answer text and a KnowledgeGraph, this engine:
      1. Splits the answer into atomic claims (sentence boundaries).
      2. For each claim, checks whether its key entities appear in the graph.
      3. Marks unverifiable claims as retracted.
      4. Returns a VerificationResult with only verified claims in final_answer.

    Bootstrap path (empty graph): all claims are marked verified vacuously
    and logged as UNVERIFIED_VACUOUS.
    """

    def __init__(
        self,
        max_claims: int = 20,
        log_path: Path | None = None,
    ) -> None:
        """Initialize ChainOfVerification.

        Args:
            max_claims: Maximum number of claims to process per answer.
            log_path: Optional JSONL log file path.

        """
        self.max_claims = max_claims
        self._log_path = log_path

    def verify(
        self,
        answer_text: str,
        graph: KnowledgeGraph | None = None,
    ) -> VerificationResult:
        """Decompose, verify, and reassemble answer_text.

        Args:
            answer_text: Candidate answer to verify.
            graph: Optional KnowledgeGraph for claim verification.

        Returns:
            VerificationResult with verification metadata and final_answer.

        """
        aid = _answer_id(answer_text)
        raw_sentences = _SENTENCE_BOUNDARY.split(answer_text.strip())
        sentences = [s.strip() for s in raw_sentences if s.strip()][: self.max_claims]

        is_empty_graph = graph is None or graph.node_count == 0

        claims: list[VerificationClaim] = []
        verified_count = 0
        retracted_count = 0
        kept_sentences: list[str] = []

        for idx, sentence in enumerate(sentences):
            cid = _compute_claim_id(aid, idx)
            tokens = _key_tokens(sentence)

            if is_empty_graph:
                # Vacuous verification (bootstrap)
                claim = VerificationClaim(
                    id=cid,
                    answer_id=aid,
                    claim_text=sentence,
                    verified=True,
                    evidence=[],
                )
                claims.append(claim)
                verified_count += 1
                kept_sentences.append(sentence)
                self._log({"event": "UNVERIFIED_VACUOUS", "claim_id": cid, "sentence": sentence})
                continue

            # Check claim tokens against graph entity names
            if graph is None:
                # Should not reach here (empty graph handled above), but be safe
                claim = VerificationClaim(
                    id=cid, answer_id=aid, claim_text=sentence,
                    verified=True, evidence=[],
                )
                claims.append(claim)
                verified_count += 1
                kept_sentences.append(sentence)
                continue
            evidence_frags: list[str] = []
            all_found = True

            if not tokens:
                # No content words — treat as verified
                claim = VerificationClaim(
                    id=cid, answer_id=aid, claim_text=sentence,
                    verified=True, evidence=[],
                )
                claims.append(claim)
                verified_count += 1
                kept_sentences.append(sentence)
                continue

            for token in sorted(tokens):
                node = graph.find_entity_by_name(token)
                if node is not None:
                    frags = graph.fragments_for_entity(node.id)
                    evidence_frags.extend(f.id for f in frags)
                else:
                    all_found = False
                    break

            if all_found:
                claim = VerificationClaim(
                    id=cid, answer_id=aid, claim_text=sentence,
                    verified=True, evidence=evidence_frags,
                )
                claims.append(claim)
                verified_count += 1
                kept_sentences.append(sentence)
                self._log({"event": "verified", "claim_id": cid})
            else:
                claim = VerificationClaim(
                    id=cid, answer_id=aid, claim_text=sentence,
                    verified=False, evidence=[],
                )
                claims.append(claim)
                retracted_count += 1
                self._log({"event": "retracted", "claim_id": cid, "sentence": sentence})

        final_answer = " ".join(kept_sentences)
        return VerificationResult(
            answer_id=aid,
            claims=claims,
            verified_claims=verified_count,
            retracted_claims=retracted_count,
            final_answer=final_answer,
        )

    def _log(self, payload: dict[str, Any]) -> None:
        """Append an event to the JSONL log if configured."""
        if self._log_path is None:
            return
        event = {
            "timestamp_ns": time.time_ns(),
            "version": REASONING_SCHEMA_VERSION,
            "module": "reasoning.cov",
            "payload": payload,
        }
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event) + "\n")
