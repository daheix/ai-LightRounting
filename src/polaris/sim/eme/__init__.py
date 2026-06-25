"""sim/eme 包：EME 本征模展开求解器（A02 聚类，P0 频域全波双向传播方法）。

按 A02-EME 算法文档实现（Gallagher & Felici 2003 + Lumerical EME + SimWorks EME）：
- 双向本征模展开（前向/后向波），天然处理反射、谐振、周期结构
- cell 沿 z 切分，每 cell 中心调用 FDE 求本地模（A04 共享内核，零成本复用）
- 界面 S 矩阵：切向场连续 + 模式重叠积分（A02 §7.3）
- 传播 S 矩阵：均匀段相位累积 P = diag(exp(i·β·L))（A02 §7.4）
- Redheffer 星积级联（C03 共享内核，避免消逝波指数发散）
- Analysis 模式：cell 长度可任意扫描无需重算模式（Lumerical EME Propagate）

子模块：
- overlap.py    : 重叠积分矩阵 M_E / M_H（einsum 向量化，禁止循环）
- interface.py  : 界面 S 矩阵（切向场连续 + 正交投影）
- propagation.py: 传播 S 矩阵（均匀段相位累积）
- solver.py     : EmeCell/EmeConfig/EmeResult/EmeSolver/solve_eme 主体

文献来源（≥5，规则 18 学术诚信）：
1. Gallagher & Felici 2003 SPIE 4987, 69-82（EME Pros and Cons）—
   https://doi.org/10.1117/12.478061
2. Ansys Lumerical MODE-EME solver introduction —
   https://optics.ansys.com/hc/en-us/articles/360034396614
3. SimWorks Eigenmode Expansion (EME) Solver —
   https://www.emsimworks.com/en/solver/EME
4. EMEpy — Open-source eigenmode expansion solver in Python（BYUCamachoLab）—
   https://emepy.readthedocs.io/en/stable/index.html
5. Liu & Fan 2012 S4 CPC 183, 2233 —
   https://web.stanford.edu/group/fan/S4/
6. Photon Design FIMMPROP EME paper —
   https://photond.com/assets/files/FIMMWAVE/PW03_eme_paper.pdf
7. Oktay & Magden 2024 arXiv:2407.09847 —
   https://arxiv.org/abs/2407.09847

规则依据：project_rules.md 规则 14（禁止 fall-back）/规则 18（学术诚信）
/规则 26（GPU 不参与，纯 NumPy）
"""

from polaris.sim.eme.interface import build_interface_smatrix
from polaris.sim.eme.overlap import overlap_matrix
from polaris.sim.eme.propagation import build_propagation_smatrix
from polaris.sim.eme.solver import (
    EmeCell,
    EmeConfig,
    EmeResult,
    EmeSolver,
    solve_eme,
)

__all__ = [
    "overlap_matrix",
    "build_interface_smatrix",
    "build_propagation_smatrix",
    "EmeCell",
    "EmeConfig",
    "EmeResult",
    "EmeSolver",
    "solve_eme",
]
