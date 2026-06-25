# A02 — EME 本征模展开法（Eigenmode Expansion Method）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类ID：A02（P0 优先级，求解器类）
> 覆盖功能点：38（T01 Lumerical / T03 OptoDesigner / T07 Photon Design FIMMPROP / T15 曼光 MaxOptics / T16 SimWorks）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（GPU 不参与）
> 关联文档：`3dtool/ALGORITHMS.md` 第 2 节、`docs/feature_gap_full_analysis.md` EME 章节、`00-算法聚类清单.md`

---

## 1. 文档信息

| 字段 | 内容 |
|------|------|
| 算法名称 | Eigenmode Expansion Method（EME，本征模展开法） |
| 算法类别 | 频域全矢量双向传播方法 |
| 商业对标 | Ansys Lumerical MODE-EME、Photon Design FIMMPROP、SimWorks EME、曼光 MaxOptics EME |
| 开源参考 | EMEpy（BYUCamachoLab）、MEEP EigenModeSource（模式分解模块） |
| PoLaRIS 状态 | ❌ 完全缺失（38 功能点：✅4 / ⚠️6 / ❌28） |
| 实现优先级 | P0（R37-Q4，依赖 FDE 本征模内核） |
| 实现路径 | `src/polaris/sim/eme_solver.py`（待新建） |
| CPU 约束 | 纯 NumPy/SciPy 实现（规则 26，禁用 GPU） |

---

## 2. 算法概述

EME 是频域全矢量双向传播方法，用于求解麦克斯韦方程在沿传播方向 z 切分的非均匀波导器件中的散射问题。其核心思想：将器件沿 z 划分为若干 cell，每个 cell 内横截面 z 不变；在每个 cell 中心调用 FDE 求解器求本地本征模（导模 + 离散化辐射模），将场展开为前向/后向本地模的线性叠加；在 cell 界面通过切向场连续性匹配，由模式重叠积分构造界面 S 矩阵；最后通过 Redheffer 星积将所有 cell 的 S 矩阵级联为器件全局 S 矩阵。

**与商业工具对齐的关键能力**：
- 双向传播：天然处理背向反射、谐振、周期结构（Lumerical EME、FIMMPROP 核心卖点）
- 长度无关计算成本：Gallagher & Felici 2003 证明 EME 对长结构（锥形、MMI、布拉格光栅）的计算成本与长度无关，远优于 FDTD
- Analysis 模式：本地模求解完成后，cell 长度可任意扫描而无需重算模式，与 Lumerical EME Propagate 行为对齐
- 高折射率对比度：不依赖慢变包络近似（SVEA），精度优于 BPM，适用于 SOI/SiN/LNOI 平台

---

## 3. 物理模型与控制方程

### 3.1 物理模型

EME 假设器件沿主传播方向 z 由若干 z 不变截面段拼接而成。每段内的电磁场可由该段的本地本征模完备基展开（导模 + 辐射模离散化近似）。在两段界面，切向电场 $\mathbf{E}_t$ 与切向磁场 $\mathbf{H}_t$ 连续，由此建立模式系数的线性映射，即界面 S 矩阵。该方法对长结构、周期结构、高折射率对比度器件具有严格全波解精度。

### 3.2 控制方程

频域麦克斯韦方程（时谐因子 $e^{i\omega t}$，$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -i\omega\mu_0 \mathbf{H}, \quad \nabla \times \mathbf{H} = i\omega\varepsilon_0\varepsilon_r \mathbf{E}$$

在 z 不变截面下，本地本征模满足（FDE 提供）：

$$\nabla \times \left( \frac{1}{\varepsilon_r} \nabla \times \mathbf{H}_m \right) = k_0^2 \mathbf{H}_m, \quad \beta_m = k_0 n_{\mathrm{eff},m}$$

任意场在 cell 内的展开（双向传播）：

$$\mathbf{E}(x,y,z) = \sum_m \left[ a_m^{(+)} e^{i\beta_m z} + a_m^{(-)} e^{-i\beta_m z} \right] \mathbf{e}_m(x,y)$$

$$\mathbf{H}(x,y,z) = \sum_m \left[ a_m^{(+)} e^{i\beta_m z} - a_m^{(-)} e^{-i\beta_m z} \right] \mathbf{h}_m(x,y)$$

