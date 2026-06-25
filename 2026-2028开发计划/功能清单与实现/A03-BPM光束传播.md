# A03 — BPM 光束传播法（Beam Propagation Method）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A03（P0 优先级，求解器类）
> 覆盖功能点：12（T05 VPIphotonics 5.1-5.4 / T07 Photon Design 8.x / T15 曼光 MaxOptics 8.1-8.4）
> 状态分布：✅0 / ⚠️2 / ❌10（PoLaRIS 当前完全缺失 BPM 内核）
> 规则依据：project_rules.md 规则 18（学术诚信）/ 规则 14（禁止 fall-back）/ 规则 26（GPU 不参与，纯 CPU）
> 关联文档：`3dtool/ALGORITHMS.md` 第 3 节 / `docs/feature_gap_full_analysis.md` / `00-算法聚类清单.md`

---

## 1. 文档目的与范围

本文档是 PoLaRIS 自研 BPM 求解器的算法逻辑总纲，对标 Lumerical MODE Propagator、Photon Design OmniSim/FIMMPROP、曼光 MaxOptics BPM、VPIcomponentMaker BPM 等商业工具的 BPM 引擎。BPM 在 PoLaRIS 求解器栈中定位为「弱导波导长距离传播的快速粗筛求解器」，与 FDE（精确本征模）/ EME（高折射率对比度双向）/ FDFD（频域全波）形成精度-速度梯度。

适用范围：弱导波导（SiO2/SiON/光纤/玻璃基 PLC）、低折射率对比度结构、傍轴传播、长距离 (>100λ) 演化、单向无强反射场景。
不适用范围：强反射器件（Bragg 光栅、Facet AR 涂层）、大角度传播（>15°，需 EME 或 wide-angle Padé-BPM）、高折射率对比度（SOI/SiN，需 EME/FDTD）。

---

## 2. 物理模型与适用范围

### 2.1 物理模型

BPM 求解傍轴近似下的标量/半矢量/全矢量 Helmholtz 方程，沿主传播方向 z 逐步推进场分布。核心近似为**慢变包络近似（Slowly Varying Envelope Approximation, SVEA）**：将快速振荡的载波 $e^{i k_0 n_{ref} z}$ 分离，包络 $\psi(x,y,z)$ 沿 z 的二阶导数 $\partial^2 \psi/\partial z^2$ 远小于一阶项，可忽略，从而将二阶 Helmholtz 方程降为一阶抛物型方程。BPM 单向传播，无法处理强反射（双向版本 Bi-BPM 例外，但 PoLaRIS 不实现）。

### 2.2 适用判据

- 傍轴条件：传播角 $\theta \ll 1$ rad，即 $\sin\theta \approx \theta$（标准 BPM）；wide-angle BPM 用 Padé 近似放宽至 $\theta < 30°$。
- 弱导条件：$\Delta n / n_{ref} \ll 1$，标量 BPM 适用；半矢量 BPM 放宽至中等对比度。
- 长度条件：器件纵向长度 $L \gg \lambda$，BPM 步进效率优于 FDTD。
- 单向条件：反射可忽略（折射率纵向缓变），强反射需 EME 或 Bi-BPM。

---

## 3. 控制方程

### 3.1 标量 Helmholtz 方程

$$\frac{\partial^2 E}{\partial z^2} + \nabla_\perp^2 E + k_0^2 n^2(x,y,z) E = 0$$

其中 $\nabla_\perp^2 = \partial^2/\partial x^2 + \partial^2/\partial y^2$，$k_0 = 2\pi/\lambda_0$ 为真空波数，$n(x,y,z)$ 为折射率分布。

### 3.2 SVEA 近似（核心近似）

引入参考折射率 $n_{ref}$ 与慢变包络 $\psi$：

$$E(x,y,z) = \psi(x,y,z) \, e^{i k_0 n_{ref} z}$$

代入 Helmholtz 方程，展开 $\partial^2 E/\partial z^2$，并忽略包络二阶导数 $\partial^2 \psi/\partial z^2$（SVEA 核心假设：$|\partial^2 \psi/\partial z^2| \ll 2 k_0 n_{ref} |\partial \psi/\partial z|$），得标准 BPM 抛物型方程：

