"""R801-R850 回归测试：ibis_ami._parse_iv_data fall-back 清除验证。

R03 禁止 fall-back：rows 非空但全部无法解析为 (V, I) 对时，
必须 raise ValueError，禁止返回空数组掩盖数据损坏。

测试覆盖:
1. 正常数据解析（有效行 → 返回 NDArray）
2. 空输入（rows=[] → 返回空数组，合法）
3. 部分无效行（跳过无效行，返回有效数据）
4. 全部无效行（rows 非空但全无法解析 → raise ValueError，回归测试）

来源:
- IBIS v5.0 规范: https://ibis.org/ver5.0/ver5_0.txt
- R03 禁止 fall-back 规则
"""

from __future__ import annotations

import numpy as np
import pytest

from polaris.sim.ibis_ami import IBISParser


class TestParseIvDataR801:
    """R801-R850: _parse_iv_data fall-back 清除回归测试。"""

    def test_normal_data(self) -> None:
        """正常 IV 数据行解析为 (N, 2) 数组。"""
        rows = [["0.0", "0.0"], ["1.0", "0.01"], ["2.0", "0.02"]]
        result = IBISParser._parse_iv_data(rows)
        assert result.shape == (3, 2)
        assert result[0, 0] == pytest.approx(0.0)
        assert result[2, 1] == pytest.approx(0.02)

    def test_empty_rows_returns_empty_array(self) -> None:
        """空输入（rows=[]）返回空数组（合法 — 无数据段）。"""
        result = IBISParser._parse_iv_data([])
        assert result.shape == (0, 2)

    def test_partial_invalid_rows_skipped(self) -> None:
        """部分无效行被跳过，有效行正常解析。

        IBIS 文件中 IV 数据段可能包含 [typ]/[min]/[max] 子关键字行，
        跳过这些行是合法的数据清洗。
        """
        rows = [
            ["[typ]"],
            ["0.0", "0.0"],
            ["[min]"],
            ["1.0", "0.01"],
            ["bad", "data"],
            ["2.0", "0.02"],
        ]
        result = IBISParser._parse_iv_data(rows)
        assert result.shape == (3, 2)
        assert result[0, 0] == pytest.approx(0.0)
        assert result[2, 1] == pytest.approx(0.02)

    def test_all_invalid_rows_raises(self) -> None:
        """rows 非空但全部无法解析 → raise ValueError（R03 回归测试）。

        修复前：返回 np.zeros((0, 2))（静默 fall-back，掩盖数据损坏）。
        修复后：raise ValueError，明确告知数据格式错误。
        """
        rows = [["[typ]"], ["[min]"], ["[max]"], ["bad", "data"]]
        with pytest.raises(ValueError, match="全部无法解析"):
            IBISParser._parse_iv_data(rows)

    def test_single_invalid_row_raises(self) -> None:
        """单行且无效 → raise ValueError。"""
        rows = [["not_a_number", "also_bad"]]
        with pytest.raises(ValueError, match="全部无法解析"):
            IBISParser._parse_iv_data(rows)

    def test_single_element_rows_raises(self) -> None:
        """所有行只有一个元素（缺 I 列）→ raise ValueError。"""
        rows = [["0.0"], ["1.0"], ["2.0"]]
        with pytest.raises(ValueError, match="全部无法解析"):
            IBISParser._parse_iv_data(rows)
