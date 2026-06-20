"""pyCopyKLayout 与真实 klayout DRC 对比测试（规则 4.6）。

对比 src/polaris/sim/constraint_checker.py（pyCopyKLayout 复刻）与 KLayout
DRC 引擎的约束检查结果一致性，覆盖间距、重叠、最小宽度等 DRC 规则。

来源:
- KLayout: https://www.klayout.de/ (GPL-2.0)
- 复刻位置: src/polaris/sim/constraint_checker.py
- 复刻入口: 3dtool/pycopy/pyCopyKLayout/__init__.py
"""

from __future__ import annotations

from klayout.db import Box, Region  # noqa: E402
from pycopy.pyCopyKLayout import (  # noqa: E402
    check_min_width,
    check_overlap,
    check_spacing,
)


class TestSpacingCheck:
    """对比 pyCopyKLayout check_spacing 与 KLayout Region.separation_check。"""

    def test_spacing_ok(self):
        # Arrange — 两个矩形间距 20μm，最小间距要求 5μm（应无违规）
        placements = {
            "d1": {"x": 0, "y": 0, "w": 10, "h": 10},
            "d2": {"x": 30, "y": 0, "w": 10, "h": 10},
        }
        min_spacing = 5.0

        # Act
        violations = check_spacing(placements, min_spacing)
        r1 = Region(Box(0, 0, 10, 10))
        r2 = Region(Box(30, 0, 40, 10))
        klayout_violations = r1.separation_check(r2, int(min_spacing))

        # Assert — 两者均无违规
        assert len(violations) == 0
        assert klayout_violations.is_empty()

    def test_spacing_violation(self):
        # Arrange — 两个矩形间距 2μm，最小间距要求 5μm（应有违规）
        placements = {
            "d1": {"x": 0, "y": 0, "w": 10, "h": 10},
            "d2": {"x": 12, "y": 0, "w": 10, "h": 10},
        }
        min_spacing = 5.0

        # Act
        violations = check_spacing(placements, min_spacing)
        r1 = Region(Box(0, 0, 10, 10))
        r2 = Region(Box(12, 0, 22, 10))
        klayout_violations = r1.separation_check(r2, int(min_spacing))

        # Assert — 两者均检测到违规
        assert len(violations) > 0
        assert not klayout_violations.is_empty()


class TestOverlapCheck:
    """对比 pyCopyKLayout check_overlap 与 KLayout Region.overlap_check。"""

    def test_no_overlap(self):
        # Arrange — 两个不重叠的矩形
        placements = {
            "d1": {"x": 0, "y": 0, "w": 10, "h": 10},
            "d2": {"x": 20, "y": 0, "w": 10, "h": 10},
        }

        # Act
        violations = check_overlap(placements)
        r1 = Region(Box(0, 0, 10, 10))
        r2 = Region(Box(20, 0, 30, 10))
        klayout_overlap = r1 & r2  # 交集为空则无重叠

        # Assert
        assert len(violations) == 0
        assert klayout_overlap.is_empty()

    def test_overlap_detected(self):
        # Arrange — 两个重叠的矩形
        placements = {
            "d1": {"x": 0, "y": 0, "w": 10, "h": 10},
            "d2": {"x": 5, "y": 0, "w": 10, "h": 10},
        }

        # Act
        violations = check_overlap(placements)
        r1 = Region(Box(0, 0, 10, 10))
        r2 = Region(Box(5, 0, 15, 10))
        klayout_overlap = r1 & r2

        # Assert — 两者均检测到重叠
        assert len(violations) > 0
        assert not klayout_overlap.is_empty()


class TestMinWidthCheck:
    """对比 pyCopyKLayout check_min_width 与 KLayout Region.width_check。"""

    def test_width_ok(self):
        # Arrange — 波导宽度 0.5μm，最小宽度 0.4μm（应无违规）
        widths = {"net_1": 0.5}
        min_width = 0.4

        # Act
        violations = check_min_width(widths, min_width)
        # KLayout: 创建宽度为 500nm 的矩形，检查 width_check(400nm)
        r = Region(Box(0, 0, 500, 1000))
        klayout_violations = r.width_check(400)

        # Assert
        assert len(violations) == 0
        assert klayout_violations.is_empty()

    def test_width_violation(self):
        # Arrange — 波导宽度 0.3μm，最小宽度 0.4μm（应有违规）
        widths = {"net_1": 0.3}
        min_width = 0.4

        # Act
        violations = check_min_width(widths, min_width)
        # KLayout: 创建宽度为 300nm 的矩形，检查 width_check(400nm)
        r = Region(Box(0, 0, 300, 1000))
        klayout_violations = r.width_check(400)

        # Assert — pyCopyKLayout 检测到违规；KLayout 也检测到
        assert len(violations) > 0
        assert not klayout_violations.is_empty()
