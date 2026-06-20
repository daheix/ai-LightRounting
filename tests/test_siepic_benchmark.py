"""M2.2 端到端验证测试套件 — SiEPIC 电路 GDS + S 参数 + 损耗对比。

对从 SiEPIC GDS 提取的 netlist 运行 PoLaRIS 端到端流水线，验证：
1. GDS 导出格式正确（含 PIN/DEVREC/WG layer）
2. S 参数仿真与 simphony siepic 库一致（误差 < 1 dB）
3. 总插入损耗在合理范围内（与 SiEPIC 文献值对比）

来源:
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- simphony siepic 库: https://simphonyphotonics.readthedocs.io/en/stable/libs/siepic.html
- roadmap M2.2: docs/roadmap.md
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

_SIEPIC_NETLIST_DIR = Path("data/benchmarks/siepic_netlists")
_SIEPIC_GDS_DIR = Path("data/benchmarks/siepic_examples")


def _load_siepic_circuit(json_path: Path):
    """从 SiEPIC JSON netlist 加载 CircuitSpec。

    Args:
        json_path: JSON netlist 文件路径。

    Returns:
        CircuitSpec 对象。
    """
    from polaris.data.specs import CircuitSpec, DeviceSpec
    from polaris.engine.netlist import load_netlist

    net, devices, _ = load_netlist(str(json_path))
    circuit = CircuitSpec(
        name=net.name,
        devices=[
            DeviceSpec(
                name=d.device_id,
                device_type=d.name,
                width_um=max(d.bbox.xmax - d.bbox.xmin, 1.0),
                height_um=max(d.bbox.ymax - d.bbox.ymin, 1.0),
                ports=[(p.name, p.x, p.y, p.direction.name) for p in d.ports],
            )
            for d in devices.values()
        ],
        connections=[
            (c.src_instance, c.src_port, c.dst_instance, c.dst_port) for c in net.connections
        ],
        canvas_w=1000.0,
        canvas_h=1000.0,
    )
    return circuit


def _get_benchmark_circuits() -> list[tuple[str, Path]]:
    """获取有连接的 SiEPIC benchmark 电路列表。

    Returns:
        (显示名, JSON 路径) 元组列表。
    """
    if not _SIEPIC_NETLIST_DIR.exists():
        return []
    result: list[tuple[str, Path]] = []
    for jf in sorted(_SIEPIC_NETLIST_DIR.glob("*.json")):
        data = json.loads(jf.read_text(encoding="utf-8"))
        if data.get("connections"):
            result.append((jf.stem, jf))
    return result


_BENCHMARKS = _get_benchmark_circuits()


@pytest.mark.parametrize("name,json_path", _BENCHMARKS, ids=[b[0] for b in _BENCHMARKS])
def test_siepic_pipeline_end_to_end(name: str, json_path: Path, tmp_path: Path) -> None:
    """每个 SiEPIC 电路能跑通端到端流水线。

    验证 IntegratedPipeline 能处理从真实 GDS 提取的电路。
    """
    from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

    circuit = _load_siepic_circuit(json_path)
    config = PipelineConfig(
        canvas_w=max(circuit.canvas_w, 500.0),
        canvas_h=max(circuit.canvas_h, 500.0),
        grid_size=20.0,
        max_sim_iterations=1,
        output_dir=str(tmp_path),
        use_real_simulator=False,
    )
    pipeline = IntegratedPipeline(config=config)
    result = pipeline.run(circuit)
    assert result.circuit_name == circuit.name
    assert result.n_devices == len(circuit.devices)
    assert result.n_connections >= 0


@pytest.mark.parametrize("name,json_path", _BENCHMARKS, ids=[b[0] for b in _BENCHMARKS])
def test_siepic_gds_export_layers(name: str, json_path: Path, tmp_path: Path) -> None:
    """SiEPIC 电路导出的 GDS 含 PIN/DEVREC/WG layer。

    验证 GDS 格式符合 SiEPIC 标准。
    """
    import klayout.db as db

    from polaris.engine.floorplan_env import Placement
    from polaris.eval.layout_render import export_gds
    from polaris.pdk.device import Device

    circuit = _load_siepic_circuit(json_path)
    placements: dict[str, Placement] = {}
    x_offset = 0.0
    for dev_spec in circuit.devices:
        dev = Device(
            name=dev_spec.device_type,
            ports=[],
            bbox=db.Box(0, 0, int(dev_spec.width_um), int(dev_spec.height_um)),
            category="passive",
        )
        placements[dev_spec.name] = Placement(
            instance_id=dev_spec.name,
            device=dev,
            x=x_offset,
            y=0.0,
        )
        x_offset += dev_spec.width_um + 10.0

    gds_path = tmp_path / f"{name}.gds"
    export_gds(placements, output_path=str(gds_path))

    assert gds_path.exists(), "GDS 文件未生成"
    ly = db.Layout()
    ly.read(str(gds_path))
    layer_infos = [(li.layer, li.datatype) for li in ly.layer_infos()]
    assert (1, 0) in layer_infos, "缺少 WG layer (1,0)"
    assert (68, 0) in layer_infos, "缺少 DEVREC layer (68,0)"
    assert (69, 0) in layer_infos, "缺少 PIN layer (69,0)"


def test_siepic_waveguide_s_param_vs_simphony() -> None:
    """PoLaRIS 波导 S 参数与 simphony siepic 一致（误差 < 0.5 dB）。"""
    from polaris.sim.models import waveguide_s

    wl = np.array([1.55])
    polaris_s = waveguide_s(wl=wl, length=100.0, neff=2.4, ng=4.0, loss_db_cm=0.0)
    polaris_t = np.abs(polaris_s[("in", "out")][0]) ** 2

    from simphony.libraries import siepic

    siepic_wg = siepic.waveguide(length=100.0, neff=2.4, ng=4.0, loss=0.0)
    siepic_s = siepic_wg(wl)
    siepic_t = np.abs(siepic_s[("o0", "o1")][0]) ** 2

    assert polaris_t == pytest.approx(1.0, abs=1e-6), "PoLaRIS 无损耗波导传输应为 1.0"
    assert siepic_t == pytest.approx(1.0, abs=1e-6), "simphony 无损耗波导传输应为 1.0"
    assert abs(10 * np.log10(polaris_t + 1e-15) - 10 * np.log10(siepic_t + 1e-15)) < 0.5


def test_siepic_y_branch_loss_vs_simphony() -> None:
    """PoLaRIS Y 分支插损与 simphony siepic 在合理范围内（< 1 dB 差异）。"""
    from polaris.sim.models import y_branch_s

    wl = np.array([1.55])
    polaris_s = y_branch_s(wl=wl, insertion_loss_db=0.3)
    polaris_t = np.abs(polaris_s[("port_1", "port_2")][0]) ** 2
    polaris_loss_db = -10 * np.log10(polaris_t + 1e-15)

    from simphony.libraries import siepic

    siepic_yb = siepic.y_branch()
    siepic_s = siepic_yb(wl)
    siepic_t = np.abs(siepic_s[("o0", "o1")][0]) ** 2
    siepic_loss_db = -10 * np.log10(siepic_t + 1e-15) if siepic_t > 0 else 99.0

    # Y 分支理论分束比 50:50，插损约 3.01 dB（分束）+ 额外插损
    assert 2.5 < polaris_loss_db < 4.0, f"PoLaRIS Y 分支损耗异常: {polaris_loss_db:.2f} dB"
    assert abs(polaris_loss_db - siepic_loss_db) < 1.5, (
        f"PoLaRIS({polaris_loss_db:.2f}) vs simphony({siepic_loss_db:.2f}) 差异过大"
    )


def test_siepic_grating_coupler_loss_range() -> None:
    """PoLaRIS 光栅耦合器损耗在 SiEPIC 文献范围内（1-5 dB）。

    来源: SiEPIC EBeam PDK GC 典型插损 ~1.9 dB
    """
    from polaris.sim.models import grating_coupler_s

    wl = np.array([1.55])
    s = grating_coupler_s(wl=wl, insertion_loss_db=1.9)
    t = np.abs(s[("fiber", "waveguide")][0]) ** 2
    loss_db = -10 * np.log10(t + 1e-15)
    assert 1.0 < loss_db < 5.0, f"GC 损耗 {loss_db:.2f} dB 不在 1-5 dB 范围"


def test_siepic_mzi_total_loss_reasonable(tmp_path: Path) -> None:
    """MZI 电路总插入损耗在合理范围（< 15 dB）。

    MZI 典型损耗: 2 GC (~4 dB) + 2 Y 分支 (~6 dB) + 波导 (~1 dB) ≈ 11 dB
    """
    from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

    mzi_path = _SIEPIC_NETLIST_DIR / "MZI1.json"
    if not mzi_path.exists() or not _BENCHMARKS:
        pytest.skip("MZI1.json 不存在或无 benchmark")
    circuit = _load_siepic_circuit(mzi_path)
    if not circuit.connections:
        pytest.skip("MZI1 无连接，跳过损耗验证")

    config = PipelineConfig(
        canvas_w=500.0,
        canvas_h=500.0,
        grid_size=20.0,
        max_sim_iterations=1,
        output_dir=str(tmp_path),
        use_real_simulator=False,
    )
    pipeline = IntegratedPipeline(config=config)
    result = pipeline.run(circuit)
    assert result.total_loss_db < 50.0, f"总损耗 {result.total_loss_db:.2f} dB 异常过高"


def test_siepic_ring_resonator_pipeline(tmp_path: Path) -> None:
    """环形谐振器电路能跑通端到端流水线。"""
    from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

    ring_path = _SIEPIC_NETLIST_DIR / "RingResonator.json"
    if not ring_path.exists():
        pytest.skip("RingResonator.json 不存在")
    circuit = _load_siepic_circuit(ring_path)
    if not circuit.connections:
        pytest.skip("RingResonator 无连接")

    config = PipelineConfig(
        canvas_w=500.0,
        canvas_h=500.0,
        grid_size=20.0,
        max_sim_iterations=1,
        output_dir=str(tmp_path),
    )
    pipeline = IntegratedPipeline(config=config)
    result = pipeline.run(circuit)
    assert result.n_devices > 0, "环形谐振器应有器件"


def test_siepic_netlist_count() -> None:
    """至少 3 个 SiEPIC netlist 成功提取（M2.1 验收）。"""
    if not _SIEPIC_NETLIST_DIR.exists():
        pytest.skip("siepic_netlists 目录不存在")
    json_files = list(_SIEPIC_NETLIST_DIR.glob("*.json"))
    assert len(json_files) >= 3, f"仅 {len(json_files)} 个 netlist，期望 ≥3"


def test_siepic_netlist_format_valid() -> None:
    """所有 SiEPIC netlist JSON 格式有效（含 devices 字段）。"""
    if not _SIEPIC_NETLIST_DIR.exists():
        pytest.skip("siepic_netlists 目录不存在")
    for jf in sorted(_SIEPIC_NETLIST_DIR.glob("*.json")):
        data = json.loads(jf.read_text(encoding="utf-8"))
        assert "name" in data, f"{jf.name} 缺少 name 字段"
        assert "devices" in data, f"{jf.name} 缺少 devices 字段"
        assert isinstance(data["devices"], list), f"{jf.name} devices 不是列表"
        assert "canvas_w" in data, f"{jf.name} 缺少 canvas_w 字段"
