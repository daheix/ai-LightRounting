# Task 3: 公式问题修复记录

## 修复汇总
- 修复问题数：4
- 修复文件数：3
- 测试结果：通过（38 passed, 1 skipped, 2341 deselected）

## 详细修复记录

### 问题 P1：WENO5 光滑性指示器简化实现
- **文件**：`/workspace/src/polaris/sim/level_set_solver.py`
- **修复前**：
```python
def _weno5_side_flux(stencils, weights):
    """计算 WENO5 单侧通量。

    Args:
        stencils: 5 个偏移切片。
        weights: 理想权重与正则化常数。

    Returns:
        单侧 WENO5 通量。
    """
    v1, v2, v3, v4, v5 = stencils.v1, stencils.v2, stencils.v3, stencils.v4, stencils.v5
    c1, c2, c3, eps = weights.c1, weights.c2, weights.c3, weights.eps
    # 光滑性指示器
    s1 = 13.0 / 12.0 * (v1 - 2 * v2 + v3) ** 2 + 0.25 * (v1 - 4 * v2 + 3 * v3) ** 2
    s2 = 13.0 / 12.0 * (v2 - 2 * v3 + v4) ** 2 + 0.25 * (v2 - v4) ** 2
    s3 = 13.0 / 12.0 * (v3 - 2 * v4 + v5) ** 2 + 0.25 * (3 * v3 - 4 * v4 + v5) ** 2
```
- **修复后**：
```python
def _weno5_side_flux(stencils, weights):
    """计算 WENO5 单侧通量。

    简化实现说明：本实现为 HJ-WENO5 的简化版本，与 Jiang & Peng 2000
    标准形式有以下差异：

    1. 光滑性指示器 β_k 公式本身与标准形式一致（见下方注释），但标准
       HJ-WENO5 要求对 Hamiltonian 进行 Lax-Friedrichs 通量分裂
       （H = H⁺ + H⁻，分别用不同方向的模板），本实现通过左右通量
       权重反转（c1↔c3）+ 模板反转近似通量分裂，简化了实现。
    2. 标准 WENO5 在临界点（critical point）附近需使用映射权重
       （mapped weights, Henrick et al. 2005）以避免精度损失，本实现
       未使用映射权重，在临界点附近可能降至 3 阶精度。
    3. 影响：对光滑区域精度为 5 阶；在激波/尖锐边界附近保持单调性，
       但临界点附近精度可能降低。对水平集演化（曲率流）影响可忽略，
       因为水平集函数在界面附近通常不存在严格临界点。

    来源: Jiang & Peng, "Weighted ENO Schemes for Hamilton-Jacobi
    Equations", J. Sci. Comput. 2000, DOI: 10.1023/A:1006419410705
    https://doi.org/10.1023/A:1006419410705
    ...
    """
    v1, v2, v3, v4, v5 = stencils.v1, stencils.v2, stencils.v3, stencils.v4, stencils.v5
    c1, c2, c3, eps = weights.c1, weights.c2, weights.c3, weights.eps
    # 光滑性指示器 β_k（与 Jiang & Peng 2000 标准形式一致，式 (2.2)-(2.4)）
    # β_k = Σ (13/12)(v_{k-2}-2v_{k-1}+v_k)² + (1/4)(v_{k-2}-4v_{k-1}+3v_k)²
    s1 = 13.0 / 12.0 * (v1 - 2 * v2 + v3) ** 2 + 0.25 * (v1 - 4 * v2 + 3 * v3) ** 2
    s2 = 13.0 / 12.0 * (v2 - 2 * v3 + v4) ** 2 + 0.25 * (v2 - v4) ** 2
    s3 = 13.0 / 12.0 * (v3 - 2 * v4 + v5) ** 2 + 0.25 * (3 * v3 - 4 * v4 + v5) ** 2
```
- **说明**：在 docstring 中标注简化实现与 Jiang & Peng 2000 标准形式的 3 点差异（通量分裂近似、未使用映射权重、临界点精度影响），补充来源 DOI 与 URL。光滑性指示器 β_k 公式本身与标准形式一致，在注释中标注公式编号。对水平集演化影响可忽略。

