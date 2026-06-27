# Checklist

## Task 1: fall-back/假数据扫描
- [ ] 全量 grep except:pass / return None / return [] / TODO / FIXME / HACK 完成
- [ ] 每个匹配项核查为真实 fall-back 还是边界处理
- [ ] 真实 fall-back 全部修复（R03/R05）

## Task 2: 物理常数审核
- [ ] 所有硬编码物理常数已提取
- [ ] 来源核查（CODATA 2018 / 论文 / 开源仓库）
- [ ] 核心公式实现正确性已审核

## Task 3: 文献引用审核
- [ ] 所有 docstring 文献 URL 已提取
- [ ] 作者/年份/标题一致性已核查
- [ ] 可疑/编造引用已标记

## Task 4: 算法实现审核
- [ ] FDTD（Yee/CPML/TFSF/Drude）已审核
- [ ] EME（模式/重叠/Redheffer）已审核
- [ ] FDE（Arnoldi/TE-TM）已审核
- [ ] RCWA（傅里叶/层矩阵）已审核
- [ ] BPM（ADI/Crank-Nicolson）已审核

## Task 5: 代码-文档一致性
- [ ] 设计文档模块清单已读取
- [ ] 实际文件已对照
- [ ] 分歧已记录并网络检索评价

## Task 6: 质量门禁
- [ ] 文件行数 ≤800 已扫描
- [ ] 函数行数 ≤80 已扫描
- [ ] 圈复杂度 ≤15 已扫描

## Task 7: 网络检索
- [ ] 分歧点已检索权威资源
- [ ] 最优结果已保留并记录

## Task 8: 审核报告
- [ ] 20260627-mvp技术诚信学术审核.md 已生成
- [ ] 包含全部审核维度结论
- [ ] Bug 清单与修复状态已记录

## Task 9: 提交
- [ ] Bug 已修复
- [ ] 代码已提交合并 main
- [ ] 操作记录已追加
