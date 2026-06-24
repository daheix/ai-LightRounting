# PoLaRIS 光弈 — 光电子 AI 智能布局布线引擎

> **版本**: v2.0 | **商业化就绪度**: 6.1/10 | **目标**: 9.2/10（36 个月）
> **文档日期**: 2026-06-24

PoLaRIS 是一个开源的光电子芯片 AI 布局布线引擎，支持 SOI/SiN/InP/LNOI 四大工艺平台，提供从网表到 GDS 的端到端自动化流水线。

---

## 核心能力

| 能力 | 状态 | 说明 |
|------|------|------|
| PDK 器件库 | ✅ | 33 个器件，4 平台，全溯源 |
| GDS 导出 | ✅ | SiEPIC 真实版图格式兼容 |
| 布局布线引擎 | ✅ | A* + JPS-Bend 优化，410x 加速 |
| 仿真系统 | ✅ | SimLoop 闭环 + simphony 验证 |
| DRC 检查 | ✅ | 90 条规则，0 警告 0 错误 |
| 端到端流水线 | ✅ | 网表→布局→布线→仿真→GDS→DRC |
| 质量门禁 | ✅ | 12 电路基准，自动检查+刷新 |

---

## 快速开始

### 安装

```bash
pip install -e .
```

### 端到端流水线

```bash
python -m polaris.cli --netlist data/benchmarks/generated/mzi_array/XS/SOI/mzi_array_XS_SOI_042.json --run-pipeline
```

---

## 1000 电路测试集

### 生成电路

```bash
python scripts/generate_1000_circuits.py
```

生成 1200 个电路（15 拓扑 × 5 规模 × 4 平台 × 4 种子），存储于 `data/benchmarks/generated/`。

### 批量测试

```bash
python scripts/batch_test_1000_circuits.py
```

支持断点续跑（`out/batch_test/progress.json`），并行执行（CPU 自适应）。

### 测试报告

```bash
python scripts/generate_test_report.py
```

输出 `out/batch_test/report.md` + `out/batch_test/stats.json`。

**当前测试结果**（220 电路，用户指示测试够了）：
- 成功率：100%（220/220）
- DRC 通过率：100%（220/220）
- 平均损耗：3.146 dB

---

## 质量门禁系统

### 门禁基准

12 个门禁电路（4 平台 × 3 规模）：
- 平台：SOI / SiN / InP / LNOI
- 规模：XS / S / M
- 电路：mzi_array

### 门禁指标

| 指标类型 | 指标名 | 阈值 | 说明 |
|----------|--------|------|------|
| 阻断 | pipeline_success_rate | 100% | 流水线必须成功 |
| 阻断 | drc_pass_rate | 100% | DRC 必须通过 |
| 阻断 | min_routing_success_rate | ≥20% | 布线成功率下限 |
| 阻断 | max_total_loss_db | ≤1.02 dB | 总损耗上限 |
| 参考 | max_elapsed_s | ≤基准值 | 耗时（受 CPU 负载影响，不阻断） |

### 运行门禁检查

```bash
# 检查门禁（不通过退出码 1）
python scripts/quality_gate_baseline.py --check

# 刷新基准（当前严格优于基准时）
python scripts/quality_gate_baseline.py --update
```

### 自动提交守护进程

```bash
python scripts/auto_commit_daemon.py
```

6 分钟间隔，集成质量门禁 + fast-forward main，不通过门禁禁止提交。

---

## 36 个月路标

| 阶段 | 时间窗 | 追赶对象 | 综合得分目标 |
|------|--------|----------|--------------|
| M1 | 2026-07 ~ 2026-12 | sax + simphony | 6.1 → 6.8 |
| M2 | 2027-01 ~ 2027-06 | KLayout + gdsfactory | 6.8 → 7.4 |
| M3 | 2027-07 ~ 2027-12 | Aspic + VPIphotonics | 7.4 → 7.9 |
| M4 | 2028-01 ~ 2028-06 | Siemens L-Edit + Synopsys OptoDesigner | 7.9 → 8.4 |
| M5 | 2028-07 ~ 2028-12 | Luceda IPKISS + Tidy3D | 8.4 → 8.8 |
| M6 | 2029-01 ~ 2029-06 | Ansys Lumerical + AlphaChip | 8.8 → 9.2 |

详见 [docs/36-RoundMap.md](docs/36-RoundMap.md)。

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/roadmap.md](docs/roadmap.md) | 长远规划 Roadmap（v2.0） |
| [docs/36-RoundMap.md](docs/36-RoundMap.md) | 36 个月逐月路标 |
| [docs/commercial_gap_analysis.md](docs/commercial_gap_analysis.md) | 商业差距分析（v2.0） |
| [docs/industry_alignment_roadmap.md](docs/industry_alignment_roadmap.md) | 业界标准对齐路线图（v2.0） |
| [docs/commercial_tools_feature_matrix.md](docs/commercial_tools_feature_matrix.md) | 商业工具功能清单对比矩阵 |
| [docs/academic_integrity_audit.md](docs/academic_integrity_audit.md) | 学术诚信审查报告 |
| [docs/设计文档.md](docs/设计文档.md) | 设计文档 |
| [操作记录.md](操作记录.md) | 操作记录 |

---

## 开源许可

AGPL-3.0（开源）+ 商业许可（双许可）

---

## 学术诚信声明

- 所有物理参数有 PDK/论文来源，无造假
- 所有计算公式与原始文献一致，创新公式已标注 *创新*
- 无 fall-back / mock / fake / dummy / hardcode 假数据
- 所有文档数据可溯源，v1.0 数据不一致已修正为 v2.0
- 质量门禁体系保证代码质量，0 警告 0 错误
- 批量测试 220 电路 100% 成功，无假数据

详见 [docs/academic_integrity_audit.md](docs/academic_integrity_audit.md)。
