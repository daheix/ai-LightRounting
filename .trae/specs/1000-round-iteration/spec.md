# PoLaRIS 千轮迭代优化工程 - Product Requirement Document

## Overview
- **Summary**: 对 PoLaRIS 光子 EDA 进行 1000 轮原子级迭代优化，覆盖 22 子包全模块，每轮聚焦一个微小改进点，确保每轮可验证、可提交、可追溯。最终目标：将 PoLaRIS 从 v4.12（100轮收官，98%可用）提升至 v5.0（1000轮收官，商业可用级）。
- **Purpose**: 通过精细化迭代，系统性填补与商业工具（Synopsys/Ansys/逍遥科技/gdsfactory）的功能差距，完善 DRC/LVS/寄生提取/良率分析等工业级功能，强化 AI RL 布局布线核心优势，为开源社区版 v0.9 beta 发布奠定坚实基础。
- **Target Users**: 光子 EDA 开发者、高校研究者、PoLaRIS 开源社区贡献者

## Goals
1. **功能补全**: 补齐 DRC 18规则几何运算、LVS 完整实现、寄生提取、良率分析等工业级功能
2. **性能优化**: FDTD/FDE/EME 等核心仿真器性能提升 30-50%（CPU 模式下，R04 合规）
3. **学术诚信**: 所有物理公式 100% 有文献溯源，每个模块 docstring ≥5 篇引用
4. **代码质量**: 圈复杂度≤15，函数≤80行，文件≤800行，测试覆盖率≥90%
5. **商业对标**: 与 gdsfactory 9.43 深度集成，核心功能对标 Synopsys OptoDesigner 70%
6. **AI 增强**: RL 布局布线算法升级，支持更大规模电路，收敛速度提升 2x
7. **文档完善**: API 文档 100% 覆盖，教程体系完整（入门→进阶→专家）

## Non-Goals (Out of Scope)
- GPU 加速实现（R04 战略限制，永久不做）
- 硬件流片验证（需 foundry 合作，非纯代码任务）
- 商业 PDK 认证（需 foundry 授权，非纯代码任务）
- GUI 专业 IDE 开发（优先 CLI + Web 基础版）
- SaaS 云服务平台建设
- 公司注册、融资等商业运营事务

## Background & Context
**当前状态（v4.12，2026-06-30）**:
- 22 子包 / 357 文件 / 121,121 行代码
- 113 项可定位 Bug 100% 修复（P0=0, P1=0, P2=0）
- 80+ 项 fall-back 消除，R03 合规
- 337 测试通过，冒烟测试 2/2
- 综合商业可用率 98%+

**商业工具差距分析**:
| 领域 | PoLaRIS | Synopsys OptoDesigner | Ansys Lumerical | gdsfactory 9.43 | 差距等级 |
|------|---------|----------------------|-----------------|-----------------|---------|
| 版图设计 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中 |
| FDTD 仿真 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | 高（R04限制） |
| FDE 模式求解 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | 中 |
| EME 本征模展开 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | 低 |
| BPM 光束传播 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | 持平 |
| RCWA 衍射 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | 低 |
| DRC 设计规则检查 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 高 |
| LVS 版图原理图一致 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | 高 |
| 寄生提取 | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | 极高 |
| 良率分析 | ⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | 极高 |
| PDK 支持 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 中 |
| RL 布局布线 | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ❌ | 领先 |
| 量子光子仿真 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ❌ | 领先 |
| AI 逆向设计 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | 持平 |

**1000 轮迭代分解策略**:
- 每轮任务粒度：1-4 小时工作量，可独立验证
- 分类：仿真类 250轮 / 版图类 200轮 / DRC+LVS 150轮 / PDK 100轮 / RL+AI 150轮 / 量子 50轮 / 性能优化 50轮 / 文档+测试 50轮
- 每轮产出：代码修改 + 单元测试 + 操作记录 + git commit

## Functional Requirements

### FR-1: DRC 18 规则完整实现
- 宽度规则（Width）：最小线宽检查
- 间距规则（Spacing）：最小间距检查
- 包围规则（Enclosure）：层包围检查
- 覆盖规则（Coverage）：层覆盖检查
- 密度规则（Density）：图形密度检查
- 凹角规则（Notch）：凹角宽度检查
- 阶梯规则（Step）：金属阶梯覆盖检查
- 通孔规则（Via）：通孔尺寸/间距检查
- 对齐规则（Alignment）：层间对齐检查
- 边缘规则（Edge）：边缘放置检查
- 面积规则（Area）：最小面积检查
- 周长规则（Perimeter）：最小周长检查
- 角度规则（Angle）：最小角度检查
- 对称性规则（Symmetry）：对称结构检查
- 阵列规则（Array）：阵列间距检查
- 端点规则（End-of-Line）：线端间距检查
- 延伸规则（Extension）：层延伸检查
- 最大宽度规则（Max Width）：最大线宽检查

### FR-2: LVS 版图原理图一致性验证
- 器件识别与提取
- 网表生成与对比
- 连接性验证
- 参数提取与匹配
- 短路/开路检测
- 悬浮节点检测

### FR-3: 寄生参数提取
- 电容提取（几何近似法）
- 电阻提取（片电阻法）
- 电感提取（近似解析法）
- S 参数生成
- SPICE 网表输出

### FR-4: 良率与统计分析
- Monte Carlo 仿真
- 工艺偏差建模
- 良率预估
- 灵敏度分析
- 最坏情况分析

### FR-5: gdsfactory 深度集成
- gdsfactory 组件库导入导出
- PDK 双向兼容
- 联合仿真流程
- KLayout 集成优化

