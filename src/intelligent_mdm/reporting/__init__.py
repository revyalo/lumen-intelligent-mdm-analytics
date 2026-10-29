"""Portable evidence reports generated from actual selected data; no LLM required."""
import base64
import html
import io
import json
import zipfile
from importlib.metadata import version

import pandas as pd

from intelligent_mdm.analytics import business_summary, rfm
from intelligent_mdm.cleaning import normalize
from intelligent_mdm.data_quality import assess, compare_sources
from intelligent_mdm.eda import missing_patterns, profile, static_distribution
from intelligent_mdm.matching import match
from intelligent_mdm.models import DatasetBundle
from intelligent_mdm.sql import run_named


def insights(bundle: DatasetBundle) -> list[dict]:
    summary = business_summary(bundle)
    findings = [{"finding": "Customer revenue is concentrated",
                 "evidence": {"top_20_pct_share": summary["top20_share"], "customer_accounts": summary["customers"],
                              "revenue_eur": summary["revenue"]},
                 "method": "Revenue rank; top ceil(20% × all customer accounts), fulfilled orders only",
                 "limitation": "Descriptive synthetic data; concentration is undefined when revenue is zero",
                 "action": "Review dependency on large accounts and investigate retention priorities"}]
    if summary["revenue"] == 0:
        findings = []
    source = bundle.tables.get("customer_sources")
    if source is not None and "email" in source and "source" in source:
        for name, group in source.groupby("source"):
            count = int(group.email.isna().sum())
            if count:
                findings.append({"finding": f"Missing email addresses in {name}",
                                 "evidence": {"missing": count, "rows": len(group), "missing_pct": count/len(group)*100},
                                 "method": "Missing-cell count in original customer-source records",
                                 "limitation": "Syntax-valid addresses are not verified contacts; blanks from external data need normalization",
                                 "action": "Ask the source owner to validate and recover contacts from authoritative records"})
    monthly = run_named(bundle, "monthly_sales")
    if len(monthly) > 1 and pd.notna(monthly.iloc[-1].mom_pct) and abs(monthly.iloc[-1].mom_pct) >= 20:
        row = monthly.iloc[-1]
        findings.append({"finding": "Latest observed month changed materially",
                         "evidence": {"month": str(row.month.date()), "revenue_eur": row.revenue,
                                      "previous_revenue_eur": row.previous_revenue, "mom_pct": row.mom_pct},
                         "method": "100 × (current/prior − 1); rule threshold |20%|",
                         "limitation": "Calendar composition, constructed seasonality and partial periods can explain changes",
                         "action": "Compare equivalent full periods and category mix before acting"})
    segments = rfm(bundle)
    if not segments.empty:
        count = int(segments.segment.eq("At risk").sum())
        findings.append({"finding": "Some purchasing accounts have aged beyond the recency threshold",
                         "evidence": {"at_risk": count, "customers": len(segments), "recency_days_threshold": 180},
                         "method": "RFM: last 365 days; >180 days since last fulfilled purchase",
                         "limitation": "No purchases in the window are a separate segment; purchase cadence varies by business",
                         "action": "Validate expected purchasing cadence before designing a reactivation campaign"})
    return findings


