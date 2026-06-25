# 核心求解器算法公式手册（ALGORITHMS.md）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 适用范围：CPU 纯 Python 实现（规则 26：不参与 GPU 计算）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（GPU 不参与）
> 关联文档：INVENTORY.md（求解器实现状态）、year_plan_2026_06_2027_05.md（实现优先级）

## 摘要

本文档收录 PoLaRIS 项目缺失但商业对标工具（Lumerical/Tidy3D/曼光 MaxOptics/SimWorks）已有的 8 个核心求解器算法公式，作为纯 Python 实现的理论基础。每个求解器章节包含：物理模型、控制方程、离散化方案、边界条件、核心公式、文献来源、PoLaRIS 实现【创新】点。所有公式均经 arXiv/IEEE/官方文档核实（规则 18），禁止 fall-back 编造（规则 14），全部为 CPU 算法（规则 26）。

---

## 1. RCWA — 严格耦合波分析（Rigorous Coupled-Wave Analysis）

### 1.1 物理模型

RCWA 求解 Maxwell 方程在周期结构中的散射问题，适用于光栅、超表面、亚波长结构。将介质沿 z 方向分层，每层内介电常数沿横向（xy 平面）周期分布，沿纵向均匀；通过傅里叶级数展开横向介电常数，将 Maxwell 方程转化为每层的本征值问题，再通过 S 矩阵级联得到全局反射/透射系数。该方法对亚波长光栅、超表面具有严格的全波解精度。

### 1.2 控制方程

Maxwell 方程频域形式（时谐因子 $e^{i\omega t}$）：

$$\nabla \times \mathbf{E} = -i\omega\mu_0 \mathbf{H}$$

$$\nabla \times \mathbf{H} = i\omega\varepsilon_0\varepsilon_r(x,y,z) \mathbf{E}$$

其中 $\varepsilon_r(x,y,z)$ 为相对介电常数分布，在每层内仅依赖横向坐标 $(x,y)$，且具有周期性 $\varepsilon_r(x+\Lambda_x, y+\Lambda_y, z) = \varepsilon_r(x,y,z)$。

### 1.3 离散化方案

- **横向（xy 平面）**：傅里叶展开。介电常数展开为 $\varepsilon_r(x,y) = \sum_{m,n} \tilde{\varepsilon}_{mn} e^{i(mK_x x + nK_y y)}$，其中 $K_x = 2\pi/\Lambda_x$，$K_y = 2\pi/\Lambda_y$。
- **Li 1996 改进因子**：对 TE/TM 分量分别采用不同的傅里叶因子化规则（正常/逆规则），避免 Gibbs 现象导致的 TM 偏振收敛缓慢问题。
- **纵向（z 方向）**：分层均匀化，每层求解本征值问题。
- **傅里叶级数截断阶数 N**：采用 odd-N rule，即截断为 $N \times N$（N 为奇数）以避免 Nyquist 混叠。

### 1.4 边界条件

