from collections import defaultdict
from itertools import combinations
from time import perf_counter

import pandas as pd
from rapidfuzz.fuzz import WRatio

from intelligent_mdm.cleaning import normalize, text_key

PAIR_COLUMNS = ["left_id", "right_id", "method", "score", "name_score", "conflict", "evidence", "band"]


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    if not {"record_id", "name"} <= set(frame):
        raise ValueError("Matching requires record_id and name")
    if frame.record_id.isna().any() or frame.record_id.astype(str).duplicated().any():
        raise ValueError("record_id must be unique and nonmissing")
    clean, _ = normalize(frame.reset_index(drop=True))
    clean["record_id"] = clean.record_id.astype(str)
    return clean.set_index("record_id", drop=False)


def match(frame: pd.DataFrame, method: str = "fuzzy", *, min_score: float = 65,
          max_block: int = 500, max_pairs: int = 500000) -> pd.DataFrame:
    """Block on identifiers or name tokens; oversized blocks fail visibly instead of dropping candidates."""
    if method not in {"exact", "fuzzy"}:
        raise ValueError("Use exact or fuzzy; embeddings have a separate opt-in adapter")
    if not 0 <= min_score <= 100:
        raise ValueError("min_score must be 0–100")
    started = perf_counter()
    df = _prepare(frame)
    blocks = defaultdict(list)
    names = {}
    token_rows = defaultdict(list)
    for row in df.to_dict("records"):
        rid = row["record_id"]
        name = text_key(row["name"])
        names[rid] = name
        for key in ["tax_id", "email", "sku"]:
            if key in row and pd.notna(row[key]) and str(row[key]).strip():
                blocks[(key, str(row[key]))].append(rid)
        if name:
            blocks[("name", name)].append(rid)
            if method == "fuzzy":
                for token in set(name.split()):
                    token_rows[token].append(rid)
    # Shared non-common tokens retain spelling-variant recall without quadratic common-word blocks.
    excluded_tokens = 0
    if method == "fuzzy":
        for token, ids in token_rows.items():
            if 1 < len(ids) <= max_block:
                blocks[("token", token)] = ids
            elif len(ids) > max_block:
                excluded_tokens += 1
    pairs = set()
    for ids in blocks.values():
        if len(ids) > max_block:
            raise ValueError(f"Candidate block has {len(ids)} rows (> {max_block}); refine blocking or raise explicit cap")
        pairs.update(tuple(sorted(p)) for p in combinations(ids, 2))
        if len(pairs) > max_pairs:
            raise ValueError("Candidate budget exceeded; partition data or refine blocking")
    rows = []
    records = df.to_dict("index")
    for left, right in sorted(pairs):
        a, b = records[left], records[right]
        equal, conflicts = [], []
        for key in ["tax_id", "email", "sku"]:
            av, bv = a.get(key), b.get(key)
            if pd.notna(av) and pd.notna(bv) and str(av) and str(bv):
                if av == bv:
                    equal.append(key)
                elif key in {"tax_id", "sku", "email"}:
                    conflicts.append(key)
        ns = WRatio(names[left], names[right]) if names[left] and names[right] else 0.
        exact_name = bool(names[left] and names[left] == names[right])
        exact = bool(equal or exact_name)
        if method == "exact" and not exact:
            continue
        score = max(98. if equal else 0., 95. if exact_name else 0., ns*.90)
        if score < min_score:
            continue
        evidence = equal + (["normalized_name"] if exact_name else ["fuzzy_name"])
        band = "conflict" if conflicts else "high" if score >= 95 else "review" if score >= 80 else "weak"
        rows.append({"left_id": left, "right_id": right, "method": method, "score": round(score, 3),
                     "name_score": round(ns, 3), "conflict": bool(conflicts),
                     "evidence": ", ".join(evidence + [f"different_{k}" for k in conflicts]), "band": band})
    result = pd.DataFrame(rows, columns=PAIR_COLUMNS).sort_values(["score", "left_id", "right_id"], ascending=[False, True, True])
    result.attrs.update(candidate_pairs=len(pairs), all_pairs=len(df)*(len(df)-1)//2,
                        seconds=perf_counter()-started, blocking="nonempty exact keys + shared non-common name tokens",
                        excluded_common_tokens=excluded_tokens)
    return result.reset_index(drop=True)


def positive_pairs(labels: pd.DataFrame) -> set[tuple[str, str]]:
    if labels.record_id.duplicated().any():
        raise ValueError("Labels must map each record_id to one entity")
    return {tuple(sorted((str(a), str(b)))) for _, g in labels.groupby("entity_id")
            for a, b in combinations(g.record_id, 2)}


def evaluate(pairs: pd.DataFrame, labels: pd.DataFrame, threshold: float = 85.) -> dict:
    truth = positive_pairs(labels)
    eligible = pairs[pairs.score.ge(threshold) & ~pairs.conflict]
    known = set(labels.record_id.astype(str))
    if not set(pairs.left_id).union(pairs.right_id) <= known:
        raise ValueError("Predictions contain records without evaluation labels")
    predicted = {tuple(sorted((str(r.left_id), str(r.right_id)))) for r in eligible.itertuples()}
    tp, fp, fn = len(truth & predicted), len(predicted-truth), len(truth-predicted)
    precision = tp/(tp+fp) if tp+fp else 0.
    recall = tp/(tp+fn) if tp+fn else 0.
    return {"threshold": threshold, "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": 2*precision*recall/(precision+recall) if precision+recall else 0.,
            "labelled_positive_pairs": len(truth), "predicted_pairs": len(predicted),
            "seconds": pairs.attrs.get("seconds"), "candidate_pairs": pairs.attrs.get("candidate_pairs"),
            "excluded_common_tokens": pairs.attrs.get("excluded_common_tokens", 0)}
