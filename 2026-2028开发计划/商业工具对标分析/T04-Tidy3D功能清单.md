# T04 Flexcompute Tidy3D 商业光子 EDA 工具功能点清单

- **工具名称**: Tidy3D
- **厂商**: Flexcompute
- **官网 URL**: https://tidy3d.simulation.cloud/ ；https://www.flexcompute.com/tidy3d
- **调研日期**: 2026-06-25
- **版本**: v1.0
- **学术诚信声明**: 本文档所有功能点均来源于 Flexcompute 官网及 Tidy3D 官方文档（docs.flexcompute.com / docs.simulation.cloud），未公开项已明确标注。

---

## 一、FDTD 求解器与硬件加速

- **GPU 加速 FDTD (GPU-accelerated FDTD)**: 基于 GPU/TPU/FPGA 等先进并行计算硬件的 FDTD 求解器，比传统 CPU 工作站快 10-5000 倍，可处理比工作站大 100-1000 倍的问题规模。来源: [https://www.flexcompute.com/tidy3d](https://www.flexcompute.com/tidy3d) ；[https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf](https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf)
- **云原生架构 (Cloud-native)**: 仿真在 Flexcompute 云服务器上运行，支持弹性云与动态资源分配，可并发数十至数百个任务而无需额外许可证或计算机。来源: [https://www.flexcompute.com/tidy3d](https://www.flexcompute.com/tidy3d) ；[https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf](https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf)
- **内存高效 FDTD 算法 (Memory-efficient FDTD Algorithms)**: 专有内存高效 FDTD 算法，针对高级 GPU 微调。来源: [https://www.flexcompute.com/tidy3d](https://www.flexcompute.com/tidy3d)
- **Yee 网格 (Yee Lattice)**: 基于 Yee 网格的交错矩形网格离散化，直接求解 Maxwell 方程。来源: [https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf](https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf)
- **虚拟 GPU 分配控制 (Virtual GPU Allocation Control)**: 通过 run_async、Job、Batch 控制云任务提交的虚拟 GPU 分配。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)

---

## 二、网格与边界条件

- **亚像素平滑 (Sub-pixel Smoothing)**: 支持亚像素平滑方案，在给定分辨率下显著提升 FDTD 精度，可在更低分辨率下运行以加速仿真并减少内存。来源: [https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf](https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf)
- **PML 边界条件 (Perfectly Matched Layer)**: 完美匹配层吸收边界，PML 区域延伸至用户定义仿真域之外。来源: [https://docs.simulation.cloud/projects/tidy3d/en/latest/notebooks/Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/latest/notebooks/Simulation.html)
- **Absorber 边界 (Adiabatic Absorber)**: 绝热吸收体，包含多层电导率渐增的吸收层，适用于色散材料与仿真边界相交的情况。来源: [https://arxiv.org/pdf/2506.16665](https://arxiv.org/pdf/2506.16665)
- **StablePML 边界**: 稳定型 PML 边界条件。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **Periodic / BlochBoundary 边界**: 支持周期性与 Bloch 边界条件。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **自动非均匀网格 (Automatic Nonuniform Meshing)**: 支持自动非均匀网格与局部网格细化 (local mesh refinement)。来源: [https://docs.simulation.cloud/projects/tidy3d/en/latest/faq/docs/grid-specification.html](https://docs.simulation.cloud/projects/tidy3d/en/latest/faq/docs/grid-specification.html)

---

## 三、材料库 (Material Library)

- **基础介质 (Medium)**: 基础均匀介质。来源: [https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html)
- **各向异性介质 (AnisotropicMedium / FullyAnisotropicMedium)**: 支持各向异性介质与完全各向异性介质。来源: [https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html)
- **PEC / PMC 介质**: 完美电导体 (PECMedium) 与完美磁导体 (PMCMedium)。来源: [https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html)
- **Pole Residue 色散模型**: 极点留数色散材料模型。来源: [https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html)
- **Sellmeier 色散模型**: Sellmeier 色散材料模型。来源: [https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html)
- **Lorentz / Debye / Drude 色散模型**: 支持 Lorentz、Debye、Drude 色散材料模型。来源: [https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html)
- **自定义介质 (CustomMedium / CustomPoleResidue / CustomSellmeier 等)**: 支持空间自定义介质（CustomMedium、CustomPoleResidue、CustomSellmeier、CustomLorentz、CustomDebye、CustomDrude、CustomAnisotropicMedium）。来源: [https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html)
- **扰动介质 (PerturbationMedium / PerturbationPoleResidue)**: 支持扰动介质模型，用于多物理耦合。来源: [https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html)
- **有损金属介质 (LossyMetalMedium)**: 有损金属介质模型（RF 模块）。来源: [https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html)

---

## 四、光源类型 (Sources)

- **平面波 (PlaneWave)**: 平面波光源，支持 angular_spec（FixedInPlaneKSpec / FixedAngleSpec）实现固定角度（频率无关传播方向）设置。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **TFSF 光源 (Total-Field Scattered-Field)**: 全场散射场光源，支持 angular_spec 字段实现固定角度 TFSF 设置，适用于孤立散射体；固定角度 TFSF 拒绝 Periodic 与 BlochBoundary 横向边界。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **TerminalWavePort 光源**: 终端驱动模式激励，用于传输线仿真，支持 reference_impedance 字段。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **模式光源 / 偶极子 / 高斯光束**: 支持模式光源、偶极子光源、高斯光束等光源类型。来源: [https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf](https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf)

---

## 五、监视器 (Monitors)

- **场监视器 (FieldMonitor)**: 频域/时域场监视器，记录电场与磁场。来源: [https://docs.simulation.cloud/projects/tidy3d/en/latest/notebooks/Metalens.html](https://docs.simulation.cloud/projects/tidy3d/en/latest/notebooks/Metalens.html)
- **点云场监视器 (PointCloudFieldMonitor)**: 在自定义点云坐标上进行频域 E/H 场采样，按点索引。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **稳态电荷残差监视器 (SteadyChargeResidualMonitor)**: 调试级 Charge 仿真监视器，记录每个 governing equation 的每节点有符号残差（Poisson/电子连续性/空穴连续性/热方程）。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **偶极子发射监视器 (DipoleEmissionMonitor)**: 偶极子发射研究插件监视器，包含核心 DipoleEmissionData、辐射强度输出等。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **功率 / 通量 / 模式监视器**: 支持功率通量监视器、模式监视器等用于测量功率、模式幅度等。来源: [https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf](https://www.flexcompute.com/assets/tidy3d/tidy3d__hardware_accelerated_electromagnetic_solver_for_fast_simulations_at_scale.pdf)

---

## 六、逆向设计与优化 (Inverse Design & Optimization)

- **伴随优化 / 自动微分 (Adjoint Optimization via autograd)**: 原生 autograd 支持（2.7+ 实验性），通过伴随方法仅需两次 FDTD 仿真即可计算梯度，与参数数量无关，支持任意函数微分。来源: [https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/Autograd1Intro.html](https://docs.flexcompute.com/projects/tidy3d/en/v2.9.2/notebooks/Autograd1Intro.html)
- **JAX 伴随插件 (jax-based adjoint plugin, 已弃用)**: 原 jax 伴随插件从 2.7 起弃用，推荐使用原生 autograd。来源: [https://www.flexcompute.com/tidy3d/examples/notebooks/AdjointPlugin1Intro/](https://www.flexcompute.com/tidy3d/examples/notebooks/AdjointPlugin1Intro/)
- **粒子群优化 (Particle Swarm Optimization, PSO)**: 支持梯度无关的粒子群进化优化。来源: [https://cdn.simulation.cloud/documents/harvard%20workshop.pdf](https://cdn.simulation.cloud/documents/harvard%20workshop.pdf)
- **遗传算法 (Genetic Algorithm, GA)**: 支持梯度无关的遗传算法优化。来源: [https://cdn.simulation.cloud/documents/harvard%20workshop.pdf](https://cdn.simulation.cloud/documents/harvard%20workshop.pdf)
- **拓扑优化 (Topology Optimization)**: 支持基于伴随方法的拓扑优化。来源: [https://cdn.simulation.cloud/documents/harvard%20workshop.pdf](https://cdn.simulation.cloud/documents/harvard%20workshop.pdf) ；[https://docs.simulation.cloud/projects/tidy3d/en/latest/faq/docs/faq/what-are-the-differences-between-adjoint-shape-topology-and-level-set-optimizations.html](https://docs.simulation.cloud/projects/tidy3d/en/latest/faq/docs/faq/what-are-the-differences-between-adjoint-shape-topology-and-level-set-optimizations.html)
- **形状优化 - 边界梯度 (Shape Optimization - Boundary Gradient)**: 支持边界梯度形状优化。来源: [https://cdn.simulation.cloud/documents/harvard%20workshop.pdf](https://cdn.simulation.cloud/documents/harvard%20workshop.pdf)
- **形状优化 - 水平集 (Shape Optimization - Level Set)**: 支持参数化水平集形状优化。来源: [https://cdn.simulation.cloud/documents/harvard%20workshop.pdf](https://cdn.simulation.cloud/documents/harvard%20workshop.pdf) ；[https://docs.simulation.cloud/projects/tidy3d/en/latest/faq/docs/faq/how-do-i-create-an-adjoint-parameterized-level-set-optimization.html](https://docs.simulation.cloud/projects/tidy3d/en/latest/faq/docs/faq/how-do-i-create-an-adjoint-parameterized-level-set-optimization.html)
- **逆向设计平台 (Inverse Design Platform)**: 提供 GUI 或 Python 一行代码将仿真转为优化的简易接口，含模式转换器、波导锥、光栅耦合器、超透镜、WDM 等示例。来源: [https://home.flexcompute.com/tidy3d/inverse-design/](https://home.flexcompute.com/tidy3d/inverse-design/)

---

## 七、用户界面与 API

- **Web GUI (Web-based Graphical User Interface)**: 基于 Web 的图形用户界面，支持通过浏览器进行大规模多物理仿真。来源: [https://www.flexcompute.com/tidy3d](https://www.flexcompute.com/tidy3d) ；[https://docs.flexcompute.com/projects/tidy3d/en/latest/index.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/index.html)
- **开源 Python API**: 开源 Python 包 (pip install tidy3d)，可编程定义 FDTD 仿真、提交管理云端仿真、下载与后处理结果。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/index.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/index.html) ；[https://github.com/flexcompute/tidy3d](https://github.com/flexcompute/tidy3d)
- **Tidy3D + AI**: 集成 AI 能力的电磁平台。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/index.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/index.html)

---

## 八、多物理与其他求解器

- **EME 求解器 (Eigenmode Expansion)**: 内置 EME 求解器，支持 EME 重叠与通量计算（使用 Yee 交错积分约定），支持 smatrix_in_basis 与 field_in_basis。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **热仿真 (Heat Simulation)**: 支持热仿真，包含热源、热边界条件、热数据用于 FDTD 仿真。来源: [https://docs.simulation.cloud/projects/tidy3d/en/latest/faq/docs/faq/how-do-i-set-a-heat-simulation.html](https://docs.simulation.cloud/projects/tidy3d/en/latest/faq/docs/faq/how-do-i-set-a-heat-simulation.html)
- **电荷仿真 (Charge Simulation)**: 支持电荷仿真，含 SteadyChargeResidualMonitor 调试监视器。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)
- **场投影 (Field Projection)**: 支持近场到远场（焦平面）的场投影，无需仿真大段空白空间。来源: [https://docs.simulation.cloud/projects/tidy3d/en/latest/notebooks/Metalens.html](https://docs.simulation.cloud/projects/tidy3d/en/latest/notebooks/Metalens.html)
- **偶极子发射研究插件 (Dipole Emission Study Plugin)**: 包含 DipoleEmissionMonitor、DipoleEmissionData、DipoleEmissionStudyData、SphericalAngleDataArray、辐射强度输出与传输属性等。来源: [https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html](https://docs.flexcompute.com/projects/tidy3d/en/latest/changelog.html)

---

## 功能点统计

| 模块 | 功能点数量 |
|------|-----------|
| FDTD 求解器与硬件加速 | 5 |
| 网格与边界条件 | 6 |
| 材料库 | 9 |
| 光源类型 | 4 |
| 监视器 | 5 |
| 逆向设计与优化 | 8 |
| 用户界面与 API | 3 |
| 多物理与其他求解器 | 5 |
| **总计** | **45** |
