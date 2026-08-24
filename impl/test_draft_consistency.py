"""Structural checks for the published CPB draft and local validation assets."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / "draft-perry-dtn-cpb.xml"
README = ROOT / "README.md"
CDDL = ROOT / "impl" / "cpb.cddl"


def test_retains_the_architectural_and_cbor_material():
    text = XML.read_text(encoding="utf-8")
    assert "Why NOT URI Query Parameters" in text
    assert "CPB Extension Block Binding" in text
    assert "CPB Data Structure" in text
    assert "CBOR Encoding: Major Type 7" in text
    assert "Hex Encoding Table" in text


def test_validation_scope_has_no_performance_or_real_stack_claims():
    text = XML.read_text(encoding="utf-8")
    assert "First-Draft Validation" in text
    for stale in (
        "exp-real-validation",
        "real-pwg-deployment",
        "real-cpb-ion-test",
        "Tailscale mesh",
        "paper battery",
        "mean delivery ratio",
        "p95 latency",
    ):
        assert stale not in text, stale


def test_standalone_cddl_matches_the_document_schema():
    text = XML.read_text(encoding="utf-8")
    cddl = CDDL.read_text(encoding="utf-8")
    for production in (
        "cpb-data = {",
        "? 0: probability",
        "? 7: uint",
        "probability = float",
        "path-entry = [",
        "eid-reference = uint / tstr",
        "metric-type = &(",
    ):
        assert production in text, production
        assert production in cddl, production


def test_repository_link_is_present():
    assert "draft-perry-dtn-cpb.xml" in README.read_text(encoding="utf-8")


if __name__ == "__main__":
    test_retains_the_architectural_and_cbor_material()
    test_validation_scope_has_no_performance_or_real_stack_claims()
    test_standalone_cddl_matches_the_document_schema()
    test_repository_link_is_present()
    print("All draft consistency tests passed.")