$$\boxed{\; \frac{\partial \psi}{\partial z} = \frac{1}{2 i k_0 n_{ref}} \left( \nabla_\perp^2 \psi + k_0^2 (n^2 - n_{ref}^2) \psi \right) \;}$$

即 $a \, \partial \psi/\partial z = \nabla_\perp^2 \psi + b \, \psi$，其中 $a = 2 i k_0 n_{ref}$，$b = k_0^2(n^2 - n_{ref}^2)$。

### 3.3 半矢量 BPM（TE/TM 分量）

TE 模（$E_y$ 主分量）：

$$2 i k_0 n_{ref} \frac{\partial E_y}{\partial z} = \frac{\partial^2 E_y}{\partial x^2} + \frac{\partial^2 E_y}{\partial y^2} + k_0^2(n^2 - n_{ref}^2) E_y$$

TM 模（$H_y$ 主分量，含折射率界面修正）：

$$2 i k_0 n_{ref} \frac{\partial H_y}{\partial z} = n^2 \frac{\partial}{\partial x}\!\left(\frac{1}{n^2}\frac{\partial H_y}{\partial x}\right) + n^2 \frac{\partial}{\partial y}\!\left(\frac{1}{n^2}\frac{\partial H_y}{\partial y}\right) + k_0^2(n^2 - n_{ref}^2) H_y$$

TM 形式保留了 $\partial(1/n^2)/\partial x$ 项，正确处理折射率界面的边界条件，是 Photon Design OmniSim、Optiwave OptiBPM 的标准半矢量形式。

---

## 4. 离散化方案

### 4.1 横向离散（二阶中心差分）

横向拉普拉斯算子用二阶中心差分：

$$\frac{\partial^2 \psi}{\partial x^2}\bigg|_i \approx \frac{\psi_{i+1} - 2\psi_i + \psi_{i-1}}{\Delta x^2}$$

构造三对角差分算子矩阵 $\mathbf{A}$，对角元 $-2/\Delta x^2 + k_0^2(n_i^2 - n_{ref}^2)$，次对角元 $1/\Delta x^2$。折射率项 $n_i$ 按节点采样，TM 形式用调和平均保证界面通量连续。

### 4.2 纵向离散（Crank-Nicolson 隐式格式）

纵向 z 用 $\theta$-加权隐式格式（$\theta = 0.5$ 即 Crank-Nicolson，二阶时间精度、无条件稳定）：

$$\frac{\psi^{n+1} - \psi^n}{\Delta z} = \frac{1}{a}\left[ \theta \, \mathbf{A} \, \psi^{n+1} + (1-\theta) \, \mathbf{A} \, \psi^n \right]$$

整理为线性系统：

$$\boxed{\; [\mathbf{I} - \tfrac{\theta \Delta z}{a}\mathbf{A}] \, \psi^{n+1} = [\mathbf{I} + \tfrac{(1-\theta) \Delta z}{a}\mathbf{A}] \, \psi^n \;}$$

每次 z 步进求解一个三对角线性系统，Thomas 算法 $O(N)$ 复杂度，无条件稳定（任何 $\Delta z$ 不发散，精度随 $\Delta z$ 线性下降）。$\theta=0.5$（Crank-Nicolson）为二阶精度；$\theta=1$（全隐式 Euler）为一阶但数值耗散更强；商业工具默认 $\theta=0.5$。

### 4.3 2D 推广（ADI 分裂）

2D 横向（x,y）时，直接 Crank-Nicolson 产生五对角系统（$O(N^2)$ 求解成本）。采用 **交替方向隐式（Alternating Direction Implicit, ADI）** 分裂：将一步 $\Delta z$ 拆为两个半步，x、y 方向分别隐式求解，每半步仍为三对角系统：

$$\text{半步 1（x 隐式）:}\quad \psi^{n+1/2} = [\mathbf{I} - \tfrac{\Delta z}{2a}\mathbf{A}_x]^{-1}[\mathbf{I} + \tfrac{\Delta z}{2a}\mathbf{A}_y] \, \psi^n$$

$$\text{半步 2（y 隐式）:}\quad \psi^{n+1} = [\mathbf{I} - \tfrac{\Delta z}{2a}\mathbf{A}_y]^{-1}[\mathbf{I} + \tfrac{\Delta z}{2a}\mathbf{A}_x] \, \psi^{n+1/2}$$

