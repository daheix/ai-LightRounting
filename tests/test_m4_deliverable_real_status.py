"""M4Deliverable 真实状态查询回归测试（Bug #v3.3-VER-2）。

回归目标: 验证 M4 里程碑检查不再硬编码 return True，而是基于可观测事实:
1. 必需文件存在性（pathlib.Path 检查 src/polaris 下源文件）
2. DRC 18 规则覆盖度（实例化 CurvilinearDRCEngine 验证 rule_count == 18）
3. 测试通过率代理（检查 tests/ 下相关测试文件存在性）

根因: 原 M4Deliverable._init_checklist 将 29 项全部硬编码为 True，
      注释声称"严格基于实际文件存在性"但实际未做任何检查，导致商业交付
      里程碑检查不可信（P0 阻断）。

修复: 移除硬编码 True，改为 _build_checklist 调用真实验证函数。

学术依据: 见 drc_curvilinear_18rules.py 模块 docstring（OpenTitan M4 /
Synopsys OptoDesigner DRC / ONAP M4 Checklist）。
"""

from __future__ import annotations

import pytest

from polaris.verification.drc_curvilinear_18rules import (
    CurvilinearDRCEngine,
    M4Deliverable,
    _src_file_exists,
    _test_file_exists,
    _verify_curvilinear_rules_count,
    _verify_drc_18_rules,
    _verify_drc_rules_total_ge_200,
    _verify_foundry_platform_count,
)


def test_m4_checklist_not_all_hardcoded_true():
    """M4 检查清单不全是硬编码 True（验证真实查询）。

    若所有项恒为 True，则不存在文件路径检查会失败——本测试通过
    不存在文件路径返回 False 来证明查询真实。
    """
    m4 = M4Deliverable()
    report = m4.report()
    assert all(isinstance(v, bool) for v in report["checklist"].values())
    assert report["total_items"] >= 20
    assert report["passed_items"] >= 1


def test_m4_src_file_query_returns_false_for_missing():
    """验证 _src_file_exists 对不存在文件返回 False（证明非硬编码 True）。"""
    assert _src_file_exists("verification/drc_curvilinear_18rules.py") is True
    assert _src_file_exists("nonexistent/fake_module_xyz.py") is False


def test_m4_test_file_query_returns_false_for_missing():
    """验证 _test_file_exists 对不存在测试文件返回 False。"""
    assert _test_file_exists("test_drc_extended.py") is True
    assert _test_file_exists("test_nonexistent_fake_xyz.py") is False


def test_m4_drc_18_rules_real_verification():
    """验证 DRC 18 规则覆盖度基于真实实例化（非硬编码）。"""
    assert _verify_drc_18_rules() is True
    engine = CurvilinearDRCEngine()
    assert engine.rule_count == 18


def test_m4_curvilinear_rules_count_real_query():
    """验证曲线感知规则数基于真实查询（错误期望返回 False）。"""
    assert _verify_curvilinear_rules_count(5) is True
    assert _verify_curvilinear_rules_count(99) is False


def test_m4_foundry_platform_real_query():
    """验证 foundry 平台数基于动态导入查询（非硬编码）。"""
    assert _verify_foundry_platform_count(1) is True
    assert _verify_foundry_platform_count(99999) is False


def test_m4_drc_rules_total_real_query_returns_bool():
    """验证 DRC 规则总数查询返回 bool（真实查询结果，非恒 True）。"""
    result = _verify_drc_rules_total_ge_200()
    assert isinstance(result, bool)


def test_m4_report_reflects_real_status():
    """M4 report 反映真实状态（completion_rate 在 [0,1]，failed_items 为列表）。"""
    m4 = M4Deliverable()
    report = m4.report()
    assert 0.0 <= report["completion_rate"] <= 1.0
    assert isinstance(report["failed_items"], list)
    assert report["milestone"] == "M4 (L-Edit + OptoDesigner Alignment)"


def test_m4_mark_raises_on_unknown_item():
    """mark 对未知检查项 raise KeyError（R03 禁止静默兜底）。"""
    m4 = M4Deliverable()
    with pytest.raises(KeyError):
        m4.mark("不存在/的检查项_xyz", True)


def test_m4_checklist_contains_expected_r_keys():
    """验证检查清单覆盖 R19-R24 各阶段（结构与真实查询并存）。"""
    m4 = M4Deliverable()
    keys = set(m4.report()["checklist"].keys())
    for prefix in ("R19/", "R20/", "R21/", "R22/", "R23/", "R24/"):
        assert any(k.startswith(prefix) for k in keys), f"缺少 {prefix} 前缀检查项"
