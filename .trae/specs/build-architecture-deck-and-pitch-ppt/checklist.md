# Checklist

## 架构讲解文档
- [x] `docs/architecture_overview.md` 已创建
- [x] 项目一句话定位清晰（开源 AI 光电子 EDA）
- [x] 体量数据准确（33 模块/289 文件/99,017 行/1,614 passed/3,031 URL）
- [x] 模块分层图包含 6 层（应用/AI/算法/验证/输出/物理求解器/核心编排）
- [x] 10 阶段流水线表完整（stage1-10 名称/输入/输出/子模块/文献）
- [x] 6 大业务流程 Mermaid 图语法正确（GitHub 可渲染）
  - [x] 流程 A: 网表→GDS 主流水线
  - [x] 流程 B: AI 布局布线（PPO 训练→推理）
  - [x] 流程 C: 逆向设计（JAX adjoint→拓扑→level-set）
  - [x] 流程 D: 量子光子验证（Clements→HOM→玻色采样）
  - [x] 流程 E: 光电协同（寄生→Verilog-A→Ngspice）
  - [x] 流程 F: Web GUI（showcase 11 阶段+编辑器双模式）
- [x] 15 维度得分表与 `final_defect_audit_report_2026_07.md` 一致
- [x] 关键文献来源表每算法有 URL（R02 合规）

## 技术汇报 PPT
- [x] `docs/decks/tech_report.html` 已创建
- [x] slide deck 支持键盘左右键翻页
- [x] 页数 15-20 页（实际 17 页）
- [x] 封面含项目名/定位/版本/日期
- [x] 模块分层架构图正确渲染
- [x] 10 阶段流水线图正确渲染
- [x] 15 维度雷达图用 SVG/canvas 绘制
- [x] 核心算法能力页（DREAMPlace/AlphaChip/LiDAR/JAX adjoint）
- [x] AI/ML 能力页（PPO/迁移学习/expert demos）
- [x] 物理求解器矩阵页（FDTD/FDE/FDFD/EME/BPM/RCWA）
- [x] GUI 交互式编辑器页（R19 + KLayout 双模式）
- [x] 竞品对标页（Lumerical/KLayout/gdsfactory）
- [x] 诚实差距声明页（5 未达标维度，Slide 14 差距声明）
- [x] 浏览器预览渲染正确

## 投资人汇报 PPT
- [x] `docs/decks/investor_pitch.html` 已创建
- [x] 视觉风格简洁专业（与技术 PPT 区分，浅色主题）
- [x] 页数 12-15 页（实际 13 页）
- [x] 问题与机遇页（光子 EDA 海外垄断 + AI 机会）
- [x] 解决方案页（PoLaRIS 开源 AI EDA）
- [x] 产品演示页（showcase 11 阶段流程图 + 编辑器）
- [x] 技术壁垒页（33 模块/99K 行/3031 文献）
- [x] 市场规模页（数据有公开来源 URL，Yole/SEMI，R02 合规）
- [x] 竞争格局页（6 维度对比表）
- [x] 商业模式页（开源+商业版+MPW+学术）
- [x] 路线图页（3 波 8.08→8.86）
- [x] 团队页标注"待补充"
- [x] 融资页标注"待补充"
- [x] 诚实声明页（8.08 分，未达 9.20 目标）
- [x] 浏览器预览渲染正确

## 数据一致性
- [x] 三份文档体量数字一致（33/289/99017/1614/3031）
- [x] 三份文档综合得分一致（8.08/10）
- [x] 三份文档 15 维度得分逐项一致（架构文档+技术PPT雷达图完整，投资人PPT侧重未达标维度）
- [x] 三份文档路标一致（36 月路标完成）
- [x] 三份文档差距一致（5 未达标：D07/D10/D11/D12/D15）
- [x] 无假数据（R03 合规）
- [x] 无夸大（综合得分诚实声明未超 9.0）

## 合规
- [x] 不改动任何 .py 代码文件
- [x] 所有市场数据有公开来源（不编造）
- [x] 文献 URL 抽查 ≥5 个可访问
- [x] 团队/融资占位明确标注
