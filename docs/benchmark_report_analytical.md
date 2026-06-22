# PoLaRIS Benchmark 对比评估报告

## 1. 摘要

- **Benchmark 总数**: 4
- **达标数**: 3
- **达标率**: 75.00%
- **平均 HPWL**: 7623.62 μm
- **平均利用率**: 0.6667
- **总模块数**: 56
- **总连接数**: 74
- **总重叠对数**: 0
- **评估时间**: 2026-06-22T10:04:12Z

## 2. 各 Benchmark 详细结果

| Benchmark | 来源 | 工艺 | 方法 | HPWL (μm) | 重叠 | 利用率 | 模块 | 连接 | 达标 |
|-----------|------|------|------|-----------|------|--------|------|------|------|
| tilos_ariane | tilos | NanGate45 | analytical | 9372.50 | 0 | 0.6667 | 17 | 25 | ✅ |
| apollo_ptc | apollo | 220nm SOI | analytical | 5489.00 | 0 | 0.6667 | 12 | 13 | ❌ |
| apollo_onoc | apollo | 220nm SOI | analytical | 12425.00 | 0 | 0.6667 | 15 | 23 | ✅ |
| lidar_ptc | lidar | 220nm SOI | analytical | 3208.00 | 0 | 0.6667 | 12 | 13 | ✅ |

## 3. 来源

- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
