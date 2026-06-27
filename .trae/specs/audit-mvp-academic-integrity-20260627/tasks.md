# Tasks

- [ ] Task 1: 全量 fall-back/假数据/TODO 扫描
  - [ ] SubTask 1.1: grep 扫描 except:pass / return None / return [] / TODO / FIXME / HACK
  - [ ] SubTask 1.2: 核查每个匹配项是否为真实 fall-back（非边界处理）
  - [ ] SubTask 1.3: 修复真实 fall-back（R03/R05）

- [ ] Task 2: 物理常数与公式来源审核
  - [ ] SubTask 2.1: 扫描所有硬编码物理常数（光速/介电常数/磁导率等）
  - [ ] SubTask 2.2: 核查来源（CODATA 2018 / 论文 / 开源仓库）
  - [ ] SubTask 2.3: 审核核心公式（CFL/Yee/CPML/Redheffer/Drude ADE）

- [ ] Task 3: 文献引用真实性审核
  - [ ] SubTask 3.1: 提取所有 docstring 中的文献 URL
  - [ ] SubTask 3.2: 核查作者/年份/标题一致性
  - [ ] SubTask 3.3: 标记可疑/编造引用

- [ ] Task 4: 核心算法实现正确性审核
  - [ ] SubTask 4.1: FDTD（Yee leapfrog/CPML/TFSF/Drude ADE）
  - [ ] SubTask 4.2: EME（模式求解/重叠积分/Redheffer 星积）
  - [ ] SubTask 4.3: FDE（shift-invert Arnoldi/TE-TM 分离）
  - [ ] SubTask 4.4: RCWA（傅里叶展开/层矩阵）
  - [ ] SubTask 4.5: BPM（ADI/Crank-Nicolson）

- [ ] Task 5: 代码-设计文档一致性核查
  - [ ] SubTask 5.1: 读取 docs/设计文档.md 模块清单
  - [ ] SubTask 5.2: 对照 src/polaris/ 实际文件
  - [ ] SubTask 5.3: 记录分歧并网络检索评价

- [ ] Task 6: 质量门禁扫描
  - [ ] SubTask 6.1: 文件行数 ≤800
  - [ ] SubTask 6.2: 函数行数 ≤80
  - [ ] SubTask 6.3: 圈复杂度 ≤15

- [ ] Task 7: 网络检索权威资料解决分歧
  - [ ] SubTask 7.1: 对每个分歧点检索权威资源
  - [ ] SubTask 7.2: 保留最优结果，记录决策

- [ ] Task 8: 生成审核报告
  - [ ] SubTask 8.1: 编写 20260627-mvp技术诚信学术审核.md
  - [ ] SubTask 8.2: 包含全部审核维度结论
  - [ ] SubTask 8.3: Bug 清单与修复状态

- [ ] Task 9: 提交代码 + 操作记录追加
  - [ ] SubTask 9.1: 修复发现的 Bug
  - [ ] SubTask 9.2: 提交合并 main
  - [ ] SubTask 9.3: 操作记录追加

# Task Dependencies
- [Task 7] depends on [Task 2,3,4,5]
- [Task 8] depends on [Task 1,2,3,4,5,6,7]
- [Task 9] depends on [Task 8]