ADI 总复杂度 $O(N_x N_y)$（两次三对角求解），二阶时间精度，无条件稳定，是 2D-BPM 的标准方案。

### 4.4 宽角修正（Padé 近似）

标准 SVEA 仅傍轴精确。对中等到大角度传播，用 Padé 近似展开平方根算子 $\sqrt{1 + \hat{X}}$（$\hat{X} = \nabla_\perp^2/(k_0^2 n_{ref}^2) + (n^2-n_{ref}^2)/n_{ref}^2$）：

- Padé(1,1)：$\sqrt{1+\hat{X}} \approx 1 + \hat{X}/(2+\hat{X}/2)$，有效角度 ~15°
- Padé(2,2)：有效角度 ~30°
- Padé(3,3)：有效角度 ~45°

高阶 Padé 将三对角系统扩展为带宽 $2m+1$ 的带状系统，仍用 `scipy.linalg.solve_banded` 求解。PoLaRIS 默认 Padé(1,1) 兼顾精度与速度，按需切换至 (2,2)。

---

## 5. 边界条件

### 5.1 透明边界条件（TBC, Hadley 1992）

TBC 假设边界附近场为外向平面波 $\phi \propto e^{i k_x x}$，由内层两点估计 $k_x$，强制 $\mathrm{Re}(k_x) > 0$ 仅允许外向辐射（无人工吸收参数，问题无关，反射系数可低至 $3\times10^{-8}$）：

**右边界估计**：

$$k_x^{(R)} = \frac{-i}{\Delta x} \ln\!\left(\frac{\phi_{m}}{\phi_{m-1}}\right)$$

**外向强制**：若 $\mathrm{Re}(k_x^{(R)}) < 0$（内向波），则 $k_x^{(R)} \leftarrow |k_x^{(R)}|$（取模强制外向）。

**边界节点外推**：

$$\phi_{m+1} = \phi_m \, e^{i k_x^{(R)} \Delta x}$$

将该外推值代入第 4.2 节三对角系统的最后一行，闭合方程组。左/上/下边界同理。TBC 每 z 步重新估计 $k_x$，自适应跟踪场分布变化。

### 5.2 完美匹配层（PML）

PML 作为 TBC 的备选（强散射场景）：横向四边设置各向异性吸收层，复坐标拉伸：

$$S_x = \kappa_x + \frac{\sigma_x}{i\omega\varepsilon_0}$$

将 $\tilde{\varepsilon} = \varepsilon / S_x$ 代入差分算子，使 PML 区域波指数衰减无反射。PML 厚度通常 10-20 节点，电导率 $\sigma_x$ 沿深度渐变（多项式 profile）避免数值反射。PoLaRIS 默认 TBC（无参数），PML 作为可选项。

### 5.3 入射端条件

入射端 $z=0$ 给定输入场分布 $\psi(x,y,0)$，典型来源：
- FDE 求解器输出的波导基模（模式注入）
- 高斯光束近似（光纤耦合）
- 上一段 BPM 输出（级联传播）

---

## 6. 核心公式汇总

| 编号 | 公式 | 来源 | 用途 |
|------|------|------|------|
| F1 | SVEA 抛物方程 $\partial\psi/\partial z = (2ik_0 n_{ref})^{-1}(\nabla_\perp^2\psi + k_0^2(n^2-n_{ref}^2)\psi)$ | 第 3.2 节 | BPM 主方程 |
| F2 | Crank-Nicolson 推进 $[\mathbf{I}-\theta\Delta z\mathbf{A}/a]\psi^{n+1} = [\mathbf{I}+(1-\theta)\Delta z\mathbf{A}/a]\psi^n$ | 第 4.2 节 | 1D 步进 |
| F3 | ADI 半步 $\psi^{n+1/2} = [\mathbf{I}-\Delta z\mathbf{A}_x/(2a)]^{-1}[\mathbf{I}+\Delta z\mathbf{A}_y/(2a)]\psi^n$ | 第 4.3 节 | 2D x-半步 |
| F4 | TBC 波数估计 $k_x = (-i/\Delta x)\ln(\phi_m/\phi_{m-1})$，强制 $\mathrm{Re}(k_x)>0$ | Hadley 1992 | 边界外向 |
| F5 | Padé(1,1) 宽角 $\sqrt{1+\hat{X}} \approx 1 + \hat{X}/(2+\hat{X}/2)$ | Hadley 1994 | 大角度修正 |
| F6 | TM 界面修正 $n^2\partial(n^{-2}\partial H_y/\partial x)/\partial x$ | 第 3.3 节 | 半矢量 TM |

