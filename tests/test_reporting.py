import io
import json
import zipfile

import pandas as pd
import pytest

from intelligent_mdm.ingestion import generate
from intelligent_mdm.reporting import build_report, insights


def test_insights_carry_recomputable_evidence():
    bundle = generate()
    findings = insights(bundle)
    assert findings
    assert all({"finding", "evidence", "method", "limitation", "action"} <= set(x) for x in findings)
    source = next(x for x in findings if "Missing email" in x["finding"])
    assert source["evidence"]["missing"] == int(bundle.tables["customer_sources"].query("source == 'sales'").email.isna().sum())


def test_evidence_zip_reconciles_and_preserves_rows():
    bundle = generate()
    raw = bundle.tables["customer_sources"]
    with zipfile.ZipFile(io.BytesIO(build_report(bundle))) as archive:
        assert {"report.html", "report.json", "report.md", "cleaning_audit.csv", "invoice_distribution.png"} <= set(archive.namelist())
        payload = json.loads(archive.read("report.json"))
        assert payload["business"]["revenue"] == pytest.approx(bundle.tables["sales"].amount.sum())
        original = pd.read_csv(archive.open("original.csv"))
        assert set(original.record_id) == set(raw.record_id)
        assert len(original) == len(raw)
        assert archive.read("invoice_distribution.png").startswith(b"\x89PNG")
        assert "not establish causality" in archive.read("report.html").decode()
