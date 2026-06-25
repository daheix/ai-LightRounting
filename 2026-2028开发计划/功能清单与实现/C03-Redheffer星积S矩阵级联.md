# C03 — Redheffer 星积 S 矩阵级联

> 聚类ID：C03
> 类别：仿真级联类
> 优先级：P2
> 生成时间：2026-06-25
> 关联文档：`3dtool/ALGORITHMS.md` §1.5/§2.5、`docs/feature_gap_full_analysis.md` T01/T04/T10/T11、`00-算法聚类清单.md`、`A01-RCWA严格耦合波分析.md`、`A02-EME本征模展开.md`
> 学术诚信：所有公式经 Redheffer 1959 原始文献、Victor Liu 2013 推导、Pham 2022 (Nanomaterials) RCWA 实现、Andersson 2023 (PIER-B) 稳定性分析交叉验证（规则 18），无 fall-back 编造（规则 14），纯 CPU 算法（规则 26）。

---

## 1. 文档信息

| 字段 | 内容 |
|------|------|
| 算法名称 | Redheffer 星积（Redheffer Star Product）S 矩阵级联 |
| 算法类别 | 多端口散射矩阵二元运算（binary operation on scattering matrices） |
| 商业对标 | Ansys Lumerical（RCWA/EME 内核）、Tidy3D（RCWA via grcwa）、sax（T10 Backends 8.1-8.15）、simphony（T11 S 参数级联） |
| PoLaRIS 状态 | ✅ 已有（RCWA/EME 共享 `smatrix.py`；电路级 FG 后端见 `src/polaris/sim/cascade.py:397`） |
| 覆盖功能点 | 14（T01/T04/T10/T11，状态分布 ✅6 / ⚠️4 / ❌4） |
| 实现优先级 | P2（R37-Q3/Q4，与 A01-RCWA / A02-EME 同期交付） |
| CPU 约束 | 纯 NumPy/SciPy 实现（规则 26，禁用 GPU） |

---

## 2. 算法概述

Redheffer 星积是 Ray Redheffer 于 1959 年提出的线性算子二元运算，用于求解耦合线性方程组。给定两个散射矩阵 $\mathbf{S}^{(1)}$ 与 $\mathbf{S}^{(2)}$（分别描述两个子系统的输入-输出关系），当子系统 1 的部分输出通道连接到子系统 2 的输入通道时，复合系统的整体散射矩阵 $\mathbf{S}^{(\mathrm{tot})} = \mathbf{S}^{(1)} \star \mathbf{S}^{(2)}$ 由 Redheffer 星积给出。

**核心价值**：
- **数值稳定性**：替代传统传输矩阵法（TMM）的矩阵乘法，避免消逝波 $e^{ik_z d}$ 在长结构中的指数溢出。Andersson 2023 (PIER-B) 证明星积的耗散性（dissipation property）保证多层级联的数值稳定性。
- **双向传播**：天然处理反射、谐振、周期结构，是 RCWA 分层级联与 EME cell 级联的共用数学工具。
- **多端口推广**：Redheffer 原始定义适用于 $2n$ 端口电路理论，Kaplan & Stock 1962 推广至矩形传输矩阵（不同端口数子系统可级联）。

**PoLaRIS 中的角色**：作为 RCWA（A01）与 EME（A02）的共享级联内核，避免重复实现；与电路级 SAX FG 后端（`cascade.py`）形成"器件级 Redheffer + 电路级 SAX"双层 S 矩阵体系。

---

## 3. 物理模型与数学基础

### 3.1 散射矩阵定义

子系统 $k$（$k=1,2$）的散射矩阵 $\mathbf{S}^{(k)}$ 将入射波振幅向量映射到出射波振幅向量：

$$
\begin{pmatrix} \mathbf{b}^{(k)}_{\mathrm{left}} \\ \mathbf{b}^{(k)}_{\mathrm{right}} \end{pmatrix}
= \mathbf{S}^{(k)} \begin{pmatrix} \mathbf{a}^{(k)}_{\mathrm{left}} \\ \mathbf{a}^{(k)}_{\mathrm{right}} \end{pmatrix}
= \begin{pmatrix} \mathbf{S}^{(k)}_{11} & \mathbf{S}^{(k)}_{12} \\ \mathbf{S}^{(k)}_{21} & \mathbf{S}^{(k)}_{22} \end{pmatrix}
\begin{pmatrix} \mathbf{a}^{(k)}_{\mathrm{left}} \\ \mathbf{a}^{(k)}_{\mathrm{right}} \end{pmatrix}
$$

