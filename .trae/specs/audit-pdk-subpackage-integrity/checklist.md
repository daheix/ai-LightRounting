# Checklist

## 文件覆盖完整性
- [ ] 3.2.1 文件清单覆盖全部 46 个 .py 文件（顶层 25 + soi/ 6 + sin/ 5 + inp/ 6 + optodesigner 7）
- [ ] 每个文件记录：路径、行数、主要功能、文献 URL 数量、Source 溯源对象数量
- [ ] 按子目录组织（顶层 / soi/ / sin/ / inp/ / optodesigner_*）

## R02 学术诚信核查
- [ ] 每模块 docstring 文献 URL 数量统计（≥5 为合规）
- [ ] PDK 器件参数溯源清单（Si 折射率 3.477、SiO₂ 1.444、SiEPIC R_min 5μm、HyperLight wg_width 1.5μm、LIGENTEC AN800 min_bend 100μm、SiN TOC 2.4e-5/K 等）
- [ ] 14 个 foundry 平台 sources URL 溯源（每 foundry ≥2 公开来源）
- [ ] AWG crosstalk 公式溯源（Smit & Dam IEEE JQE 1996）
- [ ] ModelEncryptor 加密方案溯源（SHA-256 CTR + HMAC-SHA256 Encrypt-then-MAC）

## R03 禁止 fall-back 核查
- [ ] Grep except:pass 结果记录（无匹配=合规）
- [ ] 7 处 return None/return [] 逐一核实（process_nodes.py:532 / pcell.py:74,629 / gdsfactory_integration.py:412,445 / catalog.py:99,112）
- [ ] 区分"查询未命中语义"（合规）与"假数据兜底"（违规）
- [ ] gdsfactory_integration.py list_gdsfactory_pdks 返回 [] 的风格一致性观察

## R04 不参与 GPU 核查
- [ ] Grep CuPy/CUDA/ROCm 结果记录（无匹配=合规）

## R05 Bug 必修核查
- [ ] Grep TODO/FIXME/HACK/XXX 结果记录（无匹配=合规）

## Bug 清单
- [ ] #v3.3-PDK-1: process_nodes.py docstring 三处（行 282/339/541）"9 个"vs 实际 13 个 ProcessNode 不一致
- [ ] 其他发现的 Bug（如有）标注 Bug ID 与修复建议

## 报告格式
- [ ] 3.2.1 文件清单（按子目录组织）
- [ ] 3.2.2 算法清单（实现位置 + 来源文献 + 一致性）
- [ ] 3.2.3 公式清单（PDK 器件参数 + 物理公式 + 来源）
- [ ] 3.2.4 文献引用清单（≥5 URL/模块，R02 合规性）
- [ ] 3.2.5 Bug 清单（Bug ID + 位置 + 根因 + 修复建议，不实际修复）
- [ ] 3.2.6 完成度评估（覆盖度、合规度、成熟度）
- [ ] 3.2.7 代码-设计匹配性（器件参数 vs 设计文档/spec 一致性）
- [ ] 报告总行数 500-1000 行
- [ ] 全程不修改任何文件（纯只读）

## 数据真实性
- [ ] 所有数字真实可验证（文件行数、URL 数量、参数值均来自实际代码读取）
- [ ] 无造假数据（禁止凭印象填写数字）