### FR-6: RL 布局布线增强
- 更大规模电路支持（100+ 组件）
- 收敛速度提升 2x
- 多目标优化（面积+时延+损耗）
- 预训练模型库
- 混合布局（自动+手动）

### FR-7: 仿真性能优化
- FDTD 多级网格优化
- FDE 特征值求解加速
- EME 模式数自适应
- BPM 大步长算法
- JAX(CPU) 向量化增强

### FR-8: 量子光子增强
- 连续变量量子计算
- 量子纠错编码
- 光子资源态生成
- 噪声模型增强
- 实验数据拟合接口

## Non-Functional Requirements

### NFR-1: 代码质量
- 函数≤80行，文件≤800行
- 圈复杂度≤15（radon 验证）
- 测试覆盖率≥90%（pytest-cov）
- 无 TODO/FIXME/HACK 残留
- 类型注解覆盖率 100%

### NFR-2: 学术诚信
- 每个模块 docstring ≥5 篇文献引用
- 所有物理公式有溯源
- 创新点标注 `*创新*` 并详细说明
- 禁止洗稿、禁止选择性引用

### NFR-3: R03 禁止 fall-back
- 业务错误必须 raise 明确异常
- 禁止 `except: pass` / `return None` / `return []`
- 无静默兜底和假数据

### NFR-4: R04 GPU 战略
- 纯 NumPy/SciPy/JAX(CPU) 实现
- 无 CuPy/CUDA/ROCm/AppleMetal
- 无 FP16/BF16 半精度

### NFR-5: 性能
- 单元测试单文件≤30秒
- 冒烟测试≤2分钟
- 核心仿真器较 v4.12 提升≥30%

## Constraints
- **技术**: Python 3.10+ / NumPy / SciPy / JAX(CPU) / 纯 CPU 计算
- **业务**: R01-R11 项目规则强制执行
- **时间**: 1000 轮，每轮 1-4 小时，总计约 2000-4000 人时
- **依赖**: gdsfactory / KLayout（可选）/ 开源 PDK

## Assumptions
1. 开发环境：Linux + Python 3.10 + 充足 CPU 资源
2. 依赖库可用：NumPy、SciPy、JAX(CPU) 稳定运行
3. 测试环境：pytest 全量可运行
4. 提交频率：每轮完成后立即 git add + commit + push
5. 操作记录：每轮完成后 5 分钟内追加到操作记录.md

## Acceptance Criteria

### AC-1: DRC 18 规则全部实现并通过测试
- **Given**: DRC 模块 18 项规则定义清晰
- **When**: 运行 DRC 测试套件
- **Then**: 18 项规则全部有实现、有测试、有文档，测试通过率 100%
- **Verification**: `programmatic`

### AC-2: LVS 完整功能可用
- **Given**: LVS 模块具备器件提取和网表对比能力
- **When**: 对已知正确/错误版图运行 LVS
- **Then**: 正确版图通过验证，错误版图准确报错，错误定位精度≥95%
- **Verification**: `programmatic`

### AC-3: 寄生提取功能完整
- **Given**: 寄生提取模块支持电容、电阻、电感提取
- **When**: 对标准结构提取寄生参数
- **Then**: 结果与解析解误差≤10%，支持 SPICE/S 参数输出
- **Verification**: `programmatic`

### AC-4: 良率分析模块可用
- **Given**: 良率分析模块支持 Monte Carlo 仿真
- **When**: 对典型电路运行 1000 次 Monte Carlo
- **Then**: 良率估计收敛，灵敏度分析结果物理合理
- **Verification**: `programmatic`

### AC-5: gdsfactory 深度集成
- **Given**: PoLaRIS 与 gdsfactory 双向接口
- **When**: 导入 gdsfactory 组件并运行 PoLaRIS 仿真
- **Then**: 导入/导出无损失，联合仿真流程顺畅
- **Verification**: `programmatic`

### AC-6: RL 布局布线性能提升
- **Given**: RL 布局布线模块升级完成
- **When**: 对 50 组件、100 组件电路分别布线
- **Then**: 收敛速度较 v4.12 提升≥2x，成功率≥90%
- **Verification**: `programmatic`

### AC-7: 核心仿真器性能提升
- **Given**: FDTD/FDE/EME/BPM 性能优化完成
- **When**: 运行标准测试用例
- **Then**: 平均性能提升≥30%，精度损失≤1%
- **Verification**: `programmatic`

### AC-8: 代码质量达标
- **Given**: 全部 1000 轮迭代完成
- **When**: 运行 radon 复杂度检查 + pytest-cov 覆盖率检查
- **Then**: 圈复杂度≤15，覆盖率≥90%，函数≤80行，文件≤800行
- **Verification**: `programmatic`

### AC-9: 学术诚信 100% 合规
- **Given**: 全部模块代码审查完成
- **When**: 检查每个模块 docstring 文献引用
- **Then**: 每个模块≥5篇引用，物理公式 100% 有溯源，无假数据
- **Verification**: `human-judgment`

### AC-10: 操作记录完整可追溯
- **Given**: 1000 轮迭代全部完成
- **When**: 检查操作记录.md 和 git log
- **Then**: 每轮都有操作记录、有 git commit、有测试结果
- **Verification**: `programmatic`

## Open Questions
- [ ] 1000 轮中是否需要预留部分轮次应对新发现的问题？（建议预留 100 轮作为机动）
- [ ] 性能优化目标 30% 是否合理？是否需要分阶段设定目标？
- [ ] DRC/LVS 是否需要先做最小可用集再完善，还是一次性做全？
- [ ] 量子光子增强是否优先级够高？是否应先保证经典光子功能完善？