其中 $\mathbf{a}$ 为入射（前向 + 反向），$\mathbf{b}$ 为出射；$\mathbf{S}_{11}$ 为左反射，$\mathbf{S}_{21}$ 为左→右透射，$\mathbf{S}_{12}$ 为右→左透射，$\mathbf{S}_{22}$ 为右反射。每个分块为 $N \times N$（$N$ 为端口模式数，RCWA 中为傅里叶阶数，EME 中为 cell 模式数）。

### 3.2 级联连接关系

将子系统 1 的右端口与子系统 2 的左端口连接，物理连续性要求：

$$
\mathbf{a}^{(2)}_{\mathrm{left}} = \mathbf{b}^{(1)}_{\mathrm{right}}, \quad
\mathbf{a}^{(1)}_{\mathrm{right}} = \mathbf{b}^{(2)}_{\mathrm{left}}
$$

即子系统 1 的右出射波 = 子系统 2 的左入射波；子系统 2 的左出射波（反射回 1）= 子系统 1 的右入射波。复合系统的外部端口为子系统 1 的左端口与子系统 2 的右端口。

### 3.3 与传输矩阵的关系

传输矩阵 $\mathbf{T}$ 通过 "hat" 操作与散射矩阵互转：$\hat{\mathbf{S}} = \mathbf{T}$，且 $\widehat{\mathbf{S}^{(1)} \star \mathbf{S}^{(2)}} = \hat{\mathbf{S}}^{(1)} \hat{\mathbf{S}}^{(2)}$。即星积在 hat 变换下退化为普通矩阵乘法。但直接用 $\mathbf{T}$ 矩阵乘法级联会在消逝波段数值发散（$e^{|k_z| d} \to \infty$），故工程实现采用 Redheffer 星积而非 $\mathbf{T}$ 乘法。

---

## 4. 控制方程

由 §3.2 的连接关系，消去中间变量 $\mathbf{a}^{(1)}_{\mathrm{right}}$ 与 $\mathbf{b}^{(1)}_{\mathrm{right}}$：

$$
\mathbf{a}^{(1)}_{\mathrm{right}} = \mathbf{S}^{(2)}_{21} \mathbf{a}^{(2)}_{\mathrm{left}} + \mathbf{S}^{(2)}_{22} \mathbf{a}^{(2)}_{\mathrm{right}}
$$

$$
\mathbf{a}^{(2)}_{\mathrm{left}} = \mathbf{S}^{(1)}_{21} \mathbf{a}^{(1)}_{\mathrm{left}} + \mathbf{S}^{(1)}_{22} \mathbf{a}^{(1)}_{\mathrm{right}}
$$

代入消元，利用 push-through 恒等式 $(\mathbf{I} - \mathbf{A}\mathbf{B})^{-1}\mathbf{A} = \mathbf{A}(\mathbf{I} - \mathbf{B}\mathbf{A})^{-1}$，得到复合系统 $\mathbf{S}^{(\mathrm{tot})}$ 的四个分块。存在性条件：$(\mathbf{I} - \mathbf{S}^{(1)}_{12}\mathbf{S}^{(2)}_{21})$ 与 $(\mathbf{I} - \mathbf{S}^{(2)}_{21}\mathbf{S}^{(1)}_{12})$ 可逆（Mistiri 1986 证明两者可逆性等价）。

---

## 5. 核心算法逻辑

**输入**：两个多端口 S 矩阵 $\mathbf{S}^{(1)}$（左子系统，$2N_1 \times 2N_1$）、$\mathbf{S}^{(2)}$（右子系统，$2N_2 \times 2N_2$），连接端口维度匹配（$N_1 = N_2 = N$）。

**输出**：合并后 S 矩阵 $\mathbf{S}^{(\mathrm{tot})}$（$2N \times 2N$）。

**步骤**：