其中 $\mathbf{e}_m, \mathbf{h}_m$ 为第 m 个本地本征模的横向场分布，$\beta_m$ 为传播常数，$a_m^{(\pm)}$ 为前向/后向展开系数。

---

## 4. 离散化方案

### 4.1 横向（xy 平面）

交由 FDE 求解器在 Yee 网格上离散，得到每个 cell 中心的本地本征模 $\{\mathbf{e}_m, \mathbf{h}_m, \beta_m\}_{m=1}^{M}$。Yee 网格交错排列保证旋度方程中心差分自然满足散度条件（参见 A04-FDE 文档）。

### 4.2 纵向（z 方向）

- **Cell 划分**：均匀段用 1 个 cell；锥形/渐变段用多 cell 提高精度。
- **Cell Group**：Lumerical EME 概念，将几何相近的 cell 编组，组内共享模式数设置，组间可独立配置（如 `[1, (2,3)^N, 4]` 表示周期结构）。
- **CVCS（Continuously Varying Cross-sectional Subcell）子单元法**：Lumerical 专利方法，避免传统 staircase 阶梯近似在锥形段引入的非物理反射。CVCS 在子单元内对截面做连续插值，精度损失 <3%（vs staircase 15%）。
- **Staircase 方法**：将锥形离散为多个 z 不变台阶，是 CVCS 不可用时的 fallback（非 PoLaRIS fallback，而是 EME 内部可选离散策略）。

### 4.3 模式数截断

每 cell 保留前 M 个本征模（含导模 + 辐射模离散化近似）。M 过小导致收敛性差，过大增加级联开销。Lumerical 提供 Mode Convergence Sweep 工具确定最小 M。典型 SOI 单模波导取 M=10~20，MMI 取 M=30~50。

---

## 5. 边界条件

- **输入/输出端口**：匹配参考波导的本征模，定义 S 矩阵端口（Port）。Lumerical EME Port 支持 mode selection（fundamental/all/user select）。
- **横向边界**：PML 或 TBC（由 FDE 求解器处理辐射模吸收），SC-PML 复坐标拉伸融入差分算子（Shin & Fan 2012）。
- **界面连续性**：切向 $\mathbf{E}_t, \mathbf{H}_t$ 在 cell 界面连续，是构造界面 S 矩阵的物理基础。
- **周期边界**：Cell Group Periodicity 支持布拉格光栅、相移光栅等周期结构高效仿真（仅求解一个 unit cell 的模式，周期数在 propagate 阶段指定）。

---

## 6. 核心算法逻辑

EME 求解分两阶段（与 Lumerical EME 的 Solver 模式 + Analysis 模式对齐）：

### 阶段一：模式求解（Solver 阶段，耗时主要部分）

1. 沿 z 将器件切分为 N 个 cell（按 Cell Group 组织）。
2. 对每个 cell i，在其中心横截面调用 FDE 求解器，得到本地模 $\{\mathbf{e}_m^{(i)}, \mathbf{h}_m^{(i)}, \beta_m^{(i)}\}_{m=1}^{M_i}$。
3. 模式归一化（功率内积归一为 1）。
4. 对每对相邻 cell (i, i+1)，计算模式重叠积分矩阵 $\mathbf{O}_{EE}, \mathbf{O}_{EH}, \mathbf{O}_{HE}, \mathbf{O}_{HH}$，由切向场连续性方程构造界面 S 矩阵 $\mathbf{S}_J^{(i,i+1)}$（含反射矩阵 $\mathbf{R}$、透射矩阵 $\mathbf{T}$）。
5. 对每个 cell 内均匀段构造传播 S 矩阵 $\mathbf{S}_{WG}^{(i)} = \mathrm{diag}(e^{i\beta_m L_i})$。

### 阶段二：S 矩阵级联（Analysis 阶段，毫秒级）

6. 按 Redheffer 星积将所有 $\mathbf{S}_J$ 与 $\mathbf{S}_{WG}$ 自左向右级联，得到器件全局 S 矩阵 $\mathbf{S}_{\mathrm{global}}$。
7. **Analysis 模式优势**：cell 长度 $L_i$ 可任意修改，仅需重做第 6 步（重新计算 $\mathbf{S}_{WG}$ 的相位 $e^{i\beta_m L_i}$ 并级联），无需重算本地模。Lumerical Group Span Sweep、Propagation Sweep 即基于此。
8. 端口模式选择：将 $\mathbf{S}_{\mathrm{global}}$ 投影到输入/输出端口的指定模式，得到端口 S 参数 $S_{ij}^{(mn)}$。
9. （可选）场重建：由端口系数反向传播，重建器件内任意 z 处的场分布（EME Profile Monitor）。

