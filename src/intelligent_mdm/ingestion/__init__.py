"""Synthetic generation and validated local CSV ingestion."""
from .synthetic import generate
from .io import load_bundle, read_csv, save_bundle, validate_bundle

__all__ = ["generate", "load_bundle", "read_csv", "save_bundle", "validate_bundle"]