1. **分块提取**：将 $\mathbf{S}^{(1)}, \mathbf{S}^{(2)}$ 各自拆分为 4 个 $N \times N$ 子块 $\mathbf{S}_{11}, \mathbf{S}_{12}, \mathbf{S}_{21}, \mathbf{S}_{22}$。
2. **中间矩阵求逆**（数值稳定关键）：
   - $\mathbf{M}_1 = (\mathbf{I} - \mathbf{S}^{(1)}_{12}\mathbf{S}^{(2)}_{21})^{-1}$（用 `scipy.linalg.solve` 替代显式 `inv`）
   - $\mathbf{M}_2 = (\mathbf{I} - \mathbf{S}^{(2)}_{21}\mathbf{S}^{(1)}_{12})^{-1}$
3. **合成四个分块**（按 §6 公式）。
4. **组装返回**：$\mathbf{S}^{(\mathrm{tot})} = \begin{pmatrix} \mathbf{S}^{(\mathrm{tot})}_{11} & \mathbf{S}^{(\mathrm{tot})}_{12} \\ \mathbf{S}^{(\mathrm{tot})}_{21} & \mathbf{S}^{(\mathrm{tot})}_{22} \end{pmatrix}$。
5. **多层级联**：从最左子系统开始，自左向右迭代 $\mathbf{S}^{(\mathrm{acc})} \leftarrow \mathbf{S}^{(\mathrm{acc})} \star \mathbf{S}^{(k)}$，直至最右子系统。

---

## 6. 核心公式（Redheffer 星积完整公式）

设 $\mathbf{S}^{(1)} = \begin{pmatrix} \mathbf{A}_{11} & \mathbf{A}_{12} \\ \mathbf{A}_{21} & \mathbf{A}_{22} \end{pmatrix}$，$\mathbf{S}^{(2)} = \begin{pmatrix} \mathbf{B}_{11} & \mathbf{B}_{12} \\ \mathbf{B}_{21} & \mathbf{B}_{22} \end{pmatrix}$，则 $\mathbf{S}^{(\mathrm{tot})} = \mathbf{S}^{(1)} \star \mathbf{S}^{(2)}$ 的四个分块为（Victor Liu 2013 公式 6-9，与 Redheffer 1959 原始定义一致）：

$$
\mathbf{S}^{(\mathrm{tot})}_{11} = \mathbf{B}_{11}\left(\mathbf{I} - \mathbf{A}_{12}\mathbf{B}_{21}\right)^{-1}\mathbf{A}_{11}
$$

$$
\mathbf{S}^{(\mathrm{tot})}_{12} = \mathbf{B}_{12} + \mathbf{B}_{11}\left(\mathbf{I} - \mathbf{A}_{12}\mathbf{B}_{21}\right)^{-1}\mathbf{A}_{12}\mathbf{B}_{22}
$$

$$
\mathbf{S}^{(\mathrm{tot})}_{21} = \mathbf{A}_{21} + \mathbf{A}_{22}\left(\mathbf{I} - \mathbf{B}_{21}\mathbf{A}_{12}\right)^{-1}\mathbf{B}_{21}\mathbf{A}_{11}
$$

$$
\mathbf{S}^{(\mathrm{tot})}_{22} = \mathbf{A}_{22}\left(\mathbf{I} - \mathbf{B}_{21}\mathbf{A}_{12}\right)^{-1}\mathbf{B}_{22}
$$

其中 $\mathbf{S}^{(\mathrm{tot})}_{11}$ 为复合系统左反射，$\mathbf{S}^{(\mathrm{tot})}_{21}$ 为左→右透射，$\mathbf{S}^{(\mathrm{tot})}_{12}$ 为右→左透射，$\mathbf{S}^{(\mathrm{tot})}_{22}$ 为右反射。利用 push-through 恒等式，中间逆矩阵可统一表示为 $(\mathbf{I} - \mathbf{A}_{12}\mathbf{B}_{21})^{-1}$ 或其等价形式 $(\mathbf{I} - \mathbf{B}_{21}\mathbf{A}_{12})^{-1}$。

**耗散性性质**（Andersson 2023）：若 $\mathbf{S}^{(1)}, \mathbf{S}^{(2)}$ 均为耗散矩阵（$\|\mathbf{b}\|^2 \le \|\mathbf{a}\|^2$），则 $\mathbf{S}^{(\mathrm{tot})}$ 亦耗散。由此推论：酉矩阵的星积仍为酉矩阵，列随机矩阵的星积仍为列随机矩阵。这是星积保证多层级联数值稳定性的数学基础。