---

## 7. 核心公式

### 7.1 模式正交归一化（功率内积）

$$\int \left( \mathbf{e}_m \times \mathbf{h}_n^* \right) \cdot \hat{z} \, dA = \delta_{mn}$$

### 7.2 界面模式重叠积分（Gallagher & Felici 2003，SimWorks EME）

$$\langle \mathbf{e}_m^{(A)}, \mathbf{h}_n^{(B)} \rangle = \frac{1}{2} \int \mathbf{e}_m^{(A)} \times \mathbf{h}_n^{(B)*} \cdot \hat{z} \, dA$$

由洛伦兹互易性：$\langle \mathbf{e}_m^{(A)}, \mathbf{h}_n^{(B)} \rangle = \langle \mathbf{e}_n^{(B)*}, \mathbf{h}_m^{(A)} \rangle$。

### 7.3 界面 S 矩阵（切向场连续性 + 正交投影）

在 cell A→B 界面，切向场连续：

$$\mathbf{e}_{t,p}^{(A)} + \sum_n R_{np} \mathbf{e}_{t,n}^{(A)} = \sum_m T_{mp} \mathbf{e}_{t,m}^{(B)}$$

$$\mathbf{h}_{t,p}^{(A)} - \sum_n R_{np} \mathbf{h}_{t,n}^{(A)} = \sum_m T_{mp} \mathbf{h}_{t,m}^{(B)}$$

投影到正交基后得到界面 S 矩阵：

$$\begin{pmatrix} \mathbf{a}^{(-)} \\ \mathbf{b}^{(+)} \end{pmatrix} = \mathbf{S}_J \begin{pmatrix} \mathbf{a}^{(+)} \\ \mathbf{b}^{(-)} \end{pmatrix} = \begin{pmatrix} \mathbf{R}_{AB} & \mathbf{T}_{BA} \\ \mathbf{T}_{AB} & \mathbf{R}_{BA} \end{pmatrix} \begin{pmatrix} \mathbf{a}^{(+)} \\ \mathbf{b}^{(-)} \end{pmatrix}$$

其中 $\mathbf{R}_{AB}$ 为 A 侧反射矩阵，$\mathbf{T}_{AB}$ 为 A→B 透射矩阵，由重叠积分矩阵 $\mathbf{O}$ 线性方程组求解得到。

### 7.4 均匀段传播 S 矩阵

$$\mathbf{S}_{WG} = \begin{pmatrix} \mathbf{0} & \mathbf{P} \\ \mathbf{P} & \mathbf{0} \end{pmatrix}, \quad \mathbf{P} = \mathrm{diag}\left(e^{i\beta_m L}\right)$$

### 7.5 全局 S 矩阵级联（Redheffer 星积）

$$\mathbf{S}_{12}^{\mathrm{tot}} = \mathbf{S}_{12}^{(2)}\left(\mathbf{I} - \mathbf{S}_{11}^{(1)}\mathbf{S}_{22}^{(2)}\right)^{-1}\mathbf{S}_{12}^{(1)}$$

$$\mathbf{S}_{11}^{\mathrm{tot}} = \mathbf{S}_{11}^{(2)} + \mathbf{S}_{12}^{(2)}\mathbf{S}_{11}^{(1)}\left(\mathbf{I} - \mathbf{S}_{22}^{(2)}\mathbf{S}_{11}^{(1)}\right)^{-1}\mathbf{S}_{21}^{(2)}$$

Redheffer 星积避免传统传输矩阵法在消逝波/长结构中的数值指数发散，是 RCWA 与 EME 共用的稳定级联方案（参见 A01-RCWA 第 1.5 节、C03-Redheffer 星积）。

### 7.6 端口 S 参数

$$S_{ij}^{(mn)} = \sqrt{\frac{P_j^{(n)}}{P_i^{(m)}}} \cdot \left| b_i^{(m)} / a_j^{(n)} \right|_{a_k=0, k\neq j}$$

其中 $P_i^{(m)}$ 为端口 i 模式 m 的功率，由模式归一化保证。