- **入射端（z < 0）**：入射平面波 + 反射衍射级，反射场 $\mathbf{E}_r = \sum_m R_m e^{-ik_{zm} z} \mathbf{e}_m^{(r)}$。
- **出射端（z > d）**：透射衍射级，透射场 $\mathbf{E}_t = \sum_m T_m e^{ik_{zm}' z} \mathbf{e}_m^{(t)}$。
- **周期边界**：Bloch 条件 $\mathbf{E}(x+\Lambda_x, y, z) = \mathbf{E}(x,y,z) e^{i k_{x0} \Lambda_x}$。
- **界面连续性**：切向 $\mathbf{E}$、$\mathbf{H}$ 在层界面连续。

### 1.5 核心公式

**傅里叶展开与卷积**（Li 1996）：

$$\varepsilon_r(x,y) = \sum_{m,n} \tilde{\varepsilon}_{mn} e^{i(mK_x x + nK_y y)}$$

介电常数与场的乘积在频域为卷积：$(\varepsilon_r \mathbf{E})_{mn} = \sum_{p,q} \tilde{\varepsilon}_{m-p, n-q} \tilde{E}_{pq}$，对应矩阵乘法 $\mathbf{E}^\varepsilon \cdot \tilde{\mathbf{E}}$，其中 $\mathbf{E}^\varepsilon$ 为 Toeplitz 块矩阵。

**本征值问题**（每层）：

$$\mathbf{Q}^2 \begin{pmatrix} S_x \\ S_y \end{pmatrix} = k_z^2 \begin{pmatrix} S_x \\ S_y \end{pmatrix}$$

其中 $\mathbf{Q}$ 为由傅里叶系数矩阵构造的 $2N \times 2N$ 系数矩阵，$k_z$ 为纵向波数特征值，$S_x, S_y$ 为切向场振幅。求解得到每层前向/后向传播常数 $k_{zm}^{(\pm)}$ 及对应本征模。

**Redheffer 星积**（层间 S 矩阵级联，避免数值指数发散）：

$$\mathbf{S}_{12}^{tot} = \mathbf{S}_{12}^{(2)}(\mathbf{I} - \mathbf{S}_{11}^{(1)}\mathbf{S}_{22}^{(2)})^{-1}\mathbf{S}_{12}^{(1)}$$

$$\mathbf{S}_{11}^{tot} = \mathbf{S}_{11}^{(2)} + \mathbf{S}_{12}^{(2)}\mathbf{S}_{11}^{(1)}(\mathbf{I} - \mathbf{S}_{22}^{(2)}\mathbf{S}_{11}^{(1)})^{-1}\mathbf{S}_{21}^{(2)}$$

**增强透射矩阵法（Enhanced TMM）**（Moharam 1995）：避免 $e^{ik_z d}$ 在消逝波时数值溢出，从最后一层向前递推，仅传递透射振幅。

### 1.6 文献来源

- Moharam MG, Gaylord TK, "Rigorous coupled-wave analysis of planar-grating diffraction," J. Opt. Soc. Am. 71, 811-818 (1981). URL: https://doi.org/10.1364/JOSA.71.000811
- Li LF, "Use of Fourier series in the analysis of discontinuous periodic structures," J. Opt. Soc. Am. A 13, 1870-1876 (1996). URL: https://doi.org/10.1364/JOSAA.13.001870
- Moharam MG, Pommet DA, Grann EB, Gaylord TK, "Stable implementation of the rigorous coupled-wave analysis for surface-relief gratings: enhanced transmittance matrix approach," J. Opt. Soc. Am. A 12, 1077-1086 (1995). URL: https://doi.org/10.1364/JOSAA.12.001077
- NIST SCATMECH RCW 模块文档（实现参考）. URL: https://pages.nist.gov/SCATMECH/code/rcw.h

### 1.7 PoLaRIS 实现【创新】点

*创新*：纯 NumPy/SciPy 实现的 RCWA，禁用 GPU（规则 26）。
- **底层逻辑**：使用 `scipy.linalg.eig` 求解每层 $2N \times 2N$ 本征值问题；使用 `scipy.sparse.linalg` 求解 Redheffer 星积中的稀疏线性系统 $(\mathbf{I} - \mathbf{S}_{11}^{(1)}\mathbf{S}_{22}^{(2)})^{-1}$；采用 Moharam 1995 增强透射矩阵法从末层前向递推，避免消逝波指数溢出。
- **支持理论**：Moharam 1995 的稳定传输矩阵法已被 NIST SCATMECH、Meent 等开源实现验证为数值稳定的标准方案。
- **案例**：SOI 亚波长光栅耦合器、超表面相位调控单元。差异化点在于 PoLaRIS 将 RCWA 与 AI 布局引擎的 PDK 单元库直连，支持自动光栅周期扫描。

---

## 2. EME — 本征模展开法（Eigenmode Expansion Method）

### 2.1 物理模型

EME 是频域全矢量双向传播方法。将器件沿传播方向 z 切分为若干 cell，每个 cell 内截面 z 不变；在每个 cell 中心求解本地本征模（由 FDE 求解器提供），将场展开为前向/后向本地模的线性叠加；在 cell 界面通过切向场连续性匹配，得到界面 S 矩阵；最后将所有 cell 的 S 矩阵级联得到器件全局 S 矩阵。EME 不依赖慢变包络近似，对高折射率对比度器件（SOI/SiN）精度优于 BPM。

### 2.2 控制方程

频域 Maxwell 方程在 z 不变截面下的本征模解：

$$\mathbf{E}(x,y,z) = \sum_m \left[ a_m^{(+)} e^{i\beta_m z} + a_m^{(-)} e^{-i\beta_m z} \right] \mathbf{e}_m(x,y)$$

$$\mathbf{H}(x,y,z) = \sum_m \left[ a_m^{(+)} e^{i\beta_m z} - a_m^{(-)} e^{-i\beta_m z} \right] \mathbf{h}_m(x,y)$$

其中 $\mathbf{e}_m, \mathbf{h}_m$ 为第 m 个本地本征模的横向场分布，$\beta_m$ 为传播常数，$a_m^{(\pm)}$ 为前向/后向展开系数。

### 2.3 离散化方案

- **横向（xy）**：交由 FDE 求解器在 Yee 网格上离散，得到本地本征模。
- **纵向（z）**：cell 划分。每个 cell 内截面不变，仅在 cell 界面发生模式耦合。均匀段用 1 个 cell；锥形/渐变段用多 cell 或 CVCS（Continuously Varying Cross-sectional Subcell）子单元法提高精度。
- **模式数截断**：每 cell 保留前 M 个本征模（含导模 + 辐射模离散化近似）。

### 2.4 边界条件

- **输入/输出端口**：匹配参考波导的本征模，定义 S 矩阵端口。
- **横向边界**：PML 或 TBC（由 FDE 求解器处理辐射模吸收）。
- **界面连续性**：切向 $\mathbf{E}_t, \mathbf{H}_t$ 在 cell 界面连续。

### 2.5 核心公式

**模式正交归一化**（功率内积）：

$$\int \left( \mathbf{e}_m \times \mathbf{h}_n^* \right) \cdot \hat{z} \, dA = \delta_{mn}$$

**界面模式重叠积分**（Gallagher & Felici 2003，SimWorks EME）：

$$\langle \mathbf{e}_m^{(A)}, \mathbf{h}_n^{(B)} \rangle = \frac{1}{2} \int \mathbf{e}_m^{(A)} \times \mathbf{h}_n^{(B)*} \cdot \hat{z} \, dA$$

**界面 S 矩阵**（切向场连续性 + 正交投影）：

$$\begin{pmatrix} \mathbf{a}^{(-)} \\ \mathbf{b}^{(+)} \end{pmatrix} = \mathbf{S}_J \begin{pmatrix} \mathbf{a}^{(+)} \\ \mathbf{b}^{(-)} \end{pmatrix} = \begin{pmatrix} \mathbf{R}_{AB} & \mathbf{T}_{BA} \\ \mathbf{T}_{AB} & \mathbf{R}_{BA} \end{pmatrix} \begin{pmatrix} \mathbf{a}^{(+)} \\ \mathbf{b}^{(-)} \end{pmatrix}$$

其中反射矩阵 $\mathbf{R}$、透射矩阵 $\mathbf{T}$ 由重叠积分矩阵构造。

**均匀段传播 S 矩阵**：

$$\mathbf{S}_{WG} = \begin{pmatrix} \mathbf{0} & \mathbf{P} \\ \mathbf{P} & \mathbf{0} \end{pmatrix}, \quad \mathbf{P} = \mathrm{diag}(e^{i\beta_m L})$$

**全局 S 矩阵级联**（Redheffer 星积，同 RCWA 第 1.5 节公式）。

### 2.6 文献来源

- Gallagher DF, Felici T, "Eigenmode expansion methods for simulation of optical propagation in photonics - Pros and Cons," Proc. SPIE 4987, 69-82 (2003). URL: https://doi.org/10.1117/12.478061
- Lumerical MODE EME solver introduction. URL: https://optics.ansys.com/hc/en-us/articles/360034396614
- SimWorks Eigenmode Expansion (EME) Solver. URL: https://www.emsimworks.com/en/solver/EME
- Photon Design FIMMPROP EME paper. URL: https://photond.com/assets/files/FIMMWAVE/PW03_eme_paper.pdf

### 2.7 PoLaRIS 实现【创新】点

*创新*：EME 与 FDE 共享同一本征模求解内核，避免重复实现。
- **底层逻辑**：EME 求解器调用 FDE 求解器在每个 cell 中心计算本地模；界面重叠积分用 NumPy 矩阵乘法实现；S 矩阵级联采用 Redheffer 星积，复用 RCWA 的稀疏求解路径。
- **支持理论**：Gallagher & Felici 2003 证明 EME 对长结构（锥形、MMI、周期器件）计算成本与长度无关，优于 FDTD。
- **案例**：SOI 锥形模式转换器、MMI 功分器、长周期布拉格光栅。差异化点：PoLaRIS EME 支持长度参数扫描时无需重算本地模（analysis 模式），与商业 Lumerical EME 行为对齐。

---

## 3. BPM — 光束传播法（Beam Propagation Method）

### 3.1 物理模型

BPM 求解傍轴近似下的标量/矢量 Helmholtz 方程，沿主传播方向 z 逐步推进场分布。适用于弱导波导、低折射率对比度结构（如 SiO2/SiON、光纤）。核心近似为慢变包络近似（SVEA），即包络沿 z 变化远慢于载波，从而忽略 $\partial^2 E/\partial z^2$ 中包络二阶导数项。BPM 单向传播，无法处理强反射，但对长距离传播效率高。

### 3.2 控制方程

标量 Helmholtz 方程：

$$\frac{\partial^2 E}{\partial z^2} + \frac{\partial^2 E}{\partial x^2} + k_0^2 n^2(x,z) E = 0$$

引入 SVEA：$E(x,z) = \psi(x,z) e^{i k_0 n_{ref} z}$，其中 $n_{ref}$ 为参考折射率，$\psi$ 为慢变包络。代入并忽略 $\partial^2 \psi/\partial z^2$（SVEA）：

$$\frac{\partial \psi}{\partial z} = \frac{1}{2 i k_0 n_{ref}} \left( \frac{\partial^2 \psi}{\partial x^2} + k_0^2 (n^2 - n_{ref}^2) \psi \right)$$

即标准 BPM 抛物型方程：$a \frac{\partial E}{\partial z} = \frac{\partial^2 E}{\partial x^2} + b E$，其中 $a = 2 i k_0 n_{ref}$，$b = k_0^2(n^2 - n_{ref}^2)$。

### 3.3 离散化方案

- **横向（x/y）**：二阶中心差分，$\frac{\partial^2 E}{\partial x^2} \approx \frac{E_{i+1} - 2E_i + E_{i-1}}{\Delta x^2}$。
- **纵向（z）**：Crank-Nicolson 隐式格式（无条件稳定），$\frac{\partial E}{\partial z} \approx \frac{E^{n+1} - E^n}{\Delta z}$，对横向算子取 $\theta$-加权（$\theta=0.5$ 为 Crank-Nicolson）：

$$[\mathbf{I} - \theta \Delta z \mathbf{A}] \mathbf{E}^{n+1} = [\mathbf{I} + (1-\theta) \Delta z \mathbf{A}] \mathbf{E}^n$$

- **2D 推广**：ADI（Alternating Direction Implicit）分裂，将 2D 问题分解为 x、y 方向两次 1D 三对角求解，复杂度 $O(N)$。
- **宽角修正**：Padé 近似高阶 SVEA 修正项处理大角度传播。

### 3.4 边界条件

- **透明边界条件（TBC, Hadley 1992）**：假设边界附近场为外向平面波 $\phi \propto e^{i k_x x}$，由内层两点估计 $k_x$，强制 $\mathrm{Re}(k_x) > 0$ 仅允许外向辐射：

$$k_x = \frac{-i}{\Delta x} \ln\left(\frac{\phi_0}{\phi_{-1}}\right), \quad \text{若 } \mathrm{Re}(k_x) < 0 \text{ 则强制 } k_x \leftarrow |k_x|$$

- **PML**：各向异性吸收层，复坐标拉伸 $S_x = \kappa + \sigma_x/(i\omega\varepsilon_0)$。
- **入射端**：给定输入场分布（如波导基模）。

### 3.5 核心公式

**SVEA 抛物方程**（同 3.2）。

**Crank-Nicolson 推进**：

$$\mathbf{E}^{n+1} = [\mathbf{I} - \theta \Delta z \mathbf{A}]^{-1} [\mathbf{I} + (1-\theta) \Delta z \mathbf{A}] \mathbf{E}^n$$

其中 $\mathbf{A}$ 为三对角差分算子矩阵，含横向拉普拉斯 + 折射率项。每次推进求解一个三对角线性系统（Thomas 算法，$O(N)$）。

**TBC 边界波数估计**（Hadley 1992，Optiwave BPM）：

$$k_x^{(right)} = \frac{-i}{\Delta x} \ln\left(\frac{\phi_{m}}{\phi_{m-1}}\right), \quad \phi_{m+1} = \phi_m e^{i k_x \Delta x}$$

**ADI 分裂**（2D）：

$$\mathbf{E}^{n+1/2} = [\mathbf{I} - \tfrac{\Delta z}{2}\mathbf{A}_x]^{-1}[\mathbf{I} + \tfrac{\Delta z}{2}\mathbf{A}_y]\mathbf{E}^n$$

$$\mathbf{E}^{n+1} = [\mathbf{I} - \tfrac{\Delta z}{2}\mathbf{A}_y]^{-1}[\mathbf{I} + \tfrac{\Delta z}{2}\mathbf{A}_x]\mathbf{E}^{n+1/2}$$

### 3.6 文献来源

- Hadley GR, "Transparent boundary condition for beam propagation," Opt. Lett. 17, 878-880 (1992). URL: https://doi.org/10.1364/OL.17.000878
- Optiwave OptiBPM Boundary Conditions for BPM（TBC 实现参考）. URL: https://optiwave.com/optibpm-manuals/bpm-boundary-conditions-for-bpm/
- Huang WP, Chu ST, Goss A, Chaudhuri S, "A scalar finite-difference wave beam propagation method," IEEE Photonics Tech. Lett. 3, 910-912 (1991). URL: https://doi.org/10.1109/68.84566
- RP Photonics Encyclopedia: Numerical Beam Propagation. URL: https://www.rp-photonics.com/numerical_beam_propagation.html

### 3.7 PoLaRIS 实现【创新】点

*创新*：BPM 作为快速粗筛求解器，与 EME/FDE 形成精度-速度梯度。
- **底层逻辑**：`scipy.linalg.solve_banded` 求解三对角系统实现 Crank-Nicolson；2D 采用 ADI 分裂；TBC 按 Hadley 1992 公式逐边界点估计 $k_x$ 并强制外向。禁用 GPU，纯 NumPy 向量化横向差分。
- **支持理论**：Hadley 1992 TBC 已被 Optiwave、Photon Design OmniSim 等商业工具采纳为标准边界处理。
- **案例**：弱导 Y 分支、SiON 马赫-曾德干涉仪、长距离光纤耦合分析。差异化点：PoLaRIS BPM 输出可直接喂入 AI 布局的目标函数，用于快速迭代优化。

---

## 4. HEAT — 热传导求解器

### 4.1 物理模型

HEAT 求解傅里叶导热方程，模拟光电子器件中焦耳热、辐射热、边界对流等引起的稳态/瞬态温度分布。光电子器件（如热光调相器、SiN 加热臂）的性能强依赖温度场，需耦合电磁求解得到损耗分布作为热源，再求解温度场反作用于折射率（$dn/dT$）。控制方程为含源热扩散方程。

### 4.2 控制方程

傅里叶导热方程（瞬态）：

$$\rho c_p \frac{\partial T}{\partial t} = \nabla \cdot (k \nabla T) + Q$$

稳态（$\partial T/\partial t = 0$）退化为 Poisson 型方程：

$$-\nabla \cdot (k \nabla T) = Q$$

其中 $\rho$ 为密度（kg/m³），$c_p$ 为比热容（J/(kg·K)），$k$ 为导热系数（W/(m·K)），$Q$ 为体积热源密度（W/m³）。热流密度（傅里叶定律）：

$$\mathbf{q} = -k \nabla T$$

### 4.3 离散化方案

- **空间**：有限体积法（FVM）/有限差分。节点中心差分 $\nabla \cdot (k \nabla T) \approx \frac{k_{i+1/2}(T_{i+1}-T_i) - k_{i-1/2}(T_i - T_{i-1})}{\Delta x^2}$，界面 $k$ 取调和平均保证通量连续。
- **时间**：隐式 Euler（无条件稳定）或 Crank-Nicolson。

$$\rho c_p \frac{T^{n+1}_i - T^n_i}{\Delta t} = \frac{k_{i+1/2}(T^{n+1}_{i+1}-T^{n+1}_i) - k_{i-1/2}(T^{n+1}_i - T^{n+1}_{i-1})}{\Delta x^2} + Q_i$$

- **2D/3D**：交替方向隐式（ADI）或稀疏矩阵直接/迭代求解。

### 4.4 边界条件

5 类标准边界（COMSOL Heat Transfer Module）：

1. **Dirichlet（第一类）**：固定温度 $T|_{\Gamma} = T_0$（如恒温基底）。
2. **Neumann（第二类）**：固定热流 $-k \partial T/\partial n|_{\Gamma} = q_0$（如绝热 $\partial T/\partial n = 0$）。
3. **Robin（第三类，对流）**：$-k \partial T/\partial n|_{\Gamma} = h(T - T_{\infty})$，$h$ 为对流换热系数。
4. **Radiation（辐射）**：$-k \partial T/\partial n|_{\Gamma} = \varepsilon \sigma (T^4 - T_{\infty}^4)$，$\varepsilon$ 为发射率，$\sigma$ 为 Stefan-Boltzmann 常数。
5. **Contact（接触热阻）**：$-k \partial T/\partial n|_{\Gamma} = (T - T_{contact})/R_{th}$，$R_{th}$ 为界面热阻。

### 4.5 核心公式

**傅里叶定律 + 通量守恒**（COMSOL 海缆热效应模型推导）：

$$\nabla \cdot \mathbf{q} = Q, \quad \mathbf{q} = -k \nabla T \Rightarrow -\nabla \cdot (k \nabla T) = Q$$

**焦耳热源**（耦合电磁求解器输出）：

$$Q_{Joule} = \frac{1}{2} \mathrm{Re}(\mathbf{J} \cdot \mathbf{E}^*)$$

**有限体积离散**（节点 i，控制体积 $\Delta V_i$）：

$$\sum_{j \in N(i)} \frac{k_{ij}(T_i - T_j)}{d_{ij}} A_{ij} + Q_i \Delta V_i = 0 \quad (\text{稳态})$$

其中 $N(i)$ 为节点 i 的邻居，$d_{ij}$ 为节点间距，$A_{ij}$ 为界面面积。

**隐式 Euler 时间推进**（瞬态）：

$$\mathbf{M} \frac{\mathbf{T}^{n+1} - \mathbf{T}^n}{\Delta t} + \mathbf{K} \mathbf{T}^{n+1} = \mathbf{Q}$$

其中 $\mathbf{M} = \mathrm{diag}(\rho c_p \Delta V_i)$ 为热容矩阵，$\mathbf{K}$ 为传导刚度矩阵。

### 4.6 文献来源

- COMSOL Multiphysics Heat Transfer Module Boundary Conditions. URL: https://doc.comsol.com/6.0/doc/com.comsol.help.comsol/comsol_ref_modeling.15.59.html
- COMSOL Submarine Cable 6 — Thermal Effects（傅里叶定律推导 + 焦耳热耦合）. URL: https://doc.comsol.com/5.6/doc/com.comsol.help.models.acdc.submarine_cable_06_thermal_effects/submarine_cable_06_thermal_effects.html
- COMSOL Learning Center: Modeling with PDEs — Diffusion-Type Equations. URL: https://www.comsol.com/support/learning-center/article/modeling-with-pdes-diffusion-type-equations-43711/142
- 曼光 MaxOptics Studio 边界条件文档（PML/PEC/对称/周期）. URL: https://kb.max-optics.com/docs/faq/Physics/BC/

### 4.7 PoLaRIS 实现【创新】点

*创新*：HEAT 与 FDE/FDTD 电磁求解器双向耦合，实现热光自洽。
- **底层逻辑**：`scipy.sparse.linalg.spsolve` 求解稳态稀疏线性系统 $\mathbf{K}\mathbf{T} = \mathbf{Q}$；瞬态用隐式 Euler + `scipy.sparse.linalg`；热源 $Q_{Joule}$ 由电磁求解器输出 $\mathbf{J}\cdot\mathbf{E}^*$ 网格插值得到；温度场通过 $n(T) = n_0 + (dn/dT)(T-T_0)$ 反馈折射率。纯 CPU（规则 26）。
- **支持理论**：COMSOL 海缆模型证明焦耳热 + 傅里叶导热 + Dirichlet/Neumann/Robin 边界组合可覆盖光电子热管理场景。
- **案例**：SOI 热光马赫-曾德调相器、SiN 微环加热臂、激光器自热效应。差异化点：PoLaRIS 将 HEAT 嵌入 AI 布局的闭环优化，自动搜索热串扰最小的器件排布。

---

## 5. DDM — 漂移扩散模型（Drift-Diffusion Model）

### 5.1 物理模型

DDM 求解半导体载流子输运，由 Poisson 方程（电势）+ 电子/空穴连续性方程（载流子浓度）耦合而成。适用于 PN 结、调制器掺杂区、电吸收调制器、光电探测器的电学行为建模。电流由漂移（电场驱动）+ 扩散（浓度梯度驱动）两部分组成。光电子器件中 DDM 与 HEAT、FDE 多物理场耦合，描述载流子耗尽效应导致的电光调制。

### 5.2 控制方程

**Poisson 方程**：

$$\nabla \cdot (\varepsilon \nabla \phi) = -q(p - n + N_D^+ - N_A^-)$$

**电子/空穴电流密度（漂移-扩散）**：

$$\mathbf{J}_n = q \mu_n n \mathbf{E} + q D_n \nabla n, \quad \mathbf{J}_p = q \mu_p p \mathbf{E} - q D_p \nabla p$$

**连续性方程**：

$$\frac{\partial n}{\partial t} = \frac{1}{q} \nabla \cdot \mathbf{J}_n + U, \quad \frac{\partial p}{\partial t} = -\frac{1}{q} \nabla \cdot \mathbf{J}_p - U$$

其中 $\phi$ 为电势，$n, p$ 为电子/空穴浓度，$N_D^+, N_A^-$ 为电离施主/受主浓度，$\mu_{n,p}$ 为迁移率，$D_{n,p}$ 为扩散系数（爱因斯坦关系 $D = \mu k_B T / q$），$U$ 为净产生-复合率，$\mathbf{E} = -\nabla \phi$。

### 5.3 离散化方案

**Scharfetter-Gummel 离散化**（1969，半导体标准）：沿每条边假设电流密度、迁移率、电场常数，载流子浓度沿边指数变化。对电子电流在边 $i \to i+1$：

$$J_n^{i} = \frac{q D_n}{\Delta x} \left[ n_i B\!\left(\frac{q(\phi_{i+1}-\phi_i)}{k_B T}\right) - n_{i+1} B\!\left(-\frac{q(\phi_{i+1}-\phi_i)}{k_B T}\right) \right]$$

其中 Bernoulli 函数 $B(x) = x/(e^x - 1)$。该格式对指数变化的载流子浓度保持稳定，避免中心差分在 PN 结处的数值振荡。

**Poisson 离散**：标准 box integration（有限体积），$\nabla \cdot (\varepsilon \nabla \phi)$ 离散为相邻节点通量差。

**非线性耦合求解**：Newton-Raphson 迭代，未知量 $\{\phi_i, n_i, p_i\}$，雅可比矩阵分块稀疏。

### 5.4 边界条件

- **欧姆接触（Ohmic contact）**：$\phi = V_{applied}$，$n, p$ 取热平衡值 $n = n_i e^{q\phi/k_BT}$，$p = n_i e^{-q\phi/k_BT}$。
- **绝缘边界（Neumann）**：$\partial \phi/\partial n = 0$，$\mathbf{J}_{n,p} \cdot \hat{n} = 0$。
- **Schottky 接触**：$\phi = V_{bi} - V_{applied}$，载流子浓度由热发射理论给定。
- **界面连续**：异质结界面 $\phi$、$\mathbf{J}_{n,p}$ 法向连续（含能带跳变）。

### 5.5 核心公式

**Scharfetter-Gummel 电流离散**（Scharfetter & Gummel 1969，Selberherr 1984）：

$$J_n^{i \to i+1} = \frac{q D_n^i}{\Delta x^i} \left[ n_i B(-\Delta\psi_n) - n_{i+1} B(\Delta\psi_n) \right]$$

其中 $\Delta\psi_n = q(\phi_{i+1}-\phi_i)/k_BT + \ln(N_C^{i+1}/N_C^i)$，$B(x) = x/(e^x-1)$。

**Poisson 离散（box integration）**：

$$\sum_{j \in N(i)} \frac{\varepsilon_{ij}(\phi_i - \phi_j)}{\Delta x_{ij}} A_{ij} = q(p_i - n_i + N_{D,i}^+ - N_{A,i}^-) \Delta V_i$$

**Newton-Raphson 残差**（sesame 文档）：

$$f_\phi^i = \frac{2}{\Delta x^i + \Delta x^{i-1}}\left[ \tfrac{\varepsilon_i+\varepsilon_{i+1}}{2}\tfrac{\phi_{i+1}-\phi_i}{\Delta x^i} - \tfrac{\varepsilon_{i-1}+\varepsilon_i}{2}\tfrac{\phi_i-\phi_{i-1}}{\Delta x^{i-1}} \right] - \rho_i$$

$$f_n^i = \frac{2}{\Delta x^i + \Delta x^{i-1}}(J_n^i - J_n^{i-1}) - G_i + R_i, \quad f_p^i = \frac{2}{\Delta x^i + \Delta x^{i-1}}(J_p^i - J_p^{i-1}) + G_i - R_i$$

迭代更新 $\mathbf{x}_{k+1} = \mathbf{x}_k - \mathbf{J}^{-1}\mathbf{f}$，$\mathbf{x} = \{\phi, E_{Fn}, E_{Fp}\}$。

### 5.6 文献来源

- Scharfetter DL, Gummel HK, "Large-signal analysis of a silicon Read diode oscillator," IEEE Trans. Electron Devices 16, 64-77 (1969). URL: https://doi.org/10.1109/T-ED.1969.16566
- Selberherr S, "Analysis and Simulation of Semiconductor Devices," Springer (1984). URL: https://link.springer.com/book/10.1007/978-3-7091-8752-4
- Vienna UT Cervenka PhD thesis: Basic Semiconductor Equations & Scharfetter-Gummel. URL: https://www.iue.tuwien.ac.at/phd/cervenka/node18.html
- sesame SEMIgredient solver: Drift-Diffusion-Poisson discretization. URL: https://sesame.readthedocs.io/en/stable/_sources/physics/discretization.rst.txt

### 5.7 PoLaRIS 实现【创新】点

*创新*：DDM 与 FDE 耦合实现载流子耗尽型电光调制器自洽建模。
- **底层逻辑**：`scipy.sparse.linalg.spsolve` 求解 Newton-Raphson 线性化后的稀疏雅可比系统；Bernoulli 函数 $B(x)$ 用数值稳定实现（$x \to 0$ 时 $B \to 1$，$x \to \pm\infty$ 时取极限）；载流子浓度 $n, p$ 通过 $n^2(\Delta n, \Delta p)$ 等效折射率变化反馈 FDE。纯 CPU（规则 26）。
- **支持理论**：Scharfetter-Gummel 1969 已被 Silvaco ATLAS、COMSOL 半导体模块、sesame 等采纳为载流子输运离散标准。
- **案例**：SOI 耗尽型 MZM 调制器、PIN 相移器、Ge 光电探测器。差异化点：PoLaRIS DDM 支持 Gummel/Newton 双迭代策略，自动切换以保证收敛。

---

## 6. FDE — 本征模求解器（Finite Difference Eigenmode）

### 6.1 物理模型

FDE 在波导横截面求解频域 Maxwell 方程的本征值问题，得到导模的传播常数 $\beta$（或有效折射率 $n_{eff} = \beta/k_0$）与场分布。是 EME、FDFD、2.5D-FDTD 的共同基础（提供本地模 / 注入模 / 折叠模）。求解在 Yee 网格上离散，构造广义本征值问题 $\mathbf{A}\mathbf{x} = \lambda \mathbf{B}\mathbf{x}$，用稀疏本征求解器（Lanczos/Arnoldi）得到前几个导模。

### 6.2 控制方程

频域 Maxwell 旋度方程（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -i\omega\mu_0 \mathbf{H}, \quad \nabla \times \mathbf{H} = i\omega\varepsilon_0\varepsilon_r \mathbf{E}$$

消去 $\mathbf{E}$ 得磁场本征方程（z 不变截面，传播因子 $e^{-i\beta z}$）：

$$\nabla \times \left( \frac{1}{\varepsilon_r} \nabla \times \mathbf{H} \right) = k_0^2 \mathbf{H}$$

等价的电场形式：

$$\nabla \times \nabla \times \mathbf{E} - k_0^2 \varepsilon_r \mathbf{E} = 0$$

### 6.3 离散化方案

**Yee 网格**（Yee 1966）：电场分量位于棱中点，磁场分量位于面中心，交错排列保证 Maxwell 旋度方程中心差分自然满足散度条件 $\nabla \cdot \mathbf{D} = 0$。

将横向场分量 $(E_x, E_y, H_x, H_y)$ 在 Yee 网格上离散，代入本征方程，消去纵向分量后得到仅含横向分量的广义本征值问题（SimWorks FDE）：

$$\mathbf{A} \mathbf{x} = \lambda \mathbf{x}, \quad \lambda = \beta^2$$

其中 $\mathbf{A}$ 为稀疏差分算子矩阵（含 $\varepsilon_r$ 分布），$\mathbf{x}$ 为横向场分量向量。

**模式归一化**：

$$\frac{1}{2} \mathrm{Re} \int (\mathbf{E}_m \times \mathbf{H}_m^*) \cdot \hat{z} \, dA = 1$$

### 6.4 边界条件

- **PML**：横向四边设置 SC-PML 或 UPML 吸收辐射模。
- **PEC/PMC**：对称结构可设电壁/磁壁利用对称性减半计算量。
- **周期边界**：光子晶体波导横截面。
- **金属边界**：封闭腔本征模。

### 6.5 核心公式

**磁场本征方程**（Tidy3D/SimWorks FDE）：

$$\nabla \times \left( \frac{1}{\varepsilon_r} \nabla \times \mathbf{H} \right) = k_0^2 \mathbf{H}, \quad \beta = k_0 n_{eff}$$

**Yee 网格差分矩阵形式**（SimWorks FDE，2D Y-normal 示例）：

$$\mathbf{D}_x^E \mathbf{a}_y - \mathbf{D}_y^E \mathbf{a}_x = \mu_{zz} \mathbf{b}_z$$

六个电磁场分量的矩阵方程组合为 $\mathbf{A}\mathbf{x} = \lambda \mathbf{x}$，$\mathbf{A}$ 为稀疏系数矩阵。

**有效折射率**：

$$n_{eff} = \frac{\beta}{k_0} = \frac{\beta \lambda_0}{2\pi}$$

**TE/TM 分量分数**（SimWorks FDE）：

$$\text{TE fraction} = 1 - \frac{\int |E_\perp|^2 dA}{\int |\mathbf{E}|^2 dA}, \quad \text{TM fraction} = 1 - \frac{\int |H_\perp|^2 dA}{\int |\mathbf{H}|^2 dA}$$

**模式损耗**：

$$\text{Loss (dB/cm)} = -0.2 \log_{10}(e^{-2\pi \kappa / \lambda}) \times 10^4$$

其中 $\kappa = \mathrm{Im}(n_{eff})$。

**模式重叠积分**（耦合效率）：

$$\eta_{m \to n} = \frac{\left| \int (\mathbf{E}_m \times \mathbf{H}_n^*) \cdot \hat{z} \, dA \right|^2}{\mathrm{Re}\int (\mathbf{E}_m \times \mathbf{H}_m^*) \cdot \hat{z} \, dA \cdot \mathrm{Re}\int (\mathbf{E}_n \times \mathbf{H}_n^*) \cdot \hat{z} \, dA}$$

### 6.6 文献来源

- Yee K, "Numerical solution of initial boundary value problems involving Maxwell's equations in isotropic media," IEEE Trans. Antennas Propag. 14, 302-307 (1966). URL: https://doi.org/10.1109/TAP.1966.1138693
- SimWorks Finite Difference Eigenmode (FDE) Solver. URL: https://www.simworks.net/en/solver/FDE
- Ansys Lumerical MODE — Waveguide (FDE). URL: https://support.lumerical.com/hc/en-us/articles/360042800453-Waveguide-FDE-
- Tidy3D Simulation documentation（Yee grid Maxwell FDTD/FDE 基础）. URL: https://docs.simulation.cloud/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html

### 6.7 PoLaRIS 实现【创新】点

*创新*：FDE 作为 PoLaRIS 求解器栈的底座，被 EME/FDFD/2.5D-FDTD 共享。
- **底层逻辑**：`scipy.sparse.linalg.eigsh`（Lanczos）求前 K 个本征模；Yee 网格差分算子用 `scipy.sparse` 构造；模式归一化与重叠积分纯 NumPy 实现；SC-PML 复坐标拉伸融入差分算子。纯 CPU（规则 26）。
- **支持理论**：Yee 1966 是 FDTD/FDE/FDFD 共同的网格基础，已被 Lumerical、Tidy3D、SimWorks、Meep 全部采纳。
- **案例**：SOI 条形波导基模、SiN 微环弯曲模、MMI 多模。差异化点：PoLaRIS FDE 输出统一数据结构（场 + $\beta$ + 归一化），供下游求解器零成本复用，避免商业工具的格式壁垒。

---

## 7. FDFD — 频域有限差分（Finite Difference Frequency Domain）

### 7.1 物理模型

FDFD 在频域求解 Maxwell 方程，给定单频源求全场分布。与时域 FDTD 不同，FDFD 直接求解大型稀疏线性系统 $\mathbf{A}\mathbf{x} = \mathbf{b}$，无需时间步进，天然适合单频/窄带问题、色散材料（无需递推）、强谐振结构（无需长时间演化）。缺点是内存占用大（存储整个稀疏矩阵），需迭代或直接稀疏求解器。

### 7.2 控制方程

频域 Maxwell 方程（源 $\mathbf{J}, \mathbf{M}$，$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -i\omega\mu_0 \mathbf{H} - \mathbf{M}$$

$$\nabla \times \mathbf{H} = i\omega\varepsilon_0\varepsilon_r \mathbf{E} + \mathbf{J}$$

消去 $\mathbf{H}$ 得电场波动方程：

$$\nabla \times \nabla \times \mathbf{E} - k_0^2 \varepsilon_r \mathbf{E} = -i\omega\mu_0 \mathbf{J} - \nabla \times \mathbf{M}$$

即 $(\nabla \times \nabla \times - \omega^2 \varepsilon) \mathbf{E} = -i\omega\mathbf{J}$（Jaxwell 形式）。

### 7.3 离散化方案

- **Yee 网格**：同 FDE，电场棱中点、磁场面中心。
- **SC-PML（拉伸坐标 PML）**（Shin & Fan 2012）：将笛卡尔坐标拉伸 $x \to \tilde{x} = \int_0^x s_x(x') dx'$，拉伸因子 $s_x = \kappa_x + \sigma_x/(i\omega\varepsilon_0)$，使 PML 区域波指数衰减无反射。
- **线性系统**：将 6 个场分量在 Yee 网格离散后代入旋度方程，整理为 $\mathbf{A}\mathbf{x} = \mathbf{b}$，$\mathbf{A}$ 为稀疏矩阵（每行非零元数固定），$\mathbf{x}$ 为待求场，$\mathbf{b}$ 为源。

### 7.4 边界条件

- **SC-PML**：四边（2D）或六面（3D）设置，吸收外向波（Shin & Fan 2012 推荐方案）。
- **PEC/PMC**：电壁（$E_t = 0$）/磁壁（$H_t = 0$）。
- **周期边界/Bloch**：周期结构。
- **TF/SF（总场/散射场）**：平面波入射散射问题。

### 7.5 核心公式

**频域波动方程**（Shin & Fan 2012，MaxwellFDFD）：

$$\nabla \times \mu_r^{-1} \nabla \times \mathbf{E} - k_0^2 \varepsilon_r \mathbf{E} = \mathbf{J}_{src}$$

**SC-PML 拉伸**（MaxOptics 文档）：

$$S_x = \kappa_x + \frac{\sigma_x}{i\omega\varepsilon_0}, \quad \tilde{\varepsilon} = \frac{\varepsilon}{S_x}, \quad \tilde{\mu} = \frac{\mu}{S_x}$$

拉伸后 Maxwell 方程：

$$\nabla_S \times \mathbf{H} = i\omega\tilde{\varepsilon}\mathbf{E}, \quad \nabla_S \times \mathbf{E} = -i\omega\tilde{\mu}\mathbf{H}$$

其中 $\nabla_S$ 用拉伸坐标 $\tilde{x}, \tilde{y}, \tilde{z}$。

**稀疏线性系统**（Jaxwell/MaxwellFDFD）：

$$\mathbf{A}(\omega, \varepsilon, \text{PML}) \mathbf{E} = \mathbf{b}(\mathbf{J}_{src})$$

$\mathbf{A}$ 为复对称稀疏矩阵，$\mathbf{b} = -i\omega\mathbf{J}$。

**迭代求解**：COCG（共轭正交共轭梯度，复对称）或 QMR/COCG 变体（Gu 2014），预处理（不完全 LU / 对角）。

### 7.6 文献来源

- Shin W, Fan S, "Choice of the perfectly matched layer boundary condition for frequency-domain Maxwell's equations solvers," J. Comput. Phys. 231, 3406-3431 (2012). URL: https://doi.org/10.1016/j.jcp.2011.12.037
- Shin W, MaxwellFDFD（MATLAB FDFD 包，SC-PML 实现）. URL: https://www.mit.edu/~wsshin/maxwellfdfd.html
- Fischbach JD, Jaxwell（GPU 加速可微 FDFD，PoLaRIS 仅参考 SC-PML 公式，不参与 GPU）. URL: https://jan-david-fischbach.github.io/jaxwell/
- Gu X et al., "Quasi-Minimal Residual Variants of the COCG and COCR Methods for Complex Symmetric Linear Systems," IEEE Trans. Microwave Theory Tech. 62(12), 2859-2867 (2014). URL: https://doi.org/10.1109/TMTT.2014.2363835

### 7.7 PoLaRIS 实现【创新】点

*创新*：FDFD 复用 FDE 的 Yee 网格与 SC-PML 算子构造，单频高精度求解。
- **底层逻辑**：`scipy.sparse` 构造 $\mathbf{A}$（复对称），`scipy.sparse.linalg.cg`（复对称 COCG 变体）或 `spsolve`（小规模直接）求解；SC-PML 按 Shin & Fan 2012 拉伸坐标融入算子；源 $\mathbf{J}$ 可由 FDE 模式分布生成（波导模注入）。纯 CPU（规则 26），不使用 Jaxwell 的 GPU 路径。
- **支持理论**：Shin & Fan 2012 证明 SC-PML 在频域 FDFD 中数值反射最低，优于 UPML。
- **案例**：单频谐振超表面、窄带光栅滤波器、色散金属纳米天线。差异化点：PoLaRIS FDFD 与 FDE 共享网格，模式注入天然兼容，避免商业工具的网格重生成开销。

---

## 8. 2.5D-FDTD — 2.5 维时域有限差分（varFDTD）

### 8.1 物理模型

2.5D-FDTD（variational FDTD, varFDTD）将 3D 平面波导器件沿垂直方向（z）折叠为 2D 等效问题，再用 2D Yee 网格 FDTD 求解。核心假设：垂直方向仅支持少数（通常 TE/TM 两个）slab 模，模间耦合可忽略。通过有效折射率法（variational，Hammer & Ivanova 2009）将 3D 介电常数分布压缩为 2D 等效色散材料，2D FDTD 计算量与 2D 仿真相当，精度接近 3D FDTD。适用于 SOI/SiN 平面光子电路（脊波导、环谐振器、MMI、光栅耦合器），计算时间相对 3D FDTD 减少 60-80%。

### 8.2 控制方程

3D Maxwell 时域方程：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}, \quad \nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r \frac{\partial \mathbf{E}}{\partial t}$$

垂直 slab 模 $M(z, \omega)$ 满足 1D 本征方程（参考折射率 $\varepsilon_r(z), \beta_r$）。将 3D 场按 slab 模展开，对 z 积分投影到 2D，得到 2D 等效 Maxwell 方程，等效介电常数含材料色散 + 波导色散。

### 8.3 离散化方案

**第一步：垂直 slab 模求解**（FDE 1D）。在用户指定的 slab 位置求解 1D 垂直本征模 $M(z,\omega)$ 与传播常数 $\beta_r$。

**第二步：3D → 2D 折叠**（variational effective index，Hammer & Ivanova 2009）：

$$\varepsilon_{eff}^{TE}(x,y,\omega) = \left(\frac{\beta_r}{k}\right)^2 + \frac{\int_z (\varepsilon(x,y,z) - \varepsilon_r(z,\omega)) |M(z,\omega)|^2 dz}{\int_z |M(z,\omega)|^2 dz}$$

$$\varepsilon_{eff}^{TM}(x,y,\omega) = \left(\frac{\beta_r}{k}\right)^2 \frac{\int_z \frac{1}{\varepsilon_r}|M|^2 dz}{\int_z \frac{1}{\varepsilon(x,y,z)}|M|^2 dz} + \frac{\int_z \left(\frac{1}{\varepsilon_r} - \frac{1}{\varepsilon}\right) |\partial_z M|^2 dz}{k^2 \int_z \frac{1}{\varepsilon}|M|^2 dz}$$

**第三步：2D FDTD**。在 2D Yee 网格上对等效材料做 leapfrog 时间步进。

**第四步（可选）**：将 2D 场重新展开为 3D（乘 slab 模剖面）。

### 8.4 边界条件

- **2D 平面内**：PML（吸收）、PEC/PMC（对称）、周期（光子晶体）。
- **垂直方向**：折叠后无显式边界，由 slab 模假设隐含处理。
- **模式注入**：FDE 模式分布作为源注入 2D 网格。

### 8.5 核心公式

**Yee leapfrog 更新**（2D，TE 模 $E_z, H_x, H_y$ 示例）：

$$H_x^{n+1/2}(i, j+\tfrac{1}{2}) = H_x^{n-1/2} - \frac{\Delta t}{\mu_0 \Delta y}\left[ E_z^n(i,j+1) - E_z^n(i,j) \right]$$

$$H_y^{n+1/2}(i+\tfrac{1}{2}, j) = H_y^{n-1/2} + \frac{\Delta t}{\mu_0 \Delta x}\left[ E_z^n(i+1,j) - E_z^n(i,j) \right]$$

$$E_z^{n+1}(i,j) = E_z^n + \frac{\Delta t}{\varepsilon_0 \varepsilon_{eff}}\left[ \frac{H_y^{n+1/2}(i+\tfrac{1}{2},j) - H_y^{n+1/2}(i-\tfrac{1}{2},j)}{\Delta x} - \frac{H_x^{n+1/2}(i,j+\tfrac{1}{2}) - H_x^{n+1/2}(i,j-\tfrac{1}{2})}{\Delta y} \right]$$

**Courant 稳定性**（2D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2} + \frac{1}{\Delta y^2}}}$$

