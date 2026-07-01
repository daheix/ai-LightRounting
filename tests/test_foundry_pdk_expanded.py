"""R03 回归测试：foundry_pdk_expanded.py 的 fall-back 清除验证。

验证 FoundryPDKRegistry.get 对不存在的 foundry 抛 KeyError（R03 fail-fast），
以及源码不含 except:pass 的 fall-back 写法。

依据: R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from polaris.pdk.foundry_pdk_expanded import FoundryPDKRegistry


class TestFoundryPDKRegistryR03Compliance:
    """R03 合规：get 不存在时 raise，禁止 fall-back。"""

    def test_get_nonexistent_raises_keyerror(self) -> None:
        """get 不存在的 foundry 必须 raise KeyError（R03 fail-fast）。"""
        reg = FoundryPDKRegistry()
        with pytest.raises(KeyError, match="不存在"):
            reg.get("nonexistent")

    def test_get_existing_returns_spec(self) -> None:
        """get 已知 foundry 返回 FoundrySpec（amf 是内置 foundry）。"""
        reg = FoundryPDKRegistry()
        spec = reg.get("amf")
        assert spec is not None

    def test_no_except_pass_fallback(self) -> None:
        """R03 回归：源码不得包含 except:pass 的 fall-back 写法。

        验证 _test() 自测脚本中用 flag 模式断言异常，
        而非 try/except KeyError: pass 的 fall-back 写法。
        """
        src_file = Path(__file__).parent.parent / "src/polaris/pdk/foundry_pdk_expanded.py"
        src = src_file.read_text(encoding="utf-8")
        tree = ast.parse(src)
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                for stmt in node.body:
                    if isinstance(stmt, ast.Pass):
                        violations.append(node.lineno)
        assert not violations, (
            f"foundry_pdk_expanded 第 {violations} 行存在 except:pass fall-back（R03）"
        )