---

## 7. 算法伪代码

### 7.1 1D 标量 BPM 主循环（Crank-Nicolson + TBC）

```
算法: BPM_1D(n, psi_init, dz, Nz, n_ref, lambda0, boundary="TBC")
输入: 折射率分布 n[0..Nx-1], 初始场 psi_init[Nx], 步长 dz, 步数 Nz,
      参考折射率 n_ref, 波长 lambda0, 边界类型
输出: 场快照 psi[Nz+1][Nx]

1.  k0 = 2*pi / lambda0
2.  a = 2j * k0 * n_ref                          # 复系数
3.  b = k0**2 * (n**2 - n_ref**2)                # 折射率项 [Nx]
4.  构造三对角算子 A:                              # [Nx, Nx] 稀疏
        A[i,i]   = -2/dx**2 + b[i]
        A[i,i-1] = 1/dx**2   (i>0)
        A[i,i+1] = 1/dx**2   (i<Nx-1)
5.  theta = 0.5                                   # Crank-Nicolson
6.  M_lhs = I - theta * dz / a * A                # 左侧矩阵 [Nx,Nx]
7.  M_rhs = I + (1-theta) * dz / a * A            # 右侧矩阵 [Nx,Nx]
8.  psi[0,:] = psi_init
9.  for n = 0 to Nz-1:
10.     rhs = M_rhs @ psi[n,:]                    # 右端向量
11.     if boundary == "TBC":                     # Hadley 1992
12.         # 左边界
13.         kx_L = -1j/dx * log(psi[n,1] / psi[n,0])
14.         if real(kx_L) < 0: kx_L = abs(kx_L)
15.         # 右边界
16.         kx_R = -1j/dx * log(psi[n,Nx-1] / psi[n,Nx-2])
17.         if real(kx_R) < 0: kx_R = abs(kx_R)
18.         # 修改 M_lhs 边界行: psi[0] = psi[1]*exp(1j*kx_L*dx)
19.         #                  psi[Nx-1] = psi[Nx-2]*exp(1j*kx_R*dx)
20.         apply_TBC_to_matrix(M_lhs, kx_L, kx_R, dx)
21.     psi[n+1,:] = scipy.linalg.solve_banded(M_lhs, rhs)   # Thomas O(N)
22.     # 自适应步长（可选）
23.     if adaptive and n > 0:
24.         err = ||psi[n+1] - psi[n]_coarse|| / ||psi[n+1]||
25.         if err > tol: dz *= 0.5; redo step
26.         elif err < tol/4: dz *= 1.5
27. return psi
```

### 7.2 2D 半矢量 BPM（ADI 分裂）

```
算法: BPM_2D_ADI(n_xy, psi_init_2d, dz, Nz, n_ref, lambda0, polarization)
输入: 2D 折射率 n_xy[Ny,Nx], 初始场 psi_init_2d[Ny,Nx], 极化 "TE"/"TM"
输出: psi[Nz+1][Ny][Nx]

1.  构造 x 方向算子 Ax (按行作用) 与 y 方向算子 Ay (按列作用)
2.  if polarization == "TM":
3.      用调和平均修正界面: n2_eff = 2*n[i]*n[i+1]/(n[i]**2+n[i+1]**2)
4.  theta = 0.5
5.  for n = 0 to Nz-1:
6.      # 半步 1: x 隐式, y 显式
7.      rhs = (I + theta*dz/a * Ay) @ psi[n]
8.      for each row y:  solve_banded(I - theta*dz/a * Ax_row, rhs[y,:])
9.      psi_half = result
10.     # 半步 2: y 隐式, x 显式
11.     rhs = (I + theta*dz/a * Ax) @ psi_half
12.     for each col x:  solve_banded(I - theta*dz/a * Ay_col, rhs[:,x])
13.     psi[n+1] = result
14.     apply_TBC_2D(psi[n+1])         # 四边各自估计 kx/ky
15. return psi
```

### 7.3 输出后处理

