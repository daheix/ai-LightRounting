# 规则 R21：pyCopy 复刻品版本管理规范（强制）— 优化方向与验收

## 21.3 v2.0.x 能力优化方向

每个复刻品在 v1.0.0 完成后，按以下方向递增 v2.0.x：

| 复刻品 | v2.0.x 优化方向 |
|--------|----------------|
| pyCopySiPANN | 矩形波导解析解加速/耦合模理论精度提升/Monte Carlo 容差分析 |

## 21.4 验收流程

新增/升级复刻品必须执行：

1. **100% 行为对比**：`pytest tests/test_replica_<tool>.py -v` 全部通过
2. **门禁检查**：`python scripts/code_quality_gate.py` 0 警告 0 错误
3. **来源标注**：`__init__.py` 头部声明原仓库 URL/协议/commit
4. **版本登记**：更新 `VERSION.md` 和 `3dtool/pycopy/README.md` 清单
5. **操作记录**：在 `操作记录.md` 记录本次复刻/升级

## 21.5 禁止行为

- ❌ 禁止跳过 v1.0.0 直接做 v2.0.x（必须先 100% 复刻验证）
- ❌ 禁止 v2.0.x 改变 v1.0.0 的公开 API（破坏性变更须升 v3.0.0）
- ❌ 禁止复刻品与原工具行为不一致（浮点容差除外）
- ❌ 禁止不写 VERSION.md 就发布版本
- ❌ 禁止用"复刻"名义抄袭而不标注来源

来源: SemVer 语义化版本 https://semver.org/ | PyTorch 协议 https://pytorch.org/ (BSD-3-Clause) | SAX 协议 https://flaport.github.io/sax/ (Apache-2.0) | SiPANN 协议 https://sipann.readthedocs.io/ (MIT)
