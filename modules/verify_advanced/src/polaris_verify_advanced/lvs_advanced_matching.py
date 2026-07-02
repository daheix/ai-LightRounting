"""LVS 进阶器件"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
-"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/S"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs_advanced_types import (
    DeviceMatchResult,
    ParamMismatch,
    ToleranceSpec,
)


def match_devices_with_tolerance(
    reference: Extracted"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs_advanced_types import (
    DeviceMatchResult,
    ParamMismatch,
    ToleranceSpec,
)


def match_devices_with_tolerance(
    reference: ExtractedNetlist | dict[str, dict[str, float]],
    extracted: ExtractedNetlist | dict[str, dict[str, float]],
    tolerances"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs_advanced_types import (
    DeviceMatchResult,
    ParamMismatch,
    ToleranceSpec,
)


def match_devices_with_tolerance(
    reference: ExtractedNetlist | dict[str, dict[str, float]],
    extracted: ExtractedNetlist | dict[str, dict[str, float]],
    tolerances: dict[str, ToleranceSpec] | None = None,
) -> DeviceMatchResult:
    """带容差的器件参数匹配（R186"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs_advanced_types import (
    DeviceMatchResult,
    ParamMismatch,
    ToleranceSpec,
)


def match_devices_with_tolerance(
    reference: ExtractedNetlist | dict[str, dict[str, float]],
    extracted: ExtractedNetlist | dict[str, dict[str, float]],
    tolerances: dict[str, ToleranceSpec] | None = None,
) -> DeviceMatchResult:
    """带容差的器件参数匹配（R186）。

    对标 KLayout LVS tolerance 与 Calibre nmLVS TOLERANCE 规格。

    匹配规则：
    1"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs_advanced_types import (
    DeviceMatchResult,
    ParamMismatch,
    ToleranceSpec,
)


def match_devices_with_tolerance(
    reference: ExtractedNetlist | dict[str, dict[str, float]],
    extracted: ExtractedNetlist | dict[str, dict[str, float]],
    tolerances: dict[str, ToleranceSpec] | None = None,
) -> DeviceMatchResult:
    """带容差的器件参数匹配（R186）。

    对标 KLayout LVS tolerance 与 Calibre nmLVS TOLERANCE 规格。

    匹配规则：
    1. 器件名相同视为候选匹配对
    2. 对每个参数，偏差 = |ref - ext|
    3."""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs_advanced_types import (
    DeviceMatchResult,
    ParamMismatch,
    ToleranceSpec,
)


def match_devices_with_tolerance(
    reference: ExtractedNetlist | dict[str, dict[str, float]],
    extracted: ExtractedNetlist | dict[str, dict[str, float]],
    tolerances: dict[str, ToleranceSpec] | None = None,
) -> DeviceMatchResult:
    """带容差的器件参数匹配（R186）。

    对标 KLayout LVS tolerance 与 Calibre nmLVS TOLERANCE 规格。

    匹配规则：
    1. 器件名相同视为候选匹配对
    2. 对每个参数，偏差 = |ref - ext|
    3. 允许偏差 = abs_tol + rel_tol × |ref|（KLayout 公式）
"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs_advanced_types import (
    DeviceMatchResult,
    ParamMismatch,
    ToleranceSpec,
)


def match_devices_with_tolerance(
    reference: ExtractedNetlist | dict[str, dict[str, float]],
    extracted: ExtractedNetlist | dict[str, dict[str, float]],
    tolerances: dict[str, ToleranceSpec] | None = None,
) -> DeviceMatchResult:
    """带容差的器件参数匹配（R186）。

    对标 KLayout LVS tolerance 与 Calibre nmLVS TOLERANCE 规格。

    匹配规则：
    1. 器件名相同视为候选匹配对
    2. 对每个参数，偏差 = |ref - ext|
    3. 允许偏差 = abs_tol + rel_tol × |ref|（KLayout 公式）
    4. 若所有参数偏差 ≤ 允许偏差 → 匹配成功
"""LVS 进阶器件匹配增强（R186，从 v4 polaris.sim.lvs_advanced_matching 迁移）。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS tolerance: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- KLayout LVS Netter tolerance: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
- Calibre nmLVS TOLERANCE: https://eda.sw.siemens.com/en-US/calibre/
- Calibre LVS Circuit Comparison: https://blog.csdn.net/u013620135/article/details/156394479
- SiEPIC EBeam PDK 参数验证: https://github.com/SiEPIC/SiEPIC_EBeam_PDK

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from ._types import ExtractedNetlist
from .lvs_advanced_types import (
    DeviceMatchResult,
    ParamMismatch,
    ToleranceSpec,
)


def match_devices_with_tolerance(
    reference: ExtractedNetlist | dict[str, dict[str, float]],
    extracted: ExtractedNetlist | dict[str, dict[str, float]],
    tolerances: dict[str, ToleranceSpec] | None = None,
) -> DeviceMatchResult:
    """带容差的器件参数匹配（R186）。

    对标 KLayout LVS tolerance 与 Calibre nmLVS TOLERANCE 规格。

    匹配规则：
    1. 器件名相同视为候选匹配对
    2. 对每个参数，偏差 = |ref - ext|
    3. 允许偏差 = abs_tol + rel_tol × |ref|（KLayout 公式）
    4. 若所有参数偏差 ≤ 允许偏差 → 匹配成功
    5. 否则记录参数偏差
    6. 参考有但版图无 → 缺失器件
    7