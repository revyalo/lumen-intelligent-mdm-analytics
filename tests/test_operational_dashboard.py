from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"


def operational_app():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.switch_page("pages/operational_time.py").run()
    assert not app.exception, [str(e.value) for e in app.exception]
    return app


def test_ninth_page_has_known_computed_metrics_and_real_report():
    app = operational_app()
    assert [metric.value for metric in app.metric] == ["2.00", "50.0%", "3", "6"]
    app.button(key="ot_build_report").click().run()
    assert not app.exception
    assert app.session_state["ot_report_archive"].startswith(b"PK")


def test_employee_filter_changes_occupancy_and_warns_about_population():
    app = operational_app()
    app.selectbox(key="ot_population").set_value("Selected employees").run()
    app.multiselect(key="ot_employees").set_value(["Person 01"]).run()
    assert not app.exception
    assert app.session_state["ot_last_summary"]["employees"] == 1
    assert app.session_state["ot_last_summary"]["occupied_resource_seconds"] == 3600
    assert any("selected people" in warning.value for warning in app.warning)


def test_invalid_rows_need_explicit_exclusion():
    app = operational_app()
    app.selectbox(key="ot_source").set_value("Validation challenge").run()
    assert not app.exception
    assert len(app.metric) == 0
    app.checkbox(key="ot_allow_invalid").check().run()
    assert not app.exception
    assert app.session_state["ot_last_summary"]["employees"] == 1


def test_exact_identity_map_changes_peak_and_preserves_other_pages():
    app = operational_app()
    app.selectbox(key="ot_source").set_value("Identity mapping demo").run()
    assert app.session_state["ot_last_summary"]["peak_people_in_one_resource"] == 4
    app.checkbox(key="ot_apply_map").check().run()
    assert not app.exception
    assert app.session_state["ot_last_summary"]["peak_people_in_one_resource"] == 3
    app.switch_page("pages/business.py").run()
    assert not app.exception
    assert app.metric[0].label == "Fulfilled revenue"
    app.switch_page("pages/operational_time.py").run()
    assert not app.exception
    assert app.selectbox(key="ot_source").value == "Identity mapping demo"
    assert app.checkbox(key="ot_apply_map").value
    assert app.session_state["ot_last_summary"]["employees"] == 6


def test_csv_path_and_availability_toggle():
    app = operational_app()
    app.session_state["ot_upload_bytes"] = b"Employee,Start,End\nP1,08:00,09:00\nP2,08:30,09:30\n"
    app.selectbox(key="ot_source").set_value("Uploaded CSV").run()
    assert not app.exception
    assert app.session_state["ot_last_summary"]["occupied_resource_seconds"] == 5400
    app.checkbox(key="ot_schedule").uncheck().run()
    assert not app.exception
    assert app.session_state["ot_last_summary"]["utilization"] is None


def test_multiple_resource_dataset_and_heatmap_render():
    app = operational_app()
    app.selectbox(key="ot_source").set_value("Multi-day synthetic").run()
    assert not app.exception
    assert app.session_state["ot_last_summary"]["employees"] > 6
    assert any("Hourly activity" in item.value for item in app.subheader)
