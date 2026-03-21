"""
SmartVocab 功能点自动化自检（毕业设计答辩前可跑一遍）

用法（在项目根目录）:
  python automation/smoke_check.py              # 全量：智能推荐模块自检 + API
  python automation/smoke_check.py --quick      # 仅首页 + /api/health（无 MySQL 也可过）
  python automation/smoke_check.py --recommend-only  # 仅测推荐引擎（可不装 Flask，需 MySQL）
  python automation/smoke_check.py --compile    # 额外做 Python 语法编译检查
  python automation/smoke_check.py --allow-db-fail  # DB 不通时仍退出 0（仅告警）
  python automation/smoke_check.py --skip-recommend # 跳过推荐模块调用（仅测 HTTP）

退出码: 0 全部通过；1 有失败项；2 缺少依赖（如未 pip install -r requirements.txt）。
"""

from __future__ import annotations

import argparse
import compileall
import os
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]

EXIT_MISSING_DEPS = 2


def _ensure_path() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def check_flask_available() -> None:
    """缺少 Web 依赖时给出明确提示。"""
    _ensure_path()
    try:
        import flask  # noqa: F401
    except ImportError:
        print(
            "ERROR: 未检测到 Flask。请在项目根目录执行:\n"
            "  pip install -r requirements.txt",
            file=sys.stderr,
        )
        raise SystemExit(EXIT_MISSING_DEPS)


def _make_client():
    _ensure_path()
    check_flask_available()
    from api.api_launcher import create_api_launcher

    launcher = create_api_launcher()
    launcher.app.config["TESTING"] = True
    return launcher.app.test_client()


def run_recommendation_module_checks() -> tuple[list[str], list[str]]:
    """
    智能推荐核心自检：包导入、权重、公开方法、各 algorithm 分支可调用。
    """
    _ensure_path()
    passed: list[str] = []
    failed: list[str] = []

    try:
        from core.recommendation import RecommendationEngine
    except Exception as e:
        failed.append(f"导入 core.recommendation.RecommendationEngine 失败: {e}")
        return passed, failed

    try:
        eng = RecommendationEngine()
    except Exception as e:
        failed.append(f"RecommendationEngine 初始化失败: {e}")
        return passed, failed

    wsum = sum(eng.weights.values())
    if abs(wsum - 1.0) < 0.02:
        passed.append(f"推荐权重之和≈1 ({wsum:.4f})")
    else:
        failed.append(f"推荐权重之和应为 1，当前为 {wsum:.4f}")

    for name in ("get_recommendations", "get_recommendation_history", "calculate_recommendation_score"):
        if callable(getattr(eng, name, None)):
            passed.append(f"RecommendationEngine.{name} 存在")
        else:
            failed.append(f"缺少方法 RecommendationEngine.{name}")

    # 各算法分支（不含 deep_learning，避免触发长时间训练）
    for algo in ("mixed", "difficulty", "frequency", "history", "random"):
        try:
            recs = eng.get_recommendations(1, limit=5, algorithm=algo)
            if not isinstance(recs, list):
                failed.append(f"算法 {algo} 返回值类型应为 list")
                continue
            if algo == "history" and len(recs) == 0:
                passed.append(f"算法 {algo} 可调用（返回 0 条，可能无学习记录）")
            else:
                passed.append(f"算法 {algo} 可调用（{len(recs)} 条）")
        except Exception as e:
            failed.append(f"算法 {algo} 调用异常: {e}")

    return passed, failed


def _json_ok(resp) -> tuple[bool, Any]:
    if resp.status_code != 200:
        return False, None
    try:
        data = resp.get_json()
    except Exception:
        return False, None
    if not isinstance(data, dict):
        return False, data
    return data.get("success") is True, data


def _check_get_api(resp, name: str) -> tuple[bool, str]:
    ok, data = _json_ok(resp)
    if ok:
        return True, f"{name} OK"
    if resp.status_code != 200:
        return False, f"{name} HTTP {resp.status_code}"
    return False, f"{name} success!=True: {data!r}"