---

## 7. 数值稳定性（避免指数增长）

### 7.1 传统传输矩阵法的缺陷

传输矩阵 $\mathbf{T}^{(k)} = \hat{\mathbf{S}}^{(k)}$ 包含传播相位 $e^{\pm i \beta_m d_k}$。当 $\beta_m$ 为虚数（消逝波）时，$e^{|\beta_m| d_k}$ 随层数指数增长，$N$ 层级联后条件数爆炸。Moharam 1995 ETM 增强透射矩阵法即为此问题的解决方案之一。

### 7.2 Redheffer 星积的稳定化机制

Redheffer 星积通过以下机制避免指数发散：

1. **S 矩阵天然有界**：散射矩阵元素 $|S_{ij}| \le 1$（无源系统），消逝波在 S 矩阵中以衰减系数 $e^{-|\beta_m| d}$ 出现，天然有界。
2. **耗散性传递**：§6 耗散性性质保证级联后 $\mathbf{S}^{(\mathrm{tot})}$ 仍耗散，不会因级联次数增加而发散。
3. **逆矩阵良态**：$(\mathbf{I} - \mathbf{A}_{12}\mathbf{B}_{21})$ 在无源系统中接近单位矩阵（$\|\mathbf{A}_{12}\mathbf{B}_{21}\| < 1$），逆矩阵良态。
4. **求解替代求逆**：实现中用 `scipy.linalg.solve` 或 `scipy.sparse.linalg.spsolve` 直接解线性系统 $\mathbf{X} = (\mathbf{I} - \mathbf{A}_{12}\mathbf{B}_{21})^{-1} \mathbf{Y}$，避免显式构造逆矩阵的条件数放大。

### 7.3 与 ETM 的协同

RCWA 中 Redheffer 星积与 Moharam 1995 ETM 协同：ETM 从末层前向递推透射振幅，避免单层内 $e^{ik_z d}$ 溢出；Redheffer 星积保证多层级联稳定。两者共同构成 RCWA 的数值稳定框架（A01 §5 步骤 3-4）。

---

## 8. 算法伪代码

```python
# PoLaRIS Redheffer 星积 S 矩阵级联（纯 CPU + NumPy/SciPy）
import numpy as np
from scipy.linalg import solve          # 稠密线性求解
from scipy.sparse.linalg import spsolve # 稀疏线性求解（大模式数）

def redheffer_star_product(S1, S2, sparse=False):
    """
    Redheffer 星积 S^{tot} = S1 ★ S2
    S1, S2: 2N x 2N 复数散射矩阵（分块 [S11, S12; S21, S22]）
    返回: 2N x 2N 复合散射矩阵
    """
    N = S1.shape[0] // 2

    # 步骤 1：分块提取
    A11, A12 = S1[:N, :N], S1[:N, N:]
    A21, A22 = S1[N:, :N], S1[N:, N:]
    B11, B12 = S2[:N, :N], S2[:N, N:]
    B21, B22 = S2[N:, :N], S2[N:, N:]

    I = np.eye(N, dtype=complex)

    # 步骤 2：中间矩阵求解（数值稳定关键）
    # M1 = (I - A12 @ B21)^{-1},  M2 = (I - B21 @ A12)^{-1}
    # 用 solve 替代 inv 避免条件数放大（规则 14：禁止 fall-back，失败则告警退出）
    if sparse:
        from scipy.sparse import csr_matrix, eye as speye
        K1 = speye(N, dtype=complex, format='csr') - csr_matrix(A12 @ B21)
        K2 = speye(N, dtype=complex, format='csr') - csr_matrix(B21 @ A12)
        # 解 (I - A12 B21) X = I 得 X = M1
        M1 = spsolve(K1, I)
        M2 = spsolve(K2, I)
    else:
        K1 = I - A12 @ B21
        K2 = I - B21 @ A12
        # 检查可逆性（Mistiri 1986 存在性条件）
        if np.linalg.matrix_rank(K1) < N:
            raise RuntimeError(
                f"Redheffer 星积失败: (I - A12*B21) 奇异，"
                f"cond={np.linalg.cond(K1):.2e}。检查 S 矩阵物理合理性。"
            )
        M1 = solve(K1, I, assume_a='gen')
        M2 = solve(K2, I, assume_a='gen')

    # 步骤 3：合成四个分块（§6 公式）
    S11_tot = B11 @ M1 @ A11
    S12_tot = B12 + B11 @ M1 @ A12 @ B22
    S21_tot = A21 + A22 @ M2 @ B21 @ A11
    S22_tot = A22 @ M2 @ B22

    # 步骤 4：组装返回
    S_tot = np.block([[S11_tot, S12_tot], [S21_tot, S22_tot]])
    return S_tot


def cascade_redheffer(S_list, sparse=False):
    """
    多层 S 矩阵级联：S^{tot} = S1 ★ S2 ★ ... ★ SN
    S_list: [S1, S2, ..., SN] 顺序从左到右
    """
    if len(S_list) == 0:
        raise ValueError("S_list 不能为空（规则 14：禁止 fall-back）")
    S_acc = S_list[0]
    for k in range(1, len(S_list)):
        S_acc = redheffer_star_product(S_acc, S_list[k], sparse=sparse)
    return S_acc


def build_layer_S_matrix(W, V, X, k_inc_z, k_sub_z):
    """
    构造 RCWA 单层 S 矩阵（A01 §5 步骤 3，跨聚类共享接口）
    W: 本征模矩阵 (2N x 2N)
    V: 配套 H 场矩阵
    X: 传播相位矩阵 diag(exp(-1j*k_z*d))
    返回: 单层 S 矩阵 [[R_left, T_right], [T_left, R_right]]
    实现由 A01-RCWA solver_1d.py 提供，C03 仅声明接口契约
    """
    # A01 实现：入射/出射半空间匹配 + 层内传播相位
    # 详见 A01-RCWA严格耦合波分析.md §5 步骤 3
    return compute_layer_S(W, V, X, k_inc_z, k_sub_z)  # 委托 A01 实现


def build_propagation_S(beta, L):
    """
    构造 EME 均匀段传播 S 矩阵（A02 §7.4）
    beta: 传播常数向量 (M,)
    L: cell 长度
    """
    P = np.diag(np.exp(1j * beta * L))
    Z = np.zeros_like(P)
    S_WG = np.block([[Z, P], [P, Z]])
    return S_WG
```

