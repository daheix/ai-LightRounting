# 36-RoundMap 详细技术交付文档索引

**文档版本**: v1.0
**创建日期**: 2026-06-22
**目标**: 为 36-RoundMap 的每个路标（R1-R36）提供详细技术交付文档，含学术论文追踪、公式推导、开源方案缺点分析、源码解读、改进计划

---

## 路标总览

| 阶段 | 月份范围 | 追赶对象 | 综合得分目标 |
|------|----------|----------|-------------|
| 阶段 1 | R1-R6（2026-07 ~ 2026-12） | sax + simphony | 6.1 → 6.8 |
| 阶段 2 | R7-R12（2027-01 ~ 2027-06） | KLayout + gdsfactory | 6.8 → 7.4 |
| 阶段 3 | R13-R18（2027-07 ~ 2027-12） | Aspic + VPIphotonics | 7.4 → 7.9 |
| 阶段 4 | R19-R24（2028-01 ~ 2028-06） | L-Edit + OptoDesigner | 7.9 → 8.4 |
| 阶段 5 | R25-R30（2028-07 ~ 2028-12） | IPKISS + Tidy3D | 8.4 → 8.8 |
| 阶段 6 | R31-R36（2029-01 ~ 2029-06） | Lumerical + AlphaChip | 8.8 → 9.2 |

---

## 阶段 1：R1-R6 追赶 sax + simphony（电路仿真对齐）

- [R01（2026-07）](R01.md) - sax 频域 S 参数仿真对齐
- [R02（2026-08）](R02.md) - simphony 光子电路仿真对齐
- [R03（2026-09）](R03.md) - S 参数级联优化
- [R04（2026-10）](R04.md) - 子网络增长算法
- [R05（2026-11）](R05.md) - JAX 加速集成
- [R06（2026-12）](R06.md) - 阶段 1 验收 + 综合得分 6.8

## 阶段 2：R7-R12 追赶 KLayout + gdsfactory（版图/DRC/PDK 对齐）

- [R07（2027-01）](R07.md) - KLayout DRC 引擎深化
- [R08（2027-02）](R08.md) - KLayout LVS 完整对齐
- [R09（2027-03）](R09.md) - gdsfactory PDK 桥接
- [R10（2027-04）](R10.md) - gdsfactory routing strategies 对齐
- [R11（2027-05）](R11.md) - 版图参数化代码驱动
- [R12（2027-06）](R12.md) - 阶段 2 验收 + 综合得分 7.4

## 阶段 3：R13-R18 追赶 Aspic + VPIphotonics（系统级仿真对齐）

- [R13（2027-07）](R13.md) - Aspic 频域 S 参数对齐
- [R14（2027-08）](R14.md) - VPIphotonics 系统级仿真
- [R15（2027-09）](R15.md) - VPIphotonics PDK 对齐
- [R16（2027-10）](R16.md) - 时域光子电路仿真
- [R17（2027-11）](R17.md) - layout-aware 仿真
- [R18（2027-12）](R18.md) - 阶段 3 验收 + 综合得分 7.9

## 阶段 4：R19-R24 追赶 Siemens L-Edit + Synopsys OptoDesigner（商业版图/DRC/布线对齐）

- [R19（2028-01）](R19.md) - L-Edit GPIC PDK 对齐
- [R20（2028-02）](R20.md) - OptoDesigner 版图驱动
- [R21（2028-03）](R21.md) - OptoDesigner 自动布线
- [R22（2028-04）](R22.md) - 高级连接器
- [R23（2028-05）](R23.md) - DRC 认证流程
- [R24（2028-06）](R24.md) - 阶段 4 验收 + 综合得分 8.4

## 阶段 5：R25-R30 追赶 Luceda IPKISS + Tidy3D（全流程+FDTD 对齐）

- [R25（2028-07）](R25.md) - IPKISS 全流程对齐
- [R26（2028-08）](R26.md) - IPKISS CAPHE 仿真
- [R27（2028-09）](R27.md) - Tidy3D 云 API 集成
- [R28（2028-10）](R28.md) - Tidy3D GPU FDTD 对齐
- [R29（2028-11）](R29.md) - 逆向设计 adjoint
- [R30（2028-12）](R30.md) - 阶段 5 验收 + 综合得分 8.8