def run_checks(quick: bool, allow_db_fail: bool) -> tuple[list[str], list[str]]:
    """返回 (passed_messages, failed_messages)。"""
    client = _make_client()
    passed: list[str] = []
    failed: list[str] = []

    def ok(msg: str) -> None:
        passed.append(msg)

    def bad(msg: str) -> None:
        failed.append(msg)

    # --- 关键路径（无 DB 也应可用）---
    r = client.get("/")
    if r.status_code == 200:
        ok("GET / 首页静态")
    else:
        bad(f"GET / HTTP {r.status_code}")

    r = client.get("/api/health")
    o, msg = _check_get_api(r, "GET /api/health")
    if o:
        ok(msg)
    else:
        bad(msg)

    if quick:
        return passed, failed

    # --- 数据库探活 ---
    r = client.get("/api/health/db")
    o, msg = _check_get_api(r, "GET /api/health/db")
    if o:
        ok(msg)
    else:
        if allow_db_fail:
            passed.append(f"[WARN] {msg}（已 --allow-db-fail）")
        else:
            bad(msg)

    if not o and not allow_db_fail:
        # 后续依赖 DB 的接口无意义
        return passed, failed

    uid = 1

    checks: list[tuple[str, Callable]] = [
        ("GET /api/levels/gates", lambda: client.get("/api/levels/gates")),
        (f"GET /api/recommendations/{uid}", lambda: client.get(f"/api/recommendations/{uid}")),
        (f"GET /api/learning/progress/{uid}", lambda: client.get(f"/api/learning/progress/{uid}")),
        (f"GET /api/learning/statistics/{uid}", lambda: client.get(f"/api/learning/statistics/{uid}")),
        (f"GET /api/learning/records/{uid}", lambda: client.get(f"/api/learning/records/{uid}")),
        (
            f"GET /api/learning/forgetting-curve/{uid}",
            lambda: client.get(f"/api/learning/forgetting-curve/{uid}"),
        ),
        (f"GET /api/plans/{uid}", lambda: client.get(f"/api/plans/{uid}")),
        (f"GET /api/plans/{uid}/active", lambda: client.get(f"/api/plans/{uid}/active")),
        (f"GET /api/evaluation/history/{uid}", lambda: client.get(f"/api/evaluation/history/{uid}")),
        (f"GET /api/levels/progress/{uid}", lambda: client.get(f"/api/levels/progress/{uid}")),
        ("GET /api/vocabulary/export", lambda: client.get("/api/vocabulary/export?format=json&limit=5")),
    ]

    for name, fn in checks:
        try:
            resp = fn()
            o, msg = _check_get_api(resp, name)
            if o:
                ok(msg)
            else:
                bad(msg)
        except Exception as e:
            bad(f"{name} 异常: {e}")

    return passed, failed


def run_compile_check() -> tuple[bool, str]:
    """编译 api / core / tools / 根目录 py，发现语法错误则失败。"""
    dirs = [ROOT / "api", ROOT / "core", ROOT / "tools"]
    files = [ROOT / "config.py", ROOT / "main.py", ROOT / "wsgi.py"]
    ok = True
    for d in dirs:
        if d.is_dir():
            r = compileall.compile_dir(str(d), quiet=1)
            ok = ok and bool(r)
    for f in files:
        if f.is_file():
            r = compileall.compile_file(str(f), quiet=1)
            ok = ok and bool(r)
    return ok, "Python compileall 通过" if ok else "compileall 失败（存在语法错误）"


def _print_results(passed: list[str], failed: list[str], title: str | None = None) -> None:
    if title:
        print(title)
    for p in passed:
        print(f"[OK] {p}")
    for f in failed:
        print(f"[FAIL] {f}")


def main(argv: list[str] | None = None) -> int:
    # 默认跳过深度学习引擎的模型加载与自动训练，避免自检耗时；若需完整加载可事先取消：
    #   set SMARTVOCAB_SKIP_DL_INIT=0
    os.environ.setdefault("SMARTVOCAB_SKIP_DL_INIT", "1")

    parser = argparse.ArgumentParser(description="SmartVocab API 自检")
    parser.add_argument("--quick", action="store_true", help="仅测首页与健康检查（不连库）")
    parser.add_argument(
        "--recommend-only",
        action="store_true",
        help="仅运行智能推荐模块自检（不启动 Flask，需数据库）",
    )
    parser.add_argument(
        "--skip-recommend",
        action="store_true",
        help="跳过推荐引擎调用（仅测 HTTP API）",
    )
    parser.add_argument(
        "--allow-db-fail",
        action="store_true",
        help="数据库健康检查失败时仍记为告警并继续测其它项",
    )
    parser.add_argument("--compile", action="store_true", help="额外运行 compileall")
    args = parser.parse_args(argv)

    print("SmartVocab smoke_check")
    print("-" * 40)

    if args.compile:
        cok, cmsg = run_compile_check()
        print(cmsg)
        if not cok:
            return 1

    if args.recommend_only:
        rp, rf = run_recommendation_module_checks()
        _print_results(rp, rf, "[智能推荐模块]")
        print("-" * 40)
        print(f"通过 {len(rp)} 项，失败 {len(rf)} 项")
        return 1 if rf else 0

    all_passed: list[str] = []
    all_failed: list[str] = []

    if not args.skip_recommend and not args.quick:
        rp, rf = run_recommendation_module_checks()
        all_passed.extend(rp)
        all_failed.extend(rf)
        _print_results(rp, rf, "[智能推荐模块]")

    try:
        hp, hf = run_checks(quick=args.quick, allow_db_fail=args.allow_db_fail)
    except ImportError as e:
        print(f"ERROR: 导入失败: {e}", file=sys.stderr)
        print("请执行: pip install -r requirements.txt", file=sys.stderr)
        return EXIT_MISSING_DEPS

    all_passed.extend(hp)
    all_failed.extend(hf)
    _print_results(hp, hf, "[HTTP API]")

    print("-" * 40)
    print(f"合计 通过 {len(all_passed)} 项，失败 {len(all_failed)} 项")

    return 1 if all_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