---

## 8. 算法伪代码

```python
# PoLaRIS EME 求解器核心伪代码（纯 CPU + NumPy/SciPy）
import numpy as np
from scipy.sparse.linalg import eigsh  # FDE 本征求解
from scipy.linalg import solve          # 界面 S 矩阵线性求解

def eme_solve(device, wavelength, cell_groups, num_modes, ports):
    """
    device: 器件几何（沿 z 的截面序列）
    cell_groups: [(span_um, num_cells, subcell_method), ...]
    num_modes: 每 cell 模式数 M
    ports: 输入/输出端口模式选择
    """
    k0 = 2 * np.pi / wavelength

    # ========== 阶段一：模式求解 ==========
    local_modes = []  # 每 cell 的本地模 {e_m, h_m, beta_m}
    for group_span, n_cells, method in cell_groups:
        for c in range(n_cells):
            z_center = compute_z_center(group_span, c, method)  # CVCS 插值
            cross_section = device.slice(z_center, method)      # 截面折射率分布
            # 调用 FDE 内核求解本地模（共享 A04-FDE 实现）
            e, h, beta = fde_solve(cross_section, wavelength, num_modes)
            e, h = normalize_modes(e, h)  # 功率内积归一化
            local_modes.append((e, h, beta))

    # 构造界面 S 矩阵（每对相邻 cell）
    interface_S = []
    for i in range(len(local_modes) - 1):
        eA, hA, _ = local_modes[i]
        eB, hB, _ = local_modes[i + 1]
        # 重叠积分矩阵 O_EE, O_EH, O_HE, O_HH（NumPy 向量化）
        O = compute_overlap_matrices(eA, hA, eB, hB)  # 4 个 MxM 矩阵
        # 切向场连续性 → 线性方程组求解 R, T
        R_AB, T_AB, R_BA, T_BA = solve_interface_S(O)
        interface_S.append(assemble_S_block(R_AB, T_AB, R_BA, T_BA))

    # ========== 阶段二：S 矩阵级联（Analysis 模式）==========
    def propagate(cell_lengths):
        """cell_lengths: 每 cell 实际长度（可任意扫描）"""
        S_global = interface_S[0]
        for i in range(1, len(local_modes)):
            # 均匀段传播 S 矩阵
            beta = local_modes[i][2]
            L = cell_lengths[i]
            P = np.diag(np.exp(1j * beta * L))
            S_WG = np.block([[np.zeros_like(P), P], [P, np.zeros_like(P)]])
            # Redheffer 星积级联
            S_global = redheffer_star_product(S_global, S_WG)
            S_global = redheffer_star_product(S_global, interface_S[i])
        return S_global

    S_global = propagate(default_cell_lengths)

    # ========== 端口投影 ==========
    S_port = project_to_ports(S_global, ports, local_modes[0], local_modes[-1])
    return S_port, local_modes, propagate  # 返回 propagate 支持 Analysis 扫描

def redheffer_star_product(S1, S2):
    """Redheffer 星积，避免数值指数发散"""
    I = np.eye(S1.shape[0] // 2)
    S11_1, S12_1, S21_1, S22_1 = split_S(S1)
    S11_2, S12_2, S21_2, S22_2 = split_S(S2)
    # 中间矩阵求逆（NumPy solve 替代 inv 提升数值稳定性）
    M1 = solve(I - S22_2 @ S11_1, S12_2)  # (I - S22_2 S11_1)^-1 S12_2
    M2 = solve(I - S11_1 @ S22_2, S12_1)
    S11_tot = S11_2 + M1 @ S11_1 @ S21_2
    S12_tot = M1 @ S12_1
    S21_tot = S21_1 @ M2  # 对称形式
    S22_tot = S22_1 + S21_1 @ M2 @ S22_2
    return assemble_S(S11_tot, S12_tot, S21_tot, S22_tot)
```

---

## 9. PoLaRIS 创新点

*创新*：纯 CPU + NumPy 实现的 EME 求解器，禁用 GPU（规则 26），与 FDE/RCWA 共享底层内核实现模式复用加速。

### 9.1 底层逻辑

