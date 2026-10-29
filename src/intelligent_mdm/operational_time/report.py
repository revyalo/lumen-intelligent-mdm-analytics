"""Operational evidence exports without unrelated commercial metrics."""
import html
import json
from importlib.metadata import version

from intelligent_mdm.reporting.archive import package_evidence

from .analysis import TimeAnalysis


def build_time_report(result: TimeAnalysis) -> bytes:
    payload = {"metadata": result.metadata, "summary": result.summary,
               "versions": {name: version(name) for name in ["pandas", "numpy", "plotly"]}}
    serialized = json.dumps(payload, indent=2, allow_nan=False)
    method = ("Intervals are half-open. Person/resource intervals are unioned and split at local midnight. "
              "A contact requires a continuous same-resource/day overlap strictly longer than the configured threshold. "
              "Rank counts distinct people across the selected period. Utilization/idle time need explicit availability. "
              "Parallel resources contribute resource-hours. Stay statistics use consolidated clipped visits. "
              "An employee filter changes the analyzed population. Identity changes require the exported exact map. "
              "Capacity is supplied, never inferred. Naive local timestamps do not resolve DST. "
              "Synthetic fixtures are not real operational performance evidence.")
    markdown = "# Lumen — Operational Time Analytics\n\n" + method + "\n\n## Computed results\n\n"
    markdown += "\n".join(f"- {key}: {value}" for key, value in result.summary.items())
    markdown += "\n\n## Reproduction manifest\n\n```json\n"+serialized+"\n```\n"
    sections = "".join(f"<h2>{html.escape(name.replace('_', ' ').title())}</h2>"+
                       result.tables[name].head(200).to_html(index=False, escape=True)
                       for name in ["daily_summary", "peak_intervals", "ranking", "pairs"])
    document = ("<!doctype html><html lang='en'><meta charset='utf-8'><title>Lumen operational evidence</title>"
                "<style>body{font:16px/1.6 system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:#1c2540}"
                "table{border-collapse:collapse;display:block;overflow:auto;font-size:13px}td,th{padding:8px;border-bottom:1px solid #ddd}"
                "pre{overflow:auto;background:#f3f5fa;padding:16px}</style>"
                "<h1>Operational Time Analytics</h1><p>"+html.escape(method)+"</p>"
                "<p>Tables below preview up to 200 rows each. CSV files contain full results.</p>"+sections+
                "<h2>Manifest</h2><pre>"+html.escape(serialized)+"</pre></html>")
    return package_evidence({"report.json": serialized, "report.md": markdown, "report.html": document}, result.tables)
