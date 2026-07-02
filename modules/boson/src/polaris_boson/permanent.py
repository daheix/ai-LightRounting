"""矩阵积"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Gly"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)

  其中 δ_n = 1 固定，前 n-1 位遍历 ±1，"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)

  其中 δ_n = 1 固定，前 n-1 位遍历 ±1，共 2^(n-1) 项。与 Ryser 同阶但
  常数因子更小（无 (-1)^"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)

  其中 δ_n = 1 固定，前 n-1 位遍历 ±1，共 2^(n-1) 项。与 Ryser 同阶但
  常数因子更小（无 (-1)^|S| 符号翻转）。

**"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)

  其中 δ_n = 1 固定，前 n-1 位遍历 ±1，共 2^(n-1) 项。与 Ryser 同阶但
  常数因子更小（无 (-1)^|S| 符号翻转）。

**Output**:
- 返回 ``complex``"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)

  其中 δ_n = 1 固定，前 n-1 位遍历 ±1，共 2^(n-1) 项。与 Ryser 同阶但
  常数因子更小（无 (-1)^|S| 符号翻转）。

**Output**:
- 返回 ``complex`` 积和式值。

R03 合规: 输入非法（非方阵）即 raise，禁止兜底。
🚫不参与 GPU"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)

  其中 δ_n = 1 固定，前 n-1 位遍历 ±1，共 2^(n-1) 项。与 Ryser 同阶但
  常数因子更小（无 (-1)^|S| 符号翻转）。

**Output**:
- 返回 ``complex`` 积和式值。

R03 合规: 输入非法（非方阵）即 raise，禁止兜底。
🚫不参与 GPU（R04）：纯 NumPy 实现。

学术诚信（R02，≥5 文献 URL"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)

  其中 δ_n = 1 固定，前 n-1 位遍历 ±1，共 2^(n-1) 项。与 Ryser 同阶但
  常数因子更小（无 (-1)^|S| 符号翻转）。

**Output**:
- 返回 ``complex`` 积和式值。

R03 合规: 输入非法（非方阵）即 raise，禁止兜底。
🚫不参与 GPU（R04）：纯 NumPy 实现。

学术诚信（R02，≥5 文献 URL 溯源）:
- Glynn, "The permanent of a square matrix", Eur. J. Comb. 31(7):1887-1891, 2010.
  URL"""矩阵积和式（permanent）模块 — Glynn-Gray 公式实现。

Input-Process-Output 三段式文档
================================

**Input**:
- ``matrix``: n×n 方阵（实数 / 复数 / list of list of [real, imag] / numpy 数组）。

**Process**:
- Glynn-Gray 公式计算矩阵积和式（permanent），复杂度 O(n·2^n)：

      Per(A) = (1/2^(n-1)) · Σ_{δ∈{-1,+1}^(n-1)} (Π_i δ_i) · Π_j (Σ_i δ_i · a_ij)

  其中 δ_n = 1 固定，前 n-1 位遍历 ±1，共 2^(n-1) 项。与 Ryser 同阶但
  常数因子更小（无 (-1)^|S| 符号翻转）。

**Output**:
- 返回 ``complex`` 积和式值。

R03 合规: 输入非法（非方阵）即 raise，禁止兜底。
🚫不参与 GPU（R04）：纯 NumPy 实现。

学术诚信（R02，≥5 文献 URL 溯源）:
- Glynn, "The permanent of a square matrix", Eur. J. Comb. 31(7):1887-1891, 2010.
  URL: https://doi.org/10.1016/j.ejc.2010.01.010
- Björklund, "Counting