## 阶段 6：R31-R36 追赶 Ansys Lumerical + AlphaChip（顶级商业+AI 对齐）

- [R31（2029-01）](R31.md) - Lumerical FDTD 3D 全波
- [R32（2029-02）](R32.md) - Lumerical INTERCONNECT
- [R33（2029-03）](R33.md) - AlphaChip Edge-GNN
- [R34（2029-04）](R34.md) - AlphaChip 预训练-微调
- [R35（2029-05）](R35.md) - 光电协同 + 量子光子
- [R36（2029-06）](R36.md) - 阶段 6 验收 + 综合得分 9.2

---

## 每个路标文档的统一 10 章节结构

1. 交付目标摘要（100-200 字）
2. 学术论文追踪（3-5 篇，含 arXiv ID/DOI/URL）
3. 公式与理论依据（含 LaTeX 表达与推导来源）
4. 开源方案缺点分析（含 GitHub Issue/SO 链接）
5. 源代码解读分析（含 PoLaRIS 文件路径与关键函数）
6. 100% 复刻 + 更优秀方案（含创新点标注）
7. 改进计划路线图（含步骤/依赖/验收/风险）
8. 权威资源引用（按 6 大类分类）
9. 交叉验证（工程实践/学术论文/官方标准三方验证表）
10. 学术诚信声明

---

## 权威资源清单（6 大类）

### 一、国际顶级学术期刊 & 科研论文数据源

1. arXiv - https://arxiv.org
2. IEEE Xplore - https://ieeexplore.ieee.org
3. ACM Digital Library - https://dl.acm.org
4. SpringerLink - https://link.springer.com
5. ScienceDirect (Elsevier) - https://www.sciencedirect.com
6. Nature Computer Science - https://www.nature.com/natcomputsci
7. MDPI - https://www.mdpi.com
8. USENIX - https://www.usenix.org
9. VLDB / SIGMOD - https://vldb.org / https://sigmod.org

### 二、国外一线研发工程师实战论坛

1. Stack Overflow - https://stackoverflow.com
2. Hacker News - https://news.ycombinator.com
3. Reddit r/programming - https://reddit.com/r/programming
4. Dev.to - https://dev.to
5. Medium Engineering Blog - https://medium.com
6. InfoQ International - https://www.infoq.com
7. CodeProject - https://www.codeproject.com

### 三、顶级开源官方研发社区

1. GitHub Discussions - https://github.com
2. GitHub Issues - https://github.com
3. GitLab Community - https://gitlab.com
4. Apache Community - https://community.apache.org
5. CNCF Community - https://www.cncf.io

### 四、国际技术标准 & 权威规范数据源

1. IETF RFC - https://www.rfc-editor.org
2. W3C - https://www.w3.org
3. OASIS - https://www.oasis-open.org
4. OpenAPI Official - https://www.openapis.org
5. ISO/IEC - https://www.iso.org

### 五、海外高端技术智库 & 大厂技术研究院

1. Google Research - https://research.google
2. Meta Engineering Blog - https://engineering.fb.com
3. AWS Architecture Blog - https://aws.amazon.com/blogs/architecture
4. Microsoft Research - https://www.microsoft.com/research
5. Cloudflare Blog - https://blog.cloudflare.com
6. Netflix Tech Blog - https://netflixtechblog.com

### 六、国外专项高性能/架构/数据库垂直研发社区

1. High Scalability - https://highscalability.com
2. Database Internals - https://databaseinternals.com
3. Distributed Systems Reading Group - https://distsys.substack.com
4. Martin Fowler Blog - https://martinfowler.com

---

## 权威优先级

**国际顶会论文 > 大厂官方工程博客 > 海外高赞社区实践 > 国内技术内容**

## 核心使用规则

1. 所有架构疑难、性能瓶颈、分布式问题、技术短板必须优先检索以上海外资源
2. 所有解决方案必须交叉验证：国外工程实践 + 学术论文原理 + 官方标准
3. 所有项目劣势、技术短板，必须在以上清单中找到最新 3 年内最优开源方案/学术改进方案
4. 权威优先级：国际顶会论文 > 大厂官方工程博客 > 海外高赞社区实践 > 国内技术内容
