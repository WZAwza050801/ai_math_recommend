"""Phase 1 管理后端 API 单元测试。

策略：每个测试用例挂一个独立 tmp SQLite engine（monkeypatch database.engine /
SessionLocal），经 TestClient 触发 lifespan 建表，完全不触碰默认 `./aimath.db`。

覆盖：health、金标准导入（幂等 + 保持 scored）、列表筛选分页、新建 candidate 卡
（合法 + Schema 拒绝 + 非 candidate 拒绝 + 409 冲突）、生命周期合法迁移/非法 409/
禁发 400、审核追加与 human: 强制、gate 查询、**publish 无人工批准必 422 / 注入
approved review 后成功 / 非 scored 状态 409**、抽卡三模式结构、来源注册表。
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT / "apps" / "api") not in sys.path:
    sys.path.insert(0, str(ROOT / "apps" / "api"))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import cardjson, database  # noqa: E402
from app.main import app  # noqa: E402

GOLD_COUNT = 30


@pytest.fixture()
def client(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'api.db').as_posix()}"
    engine = database.make_engine(url)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(
        database,
        "SessionLocal",
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False),
    )
    with TestClient(app) as http:
        yield http
    engine.dispose()


@pytest.fixture()
def gold_client(client):
    resp = client.post("/api/admin/import_gold_set")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"imported": GOLD_COUNT, "skipped": 0}
    return client


def candidate_card(problem_id: str = "OP-900001") -> dict[str, Any]:
    """以金标准卡为底稿构造一张 Schema 合法的 candidate 卡。"""
    card = json.loads(
        (cardjson.GOLD_SET_DIR / "OP-000001.json").read_text(encoding="utf-8")
    )
    card["problem_id"] = problem_id
    card["identity"]["slug"] = problem_id.lower()
    card["publication"]["lifecycle_state"] = "candidate"
    card["publication"]["publishable"] = False
    card["audit"]["created_by"] = "human:api-tester"
    card["audit"]["human_reviews"] = []
    return card


# ---------------------------------------------------------------- health / 根路径


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"status": "ok", "db": True, "cards": 0}


def test_health_counts_cards(gold_client):
    body = gold_client.get("/api/health").json()
    assert body["cards"] == GOLD_COUNT


def test_index_serves_web_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "html" in resp.headers["content-type"]
    assert "<" in resp.text  # index.html 或占位页，二者都是 HTML


# ---------------------------------------------------------------- 导入


def test_import_gold_set_idempotent_and_stays_scored(client):
    resp = client.post("/api/admin/import_gold_set")
    assert resp.status_code == 200
    assert resp.json() == {"imported": GOLD_COUNT, "skipped": 0}

    # 幂等：再次导入全部跳过
    resp = client.post("/api/admin/import_gold_set")
    assert resp.json() == {"imported": 0, "skipped": GOLD_COUNT}

    # 红线：导入后保持 scored，绝不自动发布
    detail = client.get("/api/cards/OP-000001").json()
    assert detail["publication"]["lifecycle_state"] == "scored"
    assert detail["publication"]["publishable"] is False
    assert client.get("/api/cards?lifecycle=published").json()["total"] == 0

    # force=true 强制重导：30 张全部重写并追加版本快照
    resp = client.post("/api/admin/import_gold_set?force=true")
    assert resp.json() == {"imported": GOLD_COUNT, "skipped": 0}
    versions = client.get("/api/cards/OP-000001/versions").json()
    assert versions["total"] == 2
    assert versions["items"][-1]["reason"].startswith("import_gold_set")


# ---------------------------------------------------------------- 列表与详情


def test_list_cards_filters_and_pagination(gold_client):
    body = gold_client.get("/api/cards").json()
    assert body["total"] == GOLD_COUNT
    assert len(body["items"]) == 20  # 默认 page_size=20
    expected_keys = {
        "problem_id",
        "title",
        "primary_domain",
        "open_status",
        "lifecycle_state",
        "importance_band",
        "affordance_band",
        "publishable",
    }
    assert expected_keys <= set(body["items"][0])
    assert all(i["lifecycle_state"] == "scored" for i in body["items"])
    assert all(i["publishable"] is False for i in body["items"])

    # domain 过滤
    body = gold_client.get("/api/cards?domain=number-theory&page_size=200").json()
    assert body["total"] >= 1
    assert all(i["primary_domain"] == "number-theory" for i in body["items"])

    # open_status 过滤
    body = gold_client.get("/api/cards?status=confirmed_open&page_size=200").json()
    assert body["total"] >= 1
    assert all(i["open_status"] == "confirmed_open" for i in body["items"])

    # q 匹配 title 与卡内 JSON
    assert gold_client.get("/api/cards?q=Riemann").json()["total"] >= 1
    assert gold_client.get("/api/cards?q=Robin").json()["total"] >= 1
    assert gold_client.get("/api/cards?q=不存在关键词xyz").json()["total"] == 0

    # 分页
    page1 = gold_client.get("/api/cards?page=1&page_size=5").json()
    page2 = gold_client.get("/api/cards?page=2&page_size=5").json()
    assert page2["total"] == GOLD_COUNT
    assert len(page2["items"]) == 5
    ids1 = {i["problem_id"] for i in page1["items"]}
    ids2 = {i["problem_id"] for i in page2["items"]}
    assert ids1.isdisjoint(ids2)


def test_get_card_detail_and_404(gold_client):
    detail = gold_client.get("/api/cards/OP-000001")
    assert detail.status_code == 200
    assert detail.json()["problem_id"] == "OP-000001"
    assert detail.json()["identity"]["title"]

    assert gold_client.get("/api/cards/NOPE-404").status_code == 404
    assert gold_client.get("/api/cards/NOPE-404/gate").status_code == 404


# ---------------------------------------------------------------- 新建 candidate 卡


def test_create_candidate_card(gold_client):
    resp = gold_client.post("/api/cards", json=candidate_card())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["problem_id"] == "OP-900001"
    assert body["publication"]["lifecycle_state"] == "candidate"
    assert body["audit"]["current_version"] == 1

    assert gold_client.get("/api/cards?lifecycle=candidate").json()["total"] == 1
    versions = gold_client.get("/api/cards/OP-900001/versions").json()
    assert versions["total"] == 1
    assert versions["items"][0]["version"] == 1
    assert versions["items"][0]["reason"] == "create:candidate"


def test_create_card_schema_rejection(gold_client):
    card = candidate_card()
    del card["classification"]  # required 字段缺失
    resp = gold_client.post("/api/cards", json=card)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["errors"]
    assert "classification" in detail["errors"][0]


def test_create_card_rejects_non_candidate(gold_client):
    card = candidate_card()
    card["publication"]["lifecycle_state"] = "scored"
    resp = gold_client.post("/api/cards", json=card)
    assert resp.status_code == 422
    assert "candidate" in resp.json()["detail"]["message"]


def test_create_card_conflict_409(gold_client):
    card = candidate_card()
    assert gold_client.post("/api/cards", json=card).status_code == 201
    resp = gold_client.post("/api/cards", json=card)
    assert resp.status_code == 409


# ---------------------------------------------------------------- 生命周期状态机


def test_lifecycle_transitions(gold_client):
    gold_client.post("/api/cards", json=candidate_card())

    # 合法迁移 candidate -> normalized
    resp = gold_client.post(
        "/api/cards/OP-900001/lifecycle", json={"target": "normalized"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["publication"]["lifecycle_state"] == "normalized"
    assert body["audit"]["current_version"] == 2

    # 非法迁移 normalized -> scored（跳过 dedup/status 审核）
    resp = gold_client.post(
        "/api/cards/OP-900001/lifecycle", json={"target": "scored"}
    )
    assert resp.status_code == 409
    assert "非法生命周期迁移" in resp.json()["detail"]

    # 红线：不允许经 lifecycle 端点直达 published
    resp = gold_client.post(
        "/api/cards/OP-900001/lifecycle", json={"target": "published"}
    )
    assert resp.status_code == 400
    assert "publish" in resp.json()["detail"]

    # 未知目标状态
    resp = gold_client.post(
        "/api/cards/OP-900001/lifecycle", json={"target": "on_hold"}
    )
    assert resp.status_code == 422

    # 版本轨迹已追加迁移快照
    versions = gold_client.get("/api/cards/OP-900001/versions").json()
    assert versions["total"] == 2
    assert versions["items"][-1]["reason"] == "lifecycle:candidate->normalized"

    # 非 scored 状态下 gate 必含 gate-0 阻塞
    gate = gold_client.get("/api/cards/OP-900001/gate").json()
    assert gate["publishable"] is False
    assert any(b.startswith("gate-0") for b in gate["blockers"])


def test_lifecycle_404(gold_client):
    resp = gold_client.post("/api/cards/NOPE-404/lifecycle", json={"target": "normalized"})
    assert resp.status_code == 404


# ---------------------------------------------------------------- 审核队列


def test_reviews_append_only_and_validation(gold_client):
    resp = gold_client.post(
        "/api/cards/OP-000001/reviews",
        json={"reviewer": "human:审稿人甲", "decision": "approved", "notes": "人工核验通过"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["review"]["decision"] == "approved"
    assert body["review"]["reviewer"] == "human:审稿人甲"
    assert len(body["human_reviews"]) == 1
    assert body["version"] == 2

    detail = gold_client.get("/api/cards/OP-000001").json()
    assert detail["audit"]["human_reviews"][0]["reviewer"] == "human:审稿人甲"

    # 只增不删：追加第二条
    resp = gold_client.post(
        "/api/cards/OP-000001/reviews",
        json={"reviewer": "human:审稿人乙", "decision": "needs_changes", "notes": "证据需补充"},
    )
    assert resp.status_code == 200
    detail = gold_client.get("/api/cards/OP-000001").json()
    assert len(detail["audit"]["human_reviews"]) == 2
    assert detail["audit"]["current_version"] == 3
    versions = gold_client.get("/api/cards/OP-000001/versions").json()
    assert versions["total"] == 3

    # 非法 decision → 422
    resp = gold_client.post(
        "/api/cards/OP-000001/reviews",
        json={"reviewer": "human:x", "decision": "auto_approve"},
    )
    assert resp.status_code == 422

    # 红线（ADR-012）：非 human: 前缀的审核人一律拒绝
    for reviewer in ("agent:self", "robot:1", "human:"):
        resp = gold_client.post(
            "/api/cards/OP-000001/reviews",
            json={"reviewer": reviewer, "decision": "approved"},
        )
        assert resp.status_code == 422, reviewer

    assert gold_client.post(
        "/api/cards/NOPE-404/reviews",
        json={"reviewer": "human:x", "decision": "approved"},
    ).status_code == 404


# ---------------------------------------------------------------- 发布门禁（红线）


def test_gate_reports_blockers(gold_client):
    gate = gold_client.get("/api/cards/OP-000001/gate")
    assert gate.status_code == 200
    body = gate.json()
    assert body["publishable"] is False
    assert isinstance(body["blockers"], list) and body["blockers"]
    assert any(b.startswith("gate-p7") for b in body["blockers"])


def test_publish_without_human_approval_must_422(gold_client):
    resp = gold_client.post("/api/cards/OP-000001/publish")
    assert resp.status_code == 422
    body = resp.json()  # 响应体顶层就是 {publishable, blockers}
    assert body["publishable"] is False
    assert any(b.startswith("gate-p7") for b in body["blockers"])

    # 卡片保持 scored，publishable 仍为 false
    detail = gold_client.get("/api/cards/OP-000001").json()
    assert detail["publication"]["lifecycle_state"] == "scored"
    assert detail["publication"]["publishable"] is False
    assert gold_client.get("/api/cards?lifecycle=published").json()["total"] == 0


def test_publish_succeeds_after_approved_review(gold_client):
    resp = gold_client.post(
        "/api/cards/OP-000001/reviews",
        json={"reviewer": "human:P7领域专家", "decision": "approved", "notes": "八项门禁人工复核完成"},
    )
    assert resp.status_code == 200

    resp = gold_client.post("/api/cards/OP-000001/publish")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["publication"]["lifecycle_state"] == "published"
    assert body["publication"]["publishable"] is True

    listed = gold_client.get("/api/cards?lifecycle=published").json()
    assert listed["total"] == 1
    assert listed["items"][0]["problem_id"] == "OP-000001"
    assert listed["items"][0]["publishable"] is True

    versions = gold_client.get("/api/cards/OP-000001/versions").json()
    assert versions["items"][-1]["reason"] == "publish:publish_gate_all_clear"


def test_publish_only_from_scored_state(gold_client):
    gold_client.post("/api/cards", json=candidate_card())
    resp = gold_client.post("/api/cards/OP-900001/publish")
    assert resp.status_code == 409
    assert "非法生命周期迁移" in resp.json()["detail"]


# ---------------------------------------------------------------- 抽卡


RADIUS_VALUES = {"relevance", "adjacent_exploration", "distant_serendipity"}
DRAW_ITEM_KEYS = {
    "problem_id",
    "title",
    "one_sentence",
    "primary_domain",
    "open_status",
    "importance_band",
    "affordance_band",
    "radius",
    "score",
    "score_band",
}


def _assert_draw_item(item: dict[str, Any]) -> None:
    assert DRAW_ITEM_KEYS <= set(item)
    assert item["radius"] in RADIUS_VALUES
    assert isinstance(item["score"], float)
    assert round(item["score"], 1) == item["score"]  # 1 位小数
    assert item["one_sentence"]


def test_draw_balanced(gold_client):
    # 金标准数据下 balanced(n=6) 确定性拆分：5 relevance + 1 adjacent + 0 distant
    body = gold_client.get("/api/draw?mode=balanced&n=6").json()
    assert body["mode"] == "balanced"
    assert body["weights_version"] == "ranking-weights-v0.1"
    assert len(body["draws"]) == 6
    assert len({d["problem_id"] for d in body["draws"]}) == 6

    relevance = [d for d in body["draws"] if d["radius"] == "relevance"]
    adjacent = [d for d in body["draws"] if d["radius"] == "adjacent_exploration"]
    distant = [d for d in body["draws"] if d["radius"] == "distant_serendipity"]
    assert len(relevance) == 5 and len(adjacent) == 1 and distant == []

    scores = [d["score"] for d in relevance]
    assert scores == sorted(scores, reverse=True)  # relevance 按 user_score 降序
    assert relevance[0]["problem_id"] == "OP-000030"  # 当前权重下的最高分卡
    top_domain = relevance[0]["primary_domain"]
    assert adjacent[0]["primary_domain"] == top_domain  # adjacent 与 top1 同域
    for d in body["draws"]:
        _assert_draw_item(d)


def test_draw_steady_and_adventurous(gold_client):
    steady = gold_client.get("/api/draw?mode=steady&n=6").json()
    assert steady["mode"] == "steady"
    assert len(steady["draws"]) == 6  # steady：6 relevance + 0 + 0
    assert {d["radius"] for d in steady["draws"]} == {"relevance"}

    adventurous = gold_client.get("/api/draw?mode=adventurous&n=6").json()
    assert adventurous["mode"] == "adventurous"
    # adventurous：3 relevance + 2 adjacent（geometry 池仅剩 1 张）+ 1 distant = 5
    assert len(adventurous["draws"]) == 5
    radius_counts = {r: 0 for r in RADIUS_VALUES}
    for d in adventurous["draws"]:
        radius_counts[d["radius"]] += 1
        _assert_draw_item(d)
    assert radius_counts["relevance"] == 3
    assert radius_counts["adjacent_exploration"] == 1
    assert radius_counts["distant_serendipity"] == 1
    distant = [d for d in adventurous["draws"] if d["radius"] == "distant_serendipity"]
    assert distant[0]["primary_domain"] != "geometry"  # distant 不与 top1 同域


def test_draw_domain_filter_and_invalid_mode(gold_client):
    body = gold_client.get("/api/draw?mode=balanced&n=4&domain=number-theory").json()
    assert body["mode"] == "balanced"
    assert 0 < len(body["draws"]) <= 4
    assert all(d["primary_domain"] == "number-theory" for d in body["draws"])

    resp = gold_client.get("/api/draw?mode=yolo")
    assert resp.status_code == 422


def test_draw_pool_excludes_non_scored_states(gold_client):
    gold_client.post("/api/cards", json=candidate_card("OP-900099"))
    body = gold_client.get("/api/draw?mode=balanced&n=50").json()
    ids = {d["problem_id"] for d in body["draws"]}
    assert len(ids) == GOLD_COUNT  # 只有 30 张 scored 入池
    assert "OP-900099" not in ids


# ---------------------------------------------------------------- 来源注册表


def test_sources_listing(gold_client):
    body = gold_client.get("/api/sources").json()
    assert body["total"] == 42
    first = body["items"][0]
    for key in (
        "source_id",
        "name",
        "priority_tier",
        "trust_tier",
        "enabled",
        "source_type",
        "base_url",
    ):
        assert key in first

    tier_rank = {"P0": 0, "P1": 1, "P2": 2}
    ranks = [tier_rank.get(i["priority_tier"], 9) for i in body["items"]]
    assert ranks == sorted(ranks)  # priority_tier 升序

    enabled = gold_client.get("/api/sources?enabled=true").json()
    assert enabled["total"] == 11
    assert all(i["enabled"] is True for i in enabled["items"])

    disabled = gold_client.get("/api/sources?enabled=false").json()
    assert disabled["total"] == 31
    assert all(i["enabled"] is False for i in disabled["items"])

    resp = gold_client.get("/api/sources?enabled=maybe")
    assert resp.status_code == 422