def build_report(bundle: DatasetBundle, frame: pd.DataFrame | None = None, name: str = "customer_sources") -> bytes:
    raw = bundle.tables[name] if frame is None else frame
    clean, audit = normalize(raw)
    prof = profile(raw)
    before = assess(raw, name=name, tables=bundle.tables, as_of=bundle.metadata["as_of"])
    after = assess(clean, name=name, tables=bundle.tables, as_of=bundle.metadata["as_of"])
    observations = insights(bundle)
    metrics = business_summary(bundle)
    metadata = {**bundle.metadata, "analysis_table": name, "analysis_rows": len(raw),
                "report_scope": "Selected original table plus full supplied relational bundle",
                "versions": {p: version(p) for p in ["pandas", "numpy", "duckdb", "scikit-learn", "rapidfuzz"]}}
    payload = {"metadata": metadata, "business": metrics, "quality_before": before["dimensions"],
               "quality_after": after["dimensions"], "quality_score_before": before["score"],
               "quality_score_after": after["score"], "insights": observations}
    md = ["# Lumen — Data intelligence evidence report", "", "All business data are synthetic. No causal or production-performance claims.", "",
          "## Reproduction", "", "```json", json.dumps(metadata, indent=2), "```", "",
          "## Business metrics", "", *[f"- {k}: {v}" for k, v in metrics.items()], "",
          "## Analytical observations", ""]
    for item in observations:
        md.extend([f"### {item['finding']}", "", f"Evidence: {json.dumps(item['evidence'])}", "",
                   f"Method: {item['method']}", "", f"Limitations: {item['limitation']}", "", f"Action to investigate: {item['action']}", ""])
    md.extend(["## Quality and transformations", "", f"Original score: {before['score']}; normalized: {after['score']}.",
               f"{len(audit)} cell changes logged. Source rows are preserved. Rules/denominators are in quality_rules_*.csv.", "",
               "## Methods and limits", "",
               "Statistics use finite values and sample standard deviation. IQR/z-scores and ML flags require investigation.",
               "Revenue counts fulfilled invoices; active customers use the final 180 days. RFM uses the final 365 days.",
               "Synthetic margins use historical line costs. Quality excludes nonapplicable dimensions; scores are diagnostic.",
               "Matching scores are heuristic similarities. No automatic merges occur. Embeddings and forecasting are not part of this report.",
               "See docs/METHODOLOGY.md in the source project for exact definitions and limitations."])
    picture = static_distribution(bundle.tables["sales"].amount)
    sections = "".join(f"<article><h2>{html.escape(x['finding'])}</h2><p><b>Evidence:</b> {html.escape(json.dumps(x['evidence']))}</p>"
                       f"<p><b>Method:</b> {html.escape(x['method'])}</p><p><b>Limit:</b> {html.escape(x['limitation'])}</p>"
                       f"<p><b>Investigate:</b> {html.escape(x['action'])}</p></article>" for x in observations)
    html_doc = ("<!doctype html><html lang='en'><meta charset='utf-8'><title>Lumen evidence report</title>"
                "<style>body{font:16px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:#1c2540}"
                "h1{letter-spacing:-.04em}h2{font-size:22px}table{border-collapse:collapse;font-size:12px;display:block;overflow:auto}"
                "td,th{padding:8px;border-bottom:1px solid #dce2ee;text-align:left}article{padding:16px 0;border-bottom:1px solid #dce2ee}"
                "img{max-width:100%}pre{background:#f3f5fa;padding:16px;overflow:auto}</style>"
                "<p>LUMEN / DATA INTELLIGENCE</p><h1>Evidence, with context.</h1>"
                "<p>Reproducible synthetic analytics. Observations describe this dataset; they do not establish causality.</p>"
                "<h2>Run manifest</h2><pre>"+html.escape(json.dumps(metadata, indent=2))+"</pre>"
                "<h2>Business metrics</h2>"+pd.DataFrame([metrics]).to_html(index=False)+sections+
                "<h2>Selected-table descriptive statistics</h2>"+prof["numeric"].to_html(index=False)+
                "<h2>Original quality rules</h2>"+before["rules"].to_html(index=False)+
                "<h2>Invoice amount distribution</h2><img alt='Distribution of actual synthetic invoice amounts' src='data:image/png;base64,"+
                base64.b64encode(picture).decode()+"'><p>Extreme bulk purchases can be legitimate. No observations were removed.</p>"
                "<p>Exact definitions and caveats are included in report.md and docs/METHODOLOGY.md in the source project.</p></html>")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("report.json", json.dumps(payload, indent=2, default=str, allow_nan=False))
        archive.writestr("report.md", "\n".join(md))
        archive.writestr("report.html", html_doc)
        archive.writestr("invoice_distribution.png", picture)
        frames = {"original": raw, "normalized": clean, "cleaning_audit": audit,
                  "statistics": prof["numeric"], "schema": prof["schema"].reset_index(names="field"),
                  "missing_patterns": missing_patterns(raw), "quality_rules_before": before["rules"],
                  "quality_rules_after": after["rules"], "quality_sources": compare_sources(raw, name=name,
                      tables=bundle.tables, as_of=bundle.metadata["as_of"]),
                  "rfm": rfm(bundle)}
        frames.update({q: run_named(bundle, q) for q in ["monthly_sales", "customer_summary", "product_performance", "category_margin", "price_history"]})
        if {"record_id", "name"} <= set(raw):
            try:
                frames["matching_candidates"] = match(raw)
            except ValueError as exc:
                archive.writestr("matching_status.txt", f"Not evaluated: {exc}. Original rows are preserved.")
        for filename, data in frames.items():
            archive.writestr(filename+".csv", data.to_csv(index=False))
    return stream.getvalue()