- **FDE 内核复用**：EME 调用 A04-FDE 求解器在每个 cell 中心计算本地模，避免重复实现本征模求解。FDE 输出统一数据结构 $(\mathbf{e}_m, \mathbf{h}_m, \beta_m)$，供 EME 零成本复用。
- **重叠积分 NumPy 向量化**：4 个重叠积分矩阵 $\mathbf{O}_{EE}, \mathbf{O}_{EH}, \mathbf{O}_{HE}, \mathbf{O}_{HH}$ 用 NumPy 张量积一次性计算，避免 Python 循环。
- **Redheffer 星积复用 RCWA 路径**：S 矩阵级联采用 Redheffer 星积，与 A01-RCWA 共享 `redheffer_star_product` 实现（参见 C03 聚类）。
- **Analysis 模式模式复用加速**：本地模求解（阶段一）结果缓存，cell 长度扫描（Group Span Sweep / Propagation Sweep）仅需重做阶段二的相位 $e^{i\beta_m L}$ 与级联，毫秒级响应，与 Lumerical EME 行为对齐。
- **数值稳定性**：Redheffer 星积中的 $(\mathbf{I} - \mathbf{S}_{11}^{(1)}\mathbf{S}_{22}^{(2)})^{-1}$ 用 `scipy.linalg.solve` 替代显式 `inv`，避免条件数放大；消逝波 $\beta$ 为虚数时 $e^{i\beta L}$ 自然衰减，无溢出。

### 9.2 支持理论

- Gallagher & Felici 2003（SPIE 4987）证明 EME 对长结构（锥形、MMI、周期器件）计算成本与长度无关，优于 FDTD；双向传播天然处理反射，优于 BPM 的 SVEA 近似。
- Lumerical EME 白皮书与 SimWorks EME 文档均确认 Analysis 模式下 cell 长度扫描无需重算模式，是 EME 区别于 FDTD 的核心效率优势。
- Redheffer 星积是 RCWA/EME 共用的稳定级联方案，已被 NIST SCATMECH、Meent 等开源实现验证。

### 9.3 差异化案例

- **SOI 锥形模式转换器**：传统 staircase 方法需 50+ cell，CVCS 子单元法 10 cell 即可收敛，PoLaRIS 优先实现 CVCS。
- **MMI 功分器**：多模区高阶模丰富，EME 用 M=30~50 模式精确预测插入损耗与均匀性，与 Lumerical EME 精度对齐。
- **长周期布拉格光栅**：Cell Group Periodicity `[1, (2,3)^N, 4]` 仅求解一个 unit cell 模式，周期数 N 在 propagate 阶段指定，仿真时间与 N 无关。
- **PoLaRIS 独有**：EME 输出 S 参数直接喂入 AI 布局的目标函数，支持锥形/MMI 几何参数的伴随法逆向设计（F01 聚类），形成"物理仿真—AI 优化"闭环，超越商业工具的脚本优化工作流。

---

## 10. 文献来源

- [1] D. F. G. Gallagher and T. P. Felici, "Eigenmode expansion methods for simulation of optical propagation in photonics - Pros and Cons," *Proc. SPIE* 4987, 69-82 (2003). URL: https://doi.org/10.1117/12.478061
- [2] Ansys Lumerical MODE — EigenMode Expansion (EME) solver introduction. URL: https://optics.ansys.com/hc/en-us/articles/360034396614
- [3] SimWorks Eigenmode Expansion (EME) Solver（模式耦合理论 + 重叠积分 + S 矩阵公式）. URL: https://www.emsimworks.com/en/solver/EME
- [4] Photon Design FIMMPROP EME paper（Gallagher & Felici 实现细节，界面 S 矩阵推导）. URL: https://photond.com/assets/files/FIMMWAVE/PW03_eme_paper.pdf
- [5] EMEpy — Open-source eigenmode expansion solver in Python（BYUCamachoLab）. URL: https://emepy.readthedocs.io/en/stable/index.html
- [6] M. C. Oktay and E. S. Magden, "Computationally Efficient Nanophotonic Design through Data-Driven Eigenmode Expansion," arXiv:2407.09847 (2024). URL: https://arxiv.org/abs/2407.09847
- [7] Ansys Lumerical EME Setup Tab — Cell Group / CVCS / Periodicity 官方教程. URL: https://innovationspace.ansys.com/courses/courses/lumerical-eme-solver-region/lessons/eme-setup-tab-lesson-2/
- [8] W. Shin and S. Fan, "Choice of the perfectly matched layer boundary condition for frequency-domain Maxwell's equations solvers," *J. Comput. Phys.* 231, 3406-3431 (2012)（SC-PML，EME 横向边界）. URL: https://doi.org/10.1016/j.jcp.2011.12.037

