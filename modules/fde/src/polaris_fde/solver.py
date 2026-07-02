""""""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt +"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}],"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.c"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eig"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eig"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    """"2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1]"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx²"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / ("""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n -"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i *"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx,"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float ="""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1."""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um:"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes:"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            -"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um,"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/S"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanc"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 >"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f""""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    # 仿真窗口: width + 2"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    # 仿真窗口: width + 2*pad（x 方向），height + 2"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    # 仿真窗口: width + 2*pad（x 方向），height + 2*pad（y 方向）
    window_x_um = width_um + 2.0 * pad_um
    window_y_um = height_um"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    # 仿真窗口: width + 2*pad（x 方向），height + 2*pad（y 方向）
    window_x_um = width_um + 2.0 * pad_um
    window_y_um = height_um + 2.0 * pad_um
    nx = int(round(window_x_um / dx_um"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    # 仿真窗口: width + 2*pad（x 方向），height + 2*pad（y 方向）
    window_x_um = width_um + 2.0 * pad_um
    window_y_um = height_um + 2.0 * pad_um
    nx = int(round(window_x_um / dx_um))
    ny = int(round(window_y_um / dx_um))
    if nx < 5 or"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    # 仿真窗口: width + 2*pad（x 方向），height + 2*pad（y 方向）
    window_x_um = width_um + 2.0 * pad_um
    window_y_um = height_um + 2.0 * pad_um
    nx = int(round(window_x_um / dx_um))
    ny = int(round(window_y_um / dx_um))
    if nx < 5 or ny < 5:
        raise ValueError(
            f"网格过小 nx={nx} ny"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    # 仿真窗口: width + 2*pad（x 方向），height + 2*pad（y 方向）
    window_x_um = width_um + 2.0 * pad_um
    window_y_um = height_um + 2.0 * pad_um
    nx = int(round(window_x_um / dx_um))
    ny = int(round(window_y_um / dx_um))
    if nx < 5 or ny < 5:
        raise ValueError(
            f"网格过小 nx={nx} ny={ny}，请减小 dx_um 或增大 pad_um"
        )
    # 实际"""2D 有限差分本征模求解器（polaris-fde 内核）。

求解标量 Helmholtz 方程::

    ∇²E(x,y) + k₀² n²(x,y) E(x,y) = β² E(x,y)

其中 k₀ = 2π/λ 为真空波数，β = k₀ n_eff 为传播常数。
导模条件: k₀² n_clad² < β² < k₀² n_core²（即 n_clad < n_eff < n_core）。

## 离散化（5 点拉普拉斯，Dirichlet 边界 E=0）

对内部点 (i, j)::

    (E[i+1,j] + E[i-1,j] + E[i,j+1] + E[i,j-1] - 4E[i,j]) / dx²
    + k₀² n²[i,j] E[i,j] = β² E[i,j]

构建稀疏矩阵 M = L_5pt + diag(k₀²n²)，求最大代数特征值（β²）。
scipy.sparse.linalg.eigsh(M, k=n_modes, which='LA')。

## Input / Process / Output

- I: width_um / height_um / wavelength_um / n_core / n_clad / n_modes / dx_um / pad_um
- P: 构建 2D 折射率分布 → 5 点拉普拉斯稀疏矩阵 → ARPACK Lanczos 求解
- O: dict{modes: [{neff, field_2d, beta}], n_modes, wavelength_um, grid_info}

## 来源（R02 学术诚信，≥5 个文献 URL）
- Smit & van Dam 1996 IEEE/OSA JLT https://opg.optica.org/jlt/abstract.cfm?uri=jlt-14-7-1746
- Silvester & Ferrari 1996 Cambridge（FD/FEM 本征模求解）
- Soref 1993 IEEE JQE https://ieeexplore.ieee.org/document/1148303
- scipy.sparse.linalg.eigsh https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html
- Lumerical MODE FDE https://optics.ansys.com/hc/en-us/articles/360034902413
- NIST CODATA 2018 https://physics.nist.gov/cuu/Constants/
- Bogaerts 2012 Laser Photonics Rev https://onlinelibrary.wiley.com/doi/10.1002/lpor.201100017
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

__all__ = [
    "solve_modes",
    "build_index_profile",
    "build_laplacian_operator",
    "C0",
]

# 物理常量（NIST CODATA 2018，真空光速 m/s）
# 来源: https://physics.nist.gov/cuu/Constants/
C0: float = 299_792_458.0


def build_index_profile(
    nx: int, ny: int,
    core_x: tuple[int, int], core_y: tuple[int, int],
    n_core: float, n_clad: float,
) -> np.ndarray:
    """构建 2D 折射率分布（矩形芯 + 包层）。

    Args:
        nx, ny: 网格点数。
        core_x, core_y: 芯区在 x/y 方向的索引范围 [start, end)。
        n_core: 芯区折射率（如 Si 3.476）。
        n_clad: 包层折射率（如 SiO2 1.444）。

    Returns:
        ndarray (nx, ny): 折射率分布。

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    x0, x1 = core_x
    y0, y1 = core_y
    if not (0 <= x0 < x1 <= nx and 0 <= y0 < y1 <= ny):
        raise ValueError(
            f"芯区范围非法: x=[{x0},{x1}) y=[{y0},{y1}) 网格 {nx}×{ny}"
        )
    n = np.full((nx, ny), n_clad, dtype=np.float64)
    n[x0:x1, y0:y1] = n_core
    return n


def build_laplacian_operator(nx: int, ny: int, dx: float, dy: float) -> sparse.csr_matrix:
    """构建 5 点拉普拉斯稀疏矩阵 L（Dirichlet 边界 E=0）。

    离散化: L[i,i] = -2(1/dx² + 1/dy²)
            L[i, i±1] = 1/dy²
            L[i, i±nx] = 1/dx²

    Args:
        nx, ny: 网格点数。
        dx, dy: 网格步长（μm）。

    Returns:
        scipy.sparse.csr_matrix (nx*ny, nx*ny): 拉普拉斯算子。

    Raises:
        ValueError: 参数非法。
    """
    if nx < 3 or ny < 3:
        raise ValueError(f"网格过小 nx={nx} ny={ny}，须 >= 3")
    if dx <= 0 or dy <= 0:
        raise ValueError(f"步长须 > 0: dx={dx} dy={dy}")

    n = nx * ny
    inv_dx2 = 1.0 / (dx * dx)
    inv_dy2 = 1.0 / (dy * dy)
    diag_main = -2.0 * (inv_dx2 + inv_dy2)

    # 主对角线
    main_diag = np.full(n, diag_main, dtype=np.float64)
    # ±1 邻居（y 方向，跨行不跨）
    off_y = np.full(n - 1, inv_dy2, dtype=np.float64)
    # 边界处清零（Dirichlet）
    for i in range(1, ny):
        off_y[i * nx - 1] = 0.0
    # ±nx 邻居（x 方向）
    off_x = np.full(n - nx, inv_dx2, dtype=np.float64)

    L = sparse.diags(
        [off_x, off_y, main_diag, off_y, off_x],
        [-nx, -1, 0, 1, nx],
        format="csr",
        dtype=np.float64,
    )
    return L


def solve_modes(
    width_um: float = 0.5,
    height_um: float = 0.22,
    wavelength_um: float = 1.55,
    n_core: float = 3.476,
    n_clad: float = 1.444,
    n_modes: int = 4,
    dx_um: float = 0.025,
    pad_um: float = 1.0,
) -> dict:
    """2D 有限差分本征模求解器。

    计算矩形波导（n_core 芯 / n_clad 包层）的导模：有效折射率 neff 与模场分布。

    Args:
        width_um: 波导芯宽度（μm）。
        height_um: 波导芯高度（μm）。
        wavelength_um: 真空波长（μm）。
        n_core: 芯区折射率（Si 默认 3.476，Soref 1993）。
        n_clad: 包层折射率（SiO2 默认 1.444，Soref 1993）。
        n_modes: 求解的模式数。
        dx_um: 网格步长（μm）。
        pad_um: 包层 padding 厚度（μm，每侧）。

    Returns:
        dict: {modes, n_modes, wavelength_um, grid_info}
            - modes: list[{neff, beta, field_2d}]（按 neff 降序）
            - n_modes: 实际返回的导模数（滤除辐射模）
            - grid_info: {nx, ny, dx_um, dy_um, window_um}

    Raises:
        ValueError: 参数非法（R03 禁止 fall-back）。
        RuntimeError: 特征值求解失败或结果含 NaN（R03 禁止 fall-back）。

    来源:
        - Smit & van Dam 1996 IEEE/OSA JLT
        - Silvester & Ferrari 1996 Cambridge
        - Soref 1993 IEEE JQE（Si/SiO2 折射率）
        - scipy.sparse.linalg.eigsh（ARPACK Lanczos）
    """
    # ---- 参数校验（R03 禁止 fall-back） ----
    if width_um <= 0:
        raise ValueError(f"width_um 须 > 0，得到 {width_um}")
    if height_um <= 0:
        raise ValueError(f"height_um 须 > 0，得到 {height_um}")
    if wavelength_um <= 0:
        raise ValueError(f"wavelength_um 须 > 0，得到 {wavelength_um}")
    if n_core <= 0 or n_clad <= 0:
        raise ValueError(f"折射率须 > 0: n_core={n_core} n_clad={n_clad}")
    if n_core <= n_clad:
        raise ValueError(
            f"n_core ({n_core}) 须 > n_clad ({n_clad})，否则无导模"
        )
    if n_modes < 1:
        raise ValueError(f"n_modes 须 >= 1，得到 {n_modes}")
    if dx_um <= 0:
        raise ValueError(f"dx_um 须 > 0，得到 {dx_um}")
    if dx_um >= width_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < width_um ({width_um})，否则芯区无网格点"
        )
    if dx_um >= height_um:
        raise ValueError(
            f"dx_um ({dx_um}) 须 < height_um ({height_um})，否则芯区无网格点"
        )
    if pad_um <= 0:
        raise ValueError(f"pad_um 须 > 0，得到 {pad_um}")

    # ---- 构建网格 ----
    # 仿真窗口: width + 2*pad（x 方向），height + 2*pad（y 方向）
    window_x_um = width_um + 2.0 * pad_um
    window_y_um = height_um + 2.0 * pad_um
    nx = int(round(window_x_um / dx_um))
    ny = int(round(window_y_um / dx_um))
    if nx < 5 or ny < 5:
        raise ValueError(
            f"网格过小 nx={nx} ny={ny}，请减小 dx_um 或增大 pad_um"
        )
    # 实际步长（避免 round 误差）
    dx