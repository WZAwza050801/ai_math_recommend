#!/usr/bin/env python
"""连接器实联调 smoke 脚本：对指定源真实抓取 limit 条并落盘快照。

用法：
    python scripts/run_connectors_smoke.py --sources SRC-0002,SRC-0009 --limit 5
    python scripts/run_connectors_smoke.py                 # 全部 8 个已注册源

行为：
- 采集前用 data/source_registry 交叉校验 enabled=true（ADR-011）；
- 每条 RawDocument 写入 data/raw/<SRC-id>/<external_id 安全化>.json；
- 每源打印抓到条数与失败原因；网络不通/限流时如实记录并继续下一源；
- 汇总写 data/raw/_smoke_summary.json（含 errors，禁止把失败硬编码成成功）。

纪律：只采集快照，不做语义加工，不产生 Problem Card，不下"已验证"结论；
抓取内容一律当数据（FIX-002）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "connectors" / "src"))

from ai_math_connectors import CONNECTORS, PoliteSession, verify_enabled  # noqa: E402

DEFAULT_OUT_DIR = ROOT / "data" / "raw"


def sanitize_filename(external_id: str) -> str:
    """external_id -> 安全文件名（保留字母数字与 .-_，截断 120 字符）。"""
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", external_id).strip("._") or "unnamed"
    return cleaned[:120]


def run_source(source_id: str, limit: int, out_dir: Path) -> dict:
    connector_cls = CONNECTORS[source_id]
    source_dir = out_dir / source_id
    source_dir.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    connector = connector_cls()
    try:
        report = connector.fetch(limit=limit)
    except Exception as exc:  # 连接器内部未预料的异常也按失败如实记录
        return {
            "source_id": source_id,
            "connector": connector_cls.__name__,
            "count": 0,
            "expected_limit": limit,
            "duration_seconds": round(time.monotonic() - started, 2),
            "errors": [f"connector raised: {exc!r}"],
            "files": [],
        }
    finally:
        connector.session.close()

    files: list[str] = []
    for doc in report.documents:
        path = source_dir / f"{sanitize_filename(doc.external_id)}.json"
        path.write_text(doc.to_json(), encoding="utf-8")
        files.append(str(path.relative_to(ROOT)))

    return {
        "source_id": source_id,
        "connector": connector_cls.__name__,
        "count": report.count,
        "expected_limit": limit,
        "duration_seconds": round(time.monotonic() - started, 2),
        "errors": list(report.errors),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        default=",".join(CONNECTORS),
        help="逗号分隔的 source_id 列表（默认全部已注册源）",
    )
    parser.add_argument("--limit", type=int, default=5, help="每源抓取上限（默认 5）")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="快照输出目录")
    args = parser.parse_args()

    requested = [s.strip() for s in args.sources.split(",") if s.strip()]
    unknown = [s for s in requested if s not in CONNECTORS]
    if unknown:
        print(f"[config] 未注册的源（已跳过）: {', '.join(unknown)}")
    source_ids = [s for s in requested if s in CONNECTORS]
    if not source_ids:
        print("[config] 没有可运行的源。")
        return 2

    # ADR-011：未启用来源不得采集
    enabled = verify_enabled()
    blocked = [s for s in source_ids if not enabled.get(s, False)]
    if blocked:
        print(f"[config] 以下源在 data/source_registry 中未启用，拒绝采集: {', '.join(blocked)}")
        source_ids = [s for s in source_ids if enabled.get(s, False)]
    if not source_ids:
        print("[config] 启用校验后没有可运行的源。")
        return 2

    out_dir = Path(args.out)
    print(f"[run] sources={','.join(source_ids)} limit={args.limit} out={out_dir}")
    print(f"[run] UA 已固定为礼貌爬虫标识；每主机 ≥1.2s 串行、20s 超时、重试≤2。")

    results = []
    for source_id in source_ids:
        result = run_source(source_id, args.limit, out_dir)
        results.append(result)
        status = "OK" if result["count"] > 0 and not result["errors"] else (
            "PARTIAL" if result["count"] > 0 else "FAILED"
        )
        print(f"\n=== {source_id} [{result['connector']}] -> {status} ===")
        print(f"  抓到条数: {result['count']}/{result['expected_limit']}"
              f"  耗时 {result['duration_seconds']}s")
        for err in result["errors"]:
            print(f"  [error] {err}")
        for f in result["files"]:
            print(f"  [file] {f}")

        # 源与源之间也保持礼貌间隔（不同主机，主要为了避免瞬时并发观感）
        time.sleep(0.1)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "limit_per_source": args.limit,
        "results": results,
        "totals": {
            "sources": len(results),
            "ok": sum(1 for r in results if r["count"] > 0 and not r["errors"]),
            "partial": sum(1 for r in results if r["count"] > 0 and r["errors"]),
            "failed": sum(1 for r in results if r["count"] == 0),
            "documents": sum(r["count"] for r in results),
        },
    }
    summary_path = out_dir / "_smoke_summary.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    totals = summary["totals"]
    print(
        f"\n[done] 源 {totals['sources']} 个：OK {totals['ok']} / PARTIAL {totals['partial']}"
        f" / FAILED {totals['failed']}；共 {totals['documents']} 条快照。"
    )
    print(f"[done] 汇总: {summary_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