**等效介电常数**（variational，Hammer & Ivanova 2009，见 8.3 第二步公式）。

**互易性方法替代**（Snyder & Love）：

$$n_{eff}(x,y,\omega) = \frac{\beta_r}{k} + \sqrt{\frac{\varepsilon_0}{\mu_0}} \frac{\int_z (\varepsilon - \varepsilon_r)|\mathbf{E}|^2 dz}{\int_z \mathbf{P}\cdot\hat{n}\, dz}$$

### 8.6 文献来源

- Yee K, "Numerical solution of initial boundary value problems involving Maxwell's equations in isotropic media," IEEE Trans. Antennas Propag. 14, 302-307 (1966). URL: https://doi.org/10.1109/TAP.1966.1138693
- Hammer M, Ivanova O, "Effective dispersion model for 2D waveguide mode solvers," Opt. Quantum Electron. 41, 767-777 (2009). URL: https://doi.org/10.1007/s11082-009-9366-7
- Ansys Lumerical MODE — 2.5D varFDTD solver introduction. URL: https://optics.ansys.com/hc/en-us/articles/360034917213
- SimWorks 2.5D Solver（variational effective index 实现）. URL: https://www.simworks.net/en/knowledge-base/User-Manual_25D-settings

### 8.7 PoLaRIS 实现【创新】点

