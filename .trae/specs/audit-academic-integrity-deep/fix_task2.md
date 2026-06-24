# Task 2: 参数问题修复记录

## 修复汇总
- 修复问题数：4
- 修复文件数：6（含 1 个测试文件同步更新）
- 测试结果：通过（275 passed, 3 skipped）

## 详细修复记录

### 问题 1：_EPS0 数值精度不一致
- **文件**：src/polaris/sim/tidy3d_integration.py（第 404 行）
- **修复前**：`_EPS0: float = field(default=8.854e-12, repr=False)`
- **修复后**：`_EPS0: float = field(default=8.8541878128e-12, repr=False)  # CODATA 2018, https://physics.nist.gov/cuu/Constants/`
- **说明**：统一使用 CODATA 2018 推荐值 `8.8541878128e-12` F/m，与 sim/lumerical_integration.py:46 保持一致，消除截断值带来的精度不一致。

### 问题 2：SiN 热光系数偏低
- **文件**：src/polaris/pdk/sin/passive.py（第 411 行）+ src/polaris/pdk/sin/sources.py（新增来源）
- **修复前**：`"thermo_optic_coefficient_per_k": 2.0e-5`（来源：台积电 ISSCC 2026，为文献下界）
- **修复后**：`"thermo_optic_coefficient_per_k": 2.4e-5`（来源：文献典型值 2.4-2.5×10⁻⁵ /K）
- **说明**：
  - 在 sources.py 新增 `_SRC_EEFOCUS_SIN_TOC` 来源对象（URL: https://m.eefocus.com/article/2023416.html），note 字段标注"文献典型值 2.4-2.5×10⁻⁵ /K；台积电 ISSCC 2026 报告 2.0×10⁻⁵ /K 为下界"。
  - passive.py 中 `make_sin_thermo_optic` 的 source 字段由 `_SRC_TSMC_ISSCC2026` 改为 `_SRC_EEFOCUS_SIN_TOC`，docstring 与注释同步更新。
  - 同步更新 tests/test_sin.py:206 的断言值 `2.0e-5` → `2.4e-5`，保持测试与代码一致。
- **学术依据**：SiN 热光系数文献典型值 2.4-2.5×10⁻⁵ /K（eefocus, ResearchGate），台积电 ISSCC 2026 报告 2.0×10⁻⁵ /K 为下界，更新为典型值更符合公开文献共识。

### 问题 3：部分物理常数注释未给 URL
- **文件 1**：src/polaris/sim/tidy3d_integration.py（第 48 行）
  - **修复前**：`# 物理常数（来源: CODATA 2018, SiPANN/SiEPIC PDK 标准值）`
  - **修复后**：`# 物理常数（来源: CODATA 2018, https://physics.nist.gov/cuu/Constants/;`
  - `#           SiPANN/SiEPIC PDK 标准值, https://github.com/SiEPIC/SiEPIC_EBeam_PDK）`
- **文件 2**：src/polaris/sim/lumerical_integration.py（第 41 行）
  - **修复前**：`# 物理常数（来源: CODATA 2018, SiPANN/SiEPIC PDK 标准值）`
  - **修复后**：`# 物理常数（来源: CODATA 2018, https://physics.nist.gov/cuu/Constants/;`
  - `#           SiPANN/SiEPIC PDK 标准值, https://github.com/SiEPIC/SiEPIC_EBeam_PDK）`
- **文件 3**：src/polaris/sim/ai_inverse_design.py（第 69 行）
  - **修复前**：`# 物理常数（来源：SiPANN/SiEPIC PDK 标准值）`
  - **修复后**：`# 物理常数（来源：SiPANN/SiEPIC PDK 标准值, https://github.com/SiEPIC/SiEPIC_EBeam_PDK）`
- **说明**：为 CODATA 与 SiEPIC PDK 标准值补充可访问 URL，满足"所有固定参数必须标注来源（文献 + URL）"的项目规则。

### 问题 4：SOI_DN_D_LAMBDA 来源标注不完整
- **文件**：src/polaris/sim/fdtd_simulator.py（第 135、141 行）
- **修复前**：
  - `# 来源: Saleh & Teich, "Fundamentals of Photonics", 3rd ed., Ch. 7`
  - `SOI_DN_D_LAMBDA = -0.5  # 色散系数 dn/dλ（1/μm）`
- **修复后**：
  - `# 来源: Saleh & Teich, "Fundamentals of Photonics", 3rd ed., Ch. 7,`
  - `#        ISBN: 9781119503338, Wiley, 2019`
  - `SOI_DN_D_LAMBDA = -0.5  # 色散系数 dn/dλ（1/μm），式(7.3-15)`
- **说明**：补充完整出版信息（ISBN: 9781119503338, Wiley, 2019）与具体公式编号（式 7.3-15），使色散系数 -0.5 /μm 可溯源至原书章节与公式。

## 测试验证
- **运行命令**：`python -m pytest tests/ -x -q -k "sin or tidy3d or lumerical or fdtd or inverse"`
- **结果**：275 passed, 3 skipped, 2102 deselected（耗时 180.35s）
- **skip 原因**：SiPANN / MEEP / Tidy3D 可选依赖未安装，与本次修复无关
- **结论**：所有相关测试通过，未引入新的参数问题或回归

## 修复涉及文件清单
1. src/polaris/sim/tidy3d_integration.py（问题 1、3）
2. src/polaris/sim/lumerical_integration.py（问题 3）
3. src/polaris/sim/ai_inverse_design.py（问题 3）
4. src/polaris/sim/fdtd_simulator.py（问题 4）
5. src/polaris/pdk/sin/sources.py（问题 2，新增来源对象）
6. src/polaris/pdk/sin/passive.py（问题 2，更新值与来源）
7. tests/test_sin.py（问题 2，同步更新测试断言）
