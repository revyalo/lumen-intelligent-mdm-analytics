"""Optional local-only embeddings adapter, explicitly evaluated separately from baseline matching."""
from itertools import combinations
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from intelligent_mdm.matching.engine import PAIR_COLUMNS, _prepare


def semantic_match(frame: pd.DataFrame, model_path: str, min_score: float = 70.) -> pd.DataFrame:
    if not Path(model_path).is_dir():
        raise ValueError("Provide an existing local sentence-transformers model folder; no implicit download")
    if len(frame) > 1000:
        raise ValueError("Semantic all-pairs demo is capped at 1,000 records; add ANN indexing for larger workloads")
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ValueError("Install the optional semantic extra to enable embeddings") from exc
    started = perf_counter()
    clean = _prepare(frame)
    model = SentenceTransformer(str(Path(model_path).resolve()), local_files_only=True, trust_remote_code=False)
    vectors = model.encode(clean.name.fillna("").tolist(), normalize_embeddings=True, show_progress_bar=False)
    cosine = np.clip(vectors @ vectors.T, -1., 1.)
    records = clean.to_dict("records")
    rows = []
    for i, j in combinations(range(len(clean)), 2):
        score = float(cosine[i, j]*100)
        if score < min_score:
            continue
        a, b = records[i], records[j]
        conflict = any(pd.notna(a.get(k)) and pd.notna(b.get(k)) and a[k] != b[k]
                       for k in ["tax_id", "sku", "email"] if k in a and k in b)
        left, right = sorted([a["record_id"], b["record_id"]])
        rows.append({"left_id": left, "right_id": right, "method": "semantic", "score": score,
                     "name_score": score, "conflict": conflict, "evidence": "Local name embedding cosine × 100",
                     "band": "conflict" if conflict else "review"})
    out = pd.DataFrame(rows, columns=PAIR_COLUMNS)
    out.attrs.update(seconds=perf_counter()-started, candidate_pairs=len(clean)*(len(clean)-1)//2, model_path=str(model_path))
    return out