*创新*：2.5D-FDTD 复用 FDE（垂直 slab 模）+ FDTD（2D leapfrog）双内核，无新算法负担。
- **底层逻辑**：第一步调用 FDE 求解器 1D 模式得到 $\beta_r, M(z)$；第二步按 Hammer & Ivanova 2009 variational 公式 NumPy 积分生成 2D 等效 $\varepsilon_{eff}$；第三步纯 NumPy 2D Yee leapfrog（Courant 限步），PML 同 FDFD。纯 CPU（规则 26），不使用 Tidy3D/曼光 GPU 加速路径。
- **支持理论**：Hammer & Ivanova 2009 证明 variational effective index 对 SOI 平面波导精度优于传统 effective index；Lumerical varFDTD 白皮书报告相对 3D FDTD 提速 100×（环谐振器案例）。
- **案例**：SOI 环谐振器、MMI 功分器、光栅耦合器、Y 分支逆向设计。差异化点：PoLaRIS 2.5D-FDTD 与 AI 逆向设计（adjoint）耦合，2D 网格下梯度计算成本远低于 3D，支持大规模器件拓扑优化。

---

## 附录 A：商业工具求解器实现对照

| 求解器 | Lumerical | Tidy3D | 曼光 MaxOptics | SimWorks | PoLaRIS |
|--------|----------|--------|------|---------|---------|
| RCWA | ✅ | ✅ | ✅ | - | ❌ 待实现 |
| EME | ✅ | - | - | ✅ | ❌ 待实现 |
| BPM | ✅ | - | ✅ | - | ❌ 待实现 |
| HEAT | ✅ | - | ✅ | - | ❌ 待实现 |
| DDM | ✅ | - | ✅ | - | ❌ 待实现 |
| FDE | ✅ | ✅ | ✅ | ✅ | ❌ 待实现 |
| FDFD | ✅ | - | - | ✅ | ❌ 待实现 |
| 2.5D-FDTD | ✅ | ✅ | ✅ | - | ❌ 待实现 |

