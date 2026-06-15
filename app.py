"""Streamlit entrypoint — Page 1: Process documents (the product view).

Multi-upload; works on any document. Each file is classified first: if it is one of the four
supported types it is extracted (type, tags, fields, summary); if it classifies as "Other" the
run stops with an unsupported-document message — no extraction. Ground-truth independent.

Run with:  PYTHONPATH=src streamlit run app.py
(The Evaluation page lives in pages/ and appears in the sidebar.)
"""

import streamlit as st

import ui_common as ui

st.set_page_config(page_title="Process documents", page_icon="📄", layout="wide")

st.title("📄 Multi Agent Document Processing Pipeline")
st.caption(
    "Upload one or more documents. Each is classified, tagged, has its key fields extracted, and "
    "is summarised. Supported types: " + ", ".join(ui.SUPPORTED_TYPES) + ". "
    "Use the **Evaluation** page (sidebar) to score the samples against ground truth."
)

uploads = st.file_uploader(
    "Upload document(s)", type=["docx", "pdf"], accept_multiple_files=True
)

if uploads and st.button("Run pipeline", type="primary"):
    results: list[tuple[str, str, dict | None]] = []        # (name, predicted_type, data|None)
    progress = st.progress(0.0, "Starting…")
    for i, up in enumerate(uploads):
        with st.spinner(f"Processing {up.name}…"):
            doc_type, data = ui.process_for_product(up)
        results.append((up.name, doc_type, data))
        progress.progress((i + 1) / len(uploads), f"Processed {i + 1}/{len(uploads)}")
    progress.empty()

    for (name, doc_type, data), tab in zip(results, st.tabs([n for n, *_ in results])):
        with tab:
            if data is None:
                ui.unsupported_type_message(name, doc_type)
            else:
                ui.render_structured_output(data)