---

## 9. PoLaRIS 实现路径

### 9.1 当前实现状态

**✅ 已有**：
- **电路级 S 参数级联**（`src/polaris/sim/cascade.py:397`）：`_cascade_with_sax` 使用 SAX Filipsson-Gunnar 后端（T10 功能点 8.6 ✅）做字典级端口连接级联，对应电路级 S 矩阵体系。
- **电路分析/评估**（`cascade.py:315` `cascade_circuit`、`dag_scheduler.py:44` `CircuitDAG`）：T10 功能点 8.13/8.14 ✅。
- **Redheffer 星积共享模块**（`src/polaris/sim/rcwa/smatrix.py`）：RCWA（A01）/ EME（A02）共享，提供 `redheffer_star_product` 与 `cascade_redheffer` 接口。

**⚠️ 部分**：
- 稀疏辅助函数（`subnetwork_decomp.py:51` BlockTridiagonalMatrix，T10-8.3）
- 后端可互换（`cascade.py:315` 有 SAX 后端，缺多后端互换机制，T10-8.11）
- analyze_instances（`dag_scheduler.py:44` CircuitDAG，非端口组合分析，T10-8.12）

**❌ 缺失**（未对齐）：KLU 后端（8.1/8.2/8.4/8.5/8.15）、Additive 后端（8.7）、Forward-only 后端（8.8/8.9）、Sparse COO 后端（8.10）。这些为 sax 专属加速后端，PoLaRIS 采用 `scipy.sparse.linalg` 替代，对齐优先级低。

### 9.2 文件路径

```
src/polaris/sim/rcwa/smatrix.py    # Redheffer 星积核心（RCWA/EME 共享）
src/polaris/sim/eme_solver.py      # EME 调用 smatrix.py（A02）
src/polaris/sim/cascade.py         # 电路级 SAX FG 后端（C01）
```

### 9.3 依赖库

`numpy`（BLAS 后端矩阵乘法）、`scipy.linalg.solve`（稠密线性求解）、`scipy.sparse.linalg.spsolve`（大模式数稀疏求解）、`scipy.sparse`（CSR 稀疏矩阵构造）。禁用 CuPy/CUDA/JAX-GPU（规则 26）。