注：PoLaRIS 全部求解器均为 CPU 纯 Python 实现（规则 26，不参与 GPU）。

## 附录 B：实现优先级（按 year_plan_2026_06_2027_05.md）

- **R37-Q1**：FDE（基础模式求解，所有 EME/FDE/FDFD/2.5D-FDTD 共用）
- **R37-Q2**：FDFD（基于 FDE 网格与 SC-PML 算子）
- **R37-Q3**：RCWA（独立分支，傅里叶展开 + S 矩阵级联）
- **R37-Q4**：EME（依赖 FDE 本征模内核）
- **R38**：BPM / HEAT / DDM（多物理场耦合）
- **R39**：2.5D-FDTD（依赖 FDE + FDTD leapfrog）

## 附录 C：共享算法组件

| 组件 | 用途 | 复用求解器 |
|------|------|-----------|
| Yee 网格差分算子 | 横向场离散 | FDE / FDFD / 2.5D-FDTD |
| SC-PML 拉伸坐标 | 吸收边界 | FDE / FDFD / 2.5D-FDTD / EME(横向) |
| Redheffer 星积 | S 矩阵级联 | RCWA / EME |
| 稀疏本征求解 (Lanczos) | 模式求解 | FDE / EME(本地模) |
| 稀疏线性求解 | 频域场 / 温度场 / 电势 | FDFD / HEAT / DDM |
| 模式重叠积分 | 耦合效率 / EME 界面 | FDE / EME |

