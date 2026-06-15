"""Schema contract tests: nullability, strictness, tag rules, registry completeness."""

import typing

import pytest
from pydantic import BaseModel, ValidationError

from registry import EXTRACTORS
from schemas.common import Classification, TagSet
from schemas.invoice import InvoiceFields
from schemas.statement_of_work import SOWFields
from schemas.support_ticket import TicketFields
from schemas.vendor_contract import ContractFields


TOP_LEVEL_MODELS = [ContractFields, TicketFields, SOWFields, InvoiceFields]


def collect_models(model: type[BaseModel], seen: set | None = None) -> set[type[BaseModel]]:
    """Recursively collect a model and every nested BaseModel it references."""
    seen = seen if seen is not None else set()
    if model in seen:
        return seen
    seen.add(model)
    for field in model.model_fields.values():
        for candidate in [field.annotation, *typing.get_args(field.annotation)]:
            inner = typing.get_args(candidate) or [candidate]
            for t in inner:
                if isinstance(t, type) and issubclass(t, BaseModel):
                    collect_models(t, seen)
    return seen


ALL_MODELS = sorted(
    {m for top in TOP_LEVEL_MODELS for m in collect_models(top)}, key=lambda m: m.__name__
)


@pytest.mark.parametrize("model", TOP_LEVEL_MODELS, ids=lambda m: m.__name__)
def test_constructs_fully_null(model: type[BaseModel]) -> None:
    """Every extraction schema must be constructible with zero arguments (all-null)."""
    instance = model()
    assert instance.model_dump() is not None


@pytest.mark.parametrize("model", ALL_MODELS, ids=lambda m: m.__name__)
def test_extra_keys_forbidden(model: type[BaseModel]) -> None:
    """Every model (including nested ones) must reject unknown keys."""
    with pytest.raises(ValidationError):
        model.model_validate({"definitely_not_a_real_field": 1})


def test_tagset_accepts_valid() -> None:
    assert TagSet(tags=["net-30", "gst", "p1"]).tags == ["net-30", "gst", "p1"]


@pytest.mark.parametrize(
    "tags",
    [
        ["a", "b"],                       # too few
        ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8"],  # too many
        ["Net-30", "gst", "p1"],          # uppercase
        ["net_30", "gst", "p1"],          # underscore
        ["-leading", "gst", "p1"],        # leading hyphen
        ["gst", "gst", "p1"],             # duplicate
    ],
)
def test_tagset_rejects_invalid(tags: list[str]) -> None:
    with pytest.raises(ValidationError):
        TagSet(tags=tags)


def test_classification_bounds() -> None:
    ok = Classification(document_type="Invoice", confidence=0.98, signals=["INVOICE header"])
    assert ok.document_type == "Invoice"
    with pytest.raises(ValidationError):
        Classification(document_type="Invoice", confidence=1.5, signals=["x"])
    with pytest.raises(ValidationError):
        Classification(document_type="invoice", confidence=0.9, signals=["x"])  # wrong case
    with pytest.raises(ValidationError):
        Classification(document_type="Invoice", confidence=0.9, signals=[])  # no signals


def test_registry_covers_all_known_types() -> None:
    assert set(EXTRACTORS) == {"Vendor Contract", "Support Ticket", "Statement of Work", "Invoice"}
    for config in EXTRACTORS.values():
        assert issubclass(config.schema, BaseModel)
        assert config.prompt.strip()
