"""polaris-orchestrator 编排层测试。

测试覆盖:
- test_run_eda_flow_mzi: 5 器件 MZI 完整 EDA 流程，n_success>=7, n_failed<=2
- test_run_eda_flow_strict: strict=True 模式，首 stage 失败即 raise
- test_run_eda_flow_skip: skip_stages 跳过逆向设计 stage，n_skipped>=1
- test_run_eda_flow_invalid_circuit: 非 dict circuit 直接 raise（R03）

来源（R02 学术诚信）:
- pytest 文档: https://docs.pytest.org/
- OpenROAD 流程编排: https://github.com/The-OpenROAD-Project/OpenROAD
- TILOS MacroPlacement benchmark:
  https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- gdsfactory 流程: https://gdsfactory.github.io/gdsfactory/
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
# orchestrator 依赖 8 个子模块，统一加入 sys.path
_MODULES = Path(__file__).resolve().parents[2]
for _m in ("core", "pdk", "place", "route", "sim", "verify", "inverse",
           "quantum", "orchestrator"):
    _src = str(_MODULES / _m / "src")
    if _src not in sys.path:
        sys.path.insert(0, _src)

import polaris_pdk  # noqa: E402  用于 monkey-patch
from polaris_core import make_circuit, make_device  # noqa: E402
from polaris_orchestrator import run_eda_flow  # noqa: E402


def _make_mzi_circuit() -> dict:
    """创建 5 器件 MZI 电路（gc → mmi_1x2 → 双臂波导 → mmi_2x2）。

    电路结构:
        gc1.out → mmi1.in
        mmi1.out1 → wg1.in  (上臂 100μm)
        mmi1.out2 → wg2.in  (下臂 120μm)
        wg1.out → mmi2.in1
        wg2.out → mmi2.in2

    Returns:
        polaris-core circuit dict。
    """
    gc = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    mmi = make_device(
        "mmi1", "mmi_1x2", 20, 5,
        ports=[("in", 0, 2.5, "west"),
               ("out1", 20, 1.5, "east"),
               ("out2", 20, 3.5, "east")],
    )
    wg1 = make_device(
        "wg1", "strip_waveguide", 100, 0.5,
        ports=[("in", 0, 0.25, "west"), ("out", 100, 0.25, "east")],
    )
    wg2 = make_device(
        "wg2", "strip_waveguide", 120, 0.5,
        ports=[("in", 0, 0.25, "west"), ("out", 120, 0.25, "east")],
    )
    mmi2 = make_device(
        "mmi2", "mmi_2x2", 20, 5,
        ports=[("in1", 0, 1.5, "west"), ("in2", 0, 3.5, "west"),
               ("out1", 20, 1.5, "east"), ("out2", 20, 3.5, "east")],
    )
    return make_circuit(
        "MZI", [gc, mmi, wg1, wg2, mmi2],
        [
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out1", "wg1", "in"),
            ("mmi1", "out2", "wg2", "in"),
            ("wg1", "out", "mmi2", "in1"),
            ("wg2", "out", "mmi2", "in2"),
        ],
        canvas_w=500, canvas_h=300,
    )


def test_run_eda_flow_mzi(tmp_path):
    """5 器件 MZI 完整 EDA 流程: n_success>=7, n_failed<=2。

    9 个 stage 顺序执行（含 inverse n_iterations=10 约 2 分钟）。
    验证:
    - 返回 dict 含 stages/n_success/n_failed/total_duration 字段
    - n_success >= 7（至少 7 个 stage 成功）
    - n_failed <= 2（最多 2 个 stage 失败，留容错空间）
    - 每个 stage dict 含 stage_id/name/status/duration/result/error
    - 成功 stage 的 result 非 None
    """
    circuit = _make_mzi_circuit()
    output_dir = str(tmp_path / "orchestrator_mzi")
    result = run_eda_flow(circuit, output_dir)

    # 顶层字段完整性
    assert "stages" in result, f"缺 stages 字段: {list(result.keys())}"
    assert "n_success" in result
    assert "n_failed" in result
    assert "n_skipped" in result
    assert "total_duration" in result

    # 9 个 stage（pdk 用于 stage 1 与 stage 7）
    assert len(result["stages"]) == 9, \
        f"期望 9 个 stage，实际 {len(result['stages'])}"

    # 每个 stage dict 字段完整性
    for s in result["stages"]:
        for key in ("stage_id", "name", "status", "duration", "result", "error"):
            assert key in s, f"stage {s.get('stage_id')} 缺字段: {key}"
        assert s["status"] in ("success", "failed", "skipped"), \
            f"stage {s['stage_id']} status 非法: {s['status']}"
        assert isinstance(s["duration"], float) and s["duration"] >= 0.0
        # 成功 stage 的 result 不应为 None
        if s["status"] == "success":
            assert s["result"] is not None, \
                f"stage {s['stage_id']} 成功但 result 为 None"
            assert s["error"] is None
        elif s["status"] == "failed":
            assert s["error"] is not None, \
                f"stage {s['stage_id']} 失败但 error 为 None"
            assert s["result"] is None

    # 至少 7 个成功，最多 2 个失败
    assert result["n_success"] >= 7, \
        f"n_success 期望 >=7，实际 {result['n_success']}\n" \
        + "\n".join(f"  stage {s['stage_id']}: {s['name']} {s['status']} "
                    f"{s.get('error') or ''}" for s in result["stages"])
    assert result["n_failed"] <= 2, \
        f"n_failed 期望 <=2，实际 {result['n_failed']}"

    # total_duration 为正数（9 个 stage 至少有耗时）
    assert result["total_duration"] > 0.0

    # stage_id 从 1 到 9 连续
    stage_ids = [s["stage_id"] for s in result["stages"]]
    assert stage_ids == list(range(1, 10)), \
        f"stage_id 不连续: {stage_ids}"


def test_run_eda_flow_strict(tmp_path, monkeypatch):
    """strict=True 模式: 首 stage 失败即 raise。

    用 monkey-patch 让 polaris_pdk.list_platforms raise，stage 1 PDK 目录
    失败 → strict 模式立即 raise RuntimeError（含 stage_id 信息）。
    """
    # mock list_platforms 抛异常，模拟 stage 1 失败
    def _fail_pdk():
        raise RuntimeError("mocked PDK catalog failure")
    monkeypatch.setattr(polaris_pdk, "list_platforms", _fail_pdk)

    circuit = _make_mzi_circuit()
    output_dir = str(tmp_path / "orchestrator_strict")
    with pytest.raises(RuntimeError, match="stage 1"):
        run_eda_flow(circuit, output_dir, strict=True)


def test_run_eda_flow_skip(tmp_path):
    """skip_stages 跳过 stage 8（逆向设计），加速测试。

    验证:
    - n_skipped == 1
    - 跳过的 stage status 为 "skipped"
    - 其他 stage 正常执行
    """
    circuit = _make_mzi_circuit()
    output_dir = str(tmp_path / "orchestrator_skip")
    result = run_eda_flow(circuit, output_dir, skip_stages=[8])

    assert result["n_skipped"] == 1, \
        f"n_skipped 期望 1，实际 {result['n_skipped']}"
    skipped = [s for s in result["stages"] if s["status"] == "skipped"]
    assert len(skipped) == 1
    assert skipped[0]["stage_id"] == 8
    assert skipped[0]["name"] == "逆向设计"
    # 总 stage 仍为 9
    assert len(result["stages"]) == 9


def test_run_eda_flow_invalid_circuit(tmp_path):
    """非 dict circuit 直接 raise（R03 禁止 fall-back）。

    编排层入口校验 circuit 类型，非 dict 不进入 stage 执行。
    """
    with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
        run_eda_flow("not_a_dict", str(tmp_path / "invalid"))

    # 空 output_dir 也应 raise
    circuit = _make_mzi_circuit()
    with pytest.raises(RuntimeError, match="output_dir"):
        run_eda_flow(circuit, "")