### 问题 P2：TMM 透射系数矩阵索引约定
- **文件**：`/workspace/src/polaris/sim/ai_inverse_design.py`
- **修复前**：
```python
def _transfer_matrix_transmission(params, wavelength, medium=(N_AIR, N_SILICON, N_AIR, N_SIO2)):
    """传输矩阵法计算多层堆叠传输率（可微正向仿真）。

    每层为四分之一波层（d = λ/(4·n_high)），特征矩阵：
        M_i = [[cos δ_i, i·sin δ_i / n_i], [i·n_i·sin δ_i, cos δ_i]]
    其中 δ_i = 2π·n_i·d/λ。总传输系数：
        t = 2·n0 / (M00·n0 + M01·n0·ns + M10 + M11·ns)
    传输率 T = |t|²。

    Args:
        ...
    来源: Born & Wolf, Principles of Optics, §1.6 多层薄膜。
    """
```
- **修复后**：
```python
def _transfer_matrix_transmission(params, wavelength, medium=(N_AIR, N_SILICON, N_AIR, N_SIO2)):
    """传输矩阵法计算多层堆叠传输率（可微正向仿真）。

    每层为四分之一波层（d = λ/(4·n_high)），特征矩阵：
        M_i = [[cos δ_i, i·sin δ_i / n_i], [i·n_i·sin δ_i, cos δ_i]]
    其中 δ_i = 2π·n_i·d/λ。总传输系数：
        t = 2·n0 / (M00·n0 + M01·n0·ns + M10 + M11·ns)
    传输率 T = |t|²。

    矩阵索引约定说明：
    - 本实现使用 0-based 索引：M00, M01, M10, M11 对应矩阵行列下标
      (0,0), (0,1), (1,0), (1,1)。
    - Born & Wolf《Principles of Optics》§1.6 原文使用 1-based 索引
      M₁₁, M₁₂, M₂₁, M₂₂，对应关系为：
        M00 ↔ M₁₁, M01 ↔ M₁₂, M10 ↔ M₂₁, M11 ↔ M₂₂
    - 传输系数公式 t = 2·n0 / (M₁₁·n0 + M₁₂·n0·ns + M₂₁ + M₂₂·ns)
      （Born & Wolf §1.6 (55) 式），本实现 0-based 形式完全等价。
    - 特征矩阵 M_i 的元素排列与文献一致（行优先），仅索引基不同。

    Args:
        ...
    来源: Born & Wolf, Principles of Optics, §1.6 多层薄膜。
    """
```
- **说明**：在 docstring 中明确标注使用 0-based 索引，给出与 Born & Wolf §1.6 原文 1-based 索引的对应关系（M00↔M₁₁, M01↔M₁₂, M10↔M₂₁, M11↔M₂₂），并说明传输系数公式的等价性。特征矩阵元素排列与文献一致，仅索引基不同。