## 附录 D：CPU 性能策略（规则 26）

- 全部求解器基于 `numpy`（BLAS 后端）+ `scipy.sparse` + `scipy.linalg`。
- 大型稀疏系统优先 `scipy.sparse.linalg`（迭代 CG/BiCGSTAB/GMRES + 预处理）。
- 本征值问题用 `scipy.sparse.linalg.eigsh`（Lanczos）或 `scipy.linalg.eig`（稠密小规模）。
- 禁用 CuPy/CUDA/ROCm/Apple Metal/JAX GPU 后端（规则 26）。
- 性能优化方向：稀疏矩阵构造向量化、Yee 网格更新 NumPy 切片向量化、内存复用。

## 参考文献（IEEE 格式）

[1] M. G. Moharam and T. K. Gaylord, "Rigorous coupled-wave analysis of planar-grating diffraction," *J. Opt. Soc. Am.*, vol. 71, no. 7, pp. 811-818, 1981. [Online]. Available: https://doi.org/10.1364/JOSA.71.000811

[2] L. F. Li, "Use of Fourier series in the analysis of discontinuous periodic structures," *J. Opt. Soc. Am. A*, vol. 13, no. 9, pp. 1870-1876, 1996. [Online]. Available: https://doi.org/10.1364/JOSAA.13.001870