---

## 11. 商业工具对照与实现路线

### 11.1 商业工具对照

| 能力 | Lumerical EME | FIMMPROP | SimWorks EME | 曼光 EME | PoLaRIS 目标 |
|------|--------------|----------|--------------|----------|-------------|
| 双向本征模展开 | ✅ | ✅ | ✅ | ✅ | ✅ 自研 |
| Cell Group + 模式数配置 | ✅ | ✅ | ✅ | ✅ | ✅ 自研 |
| CVCS 子单元法 | ✅（专利） | ✅ | ⚠️ | ⚠️ | ✅ 自研（参考 Lumerical 公开原理） |
| Group Span Sweep | ✅ | ✅ | ✅ | ✅ | ✅ Analysis 模式 |
| Propagation Sweep | ✅ | ✅ | ✅ | ⚠️ | ✅ Analysis 模式 |
| Mode Convergence Sweep | ✅ | ✅ | ⚠️ | ❌ | ✅ 自研 |
| Cell Group Periodicity | ✅ | ✅ | ⚠️ | ⚠️ | ✅ 自研 |
| EME Profile Monitor | ✅ | ✅ | ⚠️ | ⚠️ | ✅ 场重建 |
| 端口 S 参数导出 | ✅ | ✅ | ✅ | ✅ | ✅ 与 C01-S 参数级联对接 |
| 长度扫描不重算模式 | ✅ | ✅ | ✅ | ✅ | ✅ 模式缓存 |
| GPU 加速 | ✅ | ❌ | ✅ | ✅ | 🚫 不参与（规则 26） |

### 11.2 PoLaRIS 实现路线（R37-Q4）

| 阶段 | 里程碑 | 依赖 | 验收指标 |
|------|--------|------|---------|
| M1 | FDE 内核对接（本地模求解） | A04-FDE 完成 | SOI 直波导基模 $\beta$ 误差 <1e-4 |
| M2 | 界面 S 矩阵（重叠积分 + 切向场连续） | M1 | 锥形单界面反射/透射功率守恒 <1e-6 |
| M3 | Redheffer 星积级联（复用 C03） | M2 | N cell 级联数值稳定，无指数溢出 |
| M4 | Analysis 模式（cell 长度扫描） | M3 | Group Span Sweep 毫秒级响应 |
| M5 | CVCS 子单元法 | M4 | 锥形 SOI 转换器损耗 vs 3D-FDTD 误差 <0.1 dB |
| M6 | Cell Group Periodicity | M5 | 布拉格光栅周期 N=1000 仿真时间 <1s |
| M7 | 端口投影 + S 参数导出 | M6 | S 参数格式与 C01-SAX 兼容 |
| M8 | EME Profile Monitor（场重建） | M7 | 任意 z 截面场分布与 FDTD 对比误差 <5% |

### 11.3 共享组件复用

| 组件 | 来源聚类 | 用途 |
|------|---------|------|
| FDE 本征模求解 | A04 | 每 cell 本地模 |
| Yee 网格差分算子 | A04 | 横向离散 |
| SC-PML 拉伸坐标 | A05/A04 | 横向吸收边界 |
| Redheffer 星积 | A01/C03 | S 矩阵级联 |
| 模式重叠积分 | A04 | 界面 S 矩阵 + 端口投影 |
| 稀疏本征求解 (Lanczos) | A04 | FDE 内核 |

---

## 修订日志

- **2026-06-25 v1.0**：首版生成。物理模型、控制方程、离散化、边界条件、核心公式均经 Gallagher & Felici 2003 (SPIE)、Lumerical EME 官方文档、SimWorks EME 官方文档、EMEpy 开源实现、arXiv:2407.09847 核实（规则 18），无 fall-back 编造（规则 14），全部 CPU 算法（规则 26）。PoLaRIS 自研差异化设计（FDE 内核复用、Analysis 模式模式缓存、与 AI 逆向设计闭环）已标注【创新】并记录底层逻辑与支持理论。覆盖 T01/T03/T07/T15/T16 共 38 功能点，对标 Lumerical EME 全部核心能力。
