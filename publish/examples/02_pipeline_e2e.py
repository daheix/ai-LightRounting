"""示例 2：端到端流水线调用（无参快速演示）。

演示 IntegratedPipeline.run() 无参调用，使用内置默认 MZI 演示电路，
适合快速验证安装是否正常。

运行方式：
    python publish/examples/02_pipeline_e2e.py

来源:
- PoLaRIS 项目: https://github.com/polaris-eda/polaris
"""

from __future__ import annotations

from polaris.pipeline.integrated import IntegratedPipeline


def main() -> None:
    """运行端到端流水线快速演示。"""
    print("=" * 60)
    print("PoLaRIS 示例 2：端到端流水线（无参快速演示）")
    print("=" * 60)

    print("\n[步骤 1] 创建 IntegratedPipeline（默认配置）")
    pipeline = IntegratedPipeline()

    print("\n[步骤 2] 调用 run() 无参执行（使用内置默认 MZI 电路）")
    result = pipeline.run()

    print("\n[结果]")
    print(f"  成功: {result.success}")
    print(f"  电路: {result.circuit_name}")
    print(f"  器件数: {result.n_devices}")
    print(f"  连接数: {result.n_connections}")
    print(f"  总损耗: {result.total_loss_db:.3f} dB")
    print(f"  DRC 通过: {result.drc_passed}")
    print(f"  仿真迭代: {result.sim_iterations}")

    print("\n[布局结果]")
    for dev_name, pos in result.placements.items():
        print(f"  {dev_name}: ({pos['x']:.1f}, {pos['y']:.1f})")

    print("\n[布线结果]")
    for conn_key, pts in result.paths.items():
        n_pts = len(pts)
        start = pts[0] if pts else None
        end = pts[-1] if pts else None
        print(f"  {conn_key}: {n_pts} 点, 起点={start}, 终点={end}")

    print("\n示例 2 完成。")


if __name__ == "__main__":
    main()
