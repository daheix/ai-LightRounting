# A05 — FDFD 频域有限差分（Finite Difference Frequency Domain）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A05（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T16 SimWorks（共 14 功能点，状态分布 ✅3 / ⚠️6 / ❌5）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`3dtool/ALGORITHMS.md` 第 7 节、`docs/feature_gap_full_analysis.md` T16 第 3 章、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDFD（Finite Difference Frequency Domain，频域有限差分）在频域直接求解 Maxwell 方程，给定单频源求全场分布。与时域 FDTD 相比，FDFD 无需时间步进，天然适合单频/窄带问题、色散材料（无需递推卷积）与强谐振结构（无需长时间演化等待稳态）。其代价是需存储整个稀疏矩阵 $\mathbf{A}$ 并求解大型线性系统 $\mathbf{A}\mathbf{x}=\mathbf{b}$，对内存与稀疏求解器性能要求高。

**PoLaRIS 定位**：FDFD 是 PoLaRIS 求解器栈中"频域全波"路径的核心，与 FDE 共享 Yee 网格与 SC-PML 算子构造（ALGORITHMS.md 附录 C），由 ALGORITHMS.md 附录 B 列为 R37-Q2 优先级实现。纯 CPU + `scipy.sparse` 实现（规则 26），不参与 GPU 加速路径。

**对标状态**：T01 Lumerical 与 T16 SimWorks 均提供 FDFD 求解器（`https://www.simworks.net/solver/FDFD`），PoLaRIS 当前完全缺失自研 FDFD（仅通过 FDTD 后端间接覆盖 Yee 离散），是商业差距最大处之一。

---

## 2. 物理模型与控制方程

### 2.1 频域 Maxwell 旋度方程

时谐因子 $e^{i\omega t}$ 下，含电流源 $\mathbf{J}$ 与磁流源 $\mathbf{M}$（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -i\omega\mu_0 \mathbf{H} - \mathbf{M}$$

$$\nabla \times \mathbf{H} = i\omega\varepsilon_0\varepsilon_r \mathbf{E} + \mathbf{J}$$

### 2.2 电场波动方程（消去 $\mathbf{H}$）

$$\nabla \times \nabla \times \mathbf{E} - k_0^2 \varepsilon_r \mathbf{E} = -i\omega\mu_0 \mathbf{J} - \nabla \times \mathbf{M}$$

Jaxwell/MaxwellFDFD 标准形式（$\mathbf{M}=0$）：

$$(\nabla \times \nabla \times - \omega^2\varepsilon) \mathbf{E} = -i\omega\mathbf{J}$$

其中 $k_0=\omega/c_0$ 为真空波数，$\varepsilon=\varepsilon_0\varepsilon_r$。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 网格布局（Yee 1966）

电场分量位于棱中点（$E_x$ 在 x 棱、$E_y$ 在 y 棱、$E_z$ 在 z 棱），磁场分量位于面中心（$H_x$ 在 yz 面、$H_y$ 在 xz 面、$H_z$ 在 xy 面），交错排列。该布局使 Maxwell 旋度方程的中心差分自然满足散度条件 $\nabla\cdot\mathbf{D}=0$，且二阶精度 $O(\Delta h^2)$。

### 3.2 旋度算子差分矩阵

将旋度运算离散为稀疏差分矩阵 $\mathbf{C}$（复数）。对电场旋度 $\nabla\times\mathbf{E}$，按 Yee 网格棱-面错位，每个分量为中心差分：

$$(\nabla\times\mathbf{E})_x\big|_{i,j,k} = \frac{E_z|_{i,j+1,k}-E_z|_{i,j,k}}{\Delta y} - \frac{E_y|_{i,j,k+1}-E_y|_{i,j,k}}{\Delta z}$$

构造矩阵 $\mathbf{C}_e$、$\mathbf{C}_h$ 分别作用于电场与磁场，由 `scipy.sparse.kron` 组合单位方向差分算子得到（共 6 个一阶差分核，每核 2 非零元/行）。

### 3.3 矩阵组装

整理 6 个场分量 $(E_x,E_y,E_z,H_x,H_y,H_z)$ 为未知向量 $\mathbf{x}$，频域 Maxwell 写为分块稀疏形式（MaxwellFDFD/Shin & Fan 2012）：

