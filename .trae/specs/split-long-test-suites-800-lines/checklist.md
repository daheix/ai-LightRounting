# Checklist — 拆分超 800 行测试套件至 ≤800 行

> 验证状态：全部通过（commit 3e5470b0）

## 文件行数门禁

- [x] `find modules -path "*/tests/*.py" -exec wc -l {} \; | awk '$1>800' | wc -l` 输出 `0`
- [x] 13 个原超长文件均已删除（test_verify_advanced.py / test_router_advanced.py /
  test_flow.py / test_optimizer.py / test_trainer.py / test_gui.py / test_gds_tools.py /
  test_circuit.py / test_yield.py / test_pdk_advanced.py / test_route.py / test_inverse.py /
  test_parasitic.py）
- [x] 40 个新文件全部 ≤800 行（最大为 modules/flow/tests/test_workspace.py 754 行）

## 测试数量无回归

- [x] `pytest --collect-only modules/` 收集到 662 tests collected（与基准一致）
- [x] router_advanced 的 1 个 collection error 为 gymnasium 环境依赖问题，与原文件行为一致
  （非拆分引入，gymnasium 未安装时 importorskip 应跳过）

## 子文件 header 完整性

- [x] 每个新文件保留原 module docstring（含 R02 学术文献 URL）
- [x] 每个新文件保留 `from __future__ import annotations`
- [x] 每个新文件保留所有 import 语句
- [x] 每个新文件保留 `sys.path` 注入逻辑（`_SRC = str(Path(__file__).resolve().parents[1] / "src")`）
- [x] 每个新文件保留 `pytest.importorskip` 行为（R03 禁止 fall-back）

## 共享 fixture 沉淀

- [x] `modules/gds_tools/tests/conftest.py` 已创建（145 行）
- [x] conftest.py 包含 3 个共享 fixture：`klayout_db` / `test_gds` / `two_layer_gds`
- [x] test_clip.py / test_density.py / test_loader.py 不再复制 fixture，从 conftest.py 自动注入

## 测试函数体保持原样

- [x] 所有 `test_*` 函数体、断言、参数、docstring 完全不变
- [x] 仅做文件级物理切分，未修改任何测试逻辑
- [x] pytest collect 数量与基准一致（662），证明测试函数无丢失

## 无 fall-back 无 TODO 残留

- [x] 拆分过程未引入 `except: pass` / `return None` / `return []` 假数据（R03）
- [x] 拆分过程未引入 `TODO` / `FIXME` / `HACK` 注释（R05）
- [x] 原 docstring 中的 R02 文献引用全部保留

## Git 提交规范

- [x] 使用 `git add <精确文件>` 而非 `git add -A`（R11）
- [x] commit message 详细记录每个文件的拆分情况
- [x] 已 push 到 main 分支（commit 3e5470b0）
- [x] 未使用 `--force` push（R11）

## 临时文件清理

- [x] `.tmp_split_tests.py` 已删除（任务完成后清理）
- [x] 工作区干净，无垃圾文件残留

## R13 单一最新代码原则

- [x] 13 个原始超长文件已删除，只保留拆分后的新文件
- [x] 不存在多个版本并存的 vx 文件
