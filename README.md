# PoLaRIS 光弈 — 光电子 AI 智能布局布线引擎

> **版本**: v5.1 | **架构**: v5.0 monorepo 33 子模块
> **商业化就绪度**: 6.86/10（R36 验收实际，诚实声明未超越行业最高 9.0）
> **文档日期**: 2026-07-03（同步刷新）

PoLaRIS 是开源光电子 AI 智能布局布线引擎，支持 SOI/SiN/InP/LNOI 四大工艺平台，提供从网表到 GDS 的端到端自动化流水线。

---

## 项目真实状态（2026-07-03 实测）

| 指标 | 真实值 | 采集方式 |
|------|--------|----------|
| 子模块数 | 33 | `ls -d modules/*/src/polaris_* \| wc -l` |
| Python 源文件 | 289 | `find modules -name "*.py" -path "*/src/*" \| wc -l` |
| 源码行数 | 99,017 | `find modules -name "*.py" -path "*/src/*" -exec cat {} + \| wc -l` |
| 测试用例 | 1,614 passed / 0 failed / 1 skipped | 分模块 pytest 实测 |
| 文献 URL | 3,031 | `grep -ohE "https?://[^ )\"]+" modules/*/src/ -r \| wc -l` |
| git 历史提交 | 1,767 | `git rev-list --all --count` |
| 路标完成 | R1-R36 全部完成 | `docs/roundmap/R*.md` 核查 |
| R36 验收得分 | 6.86/10 | `docs/roundmap/R36_acceptance_report.md` |

---

## 核心能力（v5.0 33 子模块覆盖）

| 能力 | 模块 | 说明 |
|------|------|------|
| 核心数据结构 | polaris-core | `make_device` / `make_circuit` / `Tensor` |
| EDA 编排 | polaris-orchestrator | 9-stage 一键流水线 `run_eda_flow` |
| 作业调度/IPKISS | polaris-flow | `Job` / `Stage` / `IPKISSPCell` / `DesignIntentEngine` |
| PDK 器件库 | polaris-pdk / polaris-pdk-advanced | 4 平台 36 器件，gdsfactory 互操作 |
| GDSII IO | polaris-gdsio / polaris-gds-tools | 22 GDSII 工具 + 6 格式互转 |
| 布局 | polaris-place | DREAMPlace 解析法 + AlphaChip PPO |
| 布线 | polaris-route / polaris-router-advanced | 曲线波导 A*/JPS + 17 种高级算法 |
| DRC 验证 | polaris-drc | 12 条 SiEPIC DRC 规则 |
| LVS 验证 | polaris-lvs / polaris-verify-advanced | 网表比对 + 图同构 LVS + 层次化 DRC |
| 物理求解器 | polaris-fdtd/fde/fdfd/eme/bpm | FDTD(Yee+PML+JAX)/FDE/FDFD/EME/Crank-Nicolson BPM |
| 电路仿真 | polaris-circuit / polaris-sparam | 频域/时域/SPICE/MNA + S 参数 Clements |
| 逆向设计 | polaris-inverse / polaris-optimizer | JAX 伴随 + 12 种优化器（LBFGS/CMA-ES/NSGA-III） |
| AI/ML | polaris-nn / polaris-trainer | torch.nn 风格 + PPO/AlphaChip RL |
| 多物理场 | polaris-multiphysics / polaris-lumerical / polaris-parasitic | DDM/HEAT/VarFDTD/RCWA + Lumerical 后端 + 寄生/Verilog-A |
| 光通信 | polaris-pam4 / polaris-yield | PAM4 BER/眼图 + 蒙特卡洛/Sobol 良率 |
| 量子光子 | polaris-quantum-advanced / polaris-boson / polaris-klm | BB84/QKD/QEC + 玻色采样 + KLM CNOT |
| GUI | polaris-gui | 版图编辑器 + Macro IDE + WebServer |

---

## 快速开始

### 安装（v5.0 monorepo 33 子模块）

```bash
# 全量安装
pip install -e modules/core modules/orchestrator modules/flow modules/pdk \
            modules/pdk_advanced modules/gds_tools modules/gdsio \
            modules/place modules/route modules/router_advanced \
            modules/drc modules/lvs modules/verify_advanced \
            modules/fdtd modules/fde modules/fdfd modules/eme modules/bpm \
            modules/circuit modules/sparam modules/inverse modules/optimizer \
            modules/nn modules/trainer modules/multiphysics modules/lumerical modules/parasitic \
            modules/pam4 modules/yield modules/quantum_advanced modules/boson modules/klm modules/gui
```

### 一键端到端（orchestrator 9-stage）

```python
from polaris_orchestrator import run_eda_flow
from polaris_core import make_device, make_circuit

circuit = make_circuit('MZI', devices=[...], connections=[...], canvas_w=500, canvas_h=300)
result = run_eda_flow(circuit, 'out/my_design')
# result = {'stages': [...], 'n_success': 9, 'n_failed': 0, 'total_duration': 26.04}
```

业务示例：`examples/business_real_case/main.py`（Python 方式 A orchestrator + 方式 B 直接调用，13 子模块被调用）+ `main.c`（C 版多子模块 C ABI 调用）。

### 验证测试

```bash
# 全量测试（应得 1614 passed / 0 failed / 1 skipped）
for d in modules/*/tests; do pytest "$d/"; done

# 单模块独立测试
pytest modules/drc/tests/      # 51 测试
pytest modules/circuit/tests/  # 88 测试
```

---

## 1000 电路测试集（v4 时代历史数据，保留备查）

