"""契约测试：全部 Agent 任务契约 YAML 必须通过 agent_task_contract Schema；
并检查 P0–P10 覆盖完整性与关键禁令的存在。"""

from __future__ import annotations

import json
import pathlib

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONTRACTS_DIR = ROOT / "packages" / "agent_contracts"
SCHEMA = json.loads((ROOT / "schemas" / "agent_task_contract" / "schema.json").read_text(encoding="utf-8"))


def load_contracts() -> dict[str, dict]:
    return {
        p.stem.split("_", 1)[0]: yaml.safe_load(p.read_text(encoding="utf-8"))
        for p in sorted(CONTRACTS_DIR.glob("*.yaml"))
    }


class TestSchemaCompliance:
    def test_all_contracts_valid(self):
        validator = Draft202012Validator(SCHEMA)
        for name, doc in load_contracts().items():
            errors = list(validator.iter_errors(doc))
            assert not errors, f"{name}: {[e.message for e in errors[:3]]}"

    def test_pipeline_coverage_p0_to_p10(self):
        expected_tasks = {
            "TASK-000", "TASK-101", "TASK-201", "TASK-301",
            "TASK-401", "TASK-501", "TASK-601",
            "TASK-701", "TASK-801", "TASK-901", "TASK-1001",
        }
        assert set(load_contracts().keys()) == expected_tasks


class TestDisciplineInvariants:
    """§11.2 通用执行纪律在契约层的程序化体现。"""

    def test_agent_tasks_forbid_immutable_overwrite(self):
        """Agent 类任务必须禁止覆盖不可变字段。"""
        for name, doc in load_contracts().items():
            if name in {"TASK-101", "TASK-201", "TASK-301", "TASK-401", "TASK-501", "TASK-601", "TASK-1001"}:
                joined = " ".join(doc["forbidden_actions"])
                assert ("不可变" in joined) or ("覆盖" in joined) or ("原文" in joined), (
                    f"{name} 禁令未覆盖不可变字段保护"
                )

    def test_status_task_states_no_proof_not_open_rule(self):
        doc = load_contracts()["TASK-401"]
        joined = " ".join(doc["forbidden_actions"]) + doc["purpose"]
        assert "未检索到解答" in joined, "TASK-401 必须包含『没有找到证明≠仍然开放』硬性规则"

    def test_all_logging_requirements_nonempty(self):
        for name, doc in load_contracts().items():
            assert doc["logging_requirements"], f"{name} logging_requirements 为空"

    def test_retry_cap(self):
        for name, doc in load_contracts().items():
            assert doc["retry_policy"]["max_retries"] <= 3
