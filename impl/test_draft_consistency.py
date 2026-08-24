"""Consistency checks for the CPB specification and repository."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / "draft-perry-dtn-cpb.xml"
README = ROOT / "README.md"
CDDL = ROOT / "impl" / "cpb.cddl"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_document_identity():
    xml = _text(XML)
    assert 'docName="draft-perry-dtn-cpb-latest"' in xml
    assert "Bundle Protocol Contact Probability Block" in xml


def test_wire_semantics():
    xml = _text(XML)
    for phrase in (
        "bundle-conditioned",
        "decision-node: eid",
        "candidate-next-hop: eid",
        "forwarding-success-probability: probability",
        "probability = float16",
    ):
        assert phrase in xml, phrase


def test_processing_requirements():
    xml = _text(XML)
    for phrase in (
        "roundTiesToEven",
        "MUST NOT</bcp14> clamp",
        "1*8 forwarding-entry",
        "more than four CPBs",
        "1024 octets",
        "highest trust rank",
        "bundle must not be fragmented",
        "flags to zero",
    ):
        assert phrase in xml, phrase


def test_standalone_cddl_matches_normative_schema():
    xml = _text(XML)
    cddl = _text(CDDL)
    for line in (
        "cpb-btsd = bstr .cbor cpb-data",
        "* (uint .ge 4) => any",
        "entries = [1*8 forwarding-entry]",
        "decision-node: eid,",
        "candidate-next-hop: eid,",
        "forwarding-success-probability: probability",
        "probability = float16",
    ):
        assert line in xml and line in cddl, line


def test_conformance_vector_is_pinned():
    xml = _text(XML)
    assert "The 67-octet deterministic cpb-data encoding is" in xml
    assert "A400828382028218C800820282186400F93A00" in xml
    assert "8518C80200005843" in xml


def test_iana_request():
    xml = _text(XML)
    assert "Requested Bundle Block Type" in xml
    assert "creates no metric-type registry" in xml


def test_repository_source_link():
    readme = _text(README)
    assert "draft-perry-dtn-cpb.xml" in readme


def test_sand_relationship():
    xml = _text(XML)
    assert "SAND advertisements" in xml
    assert "CPB carries the result of a computation conditioned" in xml