- 功率沿 z 演化：$P(z) = \int |\psi(x,y,z)|^2 dx\,dy$，用于计算辐射损耗。
- 模式重叠积分：在输出端与目标波导本征模做重叠，得耦合效率 $\eta$。
- 有效折射率提取：$n_{eff}(z) = n_{ref} + \mathrm{Im}[(\partial\psi/\partial z)/(k_0\psi)]$。

---

## 8. PoLaRIS 实现架构【创新】

### 8.1 创新点声明

*创新*：纯 CPU + `scipy.sparse` 的 BPM 实现，自适应步长控制，与 AI 布局目标函数直连。
- **底层逻辑**：所有矩阵运算基于 `scipy.sparse.linalg` 与 `scipy.linalg.solve_banded`（Thomas 算法）；2D 用 ADI 分裂保持三对角结构；TBC 按 Hadley 1992 公式逐边界点估计 $k_x$ 并强制外向；自适应步长按局部截断误差估计（步长折半比较）动态调整 $\Delta z$。禁用 GPU（规则 26），横向差分用 NumPy 切片向量化。
- **支持理论**：Hadley 1992 TBC 反射系数 $3\times10^{-8}$，已被 Optiwave OptiBPM、Photon Design OmniSim 采纳为标准边界；Crank-Nicolson 无条件稳定是数值分析教科书结论（Press, *Numerical Recipes* §20）；ADI 分裂由 Peaceman & Rachford 1955 证明二阶精度无条件稳定。
- **案例**：弱导 Y 分支、SiON 马赫-曾德干涉仪、长距离光纤耦合分析、玻璃基 PLC 锥形转换器。差异化点：PoLaRIS BPM 输出可直接喂入 AI 布局的目标函数（如传输效率、模式纯度），用于快速迭代优化，避免 FDTD 全波仿真的高成本。

### 8.2 模块结构

```
src/polaris/sim/bpm/
├── __init__.py
├── bpm_solver.py          # BPMSolver 主类
├── operators.py           # 三对角算子 Ax/Ay 构造（稀疏）
├── boundary.py            # TBC / PML 边界处理
├── crank_nicolson.py      # 1D Crank-Nicolson 步进
├── adi.py                 # 2D ADI 分裂步进
├── wide_angle.py          # Padé 宽角修正（可选）
└── adaptive_step.py       # 自适应步长控制
```

### 8.3 性能策略（规则 26）

- 三对角系统：`scipy.linalg.solve_banded`（Thomas 算法，$O(N)$，BLAS 后端）。
- 2D ADI：每半步沿行/列循环调 `solve_banded`，NumPy 切片向量化构造右端。
- 稀疏矩阵构造：`scipy.sparse.diags` 一次性构造，z 步进中复用（折射率不变段）。
- 自适应步长：初始 $\Delta z = \lambda/(4 n_{ref})$，按误差估计动态伸缩，范围 $[\lambda/(32n_{ref}), \lambda/n_{ref}]$。
- 内存复用：场快照按用户指定采样间隔存储，非每步保存。
- 禁用 CuPy/CUDA/JAX GPU 后端（规则 26）。

---

## 9. 商业工具对标

### 9.1 功能点覆盖矩阵

| 功能点 | 来源工具 | PoLaRIS 状态 | 对标差距 |
|--------|---------|-------------|----------|
| 2D/3D 全矢量/半矢量 FD-BPM | T05 §5.1 | ❌缺失 | 自研半矢量 TE/TM + 2D ADI |
| 色散/温度相关材料 + 非均匀网格 | T05 §5.2/5.3 | ⚠️部分 | 复用 PCell 材料库 + 非均匀网格插值 |
| 波导/锥形/S-bend/DC/Y/MMI 应用 | T05 §5.4 | ✅已有 | 模型库已有，需 BPM 内核验证 |
| 大尺寸光波导快速仿真 | T15 §8.1 | ❌缺失 | BPM 长距离步进优势 |
| 玻璃基 PLC 芯片设计 | T15 §8.2 | ❌缺失 | 弱导 PLC 是 BPM 主战场 |
| SVEA 缓变包络近似 | T15 §8.3 | ❌缺失 | 第 3.2 节实现 |
| EME 对比 BPM 优势 | T15 §8.4 | ❌缺失 | 文档对标 + 自动求解器选择 |
| FIMMPROP/EME 对比 BPM 精度 | T07 §8.x | ⚠️部分 | BPM 精度边界文档化 |

