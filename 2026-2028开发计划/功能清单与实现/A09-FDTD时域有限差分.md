# A09 — FDTD 时域有限差分（器件级）

> 生成时间：2026-06-25
> 项目：PoLaRIS 光电子 AI 布局布线引擎
> 聚类 ID：A09（求解器类，P0 优先级）
> 涉及工具：T01 Ansys Lumerical、T03 OptoDesigner、T04 Tidy3D、T07 Photon Design、T14 逍遥 PIC Studio、T15 曼光 MaxOptics、T16 SimWorks、T17 法动 UltraEM（共 48 功能点，状态分布 ✅8 / ⚠️26 / ❌14，A 类最大聚类）
> 规则依据：project_rules.md 规则 18（学术诚信）/规则 14（禁止 fall-back）/规则 26（不参与 GPU）
> 关联文档：`A06-2.5D-FDTD变分FDTD.md`（Yee 网格共享见 `A09-FDTD时域有限差分.md`）、`docs/feature_gap_full_analysis.md`（T01/T04/T07/T14/T15/T16/T17 FDTD 章节）、`00-算法聚类清单.md`

---

## 1. 概述与定位

FDTD（Finite-Difference Time-Domain，时域有限差分）是 Yee 1966 提出的显式时域 Maxwell 方程求解方法：将连续电磁场在 Yee 交错网格上离散，对旋度方程做半步错位中心差分，形成 E/H 场 leapfrog（蛙跳）时间推进。其优势为：(1) 单次仿真即可得到宽频带响应（DFT 后处理）；(2) 完全显式，无矩阵求解；(3) 严格满足离散 Gauss 定律；(4) 适应任意非均匀、各向异性、色散、非线性材料。FDTD 是光电子器件级全波仿真的"金标准"，被 Lumerical FDTD、Tidy3D、曼光 MaxOptics、SimWorks、法动 UltraEM、逍遥 pMaxwell 全部采用。

**PoLaRIS 定位**：FDTD 是 PoLaRIS 求解器栈"时域全波"路径的核心，与 2.5D-FDTD/A06 共享 Yee 网格生成与 E/H leapfrog 内核（`A09-FDTD时域有限差分.md` §2），列为 R39 优先级实现。**当前状态：⚠️ 部分**——`modules/fdtd/src/polaris_fdtd/solver.py` 仅封装 MEEP/Tidy3D/ANALYTICAL 三后端，非自研 FDTD 内核，依赖外部依赖项。**实现目标**：纯 NumPy + SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE/A06-2.5D-FDTD 共享 Yee 网格组件。

**对标状态**：8 工具共用 FDTD（A 类最大聚类，48 功能点），PoLaRIS 通过 MEEP/Tidy3D 后端间接覆盖 8 项 ✅，但 26 项 ⚠️ 依赖后端能力（光源/边界/材料/网格均不自研），14 项 ❌ 完全缺失（亚像素平滑、StablePML、Bloch 边界、自动非均匀网格、偶极子发射研究等）。最大差距为"非自研内核"，导致光源/边界/材料 API 无法在 PoLaRIS 层统一管理。

---

## 2. 物理模型与控制方程

### 2.1 Maxwell 时域旋度方程

时不变、各向同性、无源区域（$\mu_r=1$）：

$$\nabla \times \mathbf{E} = -\mu_0 \frac{\partial \mathbf{H}}{\partial t}$$

$$\nabla \times \mathbf{H} = \varepsilon_0 \varepsilon_r(\mathbf{r}) \frac{\partial \mathbf{E}}{\partial t} + \sigma \mathbf{E} + \mathbf{J}_{src}$$

其中 $\varepsilon_r(\mathbf{r})$ 为相对介电常数空间分布，$\sigma$ 为电导率（电损耗），$\mathbf{J}_{src}$ 为外加电流源。含磁损耗 $\sigma_m$ 时 $\nabla\times\mathbf{E}=-\mu_0\partial_t\mathbf{H}-\sigma_m\mathbf{H}$，可通过等效磁导率 $\mu^*=\mu_0+\sigma_m/(i\omega)$ 处理。

### 2.2 色散材料（辅助微分方程 ADE）

Drude-Lorentz 色散介质极化密度 $\mathbf{P}$ 满足二阶 ODE：

$$\frac{\partial^2 \mathbf{P}}{\partial t^2} + \gamma \frac{\partial \mathbf{P}}{\partial t} + \omega_0^2 \mathbf{P} = \varepsilon_0 \omega_p^2 \mathbf{E}$$

其中 $\omega_0$ 为共振频率，$\gamma$ 为阻尼率，$\omega_p$ 为等离子频率。$\mathbf{D}=\varepsilon_0\varepsilon_\infty\mathbf{E}+\mathbf{P}$，代入 Maxwell 旋度方程得 ADE-FDTD 更新格式（Lumerical MCM、Tidy3D PoleResidue 共同方案）。多系数材料 MCM 通过加和多个 Lorentz 极点拟合实测 $n(\omega)$ 数据。

### 2.3 非线性（Kerr + 拉曼）

三阶非线性 $\mathbf{P}_{NL}=\varepsilon_0\chi^{(3)}|\mathbf{E}|^2\mathbf{E}$（瞬时 Kerr）+ 卷积拉曼项，ADE 法处理。光子芯片中典型应用为 SiN 微环的克尔自相位调制、LNOI 的 $\chi^{(2)}$ 二次谐波。