$$\begin{pmatrix} -\mu_r^{-1}\mathbf{C}_h & i\omega\mathbf{I} \\ i\omega\varepsilon\mathbf{I} & \mathbf{C}_e \end{pmatrix} \begin{pmatrix}\mathbf{E}\\\mathbf{H}\end{pmatrix} = \begin{pmatrix}-\mathbf{M}\\\mathbf{J}\end{pmatrix}$$

消去 $\mathbf{H}$ 后得到仅含 $\mathbf{E}$ 的复对称稀疏系统（Jaxwell 形式）：

$$\mathbf{A}(\omega,\varepsilon,\text{PML})\,\mathbf{E} = \mathbf{b}, \quad \mathbf{A} = \mathbf{C}_h^\top\mu_r^{-1}\mathbf{C}_h - \omega^2\varepsilon, \quad \mathbf{b} = -i\omega\mathbf{J}$$

$\mathbf{A}$ 为复对称（$\mathbf{A}=\mathbf{A}^\top$，非 Hermitian），每行非零元数固定（≤13 in 3D）。

---

## 4. SC-PML 吸收边界条件

### 4.1 拉伸坐标（Shin & Fan 2012）

将笛卡尔坐标沿各方向拉伸，使 PML 区域波指数衰减无反射：

$$\tilde{x} = \int_0^x s_x(x')\,dx', \quad s_x = \kappa_x + \frac{\sigma_x}{i\omega\varepsilon_0}$$

其中 $\kappa_x\ge 1$ 控制相速拉伸，$\sigma_x\ge 0$ 控制衰减强度，二者在 PML 内沿深度按多项式渐变（Shin & Fan 推荐 $m=3$）。

### 4.2 拉伸后 Maxwell 方程

$$\nabla_S \times \mathbf{H} = i\omega\tilde{\varepsilon}\mathbf{E}, \quad \nabla_S \times \mathbf{E} = -i\omega\tilde{\mu}\mathbf{H}$$

$$\tilde{\varepsilon} = \varepsilon\cdot\frac{s_y s_z}{s_x}, \quad \tilde{\mu} = \mu\cdot\frac{s_y s_z}{s_x}$$

其中 $\nabla_S$ 在拉伸坐标 $\tilde{x},\tilde{y},\tilde{z}$ 下取差分。SC-PML 通过修改 $\tilde\varepsilon,\tilde\mu$ 而非引入额外辅助变量，直接融入 $\mathbf{A}$ 的对角块。

### 4.3 SC-PML 优势

Shin & Fan 2012 系统对比了频域下 UPML/SC-PML/CPML 的数值反射，结论：**SC-PML 在频域 FDFD 中数值反射最低、实现最简**（无辅助微分方程），是 Lumerical FDFD、MaxwellFDFD、Jaxwell 的统一选择。

---

## 5. 稀疏线性系统构建

### 5.1 矩阵规模

3D Yee 网格 $N_x\times N_y\times N_z$，未知量数 $N = 3N_xN_yN_z$（仅 $\mathbf{E}$）或 $6N_xN_yN_z$（$\mathbf{E}+\mathbf{H}$ 混合形式）。$\mathbf{A}$ 非零元密度约 $13/N$，对 100×100×100 网格规模 $N=3\times 10^6$，非零元约 $4\times 10^7$，需 `scipy.sparse.csr_matrix` 存储。

### 5.2 构造流程（PoLaRIS）

1. 由 FDE 模块导入 Yee 网格与 $\varepsilon_r$ 分布（共享，避免重复构造）。
2. `scipy.sparse.diags` 构造一阶差分算子 $\partial_x,\partial_y,\partial_z$（含拉伸坐标 $1/s_x$）。
3. `scipy.sparse.kron` 组合得旋度矩阵 $\mathbf{C}_e,\mathbf{C}_h$。
4. 由 $\varepsilon_r$ 与 PML 拉伸因子构造对角矩阵 $\mathbf{D}_\varepsilon$。
5. $\mathbf{A} = \mathbf{C}_h^\top \mathbf{D}_\mu^{-1}\mathbf{C}_h - \omega^2\mathbf{D}_\varepsilon$，存为 CSR。
6. 源向量 $\mathbf{b}=-i\omega\mathbf{J}$，$\mathbf{J}$ 可由 FDE 模式分布生成（波导模注入）。

---

## 6. 求解器策略

### 6.1 直接求解（小规模）

`scipy.sparse.linalg.spsolve`（基于 UMFPACK/SuperLU），适合 $N\le 10^5$ 的 2D 问题或 3D 小器件。优点：一次分解多次回代（多源扫描高效）；缺点：内存 $O(N^{1.5})$ 在 3D 大规模下不可行。

### 6.2 迭代求解（大规模，PoLaRIS 主路径）

$\mathbf{A}$ 复对称非 Hermitian，专用算法（Gu 2014，Jaxwell 默认）：

- **COCG（Conjugate Orthogonal Conjugate Gradient）**：复对称系统最小残差，存储与计算量为 CG 的 2 倍实数运算。
- **QMR-COCG / QMR-COCR**（Gu 2014）：COCG 在某些问题振荡发散，QMR 变体平滑残差，IEEE TMTT 2014 验证为电磁 FDFD 推荐方案。
- `scipy.sparse.linalg.cg` 复数版可作为 COCG 等价实现（对复对称系统自动正交化）。
- `scipy.sparse.linalg.bicgstab` / `gmres` 作为通用兜底（非复对称专用）。

### 6.3 预处理

- **对角（Jacobi）预处理**：$\mathbf{M}^{-1}=\mathrm{diag}(\mathbf{A})^{-1}$，构造 $O(N)$，适合 $\varepsilon_r$ 缓变。
- **不完全 LU（ILU）**：`scipy.sparse.linalg.spilu`，对角阈值 drop tolerance 控制填充。3D 大规模下 ILU 内存可能爆炸，需用 IC(0)（不完全 Cholesky，复对称专用）。
- **模式 AMG**：超大规模可选，但 PoLaRIS CPU 路径优先 ILU。

---

## 7. 算法伪代码

```text
function FDFD_Solve(ε_r grid, ω, J_src, pml_params, grid_shape):
    # 1. 导入 FDE 共享 Yee 网格与介电常数
    Nx, Ny, Nz = grid_shape
    N = 3 * Nx * Ny * Nz

    # 2. 构造 SC-PML 拉伸因子 s_x, s_y, s_z（Shin & Fan 2012 多项式渐变）
    sx = build_pml_stretch(Nx, pml_params, ω)  # 1D 数组，内部=1，PML 区复数
    sy = build_pml_stretch(Ny, pml_params, ω)
    sz = build_pml_stretch(Nz, pml_params, ω)

    # 3. 构造一阶差分算子（含拉伸坐标 1/s_*）
    Dx = sparse_diff(Nx, 1/sx)   # tridiagonal, ±1/Δx * (1/sx)
    Dy = sparse_diff(Ny, 1/sy)
    Dz = sparse_diff(Nz, 1/sz)

    # 4. 组装旋度矩阵 Ce, Ch（scipy.sparse.kron）
    Ce = curl_E_matrix(Dx, Dy, Dz, Nx, Ny, Nz)   # (3N, 3N) sparse
    Ch = curl_H_matrix(Dx, Dy, Dz, Nx, Ny, Nz)

    # 5. 构造对角介电矩阵（含 PML 各向异性 ε̃ = ε * sy*sz/sx）
    D_eps = diag(build_tilde_eps(ε_r, sx, sy, sz))   # (3N, 3N) diagonal
    D_mu  = diag(build_tilde_mu(sx, sy, sz))         # μ_r = 1

    # 6. 组装复对称稀疏系统 A·E = b
    A = Ch.T @ inv(D_mu) @ Ch - ω**2 * D_eps       # 复对称 (A = A.T)
    b = -1j * ω * J_src                             # 源向量

    # 7. 预处理（ILU 或对角）
    M = spilu(A.tileregularized()) or diag(inv(A))

    # 8. 迭代求解（COCG/QMR-COCG, Gu 2014）
    E, info = iterative_solve(A, b, M, method="cocg", tol=1e-6, maxiter=5000)
    if info != 0:
        raise RuntimeError(f"FDFD 迭代求解未收敛, info={info}")  # 规则 14：禁止 fall-back

    # 9. 由 E 回代 H = (1/(-iωμ)) ∇×E
    H = (-1 / (1j * ω * μ0)) * (Ch @ E)

    # 10. 后处理：提取 S 参数、远场、Poynting 通量
    S = extract_s_parameters(E, ports)
    return E, H, S
```

**说明**：
- 步骤 1 复用 FDE 的 Yee 网格与 $\varepsilon_r$，避免重复构造（ALGORITHMS.md 附录 C 共享组件）。
- 步骤 6 的 $\mathbf{A}$ 为复对称，可用 `scipy.sparse.linalg.cg`（复数）实现 COCG。
- 步骤 8 失败时 `raise`（规则 14），禁止返回假数据兜底。

---

## 8. PoLaRIS 实现创新点

*创新*：FDFD 与 FDE 共享 Yee 网格与 SC-PML 算子，纯 CPU + `scipy.sparse` 单频高精度求解。

- **底层逻辑**：
  - `scipy.sparse` 构造 $\mathbf{A}$（CSR 复对称），`scipy.sparse.linalg.cg`/`spsolve` 求解；
  - SC-PML 按 Shin & Fan 2012 拉伸坐标融入算子对角块，无辅助变量；
  - 源 $\mathbf{J}$ 由 FDE 模式分布生成（波导模注入天然兼容，避免商业工具的网格重生成开销）；
  - 多源扫描（如 S 参数提取）共享同一 $\mathbf{A}$ 的 LU 分解或预处理子，2D 直接求解路径下扫描零边际成本。
- **支持理论**：
  - Shin & Fan 2012 证明 SC-PML 在频域 FDFD 中数值反射最低，优于 UPML/CPML；
  - Gu 2014 IEEE TMTT 证明 QMR-COCG/COCR 对复对称电磁系统收敛性优于 BiCGSTAB/GMRES；
  - Yee 1966 是 FDTD/FDE/FDFD 共同网格基础，已被 Lumerical、Tidy3D、SimWorks、Meep 全部采纳。
- **案例**：单频谐振超表面、窄带光栅滤波器、色散金属纳米天线、SOI 微环谐振器本征频率扫描。差异化点：PoLaRIS FDFD 与 FDE 共享网格，模式注入天然兼容；与 AI 逆向设计耦合时，单频梯度计算成本远低于 FDTD（无需时间步进）。
- **CPU 战略（规则 26）**：PoLaRIS 不参与 GPU 加速。Jaxwell 的 GPU/JAX 路径仅作公式参考，实现完全基于 `numpy`+`scipy.sparse`+`scipy.sparse.linalg`。

---

## 9. 商业工具对标

### 9.1 T16 SimWorks FDFD（10 功能点，✅3/⚠️6/❌1）

来源：`https://www.simworks.net/solver/FDFD`

| # | 功能点 | PoLaRIS 状态 | 实现路径 |
|---|--------|-------------|---------|
| 3.1 | 频域 Maxwell 方程求解（Ax=b 矩阵化） | ❌ → 待实现 | 本文档 §5-§7 |
| 3.2 | Yee cell 网格离散 | ⚠️ → ✅ | 共享 FDE Yee 网格 |
| 3.3 | 3D CAD 与 GDS 导入 | ✅ | `modules/nn/src/polaris_nn/data/gds_loader.py` |
| 3.4 | 共形网格技术 | ⚠️ | 待自研 Volume-average/Yu-Mittra 1/2 |
| 3.5 | 多种边界条件（PML/周期/Bloch/PEC/PMC） | ⚠️ → ✅ | SC-PML + PEC/PMC/Bloch |
| 3.6 | 多种光源（偶极子/平面/高斯/模式/TFSF） | ⚠️ → ✅ | 模式源由 FDE 生成，其余待补 |
| 3.7 | 各向异性材料与散点材料 | ⚠️ | $\tilde\varepsilon$ 张量支持 |
| 3.8 | 后处理分析库 | ✅ | `modules/nn/src/polaris_nn/data/benchmark_evaluator.py` |
| 3.9 | 扫描优化 | ✅ | `modules/optimizer/src/polaris_optimizer/nsga.py` |
| 3.10 | 多并行加速与云端计算 | 🚫不参与 | 规则 26，OpenMP/CUDA/MPI 不参与 |

### 9.2 T01 Ansys Lumerical（隐式 FDFD 能力）

Lumerical 主推 FDTD/EME/FDE/varFDTD，未单独销售 FDFD 模块，但其 FDTD 频域 DFT 监视器与 DGTD（Discontinuous Galerkin Time Domain，频域后处理）覆盖了 FDFD 的部分应用场景。PoLaRIS 自研 FDFD 后将在"单频全波"场景对 Lumerical 形成能力补齐。

---

## 10. 文献来源

1. Shin W, Fan S, "Choice of the perfectly matched layer boundary condition for frequency-domain Maxwell's equations solvers," *J. Comput. Phys.* 231, 3406-3431 (2012). URL: https://doi.org/10.1016/j.jcp.2011.12.037
2. Shin W, MaxwellFDFD（MATLAB FDFD 包，SC-PML 实现参考）. URL: https://www.mit.edu/~wsshin/maxwellfdfd.html
3. Fischbach JD, Jaxwell（GPU 加速可微 FDFD，PoLaRIS 仅参考公式与算法，不参与 GPU 路径，规则 26）. URL: https://jan-david-fischbach.github.io/jaxwell/
4. Gu X, Huang T, Li L, Li H, Sogabe T, Clemens M, "Quasi-Minimal Residual Variants of the COCG and COCR Methods for Complex Symmetric Linear Systems in Electromagnetic Simulations," *IEEE Trans. Microwave Theory Tech.* 62(12), 2859-2867 (2014). URL: https://doi.org/10.1109/TMTT.2014.2363835
5. Yee K, "Numerical solution of initial boundary value problems involving Maxwell's equations in isotropic media," *IEEE Trans. Antennas Propag.* 14, 302-307 (1966). URL: https://doi.org/10.1109/TAP.1966.1138693
6. SimWorks FDFD Solver 官方文档. URL: https://www.simworks.net/solver/FDFD
7. Ansys Lumerical Multiphysics（DGTD/FEM 频域求解器对照）. URL: https://www.ansys.com/products/optics/Multiphysics
8. Simsek E, Niang A, et al., "A mixed-field formulation for modeling dielectric ring resonators," *Sci. Rep.* 15, 35098 (2025). URL: https://doi.org/10.1038/s41598-025-18869-z

---

## 11. 验收与测试要点

### 11.1 正确性验证

- **解析基准 1**：二维平面波在均匀介质中传播，FDFD 场分布与解析解 $E_z=E_0 e^{ik_xx}$ 的相对误差 $\le 10^{-4}$（每波长 ≥20 网格点）。
- **解析基准 2**：金属圆柱散射（Mie 解析解），FDFD 散射场与 Mie 级数前 20 项之差的 $L^2$ 范数 $\le 10^{-3}$。
- **跨求解器对比**：与 FDTD 频域 DFT 监视器输出对比，同网格同源同边界，场幅值相对误差 $\le 1\%$。
- **与 SimWorks/Lumerical 对照**：SOI 波导模式注入 S 参数，幅值 $|S_{ij}|$ 一致性 $\le 0.5$ dB，相位一致性 $\le 2^\circ$。

### 11.2 PML 性能验证

- SC-PML 数值反射系数 $\le -60$ dB（Shin & Fan 2012 标准基准）。
- PML 厚度扫描（8/12/16 层）下反射单调下降。

### 11.3 求解器收敛性

- COCG / QMR-COCG 在 100×100×100 网格下迭代次数 ≤ 1000（ILU 预处理后）。
- 不收敛场景必须 `raise`（规则 14），禁止返回零场或上次迭代场作为 fall-back。

### 11.4 共享组件验证

- FDFD 与 FDE 使用同一 Yee 网格对象，`id(ε_r_array)` 一致，无内存复制。
- SC-PML 算子构造代码与 FDE 横向 PML 路径共享同一函数（ALGORITHMS.md 附录 C）。

### 11.5 质量门禁

- 实现文件位于 `modules/fdfd/src/polaris_fdfd/solver.py`，遵循规则 7（圈复杂度 ≤15、函数 ≤80 行、文件 ≤800 行）。
- 测试位于 `tests/test_fdfd_solver.py`，覆盖率 ≥ 90%（规则 10）。
- 文档字符串标注所有公式来源 URL（规则 18），代码无待办标记，无 fall-back。

---

## 修订日志

- **2026-06-25 v1.0**：首版生成。覆盖 FDFD 物理模型、Yee 离散、SC-PML、稀疏线性系统构建、求解器策略、伪代码、PoLaRIS 创新点、商业对标（T01/T16）、文献溯源、验收要点。所有公式经 Shin & Fan 2012 / Jaxwell / MaxwellFDFD / Gu 2014 / Yee 1966 核实（规则 18），无 fall-back 编造（规则 14），全部 CPU 算法（规则 26）。PoLaRIS 自研差异化设计标注【创新】并记录底层逻辑与支持理论。
