# PoLaRIS Benchmark 对比评估报告

## 1. 摘要

- **Benchmark 总数**: 4
- **达标数**: 3
- **达标率**: 75.00%
- **平均 HPWL**: 7359.38 μm
- **平均利用率**: 0.6667
- **总模块数**: 56
- **总连接数**: 74
- **总重叠对数**: 0
- **总运行时间**: 0.6189 s
- **平均运行时间**: 0.1547 s
- **评估时间**: 2026-06-22T10:25:14Z

## 2. 各 Benchmark 详细结果

| Benchmark | 来源 | 工艺 | 方法 | HPWL (μm) | 重叠 | 利用率 | 最大拥塞 | 溢出网格 | 模块 | 连接 | 运行时间 (s) | 达标 |
|-----------|------|------|------|-----------|------|--------|----------|----------|------|------|--------------|------|
| tilos_ariane | tilos | NanGate45 | hierarchical | 8499.50 | 0 | 0.6667 | 5.9361 | 108 | 17 | 25 | 0.3954 | ✅ |
| apollo_ptc | apollo | 220nm SOI | hierarchical | 5489.00 | 0 | 0.6667 | 3.7938 | 77 | 12 | 13 | 0.0515 | ❌ |
| apollo_onoc | apollo | 220nm SOI | hierarchical | 12265.00 | 0 | 0.6667 | 11.1435 | 56 | 15 | 23 | 0.1343 | ✅ |
| lidar_ptc | lidar | 220nm SOI | hierarchical | 3184.00 | 0 | 0.6667 | 4.1949 | 78 | 12 | 13 | 0.0376 | ✅ |

## 3. 来源

- TILOS MacroPlacement: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25: https://dl.acm.org/doi/10.1145/3698364.3705355
- Congestion: Nesterenko & Hsu TCAD 2002, BoxRouter ISPD 2006
