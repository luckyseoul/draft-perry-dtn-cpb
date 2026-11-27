"""Structural checks for the published CPB draft and local validation assets."""

from __future__ import annotations

from pathlib import Path
import re
import xml.etree.ElementTree as ET

import cbor2

from cpb import encode_cpb


ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / "draft-perry-dtn-cpb.xml"
README = ROOT / "README.md"
CDDL = ROOT / "impl" / "cpb.cddl"


def test_retains_the_architectural_and_cbor_material():
    text = XML.read_text(encoding="utf-8")
    assert "Why Not URI Query Parameters" in text
    assert "CPB Extension Block Binding" in text
    assert "CPB Data Structure" in text
    assert "CBOR Encoding: Major Type 7" in text
    assert "Hex Encoding Table" in text


def test_validation_scope_has_no_performance_or_real_stack_claims():
    text = XML.read_text(encoding="utf-8")
    assert "Experiment Description" in text
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
    doc = ET.parse(XML)
    text = doc.find('.//figure[@anchor="fig-listing-4"]/sourcecode').text
    cddl = CDDL.read_text(encoding="utf-8")
    def tokens(schema):
        # The present schema has no quoted literals containing semicolons.
        return re.findall(r"\S+", re.sub(r";[^\n]*", "", schema))

    assert tokens(text) == tokens(cddl), "embedded and standalone CDDL differ"


def test_documented_wire_sizes():
    doc = ET.parse(XML)
    probability = {0: 0.5}
    metadata = {**probability, 2: 840000000, 4: 3600, 5: 1}
    paths = {**metadata, 1: [[100 + i, 0.5] for i in range(8)]}
    complete = {**paths, 3: b"producer-node-100", 6: 0.75, 7: 1}
    configurations = [probability, metadata, paths, complete]
    rows = doc.findall('.//table[@anchor="tab-cpb-sizes"]/tbody/tr')
    assert len(rows) == len(configurations)
    block_sizes = []
    for data, row in zip(configurations, rows):
        wire = encode_cpb(data)
        block = cbor2.dumps([200, 2, 17, 0, wire])
        cells = ["".join(cell.itertext()).strip() for cell in row.findall("td")]
        assert [int(cells[1]), int(cells[2])] == [len(wire), len(block)]
        block_sizes.append(len(block))

    rows = doc.findall('.//table[@anchor="tab-overhead"]/tbody/tr')
    assert rows
    for row in rows:
        cells = ["".join(cell.itertext()).strip() for cell in row.findall("td")]
        payload = int(cells[0])
        assert cells[1:] == [f"{100 * size / payload:.1f}%" for size in block_sizes]


def test_internal_references_resolve():
    doc = ET.parse(XML)
    anchors = [node.attrib["anchor"] for node in doc.iter() if "anchor" in node.attrib]
    assert len(anchors) == len(set(anchors)), "duplicate document anchor"
    missing = {node.attrib["target"] for node in doc.iter("xref")} - set(anchors)
    assert not missing, f"unresolved document references: {sorted(missing)}"


def test_repository_link_is_present():
    readme = README.read_text(encoding="utf-8")
    assert "draft-perry-dtn-cpb.xml" in readme
    assert "draft-perry-dtn-cpb-00" in readme
    assert "-latest" not in readme


def _bcp14(section):
    return ["".join(el.itertext()) for el in section.iter("bcp14")]


def _flat(node):
    return re.sub(r"\s+", " ", "".join(node.itertext()))


def test_normative_scope_is_container_and_selection():
    doc = ET.parse(XML)
    problem = _flat(doc.find('.//section[@anchor="problem-statement"]'))
    assert "does not standardize a common forwarding algorithm" in problem
    assert "select which carried value applies" in problem

    usage = doc.find('.//section[@anchor="op-routing-usage"]')
    assert _bcp14(usage) == ["MUST NOT"]
    assert "non-normative examples" in _flat(usage)

    stability = doc.find('.//section[@anchor="stability-considerations"]')
    assert _bcp14(stability) == []
    stability_text = _flat(stability)
    for knob in ("0.75", "0.60", "0.05"):
        assert knob not in stability_text, knob

    examples = doc.find('.//section[@anchor="experiment-stability-examples"]')
    assert examples is not None
    assert examples.find("name").text == "Illustrative Stability Parameters"
    assert _bcp14(examples) == []
    example_text = _flat(examples)
    assert "non-normative" in example_text
    for knob in ("0.75", "0.60", "0.05"):
        assert knob in example_text, knob

    congestion = doc.find('.//section[@anchor="op-congestion"]')
    assert "RECOMMENDED" not in _bcp14(congestion)

    binding = doc.find('.//figure[@anchor="fig-listing-3"]/sourcecode').text
    assert "Sec 7.3.3" in binding
    assert "Sec 8.3.3" not in binding


def test_repository_docs_match_published_draft():
    quick = (ROOT / "docs" / "CPB-QUICK-REFERENCE.md").read_text(encoding="utf-8")
    lowered = quick.lower()
    assert "unsubmitted" not in lowered
    assert "pre-submission" not in lowered
    assert "draft §7" in quick
    assert "draft §8" not in quick

    impl_readme = (ROOT / "impl" / "README.md").read_text(encoding="utf-8")
    assert "clamps to [0,1]" not in impl_readme
    assert "values outside [0,1]" in impl_readme

    plan = (ROOT / "impl" / "EXPERIMENT-PLAN.md").read_text(encoding="utf-8")
    assert "presubmission" not in plan.lower()
    assert "excluded from automatic CI" not in plan
    assert "`make test`" in plan


if __name__ == "__main__":
    test_retains_the_architectural_and_cbor_material()
    test_validation_scope_has_no_performance_or_real_stack_claims()
    test_standalone_cddl_matches_the_document_schema()
    test_documented_wire_sizes()
    test_internal_references_resolve()
    test_repository_link_is_present()
    test_normative_scope_is_container_and_selection()
    test_repository_docs_match_published_draft()
    print("All draft consistency tests passed.")
