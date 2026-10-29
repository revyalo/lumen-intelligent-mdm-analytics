from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


@pytest.mark.parametrize("page", ["overview", "explorer", "eda", "quality", "business", "entities", "ml", "reports"])
def test_page_renders_without_exception(page, tmp_path, monkeypatch):
    monkeypatch.setenv("MDM_RUNTIME_DIR", str(tmp_path))
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    if page != "overview":
        app.switch_page(f"pages/{page}.py").run()
    assert not app.exception, [str(e.value) for e in app.exception]


def test_explorer_search_changes_displayed_data():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.switch_page("pages/explorer.py").run()
    app.text_input[0].set_value("NO_SUCH_CUSTOMER_XXX").run()
    assert not app.exception
    assert len(app.dataframe[0].value) == 0


def test_eda_on_transactions():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.selectbox(key="table").set_value("order_lines").run()
    app.switch_page("pages/eda.py").run()
    assert not app.exception
    assert len(app.dataframe[1].value) > 0


def test_sql_lab_runs_the_selected_query():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.switch_page("pages/business.py").run()
    app.button[0].click().run()
    assert not app.exception
    result = app.dataframe[-1].value
    assert len(result) == 24
    assert result.revenue.sum() > 0


def test_evidence_report_button_generates_real_archive():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.switch_page("pages/reports.py").run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state["report_archive"].startswith(b"PK")