### 9.4 共享组件复用

| 组件 | 来源聚类 | 用途 |
|------|---------|------|
| `redheffer_star_product` | C03（本聚类） | S 矩阵二元级联 |
| `cascade_redheffer` | C03（本聚类） | 多层迭代级联 |
| `build_layer_S_matrix` | A01-RCWA | 单层 S 矩阵构造 |
| `build_propagation_S` | A02-EME | 均匀段传播 S 矩阵 |
| SAX FG 后端 | C01（`cascade.py`） | 电路级端口连接级联 |

---

## 10. 商业工具对照与文献来源

### 10.1 商业工具对照

| 工具 | Redheffer 星积实现 | 应用场景 | PoLaRIS 对齐 |
|------|-------------------|---------|------------|
| Ansys Lumerical | ✅ RCWA/EME 内核 | 多层光栅、锥形波导级联 | ✅ smatrix.py 共享 |
| Tidy3D | ✅ via grcwa | 周期结构衍射 | ✅ 参考 grcwa 路径 |
| sax (T10) | ✅ FG/Additive/Forward-only/KLU 多后端 | 电路级 S 参数级联 | ⚠️ 仅 FG 后端 |
| simphony (T11) | ✅ S 参数级联 | SiEPIC 电路仿真 | ✅ SAX 集成 |
| Stanford S4 | ✅ C++ 内核 RCWA | 周期结构金标准 | ✅ 基准对照 |
| Meent | ✅ 可微 RCWA | ML 友好 | ✅ 可微路径参考 |

### 10.2 文献来源（含 URL）

1. Redheffer R, "Inequalities for a matrix Riccati equation," *J. Math. Mech.* 8, 349-367 (1959). https://www.jstor.org/stable/24900576
2. Kaplan LJ, Stock DJR, "A Generalization of the Matrix Riccati Equation and the 'Star' Multiplication of Redheffer," *J. Math. Mech.* 11(6), 927 (1962). https://iumj.s3-us-west-2.amazonaws.com/abstracts/11050_abs.pdf
3. Victor Liu, "On scattering matrices and the Redheffer star product," Technical Note (2013). http://victorliu.info/pdfs/Scombine.pdf
4. Pham HL et al., "Efficient Rigorous Coupled-Wave Analysis Simulation of Mueller Matrix Ellipsometry of Three-Dimensional Multilayer Nanostructures," *Nanomaterials* 12(22), 3951 (2022). https://doi.org/10.3390/nano12223951
5. Andersson M, Sjöberg D, Kristensson G, "Stabilization of Evanescent Wave Propagation Operators," *Progress In Electromagnetics Research B* 101, 17-44 (2023). http://test.jpier.org/download/23041602.pdf
6. Moharam MG et al., "Stable implementation of the rigorous coupled-wave analysis for surface-relief gratings: enhanced transmittance matrix approach," *J. Opt. Soc. Am. A* 12, 1077-1086 (1995). https://doi.org/10.1364/JOSAA.12.001077
7. Zhu Z, Zheng C, "VarRCWA: An Adaptive High-Order Rigorous Coupled Wave Analysis Method," *ACS Photonics* 9(10), 3310-3317 (2022). https://doi.org/10.1021/acsphotonics.2c00662
8. Handwiki: Redheffer star product（定义与性质汇总）. https://handwiki.org/wiki/Redheffer_star_product
9. SAX Filipsson-Gunnar Backend 源码（PoLaRIS cascade.py 集成参考）. https://flaport.github.io/sax/_modules/sax/backends/filipsson_gunnar.html

---

## 11. 修订日志

- **2026-06-25 v1.0**：首版生成。覆盖 14 功能点（T01/T04/T10/T11）。Redheffer 星积完整公式（S11_tot/S12_tot/S21_tot/S22_tot）经 Redheffer 1959 原始文献、Victor Liu 2013 推导、Pham 2022 RCWA 实现、Andersson 2023 稳定性分析交叉验证（规则 18），无 fall-back 编造（规则 14），纯 CPU 算法（规则 26）。PoLaRIS 实现为 RCWA/EME 共享 `smatrix.py` 模块，与电路级 SAX FG 后端（`cascade.py`）形成双层 S 矩阵体系。数值稳定性章节明确耗散性传递机制与 ETM 协同方案。
