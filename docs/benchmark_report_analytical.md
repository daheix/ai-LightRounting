# PoLaRIS Benchmark 对比评估报告

## 1. 摘要

- **Benchmark 总数**: 4
- **达标数**: 3
- **达标率**: 75.00%
- **平均 HPWL**: 7554.75 μm
- **平均利用率**: 0.6667
- **总模块数**: 56
- **总连接数**: 74
- **总重叠对数**: 0
- **总运行时间**: 0.4799 s
- **平均运行时间**: 0.1200 s
- **评估时间**: 2026-06-22T10:12:30Z

## 2. 各 Benchmark 详细结果

| Benchmark | 来源 | 工艺 | 方法 | HPWL (μm) | 重叠 | 利用率 | 模块 | 连接 | 运行时间 (s) | 达标 |
|-----------|------|------|------|-----------|------|--------|------|------|--------------|------|
| tilos_ariane | tilos | NanGate45 | analytical | 9046.00 | 0 | 0.6667 | 17 | 25 | 0.2588 | ✅ |
| apollo_ptc | apollo | 220nm SOI | analytical | 5659.00 | 0 | 0.6667 | 12 | 13 | 0.0385 | ❌ |
| apollo_onoc | apollo | 220nm SOI | analytical | 12310.00 | 0 | 0.6667 | 15 | 23 | 0.1547 | ✅ |
| lidar_ptc | lidar | 220nm SOI | analytical | 3204.00 | 0 | 0.6667 | 12 | 13 | 0.0280 | ✅ |

## 3. 来源

- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
