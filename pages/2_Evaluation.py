"""Page 2: Evaluation — score uploaded sample documents against their ground truth.

Multi-upload. Only files present in ground truth are evaluated (others are flagged out of scope,
no extraction). Shows a batch overview table with an aggregate row + gate, then per-document
scores and the full eval report (inline + downloadable). Nothing is hardcoded — it evaluates
exactly what is uploaded.
"""

import streamlit as st

import ui_common as ui

st.set_page_config(page_title="Evaluation", page_icon="📊", layout="wide")

st.title("📊 Evaluation — predictions vs ground truth")
st.caption(
    "Upload the sample documents you want to score. Each is run through the pipeline and compared "
    "against its expected output: classification, field accuracy, tag Jaccard, and summary score."
)

ground_truth = ui.load_ground_truth()
uploads = st.file_uploader(
    "Upload sample document(s)", type=["docx", "pdf"], accept_multiple_files=True
)

if uploads and st.button("Run evaluation", type="primary"):
    # ── process each upload ─────────────────────────────────────────────────────────────────
    details: list[tuple[str, dict | None, dict | None, dict | None]] = []
    agg_m = agg_t = class_correct = n_scored = 0
    progress = st.progress(0.0, "Starting…")
    for i, up in enumerate(uploads):
        gt = ground_truth.get(up.name)
        if gt is None:
            details.append((up.name, None, None, None))     # out of scope
        else:
            with st.spinner(f"Evaluating {up.name}…"):
                data = ui.run_on_upload(up)
            sc = ui.compute_scores(gt, data)
            details.append((up.name, gt, data, sc))
            agg_m += sc["field_m"]
            agg_t += sc["field_t"]
            class_correct += int(sc["class_ok"])
            n_scored += 1
        progress.progress((i + 1) / len(uploads), f"Evaluated {i + 1}/{len(uploads)}")
    progress.empty()

    # ── batch overview table ────────────────────────────────────────────────────────────────
    st.subheader("Batch results overview")
    rows = ["| Document | Type | Class | Field acc | Tag Jaccard | Summary |",
            "|---|---|---|---|---|---|"]
    for name, gt, _data, sc in details:
        if gt is None:
            rows.append(f"| `{name}` | — | 🚫 out of scope | — | — | — |")
        else:
            fa = f"{sc['field_m']}/{sc['field_t']} ({sc['field_m'] / sc['field_t']:.0%})"
            tj = f"{sc['tag_i']}/{sc['tag_u']} ({sc['tag_i'] / sc['tag_u']:.0%})" if sc["tag_u"] else "—"
            rows.append(f"| `{name}` | {sc['pred_type']} | {'✓' if sc['class_ok'] else '✗'} | "
                        f"{fa} | {tj} | {sc['summary']:.2f} |")
    if n_scored:
        agg_fa = f"{agg_m}/{agg_t} ({agg_m / agg_t:.0%})" if agg_t else "—"
        rows.append(f"| **Aggregate** | | **{class_correct}/{n_scored}** | **{agg_fa}** | | |")
    st.markdown("\n".join(rows))

    if n_scored:
        gate_ok = (class_correct == n_scored) and bool(agg_t) and (agg_m / agg_t >= 0.90)
        st.markdown(f"**Gate:** classification {class_correct}/{n_scored}, field accuracy "
                    f"{(agg_m / agg_t if agg_t else 0):.0%} → "
                    f"{'✅ PASS' if gate_ok else '❌ FAIL'} (needs 100% class, ≥ 90% fields)")

    # ── per-document detail ─────────────────────────────────────────────────────────────────
    scored = [(n, g, d, s) for (n, g, d, s) in details if g is not None]
    if scored:
        st.subheader("Per-document detail")
        for (name, gt, data, sc), tab in zip(scored, st.tabs([n for n, *_ in scored])):
            with tab:
                ui.render_eval_metrics(sc)
                path, md = ui.generate_report(name, gt, data)
                with st.expander("📊 View full eval report (fields, tags, summary)"):
                    st.markdown(md)
                st.download_button("⬇️ Download eval report (.md)", md,
                                   file_name=path.name, mime="text/markdown",
                                   key=f"dl_{name}")

    # ── out-of-scope notices ────────────────────────────────────────────────────────────────
    for name, gt, *_ in details:
        if gt is None:
            ui.out_of_scope_message(name, ground_truth)
