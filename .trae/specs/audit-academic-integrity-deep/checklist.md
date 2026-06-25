# Checklist

## 数据来源验证
- [x] R01-R36 全部引用论文 DOI/URL 已逐条网络验证可达性
- [x] 不可达/内容不符的 URL 已标记并记录
- [x] 所有 URL 验证结果已记录到审核报告

## 固定参数清单
- [x] src/polaris/ 全部模块的固定物理常数已提取（c₀/q/k_B/ε₀/n_Si/n_SiO2 等）
- [x] 每个参数标注来源文献与 URL
- [x] 参数值在网络公开文献报告区间内
- [x] 参数清单已记录到审核报告

## 计算公式核对
- [x] 全部核心计算公式已提取（Yee 算法/CFL/PML/TLLM/Marcuse 弯曲损耗/Adjoint 梯度/REINFORCE/PPO 等）
- [x] 每条公式与原始文献核对一致
- [x] 公式推导来源清单已记录到审核报告

## 关键人物分析
- [x] 10-15 位关键作者已筛选
- [x] 每位作者网络检索所属机构/H-index/主要贡献/被引次数
- [x] 引用权威性已评估
- [x] 人物背景清单已记录到审核报告

## fall-back / 假数据终检
- [x] src/polaris/ 全量 grep 无 fallback/mock/fake/dummy/hardcode（GAN 术语除外）
- [x] fall-back 检查测试全部通过
- [x] 终检结果已记录

## 审核报告
- [x] docs/academic_integrity_audit.md 已生成，含四大清单（367 行，v1.0）
- [x] 审核记录已追加到操作记录.md
- [x] 审核中发现的问题已修复（如有）
- [x] 全部代码已提交并推送