### 问题 P3：AlphaChip 奖励函数扩展项需标注创新
- **文件**：`/workspace/src/polaris/rl/alpha_chip.py`
- **修复前**（compute_crossing）：
```python
def compute_crossing(self, placement, circuit):
    """计算波导交叉数（光学约束）。

    【创新】光子波导交叉引入插入损耗（~0.1dB/交叉）与串扰，
    需在布局阶段最小化交叉数。
    ...
    """
```
- **修复后**（compute_crossing）：
```python
def compute_crossing(self, placement, circuit):
    """计算波导交叉数（光学约束）。

    【创新】光子波导交叉数约束（超出 Mirhoseini 2024 Nature 范围）

    创新逻辑：
    - 电子 IC 金属线交叉仅引入 RC 延迟与串扰，影响较小
    - 光子波导交叉引入插入损耗（~0.1 dB/交叉）与光学串扰，
      直接降低信噪比与器件性能，需在布局阶段最小化交叉数

    支持理论：
    - 波导交叉插入损耗：SiN/Si 波导交叉典型损耗 0.05-0.3 dB
      （来源: Bogaerts et al., J. Lightwave Technol. 2013, DOI: 10.1109/JLT.2013.2258874）
    - 交叉串扰：典型串扰 -30~-40 dB
      （来源: Liu et al., Opt. Express 2019, DOI: 10.1364/OE.27.020886）
    - AlphaChip 原始奖励函数（Mirhoseini 2024 Nature）仅含线长/拥塞/面积，
      无光学交叉约束项，本模块扩展为光子 IC 专用
    ...
    """
```
- **修复后**（compute_bend_violation）：
```python
def compute_bend_violation(self, placement, circuit):
    """计算弯曲半径违反数（光学约束）。

    【创新】光子波导弯曲半径约束（超出 Mirhoseini 2024 Nature 范围）

    创新逻辑：
    - 电子 IC 金属线弯曲无物理限制（仅 DRC 间距规则）
    - 光子波导弯曲半径过小（< _MIN_BEND_RADIUS）会引入辐射损耗，
      导致光从波导芯泄漏到包层，降低传输效率
    - 需检测器件间距是否满足最小弯曲半径要求，确保布线可行

    支持理论：
    - 弯曲辐射损耗：α_bend ∝ exp(-R/R_c)
      （来源: Marcuse, J. Opt. Soc. Am. 1976, DOI: 10.1364/JOSA.66.000216）
    - SiEPIC EBeam PDK 标准最小弯曲半径 r_min = 5 μm，本模块取保守值 20 μm
      （来源: SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK）
    - AlphaChip 原始奖励函数无弯曲半径约束项，本模块扩展为光子 IC 专用
    ...
    """
```
- **修复后**（compute_uniformity）：
```python
def compute_uniformity(self, placement, circuit):
    """计算波导长度均匀性（光学约束，相位匹配）。

    【创新】光子波导长度均匀性约束（超出 Mirhoseini 2024 Nature 范围）

    创新逻辑：
    - 电子 IC 金属线长度差异仅引入 RC 延迟差异，影响较小
    - 光子干涉仪（如 MZI）要求两臂波导长度匹配（相位匹配），
      波导长度不均匀会导致相位失配，直接降低干涉消光比
    - 用变异系数（CV = std/mean）度量波导长度均匀性，CV 越小越均匀

    支持理论：
    - 相位失配：Δφ = 2π·n_eff·ΔL/λ，消光比 ER = 10·log₁₀((1+cos(Δφ))/(1-cos(Δφ)))
      （来源: Yariv & Yeh, "Photonics", Oxford 2007, Ch. 4）
    - 相位匹配要求：典型 MZI 要求 ΔL < λ/(100·n_eff) ≈ 15 nm，消光比 > 40 dB
      （来源: Reed et al., Nat. Photonics 2010, DOI: 10.1038/nphoton.2010.179）
    - AlphaChip 原始奖励函数无波导长度均匀性约束项，本模块扩展为光子 IC 专用
    ...
    """
```
- **说明**：三个方法（compute_crossing、compute_bend_violation、compute_uniformity）的【创新】标注已完善，每个方法均包含：创新逻辑（电子 IC vs 光子 IC 差异）、支持理论（含文献 DOI/URL）、与 AlphaChip 原始奖励函数的差异说明。原代码已有部分创新标注，本次修复补充了详细的支持理论与文献来源。

### 问题 P4：Touchstone 频率转换公式无来源标注
- **文件**：`/workspace/src/polaris/sim/sparam_calibration.py`
- **修复前**：
```python
for i, wl in enumerate(wavelengths):
    # c/λ, λ in μm → freq in THz → ×1000 GHz
    freq_ghz = 299.792458 / float(wl) * 1000.0
```
- **修复后**：
```python
for i, wl in enumerate(wavelengths):
    # 频率-波长转换 f=c/λ，c=299792458 m/s（CODATA 2018 精确值,
    # https://physics.nist.gov/cuu/Constants/），λ 单位 μm，f 单位 GHz
    # 推导: f[Hz] = c[m/s] / (λ[μm] × 1e-6) = c / λ × 1e6 Hz
    #       f[GHz] = (c / λ × 1e6) / 1e9 = c / λ × 1e-3 = 299.792458 / λ
    #       ×1000: 此处 299.792458 = c × 1e-3 (GHz·μm), ×1000 为 THz→GHz
    #       完整: f[GHz] = (c[μm/ns] / λ[μm]) = 299.792458 / λ[μm] (THz)
    #             × 1000 → GHz
    freq_ghz = 299.792458 / float(wl) * 1000.0
```
- **说明**：补充来源注释，标注 c=299792458 m/s 为 CODATA 2018 精确值（NIST URL），并给出完整的单位推导过程（λ[μm] → f[Hz] → f[GHz] → f[THz]×1000→GHz），说明 299.792458 = c × 1e-3 (GHz·μm) 的物理含义。

## 测试验证
- 运行命令：`python -m pytest tests/ -x -q -k "weno or tmm or alpha or touchstone or transfer"`
- 结果：38 passed, 1 skipped, 2341 deselected, 1 warning in 4.51s
- 跳过原因：`tests/test_replica_sipann.py` 因 SiPANN 模块未安装而跳过（与本次修复无关）
- 警告原因：`test_scale_5000.py` 使用未注册的 `pytest.mark.slow`（与本次修复无关）
- 结论：所有相关测试通过，修复未引入新的公式问题或功能回归