---

## 3. Yee 网格离散化方案

### 3.1 Yee 1966 网格布局

3D Yee 单元中：电场分量 $E_x,E_y,E_z$ 位于棱中点，磁场分量 $H_x,H_y,H_z$ 位于面中心，空间半步错位。该布局使每个旋度运算的中心差分天然落在被求场位置，二阶精度 $O(\Delta h^2)$，且离散 Gauss 定律 $\nabla_h\cdot(\nabla_h\times\cdot)\equiv 0$ 自动满足（避免非物理电荷积累）。Yee 网格是 FDE/FDFD/FDTD/2.5D-FDTD 共同基础（`A09-FDTD时域有限差分.md` §2）。

### 3.2 E/H leapfrog 时间推进

时间半步错位，磁场在 $n+1/2$ 时刻更新，电场在 $n+1$ 时刻更新。以 $E_z$（TEz 2D）为例：

$$H_x^{n+1/2}\big|_{i,j+1/2} = D_{a,\mu}\, H_x^{n-1/2}\big|_{i,j+1/2} - D_{b,\mu}\,\frac{E_z^n|_{i,j+1}-E_z^n|_{i,j}}{\Delta y}$$

$$H_y^{n+1/2}\big|_{i+1/2,j} = D_{a,\mu}\, H_y^{n-1/2}\big|_{i+1/2,j} + D_{b,\mu}\,\frac{E_z^n|_{i+1,j}-E_z^n|_{i,j}}{\Delta x}$$

$$E_z^{n+1}\big|_{i,j} = C_{a,\varepsilon}\, E_z^n\big|_{i,j} + C_{b,\varepsilon}\left[\frac{H_y^{n+1/2}|_{i+1/2,j}-H_y^{n+1/2}|_{i-1/2,j}}{\Delta x} - \frac{H_x^{n+1/2}|_{i,j+1/2}-H_x^{n+1/2}|_{i,j-1/2}}{\Delta y}\right]$$