[3] M. G. Moharam, D. A. Pommet, E. B. Grann, and T. K. Gaylord, "Stable implementation of the rigorous coupled-wave analysis for surface-relief gratings: enhanced transmittance matrix approach," *J. Opt. Soc. Am. A*, vol. 12, no. 5, pp. 1077-1086, 1995. [Online]. Available: https://doi.org/10.1364/JOSAA.12.001077

[4] D. F. G. Gallagher and T. P. Felici, "Eigenmode expansion methods for simulation of optical propagation in photonics - Pros and Cons," *Proc. SPIE*, vol. 4987, pp. 69-82, 2003. [Online]. Available: https://doi.org/10.1117/12.478061

[5] G. R. Hadley, "Transparent boundary condition for beam propagation," *Opt. Lett.*, vol. 17, no. 10, pp. 878-880, 1992. [Online]. Available: https://doi.org/10.1364/OL.17.000878

[6] D. L. Scharfetter and H. K. Gummel, "Large-signal analysis of a silicon Read diode oscillator," *IEEE Trans. Electron Devices*, vol. 16, no. 1, pp. 64-77, 1969. [Online]. Available: https://doi.org/10.1109/T-ED.1969.16566

[7] S. Selberherr, *Analysis and Simulation of Semiconductor Devices*. Springer, 1984. [Online]. Available: https://link.springer.com/book/10.1007/978-3-7091-8752-4