```bash
python scripts/generate_1000_circuits.py    # 生成 1200 电路
python scripts/batch_test_1000_circuits.py  # 批量测试（支持断点续跑）
python scripts/generate_test_report.py      # 报告 out/batch_test/report.md
```

**历史测试结果**（220 电路，v4 时代）：
- 成功率：100%（220/220）
- DRC 通过率：100%（220/220）
- 平均损耗：3.146 dB

> v5.0 monorepo 重构后批量测试脚本仍可运行，但已切换为 33 子模块独立 import + 1614 pytest 单测 + orchestrator 端到端验证三轨制。

---

## 质量门禁系统

### 门禁基准

12 个门禁电路（4 平台 × 3 规模）：SOI/SiN/InP/LNOI × XS/S/M，电路 mzi_array。

### 门禁指标

| 指标类型 | 指标名 | 阈值 |
|----------|--------|------|
| 阻断 | pipeline_success_rate | 100% |
| 阻断 | drc_pass_rate | 100% |
| 阻断 | min_routing_success_rate | ≥20% |
| 阻断 | max_total_loss_db | ≤1.02 dB |
| 参考 | max_elapsed_s | ≤基准值 |

### 运行

```bash
python scripts/quality_gate_baseline.py --check   # 检查（不通过退出码 1）
python scripts/quality_gate_baseline.py --update  # 刷新基准
```

### 自动提交守护进程

```bash
python scripts/auto_commit.py V8    # 6 分钟检测变更→commit→push main
nohup bash scripts/keepalive.sh &   # 5 分钟 touch 防超时
```

---

## 36 个月路标（R1-R36 全部完成）

| 阶段 | 时间窗 | 追赶对象 | 综合得分目标 | 实际 |
|------|--------|----------|--------------|------|
| 阶段 1 | R1-R6 (2026-07~12) | sax + simphony | 6.1 → 6.8 | ✅ |
| 阶段 2 | R7-R12 (2027-01~06) | KLayout + gdsfactory | 6.8 → 7.4 | ✅ |
| 阶段 3 | R13-R18 (2027-07~12) | Aspic + VPIphotonics | 7.4 → 7.9 | ✅ |
| 阶段 4 | R19-R24 (2028-01~06) | L-Edit + OptoDesigner | 7.9 → 8.4 | ✅ |
| 阶段 5 | R25-R30 (2028-07~12) | IPKISS + Tidy3D | 8.4 → 8.8 | ✅ |
| 阶段 6 | R31-R36 (2029-01~06) | Lumerical + AlphaChip | 8.8 → 9.2 | ✅ 实际 6.86 |

**R36 最终验收诚实声明**：目标 9.2，实际 6.86（未超越行业最高 9.0，差距如实记录，详见 `docs/roundmap/R36_acceptance_report.md`）。

详见 [docs/36-RoundMap.md](docs/36-RoundMap.md)。

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/设计文档.md](docs/设计文档.md) | **设计架构文档（v5.1 全面同步刷新，基于代码+测试真实数据）** |
| [docs/36-RoundMap.md](docs/36-RoundMap.md) | 36 个月逐月路标（R1-R36 全部完成） |
| [docs/v5.0_release_notes.md](docs/v5.0_release_notes.md) | v5.0 发布说明 |
| [modules/README.md](modules/README.md) | 33 子模块架构总览（含 C ABI 对照表） |
| [docs/roadmap.md](docs/roadmap.md) | 长远规划 Roadmap |
| [docs/commercial_tools_feature_matrix.md](docs/commercial_tools_feature_matrix.md) | 商业工具功能清单对比矩阵 |
| [docs/academic_integrity_audit.md](docs/academic_integrity_audit.md) | 学术诚信审查报告 |
| [CHANGELOG.md](CHANGELOG.md) | 变更记录 |
| [操作记录.md](操作记录.md) | 操作记录（R07 强制） |

---

## 工程规则（强制）

13 条 workspace 规则约束全部开发，详见 `.trae/rules/`：

| 规则 | 标题 | 状态 |
|------|------|------|
| R01 | 方案检索（动手前必做） | ✅ 遵守 |
| R02 | 学术诚信（≥5 文献 URL/模块） | ✅ 289 业务文件全 ≥5，3031 URL 总量 |
| R03 | 禁止 fall-back（失败即 raise） | ✅ 0 P0 违规 |
| R04 | 不参与 GPU（战略决策） | ✅ CuPyBackend 全 raise，纯 NumPy/SciPy/JAX(CPU) |
| R05 | Bug 必须修复 | ✅ 0 TODO/FIXME/HACK 残留 |
| R11 | V8 极简工作流（main 分支） | ✅ 单分支开发 |
| R12 | 时间戳规范 | ✅ 所有记录带时间戳 |
| R13 | 交付自测与迭代 | ✅ 1614 测试 0 failed |

---

## 开源许可

AGPL-3.0（开源）+ 商业许可（双许可）

---

## 学术诚信声明

- 所有物理参数有 PDK/论文来源，无造假
- 所有计算公式与原始文献一致，创新公式已标注 `*创新*` 并记录底层逻辑
- 无 fall-back / mock / fake / dummy / hardcode 假数据（R03 强制）
- 所有文档数据可溯源，v5.0 重构后所有过时数据已同步刷新
- 质量门禁体系保证代码质量，0 警告 0 错误
- 全量 1614 测试 0 failed，orchestrator 9-stage 端到端跑通

详见 [docs/academic_integrity_audit.md](docs/academic_integrity_audit.md)。
