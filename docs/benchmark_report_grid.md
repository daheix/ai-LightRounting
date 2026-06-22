# PoLaRIS Benchmark 对比评估报告

## 1. 摘要

- **Benchmark 总数**: 4
- **达标数**: 3
- **达标率**: 75.00%
- **平均 HPWL**: 16291.76 μm
- **平均利用率**: 0.6667
- **总模块数**: 56
- **总连接数**: 74
- **总重叠对数**: 0
- **总运行时间**: 0.0005 s
- **平均运行时间**: 0.0001 s
- **评估时间**: 2026-06-22T10:12:30Z

## 2. 各 Benchmark 详细结果

| Benchmark | 来源 | 工艺 | 方法 | HPWL (μm) | 重叠 | 利用率 | 模块 | 连接 | 运行时间 (s) | 达标 |
|-----------|------|------|------|-----------|------|--------|------|------|--------------|------|
| tilos_ariane | tilos | NanGate45 | grid | 14707.00 | 0 | 0.6667 | 17 | 25 | 0.0005 | ✅ |
| apollo_ptc | apollo | 220nm SOI | grid | 11440.00 | 0 | 0.6667 | 12 | 13 | 0.0000 | ❌ |
| apollo_onoc | apollo | 220nm SOI | grid | 33550.00 | 0 | 0.6667 | 15 | 23 | 0.0000 | ✅ |
| lidar_ptc | lidar | 220nm SOI | grid | 5470.05 | 0 | 0.6667 | 12 | 13 | 0.0000 | ✅ |

## 3. 来源

- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
