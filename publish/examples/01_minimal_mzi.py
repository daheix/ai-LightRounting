"""示例 1：最小 MZI 电路布局布线。

演示如何用 PoLaRIS 完成一个最小 MZI 电路的自动布局与布线，
适合首次接触本工具的用户。

运行方式：
    python publish/examples/01_minimal_mzi.py

来源:
- PoLaRIS 项目: https://github.com/polaris-eda/polaris
"""

from __future__ import annotations

from polaris.data.specs import CircuitSpec, DeviceSpec
from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig


def build_mzi_circuit() -> CircuitSpec:
    """构建一个最小 MZI 电路（3 器件 2 连接）。

    结构: gc1 → mmi1 → gc2（输入耦合器 → 1x2 MMI → 输出耦合器）
    """
    return CircuitSpec(
        name="minimal_mzi",
        devices=[
            DeviceSpec(name="gc1", device_type="grating_coupler", width_um=10.0, height_um=10.0),
            DeviceSpec(name="mmi1", device_type="mmi_1x2", width_um=20.0, height_um=10.0),
            DeviceSpec(name="gc2", device_type="grating_coupler", width_um=10.0, height_um=10.0),
        ],
        connections=[
            ("gc1", "o1", "mmi1", "o1"),
            ("mmi1", "o2", "gc2", "o1"),
        ],
        canvas_w=200.0,
        canvas_h=200.0,
    )


def main() -> None:
    """运行最小 MZI 布局布线示例。"""
    print("=" * 60)
    print("PoLaRIS 示例 1：最小 MZI 电路布局布线")
    print("=" * 60)

    circuit = build_mzi_circuit()
    print(f"\n[电路] {circuit.name}: {len(circuit.devices)} 器件, {len(circuit.connections)} 连接")

    config = PipelineConfig(
        canvas_w=circuit.canvas_w,
        canvas_h=circuit.canvas_h,
        grid_size=10.0,
        max_sim_iterations=2,
        loss_target_db=5.0,
        min_bend_radius_um=5.0,
    )
    pipeline = IntegratedPipeline(config=config)
    result = pipeline.run(circuit)

    print("\n[结果]")
    print(f"  成功: {result.success}")
    print(f"  器件数: {result.n_devices}")
    print(f"  连接数: {result.n_connections}")
    print(f"  总损耗: {result.total_loss_db:.3f} dB")
    print(f"  交叉数: {result.n_crossings}")
    print(f"  DRC 通过: {result.drc_passed}")
    print(f"  仿真迭代: {result.sim_iterations}")
    print(f"  报告路径: {result.report_path}")

    print("\n[布局结果]")
    for dev_name, pos in result.placements.items():
        print(f"  {dev_name}: x={pos['x']:.1f}, y={pos['y']:.1f}")

    print("\n[布线结果]")
    for conn_key, pts in result.paths.items():
        print(f"  {conn_key}: {len(pts)} 个折线点")

    print("\n示例 1 完成。")


if __name__ == "__main__":
    main()
