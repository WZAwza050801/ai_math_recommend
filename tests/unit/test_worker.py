"""apps/worker 规则式候选生成的离线单测（不访问网络）。"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location(
    "run_once", ROOT / "apps" / "worker" / "run_once.py"
)
run_once = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_once)

from validate_gold_set import build_registry  # noqa: E402

from jsonschema import Draft202012Validator  # noqa: E402

OPG_DOC = {
    "source_id": "SRC-0009",
    "external_id": "op-test-problem",
    "url": "https://www.openproblemgarden.org/op/test_problem",
    "title": "Test Problem About Coprime Pairs",
    "text": "Is it true that for every n there exist n pairwise coprime integers with property P?",
    "fetched_at": "2026-08-28T11:00:00Z",
    "meta": {"categories": ["Number Theory"]},
}


def _validator():
    registry, _ = build_registry()
    return Draft202012Validator(
        json.loads((ROOT / "schemas" / "problem_card" / "schema.json").read_text(encoding="utf-8")),
        registry=registry,
    )


class TestCandidateGeneration:
    def test_opg_candidate_passes_schema(self):
        card = run_once.make_candidate(OPG_DOC, "number-theory")
        card["problem_id"] = "OP-800099"
        card["open_status"]["supporting_evidence"][0]["evidence_id"] = "EV-800099-1"
        errors = list(_validator().iter_errors(card))
        assert not errors, [e.message for e in errors[:3]]

    def test_candidate_discipline(self):
        card = run_once.make_candidate(OPG_DOC, "number-theory")
        card["problem_id"] = "OP-800099"
        pub = card["publication"]
        assert pub["lifecycle_state"] == "candidate"
        assert pub["publishable"] is False
        assert pub["publish_blockers"]
        assert card["open_status"]["human_verified"] is False
        assert card["open_status"]["status"] == "status_uncertain"
        assert card["importance_assessment"]["score_band"] == "insufficient_evidence"
        assert card["ai_affordance_assessment"]["score_band"] == "insufficient_evidence"
        # 规则式直通不得伪装成 LLM 输出
        assert card["audit"]["model_runs"][0]["model"].startswith("rule-based")

    def test_domain_mapping(self):
        assert run_once.domain_for(OPG_DOC) == "number-theory"
        unknown = dict(OPG_DOC, meta={"categories": ["Category Theory"]})
        assert run_once.domain_for(unknown) is None  # 不猜

    def test_slugify(self):
        assert run_once.slugify("Hello  World!!x") == "hello-worldx"