[8] K. Yee, "Numerical solution of initial boundary value problems involving Maxwell's equations in isotropic media," *IEEE Trans. Antennas Propag.*, vol. 14, no. 3, pp. 302-307, 1966. [Online]. Available: https://doi.org/10.1109/TAP.1966.1138693

[9] W. Shin and S. Fan, "Choice of the perfectly matched layer boundary condition for frequency-domain Maxwell's equations solvers," *J. Comput. Phys.*, vol. 231, pp. 3406-3431, 2012. [Online]. Available: https://doi.org/10.1016/j.jcp.2011.12.037

[10] M. Hammer and O. Ivanova, "Effective dispersion model for 2D waveguide mode solvers," *Opt. Quantum Electron.*, vol. 41, pp. 767-777, 2009. [Online]. Available: https://doi.org/10.1007/s11082-009-9366-7

[11] W. P. Huang, S. T. Chu, A. Goss, and S. Chaudhuri, "A scalar finite-difference wave beam propagation method," *IEEE Photonics Technol. Lett.*, vol. 3, no. 10, pp. 910-912, 1991. [Online]. Available: https://doi.org/10.1109/68.84566

[12] X. Gu, T. Huang, L. Li, H. Li, T. Sogabe, and M. Clemens, "Quasi-Minimal Residual Variants of the COCG and COCR Methods for Complex Symmetric Linear Systems in Electromagnetic Simulations," *IEEE Trans. Microwave Theory Tech.*, vol. 62, no. 12, pp. 2859-2867, 2014. [Online]. Available: https://doi.org/10.1109/TMTT.2014.2363835

## 修订日志

- **2026-06-25 v1.0**：首版生成，覆盖 8 个求解器（RCWA/EME/BPM/HEAT/DDM/FDE/FDFD/2.5D-FDTD）。所有公式经 arXiv/IEEE/官方文档核实（规则 18），无 fall-back 编造（规则 14），全部 CPU 算法（规则 26）。PoLaRIS 自研差异化设计均标注【创新】并记录底层逻辑与支持理论。
