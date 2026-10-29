import io
import zipfile

import streamlit as st

from dashboard.common import RUNTIME, context, download_csv, page_title, proposals
from intelligent_mdm.matching import ReviewLedger, consolidate

bundle, _, name = context()
raw = st.session_state._raw
page_title("Entity Resolution", "Which observations may describe the same entity, and what evidence supports consolidation?")
if not {"record_id", "name"} <= set(raw):
    st.info("Select customer_sources, product_sources, supplier_sources, or a CSV with unique record_id and name fields.")
    st.stop()
method = st.radio("Candidate algorithm", ["exact", "fuzzy"], horizontal=True, index=1)
try:
    pairs = proposals(raw, method)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
ledger = ReviewLedger(RUNTIME / "reviews.sqlite")
snapshot = consolidate(raw, ledger)
threshold = st.slider("Minimum similarity score", 0, 100, 80)
show_conflict = st.toggle("Conflicts only", value=False)
view = pairs[pairs.score.ge(threshold)]
if show_conflict:
    view = view[view.conflict]
c1, c2, c3 = st.columns(3)
c1.metric("Candidate pairs", f"{len(view):,}")
c2.metric("Conflicting pairs", f"{int(pairs.conflict.sum()):,}")
c3.metric("Current golden records", f"{len(snapshot['golden_records']):,}")
st.caption("Scores are heuristic similarities, not probabilities. No candidate is merged until a reviewer accepts it. Conflicts need explicit investigation.")
st.caption(f"Blocking tested {pairs.attrs.get('candidate_pairs', 0):,} pairs; "
           f"{pairs.attrs.get('excluded_common_tokens', 0)} oversized common-token blocks were excluded. "
           "Aliases with no shared tokens or identifiers can be missed.")
st.dataframe(view.head(1000), hide_index=True, width="stretch")
download_csv("Export all matching candidates", pairs, "matching_candidates.csv")
if not view.empty:
    choices = {f"{row.left_id} ↔ {row.right_id} · {row.score:.1f} · {row.band}": (row.left_id, row.right_id) for row in view.itertuples()}
    selected = st.selectbox("Review pair", list(choices))
    left, right = choices[selected]
    st.dataframe(raw[raw.record_id.astype(str).isin([left, right])], width="stretch", hide_index=True)
    with st.form("human_review"):
        a, b = st.columns(2)
        reviewer = a.text_input("Reviewer", placeholder="Your name")
        decision = b.selectbox("Decision", ["accept", "reject", "revoke"])
        reason = st.text_area("Evidence and reason", placeholder="Record what you verified and why this decision is justified.")
        override = st.checkbox("I explicitly authorize consolidation despite contradictory identity keys")
        if st.form_submit_button("Save review decision"):
            try:
                ledger.record(raw, left, right, decision, reviewer, reason, override)
                st.success("Decision saved. Golden records have been recomputed; originals remain available.")
                snapshot = consolidate(raw, ledger)
            except ValueError as exc:
                st.error(str(exc))
tabs = st.tabs(["Golden records", "Field lineage", "Review history"])
with tabs[0]:
    st.dataframe(snapshot["golden_records"], width="stretch", hide_index=True)
    if not snapshot["blocked"].empty:
        st.warning("Some accepted edges were blocked by transitive identity conflicts.")
        st.dataframe(snapshot["blocked"], hide_index=True)
with tabs[1]:
    st.dataframe(snapshot["provenance"], width="stretch", hide_index=True)
with tabs[2]:
    st.dataframe(snapshot["history"], width="stretch", hide_index=True)
stream = io.BytesIO()
with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
    archive.writestr("original_observations.csv", raw.to_csv(index=False))
    for key, value in snapshot.items():
        archive.writestr(key+".csv", value.to_csv(index=False))
st.download_button("Export reversible MDM snapshot", stream.getvalue(), "mdm_snapshot.zip", "application/zip")
