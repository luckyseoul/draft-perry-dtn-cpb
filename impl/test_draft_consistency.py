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
    assert "Why NOT URI Query Parameters" in text
    assert "CPB Extension Block Binding" in text
    assert "CPB Data Structure" in text
    assert "CBOR Encoding: Major Type 7" in text
    assert "Hex Encoding Table" in text


def test_validation_scope_has_no_performance_or_real_stack_claims():
    text = XML.read_text(encoding="utf-8")
    assert "Planned Experimental Evaluation" in text
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
    assert "draft-perry-dtn-cpb.xml" in README.read_text(encoding="utf-8")


if __name__ == "__main__":
    test_retains_the_architectural_and_cbor_material()
    test_validation_scope_has_no_performance_or_real_stack_claims()
    test_standalone_cddl_matches_the_document_schema()
    test_documented_wire_sizes()
    test_internal_references_resolve()
    test_repository_link_is_present()
    print("All draft consistency tests passed.")
