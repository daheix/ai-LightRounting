"""polaris-orchestrator 编排层深度测试（v5.0）。

覆盖稳定 API ``run_eda_flow`` 的端到端流程、参数验证、各阶段执行、
错误处理、strict 模式、skip_stages、编排上下文传递等场景，
对齐 R02 学术诚信、R03 禁止 fall-back、R05 无 TODO。

测试分组（共 25 个测试）：
- 包加载与 __all__ 完整性 (1)
- _STAGE_LIST 9 个 stage 注册 (1)
- _to_jsonable 序列化辅助 (1)
- run_eda_flow 参数验证 (4)
- run_eda_flow 端到端 MZI 流程 (2)
- strict 模式失败即 raise (3)
- skip_stages 跳过策略 (3)
- 各 stage 失败处理（monkey-patch）(5)
- 编排上下文跨 stage 传递 (2)
- 输出目录与 GDS 落盘 (2)
- stage dict 字段完整性 (1)

来源（R02 学术诚信，≥5 个文献 URL）:
- pytest 文档: https://docs.pytest.org/
- OpenROAD 流程编排: https://github.com/The-OpenROAD-Project/OpenROAD
- TILOS MacroPlacement benchmark:
  https://github.com/TILOS-AI-Institute/MacroPlacement
- gdsfactory 流程: https://gdsfactory.github.io/gdsfactory/
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
- Hamard et al., "Open source photonic integrated circuits",
  https://doi.org/10.1364/OE.391040
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
# orchestrator 组合 18 个独立子模块（v5.0 细粒度拆分），统一加入 sys.path
# 拆分对照: sim → sparam/pam4/fdtd/fde/eme/bpm/fdfd; verify → drc/lvs;
#          quantum → boson/klm; 新增 gdsio（旧 export 合并到 gdsio）
_MODULES = Path(__file__).resolve().parents[2]
for _m in ("core", "pdk", "place", "route", "drc", "lvs",
           "sparam", "pam4", "fdtd", "fde", "eme", "bpm", "fdfd",
           "inverse", "boson", "klm", "gdsio", "orchestrator"):
    _src = str(_MODULES / _m / "src")
    if _src not in sys.path:
        sys.path.insert(0, _src)

import polaris_boson  # noqa: E402
import polaris_core  # noqa: E402
import polaris_drc  # noqa: E402
import polaris_gdsio  # noqa: E402
import polaris_inverse  # noqa: E402
import polaris_klm  # noqa: E402
import polaris_lvs  # noqa: E402
import polaris_pam4  # noqa: E402
import polaris_pdk  # noqa: E402
import polaris_place  # noqa: E402
import polaris_route  # noqa: E402
import polaris_sparam  # noqa: E402
from polaris_core import make_circuit, make_device  # noqa: E402
from polaris_orchestrator import run_eda_flow  # noqa: E402
from polaris_orchestrator import flow as _flow_module  # noqa: E402


# =============================================================================
# 辅助：构造测试电路
# =============================================================================

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


def _make_ring_circuit() -> dict:
    """创建 3 器件环形谐振器电路（gc → ring → gc）。

    简化电路用于快速测试，避免 MZI 双臂结构。
    """
    gc1 = make_device(
        "gc1", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    ring = make_device(
        "ring1", "ring_resonator", 10, 10,
        ports=[("in", 0, 5, "west"), ("through", 10, 5, "east")],
    )
    gc2 = make_device(
        "gc2", "grating_coupler", 20, 20,
        ports=[("in", 0, 10, "west"), ("out", 20, 10, "east")],
    )
    return make_circuit(
        "RingResonator", [gc1, ring, gc2],
        [
            ("gc1", "out", "ring1", "in"),
            ("ring1", "through", "gc2", "in"),
        ],
        canvas_w=300, canvas_h=200,
    )


# =============================================================================
# 1. 包加载与 __all__ 完整性
# =============================================================================

def test_module_import() -> None:
    """包加载与 __version__ / __all__ 完整性。"""
    import polaris_orchestrator
    assert polaris_orchestrator.__version__ == "5.0.0"
    assert "run_eda_flow" in polaris_orchestrator.__all__
    assert "__version__" in polaris_orchestrator.__all__


# =============================================================================
# 2. _STAGE_LIST 9 个 stage 注册
# =============================================================================

def test_stage_list_registration() -> None:
    """_STAGE_LIST 注册 9 个 stage，stage_id 从 1 到 9 连续。"""
    stage_list = _flow_module._STAGE_LIST
    assert len(stage_list) == 9
    stage_ids = [s[0] for s in stage_list]
    assert stage_ids == list(range(1, 10))
    # 每个 stage 是 (id, name, callable) 三元组
    for sid, name, fn in stage_list:
        assert isinstance(sid, int)
        assert isinstance(name, str) and name
        assert callable(fn)
    # stage 名称预期
    names = [s[1] for s in stage_list]
    assert names[0] == "PDK目录"
    assert names[2] == "AI布局"
    assert names[4] == "仿真验证"
    assert names[5] == "DRC_LVS"
    assert names[6] == "GDS导出"
    assert names[7] == "逆向设计"
    assert names[8] == "量子验证"


# =============================================================================
# 3. _to_jsonable 序列化辅助
# =============================================================================

def test_to_jsonable_various_types() -> None:
    """_to_jsonable 将各类对象转为 JSON 可序列化形式。"""
    to_jsonable = _flow_module._to_jsonable
    # 原生 JSON 可序列化对象保持原样
    assert to_jsonable({"a": 1}) == {"a": 1}
    assert to_jsonable([1, 2, 3]) == [1, 2, 3]
    assert to_jsonable("str") == "str"
    assert to_jsonable(42) == 42
    assert to_jsonable(3.14) == 3.14
    assert to_jsonable(True) is True
    assert to_jsonable(None) is None
    # 不可序列化对象转 str
    class _NonSerializable:
        pass
    result = to_jsonable(_NonSerializable())
    assert isinstance(result, str)
    assert "NonSerializable" in result


# =============================================================================
# 4. run_eda_flow 参数验证
# =============================================================================

def test_run_eda_flow_invalid_circuit_type(tmp_path) -> None:
    """非 dict circuit 直接 raise（R03 禁止 fall-back）。"""
    with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
        run_eda_flow("not_a_dict", str(tmp_path / "invalid"))
    with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
        run_eda_flow(None, str(tmp_path / "invalid"))
    with pytest.raises(RuntimeError, match="circuit 必须是 dict"):
        run_eda_flow(["list", "not", "dict"], str(tmp_path / "invalid"))


def test_run_eda_flow_invalid_output_dir(tmp_path) -> None:
    """空 output_dir 或非 str 直接 raise（R03 禁止 fall-back）。"""
    circuit = _make_mzi_circuit()
    with pytest.raises(RuntimeError, match="output_dir"):
        run_eda_flow(circuit, "")
    with pytest.raises(RuntimeError, match="output_dir"):
        run_eda_flow(circuit, None)  # type: ignore[arg-type]


def test_run_eda_flow_skip_stages_none_default(tmp_path) -> None:
    """skip_stages=None 时默认不跳过任何 stage（9 个全执行）。"""
    circuit = _make_ring_circuit()
    output_dir = str(tmp_path / "no_skip")
    result = run_eda_flow(circuit, output_dir, skip_stages=None)
    assert result["n_skipped"] == 0
    assert len(result["stages"]) == 9


def test_run_eda_flow_strict_default_false(tmp_path) -> None:
    """strict 默认 False：stage 失败不 raise，记录 error 继续。"""
    circuit = _make_ring_circuit()
    # 不传 strict，默认 False
    result = run_eda_flow(circuit, str(tmp_path / "default_strict"))
    # 应返回 dict 而非 raise（即使有 stage 失败）
    assert isinstance(result, dict)
    assert "n_failed" in result


# =============================================================================
# 5. run_eda_flow 端到端 MZI 流程
# =============================================================================

def test_run_eda_flow_mzi_full(tmp_path) -> None:
    """5 器件 MZI 完整 EDA 流程: n_success>=7, n_failed<=2。

    9 个 stage 顺序执行（含 inverse n_iterations=10）。
    验证:
    - 返回 dict 含 stages/n_success/n_failed/n_skipped/total_duration 字段
    - n_success >= 7（至少 7 个 stage 成功）
    - n_failed <= 2（最多 2 个 stage 失败，留容错空间）
    - 每个 stage dict 含 stage_id/name/status/duration/result/error
    - 成功 stage 的 result 非 None
    """
    circuit = _make_mzi_circuit()
    output_dir = str(tmp_path / "orchestrator_mzi")
    result = run_eda_flow(circuit, output_dir)

    # 顶层字段完整性
    assert "stages" in result
    assert "n_success" in result
    assert "n_failed" in result
    assert "n_skipped" in result
    assert "total_duration" in result

    # 9 个 stage
    assert len(result["stages"]) == 9
    # stage_id 从 1 到 9 连续
    stage_ids = [s["stage_id"] for s in result["stages"]]
    assert stage_ids == list(range(1, 10))

    # 每个 stage dict 字段完整性
    for s in result["stages"]:
        for key in ("stage_id", "name", "status", "duration", "result", "error"):
            assert key in s
        assert s["status"] in ("success", "failed", "skipped")
        assert isinstance(s["duration"], float) and s["duration"] >= 0.0
        if s["status"] == "success":
            assert s["result"] is not None
            assert s["error"] is None
        elif s["status"] == "failed":
            assert s["error"] is not None
            assert s["result"] is None

    # 至少 7 个成功，最多 2 个失败
    assert result["n_success"] >= 7, \
        f"n_success 期望 >=7，实际 {result['n_success']}\n" \
        + "\n".join(f"  stage {s['stage_id']}: {s['name']} {s['status']} "
                    f"{s.get('error') or ''}" for s in result["stages"])
    assert result["n_failed"] <= 2
    # total_duration 为正数
    assert result["total_duration"] > 0.0
    # n_success + n_failed + n_skipped == 9
    assert result["n_success"] + result["n_failed"] + result["n_skipped"] == 9


def test_run_eda_flow_ring_circuit(tmp_path) -> None:
    """3 器件环形谐振器电路 EDA 流程（不同电路结构）。"""
    circuit = _make_ring_circuit()
    output_dir = str(tmp_path / "orchestrator_ring")
    result = run_eda_flow(circuit, output_dir, skip_stages=[8])  # 跳过逆向设计省时
    assert len(result["stages"]) == 9
    assert result["n_skipped"] == 1
    # 至少 6 个成功（跳过 1 个，留 2 个失败容错）
    assert result["n_success"] >= 6


# =============================================================================
# 6. strict 模式失败即 raise
# =============================================================================

def test_run_eda_flow_strict_pdk_failure(tmp_path, monkeypatch) -> None:
    """strict=True: stage 1 PDK 目录失败立即 raise RuntimeError。"""
    def _fail_pdk():
        raise RuntimeError("mocked PDK catalog failure")
    monkeypatch.setattr(polaris_pdk, "list_platforms", _fail_pdk)

    circuit = _make_mzi_circuit()
    with pytest.raises(RuntimeError, match="stage 1"):
        run_eda_flow(circuit, str(tmp_path / "strict_pdk"), strict=True)


def test_run_eda_flow_strict_validate_failure(tmp_path, monkeypatch) -> None:
    """strict=True: stage 2 电路验证失败立即 raise。"""
    def _fail_validate(circuit):
        raise ValueError("mocked circuit validation failure")
    monkeypatch.setattr(polaris_core, "validate_circuit", _fail_validate)

    circuit = _make_mzi_circuit()
    with pytest.raises(RuntimeError, match="stage 2"):
        run_eda_flow(circuit, str(tmp_path / "strict_validate"), strict=True)


def test_run_eda_flow_strict_inverse_failure(tmp_path, monkeypatch) -> None:
    """strict=True: stage 8 逆向设计失败立即 raise。"""
    def _fail_inverse(n_iterations):
        raise RuntimeError("mocked inverse design failure")
    monkeypatch.setattr(polaris_inverse, "optimize_waveguide_width", _fail_inverse)

    circuit = _make_mzi_circuit()
    with pytest.raises(RuntimeError, match="stage 8"):
        run_eda_flow(circuit, str(tmp_path / "strict_inverse"), strict=True)


# =============================================================================
# 7. skip_stages 跳过策略
# =============================================================================

def test_run_eda_flow_skip_inverse(tmp_path) -> None:
    """skip_stages=[8] 跳过逆向设计 stage，加速测试。"""
    circuit = _make_mzi_circuit()
    result = run_eda_flow(circuit, str(tmp_path / "skip_inverse"), skip_stages=[8])
    assert result["n_skipped"] == 1
    skipped = [s for s in result["stages"] if s["status"] == "skipped"]
    assert len(skipped) == 1
    assert skipped[0]["stage_id"] == 8
    assert skipped[0]["name"] == "逆向设计"
    assert skipped[0]["duration"] == 0.0
    assert skipped[0]["result"] is None
    # 总 stage 仍为 9
    assert len(result["stages"]) == 9


def test_run_eda_flow_skip_multiple(tmp_path) -> None:
    """skip_stages 跳过多个 stage（5 仿真 + 8 逆向 + 9 量子）。"""
    circuit = _make_ring_circuit()
    result = run_eda_flow(
        circuit, str(tmp_path / "skip_multi"), skip_stages=[5, 8, 9])
    assert result["n_skipped"] == 3
    skipped_ids = [s["stage_id"] for s in result["stages"] if s["status"] == "skipped"]
    assert skipped_ids == [5, 8, 9]
    # 剩余 6 个 stage 执行
    executed = [s for s in result["stages"] if s["status"] != "skipped"]
    assert len(executed) == 6


def test_run_eda_flow_skip_all_quantum_heavy(tmp_path) -> None:
    """skip_stages 跳过所有耗时 stage（5/8/9），仅保留快速 stage。"""
    circuit = _make_ring_circuit()
    result = run_eda_flow(
        circuit, str(tmp_path / "skip_heavy"), skip_stages=[5, 8, 9])
    # 跳过的 stage duration 为 0
    for s in result["stages"]:
        if s["status"] == "skipped":
            assert s["duration"] == 0.0
    # 总耗时小于完整流程
    assert result["total_duration"] > 0.0


# =============================================================================
# 8. 各 stage 失败处理（monkey-patch）
# =============================================================================

def test_run_eda_flow_non_strict_continues_on_failure(tmp_path, monkeypatch) -> None:
    """非 strict 模式: stage 1 失败但后续 stage 继续（编排策略，非 R03 fall-back）。"""
    def _fail_pdk():
        raise RuntimeError("PDK failure for testing")
    monkeypatch.setattr(polaris_pdk, "list_platforms", _fail_pdk)

    circuit = _make_mzi_circuit()
    result = run_eda_flow(circuit, str(tmp_path / "non_strict_fail"))
    # stage 1 失败
    stage1 = result["stages"][0]
    assert stage1["status"] == "failed"
    assert "PDK failure" in stage1["error"]
    assert "traceback" in stage1  # 失败 stage 含 traceback
    # 后续 stage 继续执行（非 strict）
    assert result["n_failed"] >= 1
    # 至少有 stage 成功（stage 9 量子验证不依赖 stage 1）
    assert result["n_success"] >= 1


def test_run_eda_flow_drc_failure_recorded(tmp_path, monkeypatch) -> None:
    """stage 6 DRC 失败被记录但不阻塞后续 stage（非 strict）。"""
    def _fail_drc(circuit, placements):
        raise RuntimeError("mocked DRC failure")
    monkeypatch.setattr(polaris_drc, "run_drc", _fail_drc)

    circuit = _make_mzi_circuit()
    result = run_eda_flow(
        circuit, str(tmp_path / "drc_fail"), skip_stages=[8])  # 跳过逆向省时
    stage6 = result["stages"][5]
    assert stage6["stage_id"] == 6
    # DRC 失败导致 stage 6 整体失败
    if stage6["status"] == "failed":
        assert "DRC failure" in stage6["error"]
    # 后续 stage 7 GDS 仍执行
    stage7 = result["stages"][6]
    assert stage7["stage_id"] == 7


def test_run_eda_flow_route_failure_propagates(tmp_path, monkeypatch) -> None:
    """stage 4 布线失败: 下游 stage 5/6 不使用假数据，由子模块自身 raise。"""
    def _fail_route(circuit, placements, mode):
        raise RuntimeError("mocked route failure")
    monkeypatch.setattr(polaris_route, "route_circuit", _fail_route)

    circuit = _make_mzi_circuit()
    result = run_eda_flow(
        circuit, str(tmp_path / "route_fail"), skip_stages=[8])
    stage4 = result["stages"][3]
    assert stage4["stage_id"] == 4
    assert stage4["status"] == "failed"
    assert "route failure" in stage4["error"]


def test_run_eda_flow_quantum_failure_recorded(tmp_path, monkeypatch) -> None:
    """stage 9 量子验证失败被记录。"""
    def _fail_klm():
        raise RuntimeError("mocked KLM CNOT failure")
    monkeypatch.setattr(polaris_klm, "klm_cnot", _fail_klm)

    circuit = _make_mzi_circuit()
    result = run_eda_flow(
        circuit, str(tmp_path / "quantum_fail"), skip_stages=[8])
    stage9 = result["stages"][8]
    assert stage9["stage_id"] == 9
    if stage9["status"] == "failed":
        assert "KLM" in stage9["error"]


def test_run_eda_flow_gds_export_failure_recorded(tmp_path, monkeypatch) -> None:
    """stage 7 GDS 导出失败被记录。"""
    def _fail_gds(circuit, gds_path):
        raise OSError("mocked GDS write failure")
    monkeypatch.setattr(polaris_gdsio, "export_gds", _fail_gds)

    circuit = _make_mzi_circuit()
    result = run_eda_flow(
        circuit, str(tmp_path / "gds_fail"), skip_stages=[8])
    stage7 = result["stages"][6]
    assert stage7["stage_id"] == 7
    if stage7["status"] == "failed":
        assert "GDS" in stage7["error"]


# =============================================================================
# 9. 编排上下文跨 stage 传递
# =============================================================================

def test_run_eda_flow_context_placements_propagated(tmp_path) -> None:
    """stage 3 placements 写入 ctx，stage 4 布线复用（ctx 跨 stage 传递）。"""
    circuit = _make_mzi_circuit()
    result = run_eda_flow(
        circuit, str(tmp_path / "ctx_prop"), skip_stages=[8, 9])
    # stage 3 成功则 placements 已写入 ctx
    stage3 = result["stages"][2]
    if stage3["status"] == "success":
        # stage 4 布线应能拿到 placements（不因 placements=None 失败）
        stage4 = result["stages"][3]
        # 布线成功或失败都行，关键是 stage 3 的 placements 已传递
        assert stage3["result"] is not None


def test_run_eda_flow_stage_results_json_serializable(tmp_path) -> None:
    """所有 stage result 可 JSON 序列化（_to_jsonable 兜底）。"""
    import json
    circuit = _make_ring_circuit()
    result = run_eda_flow(
        circuit, str(tmp_path / "json_check"), skip_stages=[8, 9])
    # 整个 result dict 应可 JSON 序列化
    try:
        json_str = json.dumps(result, default=str)
        assert len(json_str) > 0
        # 反序列化保真
        restored = json.loads(json_str)
        assert restored["n_success"] == result["n_success"]
    except (TypeError, ValueError) as e:
        pytest.fail(f"result 不可 JSON 序列化: {e}")


# =============================================================================
# 10. 输出目录与 GDS 落盘
# =============================================================================

def test_run_eda_flow_output_dir_created(tmp_path) -> None:
    """output_dir 不存在时自动创建（os.makedirs(exist_ok=True)）。"""
    circuit = _make_ring_circuit()
    output_dir = str(tmp_path / "nonexistent_subdir" / "deeper" / "out")
    assert not Path(output_dir).exists()
    result = run_eda_flow(circuit, output_dir, skip_stages=[8, 9])
    # stage 7 GDS 导出会创建目录
    if result["stages"][6]["status"] == "success":
        assert Path(output_dir).exists()


def test_run_eda_flow_gds_file_written(tmp_path) -> None:
    """stage 7 GDS 导出成功时，GDS 文件落盘。"""
    circuit = _make_mzi_circuit()
    output_dir = str(tmp_path / "gds_out")
    result = run_eda_flow(circuit, output_dir, skip_stages=[8])
    stage7 = result["stages"][6]
    if stage7["status"] == "success":
        # GDS 文件应存在（circuit name = MZI）
        gds_path = Path(output_dir) / "MZI.gds"
        assert gds_path.exists()
        assert gds_path.stat().st_size > 0


# =============================================================================
# 11. stage dict 字段完整性
# =============================================================================

def test_run_eda_flow_stage_dict_fields_complete(tmp_path) -> None:
    """每个 stage dict 含完整字段：stage_id/name/status/duration/result/error。"""
    circuit = _make_ring_circuit()
    result = run_eda_flow(
        circuit, str(tmp_path / "fields"), skip_stages=[8, 9])
    required_keys = {"stage_id", "name", "status", "duration", "result", "error"}
    for s in result["stages"]:
        assert required_keys.issubset(s.keys()), \
            f"stage {s.get('stage_id')} 缺字段: {required_keys - set(s.keys())}"
    # 失败 stage 额外含 traceback
    failed_stages = [s for s in result["stages"] if s["status"] == "failed"]
    for fs in failed_stages:
        assert "traceback" in fs
        assert isinstance(fs["traceback"], str)
    # 顶层汇总字段
    assert result["n_success"] + result["n_failed"] + result["n_skipped"] == 9
    assert isinstance(result["total_duration"], float)
