"""Deterministic entity resolution. Similarity scores are not probabilities."""
from .engine import evaluate, match, positive_pairs
from .review import ReviewLedger, consolidate, fingerprint

__all__ = ["match", "evaluate", "positive_pairs", "ReviewLedger", "consolidate", "fingerprint"]
