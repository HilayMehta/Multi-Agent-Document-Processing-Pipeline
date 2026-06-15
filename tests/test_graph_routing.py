"""Graph routing + retry tests with a mocked LLM (no API key)."""

import graph
from schemas.common import Classification
from schemas.invoice import InvoiceFields
from schemas.vendor_contract import ContractFields


def _classification(doc_type: str, confidence: float) -> Classification:
    return Classification(document_type=doc_type, confidence=confidence, signals=["x"])


# ── config_for: code-level schema selection for the supported types ─────────────
def test_known_type_routes_to_its_schema():
    assert graph.config_for("Invoice").schema is InvoiceFields
    assert graph.config_for("Vendor Contract").schema is ContractFields


# ── route_after_classify: extract a confident supported type, else stop ─────────
def test_confident_supported_type_routes_to_extract():
    state = {"classification": _classification("Invoice", 0.95)}
    assert graph.route_after_classify(state) == "extract"


def test_other_type_stops_after_classify():
    state = {"classification": _classification("Other", 0.95)}
    assert graph.route_after_classify(state) == graph.END


def test_low_confidence_stops_after_classify():
    state = {"classification": _classification("Invoice", 0.5)}   # below threshold -> stop
    assert graph.route_after_classify(state) == graph.END


# ── Full graph with a mocked LLM ────────────────────────────────────────────────
def _install_mocks(monkeypatch, tag_sequence):
    """Patch every agent wrapper; tag_sequence yields successive tag lists."""
    calls = {"classify": 0, "extract": 0, "tag": 0, "summarize": 0}

    def fake_parse(_path): return "INVOICE total due ₹14,16,000"

    def fake_classify(_text):
        calls["classify"] += 1
        return Classification(document_type="Invoice", confidence=0.98, signals=["INVOICE"])

    def fake_extract(_cfg, _text, _prior):
        calls["extract"] += 1
        return {"invoice_number": "X", "totals": {}, "line_items": [], "payment_instructions": {}}

    seq = iter(tag_sequence)

    def fake_tag(_dt, _text, _fields, _prior):
        calls["tag"] += 1
        return next(seq)

    def fake_summarize(_dt, _text, _fields, _prior):
        calls["summarize"] += 1
        return "This is an invoice. It totals a stated amount."

    monkeypatch.setattr(graph, "parse_document", fake_parse)
    monkeypatch.setattr(graph, "_classify", fake_classify)
    monkeypatch.setattr(graph, "_extract_fields", fake_extract)
    monkeypatch.setattr(graph, "_tag", fake_tag)
    monkeypatch.setattr(graph, "_summarize", fake_summarize)
    return calls


def test_happy_path_no_retries(monkeypatch):
    calls = _install_mocks(monkeypatch, [["net-30", "gst", "invoice"]])
    graph.COMPILED_GRAPH = graph.build_graph()
    result = graph.run_pipeline("dummy.pdf")
    assert result.classification.document_type == "Invoice"
    assert calls["tag"] == 1 and calls["classify"] == 1
    assert sum(result.pipeline_meta.retries.values()) == 0


def test_failing_tags_retry_only_tagger(monkeypatch):
    # first two tag attempts are invalid (too few), third is valid
    calls = _install_mocks(monkeypatch, [["only-one"], ["still-bad"], ["net-30", "gst", "ok"]])
    graph.COMPILED_GRAPH = graph.build_graph()
    result = graph.run_pipeline("dummy.pdf")
    assert calls["tag"] == 3                         # 1 initial + 2 retries
    assert calls["classify"] == 1                    # classifier NEVER retried
    assert calls["extract"] == 1                     # extractor not retried for a tag failure
    assert result.pipeline_meta.retries["tag"] == 2  # capped at MAX_RETRIES_PER_STAGE


def test_tag_retries_capped(monkeypatch):
    # always-invalid tags: should stop after the cap and emit with unresolved errors
    calls = _install_mocks(monkeypatch, [["bad"]] * 10)
    graph.COMPILED_GRAPH = graph.build_graph()
    result = graph.run_pipeline("dummy.pdf")
    assert calls["tag"] == 3                          # 1 + 2 retries, then give up
    assert result.pipeline_meta.validation_errors_unresolved


def test_other_classification_skips_extraction(monkeypatch):
    # "Other" stops after classify: no extract/tag/summarize, empty downstream fields
    calls = _install_mocks(monkeypatch, [["a", "b", "c"]])
    monkeypatch.setattr(graph, "_classify",
                        lambda _t: Classification(document_type="Other", confidence=0.95, signals=["x"]))
    graph.COMPILED_GRAPH = graph.build_graph()
    result = graph.run_pipeline("dummy.pdf")
    assert result.classification.document_type == "Other"
    assert calls["extract"] == 0 and calls["tag"] == 0 and calls["summarize"] == 0
    assert result.extracted_fields == {} and result.tags == [] and result.summary == ""
