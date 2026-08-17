"""Structural consistency checks for draft/docs claims vs shipped code.

These assert the public narrative matches what is actually in the tree
(no dead artifact paths, no phantom second routing arm, no Abstract
overclaim of adversarial routing evaluation).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / "draft-perry-dtn-cpb.xml"
README = ROOT / "README.md"
IMPL_README = ROOT / "impl" / "README.md"
SIM = ROOT / "impl" / "config1_sim.py"


def test_no_dead_real_cpb_packet_test_path():
    text = XML.read_text(encoding="utf-8")
    assert "real_cpb_packet_test" not in text, (
        "draft still references real_cpb_packet_test/ which is not in the repo"
    )
    live = ROOT / "impl" / "real-pwg-deployment" / "timeline1" / "LIVE_TRANSMISSION_STATUS.txt"
    assert live.is_file(), f"expected live notes at {live}"


def test_abstract_does_not_claim_adversarial_routing_eval():
    text = XML.read_text(encoding="utf-8")
    # Pull abstract body only
    m = re.search(r"<abstract>(.*?)</abstract>", text, re.S)
    assert m, "abstract missing"
    abstract = m.group(1)
    assert "adversarial conditions" not in abstract, (
        "Abstract must not claim adversarial routing evaluation"
    )
    assert "confidence-weighted" in abstract or "ground-truth" in abstract


def test_sim_only_baseline_and_cpb_choosers():
    src = SIM.read_text(encoding="utf-8")
    # CHOOSERS dict keys in shipped code
    m = re.search(r"CHOOSERS\s*=\s*\{([^}]+)\}", src, re.S)
    assert m, "CHOOSERS not found"
    keys = re.findall(r'["\']([a-z-]+)["\']\s*:', m.group(1))
    assert set(keys) == {"baseline", "cpb"}, keys
    assert "cpb-risk" not in src
    assert "cpb_risk" not in src


def test_docs_do_not_advertise_hypothesis_tests():
    for path in (README, IMPL_README):
        body = path.read_text(encoding="utf-8")
        assert "Hypothesis" not in body, f"{path} still claims Hypothesis tests"
        assert "cpb-risk" not in body, f"{path} still mentions cpb-risk"


def test_bcb_comment_points_to_section_8():
    text = XML.read_text(encoding="utf-8")
    assert "Section 8.3.3" in text
    assert "Section 7.2.3" not in text


def test_no_false_identical_realizations_claim():
    text = XML.read_text(encoding="utf-8")
    assert "identical contact-failure" not in text
    assert "identical contact realizations" not in text


def test_no_stale_paper_numbers():
    text = XML.read_text(encoding="utf-8")
    # superseded pre-CRN battery numbers must not reappear
    assert "0.9962" not in text
    assert "0.9998" not in text
    assert "0.9965" in text and "0.9984" in text


def test_published_cost_is_latency_over_confidence():
    text = XML.read_text(encoding="utf-8")
    assert "latency / confidence" in text or "latency / confidence" in text.replace("&#215;", "×")


if __name__ == "__main__":
    test_no_dead_real_cpb_packet_test_path()
    test_abstract_does_not_claim_adversarial_routing_eval()
    test_sim_only_baseline_and_cpb_choosers()
    test_docs_do_not_advertise_hypothesis_tests()
    test_bcb_comment_points_to_section_8()
    test_no_false_identical_realizations_claim()
    test_no_stale_paper_numbers()
    test_published_cost_is_latency_over_confidence()
    print("All draft consistency tests passed.")