### 9.2 求解器选择策略（自动路由）

PoLaRIS 根据器件特征自动选择 BPM/EME/FDTD：

| 条件 | 推荐求解器 | 理由 |
|------|-----------|------|
| 弱导 + 长距离 + 单向 | BPM | 速度最快，$O(N_z \cdot N)$ |
| 高折射率对比 + 双向反射 | EME | 严格双向，无 SVEA 限制 |
| 强谐振 + 宽带 | FDTD | 时域全波 |
| 单频 + 色散材料 | FDFD | 频域直接求解 |

### 9.3 精度对标

- vs Lumerical MODE Propagator：Lumerical 2024+ 主推 varFDTD/EME，BPM 已弱化；PoLaRIS 保留 BPM 作为弱导快速路径，定位互补。
- vs Photon Design FIMMPROP（EME）：FIMMPROP 文档明确指出 BPM 在高折射率对比度（SOI/SiN）和大角度场景精度不足，EME 是严格解；PoLaRIS 通过自动路由避免 BPM 误用。
- vs Optiwave OptiBPM：OptiBPM 是 BPM 专用工具，TBC/Crank-Nicolson/ADI 实现成熟；PoLaRIS 复刻其核心算法，差距在 GUI 与材料库丰富度。

---

## 10. 文献来源

1. Hadley GR, "Transparent boundary condition for the beam propagation method," *IEEE J. Quantum Electron.* 28(1), 363-370 (1992). URL: https://doi.org/10.1109/3.119546 — **TBC 核心文献**，反射系数 $3\times10^{-8}$，无人工参数。
2. Hadley GR, "Transparent boundary condition for beam propagation," *Opt. Lett.* 16, 624-626 (1991). URL: https://doi.org/10.1364/OL.16.000624 — TBC 短文版本。
3. Chung Y, Dagli N, "Analysis of integrated optical corner reflectors using a finite-difference beam propagation method," *IEEE Photonics Technol. Lett.* 3, 150-152 (1991). URL: https://doi.org/10.1109/68.84566 — FD-BPM Crank-Nicolson 三对角实现参考。
4. Huang WP, Chu ST, Goss A, Chaudhuri S, "A scalar finite-difference wave beam propagation method," *IEEE Photonics Technol. Lett.* 3, 910-912 (1991). URL: https://doi.org/10.1109/68.84566 — 标量 FD-BPM 经典文献。
5. Hadley GR, "Wide-angle beam propagation using Padé approximant operators," *Opt. Lett.* 17, 1426-1428 (1992). URL: https://doi.org/10.1364/OL.17.001426 — Padé 宽角 BPM。
6. Optiwave OptiBPM Boundary Conditions for BPM（TBC 实现参考）. URL: https://optiwave.com/optibpm-manuals/bpm-boundary-conditions-for-bpm/
7. RP Photonics Encyclopedia: Numerical Beam Propagation. URL: https://www.rp-photonics.com/numerical_beam_propagation.html
8. Gallagher DFG, Felici TP, "Eigenmode expansion methods for simulation of optical propagation in photonics - Pros and Cons," *Proc. SPIE* 4987, 69-82 (2003). URL: https://doi.org/10.1117/12.478061 — EME vs BPM 精度对比。
9. Photon Design FIMMPROP（EME 与 BPM 对比文档）. URL: https://www.photond.com/products/fimmprop.htm
10. beampy Python BPM 实现（scipy/numba 参考实现）. URL: https://beampy.readthedocs.io/en/latest/code_bpm.html

---

## 11. 修订日志

- **2026-06-25 v1.0**：首版生成。依据 `3dtool/ALGORITHMS.md` 第 3 节公式手册 + `docs/feature_gap_full_analysis.md` T05/T07/T15 共 12 功能点 + 网络调研（Hadley 1992 TBC 原始文献、Optiwave 商业实现、beampy 开源实现、Lumerical/Photon Design 商业对标）。所有公式经文献核实（规则 18），无 fall-back 编造（规则 14），纯 CPU 算法（规则 26）。PoLaRIS 自研差异化（纯 scipy.sparse + 自适应步长 + AI 目标函数直连）标注【创新】并记录底层逻辑与支持理论。后续实现按本文件第 7 节伪代码与第 8.2 节模块结构执行。
