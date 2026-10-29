"""Run from repository root: streamlit run dashboard/app.py."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st  # noqa: E402 — local source bootstrap must run before app imports

st.set_page_config(page_title="Lumen · Data Intelligence", page_icon="◈", layout="wide")
st.logo(str(ROOT / "dashboard" / "assets" / "lumen.svg"), size="large")
pages = {
    "WORKSPACE": [st.Page("pages/overview.py", title="Overview", icon=":material/dashboard:", default=True),
                  st.Page("pages/explorer.py", title="Data Explorer", icon=":material/table_view:")],
    "ANALYTICS": [st.Page("pages/eda.py", title="Exploratory Analysis", icon=":material/monitoring:"),
                  st.Page("pages/quality.py", title="Data Quality", icon=":material/verified:"),
                  st.Page("pages/business.py", title="Business Intelligence", icon=":material/stacked_line_chart:")],
    "INTELLIGENCE": [st.Page("pages/entities.py", title="Entity Resolution", icon=":material/hub:"),
                     st.Page("pages/ml.py", title="Machine Learning", icon=":material/science:"),
                     st.Page("pages/reports.py", title="Reports", icon=":material/download:")],
}
st.navigation(pages).run()