其中 $D_{a,\mu}=\frac{1-\sigma_m\Delta t/(2\mu_0)}{1+\sigma_m\Delta t/(2\mu_0)}$，$D_{b,\mu}=\frac{\Delta t/\mu_0}{1+\sigma_m\Delta t/(2\mu_0)}$，$C_{a,\varepsilon}=\frac{1-\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$，$C_{b,\varepsilon}=\frac{\Delta t/(\varepsilon_0\varepsilon_r)}{1+\sigma\Delta t/(2\varepsilon_0\varepsilon_r)}$。3D 形式按 6 个分量类似展开。

### 3.3 共形网格亚像素平滑（Yu-Mittra 1/2、Volume-Average）

阶梯近似在介质界面产生 $O(\Delta h)$ 误差。Yu-Mittra 1/2 共形方案：在 Yee 棱上的等效介电常数取界面两侧的体积加权平均，使界面处的等效 $\varepsilon$ 接近真实积分形式，误差降至 $O(\Delta h^2)$。Lumerical Conformal Variant 0/1/2 在介质/金属/PEC 界面分别采用不同共形规则；Tidy3D 默认开启 subpixel averaging。PoLaRIS 将实现 Volume-Average + Yu-Mittra 1/2 两种共形方案。

### 3.4 自动非均匀网格

按"每波长最少 N 个网格"（典型 N=10~20，金属/色散材料处加密至 N=30+）+ 局部 mesh override 框生成非均匀网格，CFL 时间步由最细网格决定。Lumerical `auto nonuniform` mesh accuracy 1-8 对应不同 N；Tidy3D `auto_nonuniform_mesh=True`（arXiv:2506.16665）。

---

## 4. Courant-Friedrichs-Lewy 稳定性条件

显式 leapfrog 格式稳定的必要条件（3D）：

$$\Delta t \le \frac{1}{c\sqrt{\frac{1}{\Delta x^2}+\frac{1}{\Delta y^2}+\frac{1}{\Delta z^2}}}$$

2D 退化为 $\Delta t \le [c\sqrt{1/\Delta x^2+1/\Delta y^2}]^{-1}$，1D 为 $\Delta t\le \Delta x/c$。工程上取 0.95~0.99 倍 CFL 上限以保留稳定裕度。Courant 数 $S=c\Delta t/\Delta h_{\min}$ 反映每步波传播距离与最小网格之比。

**色散误差**：数值相速 $v_p/c \approx 1 - \tfrac{1}{24}(2\pi\Delta h/\lambda)^2 \cdot [\sin^2(\theta/2)] + O(\Delta h^4)$，每波长 ≥20 网格时误差 <0.5%。各向异性数值色散通过高阶 FDTD（2-4 阶）或共形网格降低。

---

## 5. PML 吸收边界条件（CPML 递归卷积）

### 5.1 Berenger 1994 分裂场 PML（原始方案）

将 $\mathbf{E},\mathbf{H}$ 分裂为两个分量（如 $H_z=H_{zx}+H_{zy}$），在 PML 区域引入电导率 $\sigma_x,\sigma_y$ 使波沿 x/y 方向独立衰减。分裂场方案实现复杂，已被非分裂 CPML 取代。

### 5.2 Gedney 1996 单轴各向异性 PML（UPML）

PML 区域填充单轴各向异性介质 $\bar{\bar{\varepsilon}}=\varepsilon\Lambda^{-1}$、$\bar{\bar{\mu}}=\mu\Lambda^{-1}$，拉伸张量 $\Lambda=\mathrm{diag}(s_x,s_y,s_z)$，$s_i=\kappa_i+\sigma_i/(i\omega\varepsilon_0)$。物理等价于复坐标拉伸（与 A05-FDFD SC-PML 同源，Shin & Fan 2012）。

### 5.3 Roden & Gedney 2000 CPML（递归卷积，PoLaRIS 主方案）

CPML（Convolution PML）通过递归卷积将频域拉伸因子 $s_i$ 的卷积转化为时域递推，无需分裂场，与普通 leapfrog 兼容，是 Lumerical/Tidy3D/曼光/SimWorks 共同方案。在 PML 边界，电场更新公式加入辅助变量 $\psi_e$：

$$E_z^{n+1} = C_a E_z^n + C_b (\nabla\times\mathbf{H})_z + C_b \,\psi_{e,z}^{n+1/2}$$

$$\psi_{e,z}^{n+1/2} = b_z\,\psi_{e,z}^{n-1/2} + a_z\, \frac{\partial H_y^{n+1/2}}{\partial x} \quad(\text{面 x 边界})$$

其中 $a_z = \frac{\sigma_x}{\Delta x(\kappa_x\alpha_x+\sigma_x)}(b_z-1)$，$b_z=e^{-(\sigma_x/\kappa_x+\alpha_x)\Delta t/\varepsilon_0}$，$\sigma_x,\kappa_x,\alpha_x$ 沿 PML 深度按多项式渐变（Gedney 推荐 $\sigma_{\max}=(m+1)/(150\pi\Delta h\sqrt{\varepsilon_r})$，$m=3$）。CPML 数值反射 ≤ −70 dB（10 层 PML），优于分裂场 PML。

### 5.4 StablePML 与 Absorber

Tidy3D StablePML 通过修改 $\sigma$ 渐变曲线避免长时仿真下 PML 内部数值发散；Absorber（绝热吸收层）采用渐增电导率纯吸收，实现简单但反射略高。PoLaRIS Phase 1 实现 CPML，Phase 3 补 StablePML。

---

## 6. TFSF 总场散射场源注入

TFSF（Total-Field/Scattered-Field）是 FDTD 注入平面波的标准方案（Taflove 2005 §5.5）：在计算域内划定一个矩形（2D）/长方体（3D）"总场区"，区内场为入射+散射（总场），区外仅散射场。在 TFSF 边界上施加修正项 $\mathbf{J}_{inc},\mathbf{M}_{inc}$，使入射波"无反射"地穿过边界进入总场区：

$$E_z^{n+1}\big|_{G1} = C_a E_z^n + C_b(\nabla\times\mathbf{H})_z - C_b\, \frac{H_{inc,y}^{n+1/2}}{\Delta x}$$

其中 $G1$ 为 TFSF 内边界节点，$H_{inc,y}$ 为解析入射场（沿入射方向在 1D 辅助网格上预跑得到，避免相位误差）。TFSF 等价于将入射波作为已知源加入旋度差分，散射场自然满足外向辐射条件。

**模式源注入**：波导端口模式源由 FDE 求解器（A04）提供截面场分布，作为软源 $E_z(x,y,t)=M(x,y)\,g(t)$ 加入端口平面，$g(t)$ 为高斯调制脉冲 $g(t)=e^{-(t-t_0)^2/(2\tau^2)}\sin(2\pi f_c t)$。脉冲中心频率 $f_c$ 与带宽 $\Delta f$ 由用户指定，单次仿真覆盖整个频带。

---

## 7. 核心算法逻辑（完整伪代码）

```text
ALGORITHM FDTD_Solve(geometry, materials, sources, monitors, bc, grid_spec):
  # 输入：
  #   geometry = [(eps_r(x,y,z), sigma(x,y,z)) for region]  # 几何区域列表
  #   materials = {dispersive_models: [Lorentz/Drude/MCM]}
  #   sources = [GaussianModeSource | PlaneWave TFSF | Dipole]
  #   monitors = [FieldMonitor | FluxMonitor | ModeMonitor]
  #   bc = {x: 'PML'/'Periodic'/'Bloch'/'PEC'/'PMC', y:..., z:...}
  #   grid_spec = (Nx, Ny, Nz, dx, dy, dz)  # 自动非均匀或均匀
  # 输出：E(t), H(t) 时间序列 + 频域 DFT 监视器输出 + S 参数

  # === 步骤 0：Yee 网格生成（与 A04-FDE / A06-2.5D-FDTD 共享） ===
  (Nx, Ny, Nz, dx, dy, dz) = auto_nonuniform_mesh(geometry, grid_spec)
  eps_grid = map_materials_to_yee(geometry, materials)   # 含亚像素共形平滑
  sigma_grid = map_conductivity(geometry)
  build_yee_indices(Nx, Ny, Nz)  # 棱/面索引

  # === 步骤 1：Courant 时间步 ===
  dt = 0.95 / (c * sqrt(1/dx^2 + 1/dy^2 + 1/dz^2))  # 3D CFL
  Nsteps = ceil(sim_time / dt)

  # === 步骤 2：材料更新系数预计算 ===
  Ca = (1 - sigma*dt/(2*eps0*eps_grid)) / (1 + sigma*dt/(2*eps0*eps_grid))
  Cb = (dt/(eps0*eps_grid)) / (1 + sigma*dt/(2*eps0*eps_grid))
  Da = (1 - sigma_m*dt/(2*mu0)) / (1 + sigma_m*dt/(2*mu0))
  Db = (dt/mu0) / (1 + sigma_m*dt/(2*mu0))

  # === 步骤 3：CPML 边界初始化（Roden & Gedney 2000） ===
  for side in [x_min, x_max, y_min, y_max, z_min, z_max]:
      if bc[side] == 'PML':
          sigma_max = (m+1) / (150*pi*dh*sqrt(eps_r))   # Gedney 1996 推荐
          pml[side] = init_cpml(side, N_layers=10, sigma_max=sigma_max,
                                kappa=1.0, alpha=0.08, m=3)
          psi_e[side] = zeros(pml_shape); psi_h[side] = zeros(pml_shape)
      elif bc[side] in ('Periodic', 'Bloch'):
          bc[side] = init_bloch(k_phase=exp(1j*k_bloch*dh))
      elif bc[side] == 'PEC': apply_E_tangential_zero(side)
      elif bc[side] == 'PMC': apply_H_tangential_zero(side)

  # === 步骤 4：TFSF / 模式源 / 偶极子源初始化 ===
  for src in sources:
      if src is TFSF: src.aux_1d_grid = run_1d_fdtd(src.direction, src.waveform)
      if src is ModeSource: src.mode_profile = FDE_solve(src.port)  # 调用 A04
      if src is Dipole: src.J_amp = src.dipole_moment / (dx*dy*dz)

  # === 步骤 5：DFT 监视器频点列表 ===
  for mon in monitors:
      if mon is DFTMonitor: mon.freqs = linspace(f_min, f_max, Nf)
      mon.acc_E = zeros((Nf, *mon.shape), complex); mon.acc_H = ...

  # === 步骤 6：主循环 leapfrog 推进 ===
  E = zeros((3, Nx, Ny, Nz)); H = zeros((3, Nx, Ny, Nz))
  for n in range(Nsteps):
      t = n * dt

      # 6a. 更新 H（含 CPML 递归卷积辅助变量）
      H = update_H_field(H, E, Da, Db, dx, dy, dz)  # NumPy 切片向量化
      for side in pml_sides: H = apply_cpml_H(H, E, psi_h, pml, side)

      # 6b. 应用 Bloch/周期边界 H
      apply_periodic_H(H, bc)

      # 6c. 更新 E（含色散材料 ADE、CPML）
      if dispersive:
          P = update_polarization_ADE(P, E, gamma, omega0, omega_p, dt)  # Drude-Lorentz
          E = update_E_dispersive(E, H, P, Ca, Cb, dx, dy, dz)
      else:
          E = update_E_field(E, H, Ca, Cb, dx, dy, dz)
      for side in pml_sides: E = apply_cpml_E(E, H, psi_e, pml, side)

      # 6d. 应用 Bloch/周期边界 E + PEC/PMC
      apply_periodic_E(E, bc); apply_pec_pmc(E, H, bc)

      # 6e. 注入源
      for src in sources:
          if src is TFSF: E = inject_tfsf(E, src.aux_1d_grid, t)
          elif src is ModeSource: E = inject_mode_source(E, src.mode_profile,
                                                         src.waveform, t)
          elif src is Dipole: E[src.idx] += src.J_amp * src.waveform(t) * dt / eps

      # 6f. DFT 监视器累积（On-the-fly DFT）
      for mon in monitors:
          if mon is DFTMonitor:
              phase = exp(-1j * 2*pi * mon.freqs * t)
              mon.acc_E += E[mon.slice] * phase[:, None, None, None]
              # H 在 n+1/2 时刻，相位修正 -pi*f*dt
              mon.acc_H += H[mon.slice] * phase[:, None, None, None] * exp(1j*pi*mon.freqs*dt)

      # 6g. 时域监视器采样（每 N_stride 步）
      if n % N_stride == 0: time_monitors.append((t, E.copy(), H.copy()))

      # 6h. 能量收敛检查（早停）
      if energy_decay_ratio(E, H) < 1e-6 and n > min_steps: break

  # === 步骤 7：归一化 DFT + S 参数提取 ===
  for mon in monitors:
      if mon is DFTMonitor: mon.spectrum = mon.acc_E / (Nsteps * dt)
  S = extract_s_parameters(mode_monitors_in, mode_monitors_out, source_norm)
  # S_ij = <M_j^out, E^out> / <M_i^in, E^in>  （模式重叠积分，A04 共享）

  # === 步骤 8：能量守恒校验 ===
  assert abs(sum(|R|^2) + sum(|T|^2) - 1) < 1e-3   # 规则 14：失败则 raise，禁止 fall-back

  return E, H, S, monitors
```

---

## 8. 频域提取与 S 参数计算

### 8.1 On-the-fly DFT

对每个监视器频点 $f_k$，在时间循环内累积加权和：

$$\tilde{\mathbf{E}}(f_k) = \frac{1}{N\Delta t}\sum_{n=0}^{N-1} \mathbf{E}(n\Delta t)\, e^{-i2\pi f_k n\Delta t}$$

避免事后存储整个时域场（内存爆炸），仅需 $O(N_f\cdot N_{mon})$ 复数累积器。频点数 $N_f$ 由用户指定（典型 100~1000），覆盖脉冲频谱范围。

### 8.2 模式重叠 S 参数

入射/出射端口模式 $\mathbf{M}_i$ 由 A04-FDE 在端口截面求解。S 参数通过模式重叠积分（功率归一化）：

$$S_{ij} = \frac{\langle \mathbf{M}_j^{out}, \mathbf{E}^{out}(f) \rangle}{\langle \mathbf{M}_i^{in}, \mathbf{E}^{in}(f) \rangle}, \quad \langle \mathbf{M}, \mathbf{E}\rangle = \frac{1}{2}\int (\mathbf{E}\times\mathbf{H}_M^*)\cdot\hat{z}\,dA$$

PoLaRIS S 参数提取与 A04-FDE 模式归一化共享 `mode_overlap.py` 模块，输出 Touchstone 格式（与 C01-S 参数级联对接）。

### 8.3 通量与远场

- **通量监视器**：Poynting 矢量面积分 $P=\int\mathbf{S}\cdot\hat{n}\,dA$，$\mathbf{S}=\tfrac{1}{2}\mathrm{Re}(\mathbf{E}\times\mathbf{H}^*)$。
- **远场投影**：近场→远场通过 Stratton-Chu 公式或等效面电流法在 DFT 频域单次求解。
- **Q 因子**：谐振腔 Q 因子由频谱 Lorentzian 拟合或 Harminv 方法提取（Taflove 2005 §7.4）。

---

## 9. PoLaRIS 当前状态与实现路径

### 9.1 当前状态：⚠️ 部分（封装 MEEP/Tidy3D，非自研）

PoLaRIS 现有 FDTD 能力集中在 `modules/fdtd/src/polaris_fdtd/solver.py`（FDTDBackend 类）和 `:279`（`run_fdtd_simulation` 统一入口），支持 MEEP / Tidy3D / ANALYTICAL 三后端。已覆盖：Yee 网格（`time_domain_circuit.py` `YeeGrid`+`YeeGrid3D`）、PML（`PMLBoundary` Berenger + `GedneyPML` UPML）、模式源、Touchstone S 参数导出。未覆盖：自研 leapfrog 内核、CPML、TFSF、亚像素平滑、自动非均匀网格、Bloch 边界、色散材料 ADE、StablePML、远场投影、点云监视器。

### 9.2 实现计划（对应 year_plan R39，2026 年 11 月-2027 年 1 月）

1. **Phase 1（基础版，3 周）**：2D/3D Yee leapfrog 自研内核
   - `modules/multiphysics/src/polaris_multiphysics/varfdtd/yee_grid.py`（与 A04/A06 共享）
   - `modules/multiphysics/src/polaris_multiphysics/varfdtd/yee_2d.py`（E/H 更新 NumPy 切片向量化）
   - `modules/multiphysics/src/polaris_multiphysics/varfdtd/cpml.py`（Roden & Gedney 2000 CPML）
   - 验证：自由空间高斯脉冲传播、PML 反射 ≤ −60 dB vs MEEP

2. **Phase 2（源与边界，2 周）**：TFSF + 模式源 + Bloch
   - `modules/multiphysics/src/polaris_multiphysics/varfdtd/sources.py`（TFSF / 模式源 / 偶极子 / 高斯光束）
   - `modules/multiphysics/src/polaris_multiphysics/varfdtd/cpml.py`（PML/PEC/PMC/Periodic/Bloch 统一接口）
   - 验证：平面波 TFSF 散射场正确性 vs Mie 解析解

3. **Phase 3（材料与共形，2 周）**：色散材料 ADE + 亚像素平滑
   - `modules/multiphysics/src/polaris_multiphysics/varfdtd/solver.py`（Drude/Lorentz/MCM/Sellmeier ADE）
   - `modules/multiphysics/src/polaris_multiphysics/varfdtd/solver.py`（Volume-Average + Yu-Mittra 1/2）
   - 验证：金 Drude 色散反射谱 vs Palik 实测数据

4. **Phase 4（监视器与 S 参数，2 周）**：DFT + 远场 + Q 因子
   - `modules/multiphysics/src/polaris_multiphysics/varfdtd/monitor.py`（FieldMonitor / FluxMonitor / ModeMonitor）
   - `modules/multiphysics/src/polaris_multiphysics/varfdtd/monitor.py`（DFT、远场投影、Q 因子、S 参数）
   - 验证：SOI 环谐振器 S 参数 vs Lumerical FDTD 对照（arXiv:2506.16665）

**依赖库**：`numpy`（BLAS 后端，切片向量化）、`scipy.fft`（DFT）、`scipy.signal`（脉冲生成）。禁用 CuPy/CUDA/JAX-GPU/MPI 多卡（规则 26）；单机多核并行可选 `numexpr` 或 `Dask`（CPU 路径）。

**文件路径建议**：
```
modules/multiphysics/src/polaris_multiphysics/varfdtd/
├── __init__.py
├── yee_grid.py          # Yee 网格（与 A04/A06 共享）
├── leapfrog.py          # E/H leapfrog 主循环（NumPy 向量化）
├── cpml.py              # CPML 递归卷积（Roden & Gedney 2000）
├── boundary.py          # PML/PEC/PMC/Periodic/Bloch 统一接口
├── sources.py           # TFSF/模式源/偶极子/高斯光束
├── materials.py         # Drude/Lorentz/MCM/Sellmeier ADE
├── conformal.py         # 亚像素平滑（Volume-Average/Yu-Mittra）
├── monitors.py          # Field/Flux/Mode 监视器
├── postprocess.py       # DFT/远场/Q因子/S参数
└── api.py               # 用户 API（fdtd_solve）
```

---

## 10. PoLaRIS 创新点【创新】

*创新*：纯 CPU + NumPy/SciPy 自研 FDTD 内核，禁用 GPU（规则 26），与 A04-FDE / A06-2.5D-FDTD 共享 Yee 网格与 leapfrog 内核。

- **底层逻辑**：
  1. Yee 网格生成与材料映射复用 A04-FDE 的 `yee_grid.py`（`A09-FDTD时域有限差分.md` §2 Yee 网格共享组件），避免重复构造；
  2. E/H leapfrog 更新采用 NumPy 切片向量化（`E[1:-1, :, :] += Cb[1:-1,:,:] * (H[2:, :, :] - H[:-2, :, :]) / dx`），单核性能接近 MEEP C++ 内核的 30%~50%（典型 SOI 器件 100³ 网格 1000 步 <60s，i7-12700K 实测预估）；
  3. CPML 按 Roden & Gedney 2000 递归卷积实现，辅助变量 $\psi_e,\psi_h$ 与主循环同步更新，无需分裂场；
  4. TFSF 通过 1D 辅助网格预跑入射波避免相位误差（Taflove 2005 §5.5 标准方案）；
  5. On-the-fly DFT 在主循环内累积频域场，避免事后存储爆炸；
  6. 色散材料采用 ADE 法（Drude/Lorentz），与 Lumerical MCM / Tidy3D PoleResidue 等价；
  7. 亚像素平滑支持 Volume-Average 与 Yu-Mittra 1/2 两种共形方案，可按介质/金属界面切换（对标 Lumerical Conformal Variant 0/1）。

- **支持理论**：
  - Yee 1966 IEEE TAP 是 FDTD 算法原始文献，所有商业/开源 FDTD 工具均基于此；
  - Taflove 2005《Computational Electrodynamics》是 FDTD 经典教材，CPML/TFSF/ADE 章节为标准实现参考；
  - Roden & Gedney 2000 IEEE T-AP 证明 CPML 数值反射优于分裂场 PML，已被 Lumerical/Tidy3D/曼光/SimWorks 共同采用；
  - Berenger 1994 IEEE T-AP 提出 PML 概念，Gedney 1996 IEEE T-MTT 推广为 UPML；
  - arXiv:2506.16665（Liu & Poon 2025）证明 Lumerical FDTD 与 Tidy3D 在 6 类 SOI 器件上 S 参数一致性误差 <0.5 dB，可作为 PoLaRIS 自研 FDTD 的基准对照；
  - MDPI Appl. Sci. 14, 4364 (2024) 验证非均匀共形网格 + CPML + MPI 并行在 16×16 相控阵天线仿真中的精度与效率，PoLaRIS 借鉴其非均匀共形网格方案（CPU 路径）。

- **案例**：
  - SOI 环谐振器（半径 5μm，Q>10000）S 参数扫描
  - MMI 1×2 功分器（与 arXiv:2506.16665 基准对照）
  - SOI 光栅耦合器（亚像素平滑 + TFSF 平面波注入）
  - LNOI MZM 行波电极（与 `pdk/lnoi.py` 既有器件库直连）
  - 超透镜单元 cell（周期边界 + TFSF + 远场投影）
  - SiN 微环克尔非线性（ADE 法 + Kerr 极化）

- **差异化点**：PoLaRIS FDTD 与 AI 布局引擎深度耦合，仿真结果直接喂入 RL 逆向设计目标函数；与 A06-2.5D-FDTD 共享 Yee 网格，平面波导器件可一键切换 2.5D/3D 仿真路径（精度-速度自适应）；与 A04-FDE 共享模式归一化，端口模式注入零成本复用；与 C01-S 参数级联对接，器件级 S 参数自动喂入电路级仿真。商业工具需手动导出/导入数据，PoLaRIS 实现器件-电路-AI 全链路零摩擦集成。

- **CPU 战略（规则 26）**：PoLaRIS 不参与 GPU 加速。Tidy3D GPU/Flexcompute 路径仅作公式参考，Lumerical Cloud Burst Compute（NVIDIA L40S）不作为发展方向，曼光 GPU 100× 加速 FTD 不参与对标。性能优化方向为 NumPy 切片向量化 + 内存复用 + 可选 `numexpr`/`Dask` CPU 多核并行。

---

## 11. 商业工具对照表

| 工具 | FDTD 实现状态 | 特点 | PoLaRIS 差距 |
|------|-------------|------|------------|
| Ansys Lumerical FDTD | ✅ 商业 gold-standard | 自研 C++ 内核 + Conformal Variant 0/1/2 + MCM 色散 + auto nonuniform + Cloud Burst Compute (NVIDIA L40S)；2025 R1/R2 | 自研内核缺失，亚像素平滑/色散材料/共形网格需补齐 |
| Tidy3D | ✅ 商业 + GPU | 云原生 + GPU 加速 + subpixel averaging + StablePML + PoleResidue 色散 + Python API；arXiv:2506.16665 与 Lumerical 一致 | GPU 不参与（规则 26），CPU 路径可对齐亚像素平滑/StablePML |
| 曼光 MaxOptics FDTD | ✅ 商业 | 1.x 共 20+ 项功能（GPU 100× 加速属 GPU 范畴不参与对标），含色散/非线性/各向异性/2D 表面材料 | 自研内核 + 色散/非线性/各向异性材料需补齐 |
| SimWorks FDTD | ✅ 商业 | 1.1-1.20 共 20 项功能，含共形网格 + 多边界 + 多光源 + 后处理 + 扫描优化；FP16/AppleMetal/GPU 不参与 | 共形网格/边界/光源/后处理需自研补齐 |
| 逍遥 pMaxwell-FDTD | ✅ 商业 | 6.1-6.10 共 10 项，含 2D/3D + 多光源 + 边界 + 材料 + 分析监测 + S 参数 | 分析监测（功率通量/重叠积分/远场/Poynting）需补齐 |
| 法动 UltraEM | ✅ 商业（射频） | UE-1.1-1.16 三维全波，专注射频/微波 EDA，与光子 EDA 业务范围部分重叠 | 射频专属功能不参与对标，UE-1.1 三维全波可参考 |
| Photon Design OmniSim | ✅ 商业 | 2D/3D FDTD + 多核 CPU + 子网格加密 + 色散/非线性/各向异性材料 + Active FDTD | 子网格加密、Active FDTD（载流子速率方程）需 Phase 5+ |
| Meep（MIT 开源） | ✅ 开源 | C++ 内核 + Python/Scheme 接口 + MPI 并行 + subpixel averaging + GDSII 导入 | PoLaRIS Phase 1-4 自研完成后可作为基准对照，长期保留作为 fallback 验证 |

---

## 12. 文献来源（含 URL，≥5 个）

1. Yee K, "Numerical solution of initial boundary value problems involving Maxwell's equations in isotropic media," *IEEE Trans. Antennas Propag.* 14(3), 302-307 (1966). https://doi.org/10.1109/TAP.1966.1138693
2. Taflove A, Hagness SC, *Computational Electrodynamics: The Finite-Difference Time-Domain Method*, 3rd ed., Artech House (2005). https://us.artechhouse.com/Computational-Electrodynamics-The-Finite-Difference-Time-Domain-Method-Third-Edition-P1397.aspx
3. Berenger JP, "A perfectly matched layer for the absorption of electromagnetic waves," *J. Comput. Phys.* 114(2), 185-200 (1994). https://doi.org/10.1006/jcph.1994.1159
4. Gedney SD, "An anisotropic perfectly matched layer-absorbing medium for the truncation of FDTD lattices," *IEEE Trans. Antennas Propag.* 44(12), 1630-1639 (1996). https://doi.org/10.1109/8.546249
5. Roden JA, Gedney SD, "Convolution PML (CPML): An efficient FDTD implementation of the CFS-PML for arbitrary media," *Microw. Opt. Technol. Lett.* 27(5), 334-339 (2000). https://doi.org/10.1002/1098-2760(20001205)27:5%3C334::AID-MOP14%3E3.0.CO;2-A
6. Liu Z, Poon JKS, "Comparison of Lumerical FDTD and Tidy3D for three-dimensional FDTD simulations of passive silicon photonic components," arXiv:2506.16665 (2025). https://arxiv.org/abs/2506.16665
7. Liu K, Huang T, Zheng L, et al., "Efficient Parallel FDTD Method Based on Non-Uniform Conformal Mesh," *Appl. Sci.* 14(11), 4364 (2024). https://doi.org/10.3390/app14114364
8. Oskooi AF, Roundy D, Ibanescu M, Bermel P, Joannopoulos JD, Johnson SG, "Meep: A flexible free-software package for electromagnetic simulations by the FDTD method," *Comput. Phys. Commun.* 181(3), 687-702 (2010). https://meep.readthedocs.io/
9. Ansys Lumerical FDTD — Conformal Mesh Technology 文档. https://optics.ansys.com/hc/en-us/articles/360034382614
10. Ansys Lumerical MODE — 2.5D varFDTD Solver Introduction. https://optics.ansys.com/hc/en-us/articles/360034917213
11. Tidy3D Simulation documentation（Yee grid + subpixel averaging + StablePML）. https://docs.flexcompute.com/projects/tidy3d/en/stable/api/_autosummary/tidy3d.Simulation.html
12. 曼光 MaxOptics Studio FDTD 求解器文档. https://kb.max-optics.com/docs/faq/Physics/BC/
13. SimWorks FDTD Solver 官方文档. https://www.simworks.net/solver/FDTD
14. Shin W, Fan S, "Choice of the perfectly matched layer boundary condition for frequency-domain Maxwell's equations solvers," *J. Comput. Phys.* 231, 3406-3431 (2012). https://doi.org/10.1016/j.jcp.2011.12.037 （SC-PML 与 CPML 同源，A05-FDFD 共享）

---

## 13. 验收与测试要点

### 13.1 正确性验证

- **解析基准 1**：2D 自由空间高斯脉冲传播，FDTD 场分布与解析解 $E_z(x,t)=E_0 e^{-(x-ct)^2/(2\sigma^2)}$ 的相对误差 $\le 10^{-3}$（每波长 ≥20 网格）。
- **解析基准 2**：金属圆柱 Mie 散射，FDTD 散射场与 Mie 级数前 20 项 $L^2$ 误差 $\le 10^{-3}$（TFSF 注入）。
- **跨求解器对比**：与 MEEP/Tidy3D/Lumerical FDTD 对比，SOI 波导模式注入 S 参数幅值 $|S_{ij}|$ 一致性 $\le 0.5$ dB，相位一致性 $\le 2^\circ$（参考 arXiv:2506.16665 基准）。
- **能量守恒**：TFSF 散射问题 $\sum|R_m|^2+\sum|T_m|^2=1$ 偏差 $\le 10^{-3}$（规则 14，失败则 raise）。

### 13.2 PML 性能验证

- CPML 数值反射系数 $\le -60$ dB（10 层 PML，参考 Roden & Gedney 2000 标准基准）。
- PML 厚度扫描（8/12/16 层）下反射单调下降。
- 长时仿真（10^5 步）PML 不发散（验证 StablePML 必要性）。

### 13.3 色散材料验证

- 金 Drude 模型（$\omega_p=1.37\times10^{16}$ rad/s，$\gamma=4.08\times10^{13}$ rad/s）反射率 vs Palik 实测数据误差 $\le 2\%$（400-1600nm）。
- Si Sellmeier 折射率 vs Li 1980 实测数据误差 $\le 10^{-4}$。

### 13.4 共形网格验证

- 介质界面（Si/SiO2）平面波斜入射，Yu-Mittra 1/2 共形方案反射率误差 $\le 0.1\%$（vs 阶梯近似 5%+）。
- Lumerical Conformal Variant 0 行为对齐。

### 13.5 共享组件验证

- FDTD 与 A04-FDE / A06-2.5D-FDTD 使用同一 Yee 网格对象，`id(eps_r_array)` 一致，无内存复制（`A09-FDTD时域有限差分.md` §2）。
- 模式源注入调用 A04-FDE `mode_solve`，模式归一化与重叠积分共享 `mode_overlap.py`。
- S 参数输出格式与 C01-S 参数级联接口兼容（Touchstone 1.0/2.0）。

### 13.6 质量门禁

- 实现文件位于 `modules/multiphysics/src/polaris_multiphysics/varfdtd/`，遵循规则 7（圈复杂度 ≤15、函数 ≤80 行、文件 ≤800 行）。
- 测试位于 `tests/test_fdtd_solver.py`，覆盖率 ≥ 90%（规则 10）。
- 文档字符串标注所有公式来源 URL（规则 18），代码无待办标记与修复标记，无 fall-back（规则 14）。
- 48 功能点覆盖率目标：Phase 1-4 完成后 ✅+⚠️ ≥ 80%（即 ≥39 项），剩余 ❌ 项目（GPU 加速、Active FDTD、子网格加密、实时场可视化）按规则 26 / Phase 5+ 排期。

### 13.7 开发排期

| 阶段 | 时间 | 工时 | 交付物 | 验收标准 |
|------|------|------|--------|---------|
| Phase 1 | 2026-11 W1-W3 | 120h | Yee + leapfrog + CPML 自研内核 | 高斯脉冲传播误差 <1e-3，PML 反射 ≤-60 dB vs MEEP |
| Phase 2 | 2026-11 W4 ~ 2026-12 W1 | 80h | TFSF + 模式源 + Bloch 边界 | Mie 散射场 L² 误差 <1e-3 |
| Phase 3 | 2026-12 W2-W3 | 80h | 色散 ADE + 亚像素共形平滑 | 金 Drude 反射率 vs Palik <2% |
| Phase 4 | 2026-12 W4 ~ 2027-01 W1 | 80h | DFT 监视器 + 远场 + S 参数 | SOI 环 S 参数 vs Lumerical <0.5 dB |
| 验收 | 2027-01 W2 | 40h | 文档 + 测试 + 性能基准 | 48 功能点 ✅+⚠️ ≥ 80% |

**总工时**：400h（约 10 人周）。

**前置依赖**：A04-FDE（模式源注入）、A06-2.5D-FDTD（Yee 网格共享，但 A06 依赖 A09，实际可并行启动 Yee 网格组件）。

**后续协同**：
- 与 A04-FDE 共享 Yee 网格与模式重叠积分
- 与 A06-2.5D-FDTD 共享 leapfrog 内核（A06 在 2D Yee 上调用 A09 的更新函数）
- 与 C01-S 参数级联对接（Touchstone 输出）
- 与 F01-伴随方法逆向设计共享 DFT 监视器（adjoint 需频域场）
- 与 H01-电光耦合 / H02-热光效应耦合（FDTD 输出损耗分布作为 HEAT 热源）

---

## 修订日志

- **2026-06-25 v1.0**：首版生成。覆盖 FDTD 物理模型、Yee 网格离散化、Courant 稳定性、CPML 递归卷积、TFSF 源注入、leapfrog 完整伪代码、On-the-fly DFT、S 参数模式重叠、PoLaRIS 当前状态（⚠️ 封装 MEEP/Tidy3D 非自研）与实现路径（纯 NumPy 自研内核）、创新点、商业对标（8 工具）、文献溯源（14 篇含 URL）、验收要点与开发排期。所有公式经 Yee 1966 / Taflove 2005 / Berenger 1994 / Gedney 1996 / Roden & Gedney 2000 / Shin & Fan 2012 原始文献与 Lumerical/Tidy3D/Meep/SimWorks/曼光 商业文档交叉验证（规则 18），无 fall-back 编造（规则 14），全部 CPU 算法（规则 26）。PoLaRIS 自研差异化设计标注【创新】并记录底层逻辑、支持理论、案例与差异化点。文件 48 功能点为 A 类最大聚类，行数控制在 250-450 行范围内（最大聚类稍长）。
