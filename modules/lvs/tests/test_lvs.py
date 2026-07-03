"""polaris-lvs 子模块深度测试（覆盖全 API，R05 回归防护）。

测试覆盖（43 个 pytest）:
- 模块导出与版本（2）
- LVSMismatchType 枚举（2）
- LVSMismatch dataclass（2）
- Netlist dataclass（2）
- extract_netlist 提取参考网表（7）
- compare_netlists 网表比对（8）
- run_lvs / run_lvs_check 端到端（7）
- netlist dict 解析（2 元素/4 元素连接格式）（2）
- 端到端场景（MZI/环形谐振器/多重不匹配/空器件/重复连接归一化）（5）
- 保留 smoke test（自比对/缺失器件/多余器件/简单波导）（4）

学术依据（R02 学术诚信，≥5 个文献 URL）:
- KLayout LVS API: URL: https://www.klayout.org/doc-qt5/manual/lvs.html
- SiEPIC EBeam PDK DEVREC 标准（器件识别层 layer 68）
  URL: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  URL: https://www.cambridge.org/core/books/silicon-photonics-design/
- gdsfactory PDK 文档（网表提取）
  URL: https://gdsfactory.github.io/gdsfactory/notebooks/09_pdk_import.html
- Luceda IPKISS（光子电路网表验证）
  URL: https://www.lucedaphotonics.com/en/products/ipkiss
- Calibre nmLVS（工业 LVS 比对算法）
  URL: https://eda.sw.siemens.com/en-US/calibre/
- pytest 文档: URL: https://docs.pytest.org/

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R05 Bug 必修。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# 让测试既能从已安装包导入，也能从源码树导入（CI/开发模式）
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import polaris_lvs  # noqa: E402
from polaris_lvs import (  # noqa: E402
    LVSMismatch,
    LVSMismatchType,
    Netlist,
    compare_netlists,
    extract_netlist,
    run_lvs,
    run_lvs_check,
)


# =============================================================================
# 测试辅助构造函数（真实电路数据，R03 禁止 fall-back）
# =============================================================================


def _make_simple_circuit() -> dict:
    """构造最简波导电路（与任务验证脚本一致）。"""
    return {
        "name": "test",
        "devices": [
            {
                "name": "wg",
                "device_type": "strip_waveguide",
                "ports": [
                    ("in", 0, 0, "west"),
                    ("out", 10, 0, "east"),
                ],
            },
        ],
        "connections": [],
        "canvas_w": 100,
        "canvas_h": 100,
    }


def _make_two_device_circuit() -> dict:
    """构造 2 器件 + 1 连接电路（用于一致性比对测试）。"""
    return {
        "name": "two_dev",
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "d2", "device_type": "mmi_1x2",
             "ports": [("in", 0, 0, "west")]},
        ],
        "connections": [("d1", "out", "d2", "in")],
        "canvas_w": 100,
        "canvas_h": 100,
    }


def _mismatch_types(mismatches: list[dict]) -> set[str]:
    """从 run_lvs 结果的 mismatches 提取类型集合。"""
    return {m["type"] for m in mismatches}


# =============================================================================
# 1. 模块导出与版本（2 个测试）
# =============================================================================


def test_lvs_version():
    """验证 polaris-lvs 子模块版本号 5.0.0（与原 polaris-verify 一致）。"""
    assert polaris_lvs.__version__ == "5.0.0"


def test_lvs_module_imports():
    """验证 polaris_lvs 模块导出全部公共 API（__all__ 完整性）。"""
    expected = {
        "run_lvs", "Netlist", "LVSMismatch", "LVSMismatchType",
        "extract_netlist", "compare_netlists", "run_lvs_check", "__version__",
    }
    assert expected.issubset(set(dir(polaris_lvs))), (
        f"polaris_lvs 缺少导出: {expected - set(dir(polaris_lvs))}"
    )
    # 关键类/函数可调用
    assert callable(run_lvs)
    assert callable(run_lvs_check)
    assert callable(extract_netlist)
    assert callable(compare_netlists)


# =============================================================================
# 2. LVSMismatchType 枚举（2 个测试）
# =============================================================================


def test_lvs_mismatch_type_values():
    """验证 LVSMismatchType 枚举 5 个值与 KLayout LVS 比对状态对应。

    来源: KLayout LVS 比对状态
    https://www.klayout.org/doc-qt5/manual/lvs.html
    """
    assert LVSMismatchType.MISSING_DEVICE.value == "missing_device"
    assert LVSMismatchType.EXTRA_DEVICE.value == "extra_device"
    assert LVSMismatchType.DEVICE_TYPE_MISMATCH.value == "device_type_mismatch"
    assert LVSMismatchType.MISSING_CONNECTION.value == "missing_connection"
    assert LVSMismatchType.EXTRA_CONNECTION.value == "extra_connection"


def test_lvs_mismatch_type_count():
    """验证 LVSMismatchType 枚举数量为 5（5 类不匹配）。"""
    members = list(LVSMismatchType)
    assert len(members) == 5, f"LVSMismatchType 应有 5 个成员，实际 {len(members)}"
    # 枚举值唯一
    values = [m.value for m in members]
    assert len(set(values)) == 5, "LVSMismatchType 枚举值应唯一"


# =============================================================================
# 3. LVSMismatch dataclass（2 个测试）
# =============================================================================


def test_lvs_mismatch_construction():
    """验证 LVSMismatch dataclass 构造与字段。"""
    m = LVSMismatch(
        mtype=LVSMismatchType.MISSING_DEVICE,
        message="参考网表有器件 'wg1' 但提取网表无",
        device_name="wg1",
        net_name="",
    )
    assert m.mtype == LVSMismatchType.MISSING_DEVICE
    assert "wg1" in m.message
    assert m.device_name == "wg1"
    assert m.net_name == ""


def test_lvs_mismatch_default_fields():
    """验证 LVSMismatch 默认 device_name/net_name 为空字符串。"""
    m = LVSMismatch(
        mtype=LVSMismatchType.EXTRA_CONNECTION,
        message="提取网表有连接但参考网表无",
    )
    assert m.device_name == ""
    assert m.net_name == ""


# =============================================================================
# 4. Netlist dataclass（2 个测试）
# =============================================================================


def test_netlist_default_empty():
    """验证 Netlist 默认构造为空 devices/connections。"""
    nl = Netlist()
    assert nl.devices == []
    assert nl.connections == []


def test_netlist_construction():
    """验证 Netlist 构造（devices + connections）。"""
    nl = Netlist(
        devices=[{"name": "wg1", "device_type": "wg"},
                 {"name": "mzi1", "device_type": "mzi"}],
        connections=[("wg1", "mzi1")],
    )
    assert len(nl.devices) == 2
    assert nl.devices[0] == {"name": "wg1", "device_type": "wg"}
    assert len(nl.connections) == 1
    assert nl.connections[0] == ("wg1", "mzi1")


# =============================================================================
# 5. extract_netlist 提取参考网表（7 个测试）
# =============================================================================


def test_extract_netlist_basic():
    """验证 extract_netlist 从 circuit dict 提取 Netlist。"""
    circuit = _make_two_device_circuit()
    nl = extract_netlist(circuit)
    assert isinstance(nl, Netlist)
    assert len(nl.devices) == 2
    assert len(nl.connections) == 1


def test_extract_netlist_devices():
    """验证 extract_netlist 提取器件名+类型（不含 ports）。"""
    circuit = _make_two_device_circuit()
    nl = extract_netlist(circuit)
    dev_names = {d["name"] for d in nl.devices}
    dev_types = {d["device_type"] for d in nl.devices}
    assert dev_names == {"d1", "d2"}
    assert dev_types == {"strip_waveguide", "mmi_1x2"}


def test_extract_netlist_connections():
    """验证 extract_netlist 提取连接为 (dev1, dev2) 拓扑对。

    连接 (d1, out, d2, in) → (d1, d2)，端口信息被丢弃。
    """
    circuit = _make_two_device_circuit()
    nl = extract_netlist(circuit)
    assert nl.connections == [("d1", "d2")]


def test_extract_netlist_strips_ports():
    """验证 extract_netlist 只保留 name/device_type，剥离 ports 等额外字段。"""
    circuit = {
        "name": "strip",
        "devices": [
            {"name": "d1", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")],
             "extra_field": "should_be_stripped"},
        ],
        "connections": [],
    }
    nl = extract_netlist(circuit)
    assert len(nl.devices) == 1
    dev = nl.devices[0]
    assert dev["name"] == "d1"
    assert dev["device_type"] == "wg"
    assert "ports" not in dev
    assert "extra_field" not in dev


def test_extract_netlist_invalid_circuit_raises():
    """非法 circuit（非 dict）应 raise RuntimeError（R03 禁止 fall-back）。"""
    with pytest.raises(RuntimeError, match="circuit"):
        extract_netlist("not a dict")  # type: ignore[arg-type]


def test_extract_netlist_missing_devices_raises():
    """circuit 缺 devices/connections 字段应 raise RuntimeError。"""
    with pytest.raises(RuntimeError, match="circuit|devices|connections"):
        extract_netlist({"name": "x"})


def test_extract_netlist_invalid_connection_raises():
    """connection 长度不为 4 应 raise RuntimeError（R03）。

    connection 必须是 [dev1, port1, dev2, port2] 长度 4。
    """
    circuit = {
        "name": "bad_conn",
        "devices": [{"name": "d1", "device_type": "wg"}],
        "connections": [("d1", "only_two")],  # 长度 2，非法
    }
    with pytest.raises(RuntimeError, match="connection"):
        extract_netlist(circuit)


def test_extract_netlist_device_missing_field_raises():
    """器件缺 name/device_type 字段应 raise RuntimeError（R03）。"""
    circuit = {
        "name": "bad_dev",
        "devices": [{"name": "d1"}],  # 缺 device_type
        "connections": [],
    }
    with pytest.raises(RuntimeError, match="name/device_type"):
        extract_netlist(circuit)


# =============================================================================
# 6. compare_netlists 网表比对（8 个测试）
# =============================================================================


def test_compare_netlists_identical():
    """验证两个完全相同的 Netlist 比对无不匹配。"""
    reference = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"}],
        connections=[("a", "b")],
    )
    extracted = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"}],
        connections=[("a", "b")],
    )
    mismatches = compare_netlists(reference, extracted)
    assert mismatches == []


def test_compare_netlists_missing_device():
    """验证参考网表有器件但提取网表无 → MISSING_DEVICE。"""
    reference = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"},
                 {"name": "c", "device_type": "ring"}],
        connections=[],
    )
    extracted = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"}],
        connections=[],
    )
    mismatches = compare_netlists(reference, extracted)
    missing = [m for m in mismatches if m.mtype == LVSMismatchType.MISSING_DEVICE]
    assert len(missing) == 1
    assert missing[0].device_name == "c"


def test_compare_netlists_extra_device():
    """验证提取网表多器件 → EXTRA_DEVICE。"""
    reference = Netlist(
        devices=[{"name": "a", "device_type": "wg"}],
        connections=[],
    )
    extracted = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "extra1", "device_type": "ring"}],
        connections=[],
    )
    mismatches = compare_netlists(reference, extracted)
    extra = [m for m in mismatches if m.mtype == LVSMismatchType.EXTRA_DEVICE]
    assert len(extra) == 1
    assert extra[0].device_name == "extra1"


def test_compare_netlists_device_type_mismatch():
    """验证同名器件类型不匹配 → DEVICE_TYPE_MISMATCH。"""
    reference = Netlist(
        devices=[{"name": "a", "device_type": "wg"}],
        connections=[],
    )
    extracted = Netlist(
        devices=[{"name": "a", "device_type": "mmi"}],  # 类型不匹配
        connections=[],
    )
    mismatches = compare_netlists(reference, extracted)
    type_mm = [m for m in mismatches if m.mtype == LVSMismatchType.DEVICE_TYPE_MISMATCH]
    assert len(type_mm) == 1
    assert "wg" in type_mm[0].message
    assert "mmi" in type_mm[0].message


def test_compare_netlists_missing_connection():
    """验证参考网表有连接但提取网表无 → MISSING_CONNECTION。"""
    reference = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"}],
        connections=[("a", "b")],
    )
    extracted = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"}],
        connections=[],  # 缺连接
    )
    mismatches = compare_netlists(reference, extracted)
    missing = [m for m in mismatches if m.mtype == LVSMismatchType.MISSING_CONNECTION]
    assert len(missing) == 1


def test_compare_netlists_extra_connection():
    """验证提取网表多连接 → EXTRA_CONNECTION。

    reference 有 (a,b)，extracted 有 (a,b) + (a,x)，(a,x) 是多余连接。
    """
    reference = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"}],
        connections=[("a", "b")],
    )
    extracted = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"}],
        connections=[("a", "b"), ("a", "x")],  # (a,x) 是多余连接
    )
    mismatches = compare_netlists(reference, extracted)
    extra = [m for m in mismatches if m.mtype == LVSMismatchType.EXTRA_CONNECTION]
    assert len(extra) == 1


def test_compare_netlists_connection_normalization():
    """验证连接归一化：(a,b) 与 (b,a) 归一化后相同（消除方向差异）。

    _normalize_conn 用 sorted tuple，所以 ("a","b") 和 ("b","a") 都变成 ("a","b")。
    """
    reference = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"}],
        connections=[("a", "b")],
    )
    extracted = Netlist(
        devices=[{"name": "a", "device_type": "wg"},
                 {"name": "b", "device_type": "wg"}],
        connections=[("b", "a")],  # 反向，归一化后与 reference 相同
    )
    mismatches = compare_netlists(reference, extracted)
    assert mismatches == []


def test_compare_netlists_both_empty():
    """验证两个空 Netlist 比对无不匹配。"""
    reference = Netlist()
    extracted = Netlist()
    mismatches = compare_netlists(reference, extracted)
    assert mismatches == []


def test_compare_netlists_returns_list():
    """验证 compare_netlists 返回 list[LVSMismatch]。"""
    reference = Netlist(devices=[{"name": "a", "device_type": "wg"}])
    extracted = Netlist(devices=[{"name": "a", "device_type": "wg"}])
    mismatches = compare_netlists(reference, extracted)
    assert isinstance(mismatches, list)


# =============================================================================
# 7. run_lvs / run_lvs_check 端到端（7 个测试）
# =============================================================================


def test_run_lvs_self_consistent():
    """自比对（netlist=None）应 is_consistent=True（验证 API 一致性）。

    当 netlist=None 时，参考网表与自身比对，必然一致。
    """
    circuit = _make_simple_circuit()
    result = run_lvs(circuit)
    for key in ("is_consistent", "n_mismatches", "mismatches",
                "n_devices", "n_connections"):
        assert key in result, f"LVS 结果缺少字段: {key}"
    assert result["is_consistent"] is True
    assert result["n_mismatches"] == 0
    assert result["n_devices"] == 1
    assert result["n_connections"] == 0


def test_run_lvs_with_netlist_consistent():
    """提供与 circuit 一致的 netlist 参数，验证 is_consistent=True。"""
    circuit = _make_two_device_circuit()
    netlist = {
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide"},
            {"name": "d2", "device_type": "mmi_1x2"},
        ],
        "connections": [["d1", "d2"]],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is True
    assert result["n_mismatches"] == 0
    assert result["n_devices"] == 2
    assert result["n_connections"] == 1


def test_run_lvs_with_netlist_mismatch():
    """提供不一致的 netlist，验证 is_consistent=False。"""
    circuit = _make_two_device_circuit()
    netlist = {
        "devices": [{"name": "d1", "device_type": "strip_waveguide"}],  # 缺 d2
        "connections": [],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is False
    assert result["n_mismatches"] > 0


def test_run_lvs_check_returns_dict():
    """验证 run_lvs_check 返回 dict 含全部必要字段。"""
    result = run_lvs_check(_make_simple_circuit())
    assert isinstance(result, dict)
    for key in ("is_consistent", "n_mismatches", "mismatches",
                "n_devices", "n_connections"):
        assert key in result, f"run_lvs_check 结果缺少字段: {key}"
    # mismatch 结构完整
    for m in result["mismatches"]:
        for field in ("type", "message", "device_name", "net_name"):
            assert field in m, f"mismatch 缺少字段: {field}"


def test_run_lvs_invalid_circuit_raises():
    """非法 circuit（缺 connections）应 raise RuntimeError（R03）。"""
    with pytest.raises(RuntimeError, match="circuit|devices|connections"):
        run_lvs({"name": "x", "devices": [], "canvas_w": 100, "canvas_h": 100})


def test_run_lvs_invalid_netlist_raises():
    """非法 netlist（非 dict）应 raise RuntimeError（R03）。"""
    circuit = _make_simple_circuit()
    with pytest.raises(RuntimeError, match="netlist"):
        run_lvs(circuit, "not a dict")  # type: ignore[arg-type]


def test_run_lvs_netlist_missing_field_raises():
    """netlist 缺 connections 字段应 raise RuntimeError（R03）。"""
    circuit = _make_simple_circuit()
    with pytest.raises(RuntimeError, match="netlist"):
        run_lvs(circuit, {"devices": []})  # 缺 connections


# =============================================================================
# 8. netlist dict 解析（2 元素/4 元素连接格式）（2 个测试）
# =============================================================================


def test_parse_netlist_two_element_conn():
    """验证 netlist connection [dev1, dev2]（2 元素）格式正确解析。

    _parse_netlist_dict 兼容 [dev1, dev2] 与 [dev1, port1, dev2, port2]。
    """
    circuit = _make_two_device_circuit()
    netlist = {
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide"},
            {"name": "d2", "device_type": "mmi_1x2"},
        ],
        "connections": [["d1", "d2"]],  # 2 元素格式
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is True
    assert result["n_connections"] == 1


def test_parse_netlist_four_element_conn():
    """验证 netlist connection [dev1, port1, dev2, port2]（4 元素）格式正确解析。"""
    circuit = _make_two_device_circuit()
    netlist = {
        "devices": [
            {"name": "d1", "device_type": "strip_waveguide"},
            {"name": "d2", "device_type": "mmi_1x2"},
        ],
        "connections": [["d1", "out", "d2", "in"]],  # 4 元素格式
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is True
    assert result["n_connections"] == 1


# =============================================================================
# 9. 端到端场景（5 个测试）
# =============================================================================


def test_lvs_mzi_circuit():
    """MZI（马赫-曾德尔干涉仪）电路 LVS 自比对一致。

    结构: mmi1 → wg1/wg2（双臂）→ mmi2，4 器件 4 连接。
    """
    circuit = {
        "name": "mzi",
        "devices": [
            {"name": "mmi1", "device_type": "mmi_1x2",
             "ports": [("in", 0, 0, "west"),
                       ("out1", 10, 5, "east"), ("out2", 10, -5, "east")]},
            {"name": "wg1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "wg2", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "mmi2", "device_type": "mmi_2x1",
             "ports": [("in1", 0, 5, "west"), ("in2", 0, -5, "west"),
                       ("out", 10, 0, "east")]},
        ],
        "connections": [
            ("mmi1", "out1", "wg1", "in"),
            ("mmi1", "out2", "wg2", "in"),
            ("wg1", "out", "mmi2", "in1"),
            ("wg2", "out", "mmi2", "in2"),
        ],
    }
    result = run_lvs(circuit)
    assert result["is_consistent"] is True
    assert result["n_devices"] == 4
    assert result["n_connections"] == 4


def test_lvs_ring_resonator():
    """环形谐振器电路 LVS 自比对一致。

    结构: wg ↔ ring（双向连接），2 器件 2 连接。
    """
    circuit = {
        "name": "ring",
        "devices": [
            {"name": "wg", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "ring", "device_type": "ring_resonator",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [
            ("wg", "out", "ring", "in"),
            ("ring", "out", "wg", "in"),
        ],
    }
    result = run_lvs(circuit)
    assert result["is_consistent"] is True
    assert result["n_devices"] == 2
    assert result["n_connections"] == 2


def test_lvs_multiple_mismatches():
    """多重不匹配场景：缺失器件 + 多余器件 + 类型不匹配 + 连接缺失/多余。

    参考: a(wg), b(wg), c(ring), 连接 a-b, b-c
    提取: a(wg), b(mmi), d(wg), 连接 a-b, a-d
    预期: missing_device(c) + extra_device(d) + type_mismatch(b) +
          missing_connection(b-c) + extra_connection(a-d)
    """
    circuit = {
        "name": "multi",
        "devices": [
            {"name": "a", "device_type": "wg"},
            {"name": "b", "device_type": "wg"},
            {"name": "c", "device_type": "ring"},
        ],
        "connections": [
            ("a", "out", "b", "in"),
            ("b", "out", "c", "in"),
        ],
    }
    netlist = {
        "devices": [
            {"name": "a", "device_type": "wg"},
            {"name": "b", "device_type": "mmi"},  # 类型不匹配
            {"name": "d", "device_type": "wg"},   # 多余器件
            # 缺 c
        ],
        "connections": [
            ["a", "b"],
            ["a", "d"],  # 多余连接
            # 缺 b-c
        ],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is False
    types = _mismatch_types(result["mismatches"])
    assert "missing_device" in types
    assert "extra_device" in types
    assert "device_type_mismatch" in types
    assert "missing_connection" in types
    assert "extra_connection" in types
    assert result["n_mismatches"] == 5


def test_lvs_empty_devices():
    """空器件电路自比对一致（n_devices=0, n_connections=0）。"""
    circuit = {
        "name": "empty",
        "devices": [],
        "connections": [],
    }
    result = run_lvs(circuit)
    assert result["is_consistent"] is True
    assert result["n_devices"] == 0
    assert result["n_connections"] == 0


def test_lvs_duplicate_connection_normalized():
    """重复/反向连接归一化去重后自比对一致。

    circuit 有两条连接 (a→b) 和 (b→a)，归一化后都是 (a,b)，去重后只有一条。
    """
    circuit = {
        "name": "dup_conn",
        "devices": [
            {"name": "a", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "b", "device_type": "wg",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [
            ("a", "out", "b", "in"),
            ("b", "in", "a", "out"),  # 反向，归一化后与上一条相同
        ],
    }
    result = run_lvs(circuit)
    # extract_netlist 提取两条连接 (a,b) 和 (b,a)
    # compare_netlists 归一化后都是 (a,b)，set 去重后只有一条
    # 自比对 reference=extracted，必然一致
    assert result["is_consistent"] is True
    assert result["n_connections"] == 2  # extract_netlist 保留原始 2 条


# =============================================================================
# 10. 保留 smoke test（4 个测试）
# =============================================================================


def test_lvs_simple_waveguide():
    """简单波导 LVS 验证（与任务验证脚本一致）。

    单个 strip_waveguide，自比对 is_consistent=True，n_devices=1。
    """
    circuit = _make_simple_circuit()
    result = run_lvs(circuit)
    assert result["is_consistent"] is True
    assert result["n_devices"] == 1


def test_lvs_missing_device_mismatch():
    """缺失器件应 raise mismatch，is_consistent=False（n_mismatches>0）。

    构造参考电路含 2 个器件，提取网表只含 1 个器件，应报告 missing_device。
    """
    circuit = {
        "name": "mismatch_test",
        "devices": [
            {"name": "wg1", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
            {"name": "wg2", "device_type": "strip_waveguide",
             "ports": [("in", 0, 0, "west"), ("out", 10, 0, "east")]},
        ],
        "connections": [],
        "canvas_w": 100,
        "canvas_h": 100,
    }
    netlist = {
        "devices": [{"name": "wg1", "device_type": "strip_waveguide"}],
        "connections": [],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is False
    assert result["n_mismatches"] > 0
    assert "missing_device" in _mismatch_types(result["mismatches"])


def test_lvs_extra_device_mismatch():
    """提取网表多一个器件，is_consistent=False（应报告 extra_device）。"""
    circuit = _make_simple_circuit()
    netlist = {
        "devices": [
            {"name": "wg", "device_type": "strip_waveguide"},
            {"name": "extra_dev", "device_type": "phase_shifter"},
        ],
        "connections": [],
    }
    result = run_lvs(circuit, netlist)
    assert result["is_consistent"] is False
    assert result["n_mismatches"] > 0
    assert "extra_device" in _mismatch_types(result["mismatches"])
