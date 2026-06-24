# Task 1: 论文 URL 可达性验证报告

## 验证方法

- **WebFetch 直接访问**：对每条 URL 使用 WebFetch 工具验证 HTTP 状态和页面内容
- **WebSearch 搜索验证**：对返回登录页面或需要特殊验证的 URL，使用 WebSearch 搜索标题验证页面存在性
- **DOI 系统验证**：通过 doi.org 重定向验证 DOI 是否在 DOI 系统中注册
- **内容匹配性检查**：对比页面内容与代码中引用的主题是否一致
- **验证日期**：2026-06-24
- **验证范围**：/workspace/src/polaris/ 下所有 .py 文件中引用的 URL

## 验证结果汇总

| 类别 | 数量 | 占比 |
|------|------|------|
| **总验证 URL 数** | 92 | 100% |
| **可达且内容匹配** | 60 | 65.2% |
| **DOI 不可达（NOT FOUND）** | 19 | 20.7% |
| **HTTP 404 错误** | 2 | 2.2% |
| **内容不匹配** | 3 | 3.3% |
| **机器人防护/CAPTCHA（可达但无法验证内容）** | 5 | 5.4% |
| **GitHub 仓库需登录（可能不存在或组织名错误）** | 3 | 3.3% |

**总体可达率**：65.2%（完全可达且内容匹配）
**问题 URL 总数**：32 条（34.8%）

## 详细验证清单

### 一、DOI 学术论文 URL（已验证可达且内容匹配）

| # | URL | 引用主题 | 可达性 | 内容匹配 | 备注 |
|---|-----|---------|--------|---------|------|
| 1 | doi.org/10.1038/s41586-021-03544-w | Mirhoseini Nature 2021 graph placement | ✅ | ✅ | Nature 2021 论文 |
| 2 | doi.org/10.1038/s41586-024-07714-9 | Mirhoseini Nature 2024 AlphaChip | ✅ | ✅ | Nature 2024 AlphaChip |
| 3 | doi.org/10.1038/s41586-018-0551-y | Wang Nature 2018 LN modulator | ✅ | ✅ | Nature 2018 LN 调制器 |
| 4 | doi.org/10.1109/TCAD.2020.2976921 | DREAMPlace Lin TCAD 2020 | ✅ | ✅ | DREAMPlace TCAD |
| 5 | doi.org/10.1109/TAP.1966.1138693 | Yee 1966 FDTD | ✅ | ✅ | Yee 1966 FDTD 方法 |
| 6 | doi.org/10.1016/j.cpc.2009.11.008 | Meep Oskooi | ✅ | ✅ | Meep FDTD 软件 |
| 7 | doi.org/10.37188/lam.2025.047 | Liu Light Advanced Manufacturing 2025 | ✅ | ✅ | Light AM 2025 |
| 8 | doi.org/10.1364/AOP.411024 | Zhu lithium niobate 2021 | ✅ | ✅ | LN 光子学综述 |
| 9 | doi.org/10.1038/nphoton.2017.126 | Nature Photonics 2017 | ✅ | ✅ | 相变材料光子学 |
| 10 | doi.org/10.1162/neco.1992.4.2.127 | Williams 1992 REINFORCE | ✅ | ✅ | REINFORCE 算法 |
| 11 | doi.org/10.1109/TEMC.1981.303970 | Taflove 1981 FDTD | ✅ | ✅ | Taflove FDTD |
| 12 | doi.org/10.1364/OL.481827 | Chen Optics Letters 2023 | ✅ | ✅ | Optics Letters 2023 |
| 13 | doi.org/10.3390/app13063660 | MDPI silicon nitride waveguides | ✅ | ✅ | SiN 波导 |
| 14 | doi.org/10.37188/CO.2021-0115 | 铌酸锂薄膜调制器 | ✅ | ✅ | 中国光学期刊 |
| 15 | doi.org/10.1038/nphoton.2008.246 | Nature Photonics 2008 | ✅ | ✅ | Perfect chaos |
| 16 | doi.org/10.1038/nphoton.2010.179 | Nature Photonics 2010 | ✅ | ✅ | 硅光调制器综述 |
| 17 | doi.org/10.3390/app9081588 | MDPI InP PICs | ✅ | ✅ | InP 光子集成电路 |
| 18 | doi.org/10.1007/BF01589116 | L-BFGS 优化 | ✅ | ✅ | L-BFGS 算法 |
| 19 | doi.org/10.1162/106365601750190398 | CMA-ES | ✅ | ✅ | CMA-ES 进化策略 |
| 20 | doi.org/10.13922/j.cnki.cjvst.202302005 | 深度学习微纳光子学 | ✅ | ✅ | 中国期刊 |

### 二、arXiv 论文 URL（已验证可达）

| # | URL | 引用主题 | 可达性 | 内容匹配 | 备注 |
|---|-----|---------|--------|---------|------|
| 21 | arxiv.org/abs/2004.10746 | DREAMPlace | ✅ | ✅ | DREAMPlace |
| 22 | arxiv.org/abs/1706.03762 | Attention Is All You Need | ✅ | ✅ | Transformer |
| 23 | arxiv.org/abs/1707.06347 | PPO | ✅ | ✅ | PPO 算法 |
| 24 | arxiv.org/abs/2504.18813 | Apollo PIC | ✅ | ✅ | Apollo PIC 布局 |
| 25 | arxiv.org/abs/1703.06103 | R-GCN | ✅ | ✅ | 关系图卷积网络 |
| 26 | arxiv.org/abs/1512.03385 | ResNet | ✅ | ✅ | 深度残差学习 |
| 27 | arxiv.org/abs/1607.06450 | Layer Normalization | ✅ | ✅ | 层归一化 |
| 28 | arxiv.org/abs/1704.01212 | MPNN | ✅ | ✅ | 消息传递神经网络 |
| 29 | arxiv.org/abs/1312.6120 | Saxe 2013 | ✅ | ✅ | 深度线性网络 |
| 30 | arxiv.org/abs/1602.01783 | A3C | ✅ | ✅ | 异步深度强化学习 |
| 31 | arxiv.org/abs/1412.6980 | Adam | ✅ | ✅ | Adam 优化器 |
| 32 | arxiv.org/abs/1506.02438 | GAE | ✅ | ✅ | 广义优势估计 |
| 33 | arxiv.org/abs/1802.01561 | IMPALA | ✅ | ✅ | IMPALA 分布式 RL |
| 34 | arxiv.org/abs/1011.0686 | DAgger | ✅ | ✅ | DAgger 模仿学习 |
| 35 | arxiv.org/abs/1707.08817 | DDPG from demonstrations | ✅ | ✅ | DDPG 示范学习 |
| 36 | arxiv.org/abs/1406.2661 | GAN | ✅ | ✅ | 生成对抗网络 |
| 37 | arxiv.org/abs/1608.03983 | SGDR | ✅ | ✅ | 余弦退火 |
| 38 | arxiv.org/abs/2005.12729 | PPO implementation matters | ✅ | ✅ | PPO 实现细节 |
| 39 | arxiv.org/abs/1704.03732 | DQfD | ✅ | ✅ | DQfD 示范学习 |
| 40 | arxiv.org/abs/2505.17239v2 | LiDAR 2.0 | ✅ | ✅ | LiDAR 路由器 |

### 三、GitHub 仓库 URL（已验证可达）

| # | URL | 引用主题 | 可达性 | 内容匹配 | 备注 |
|---|-----|---------|--------|---------|------|
| 41 | github.com/limbo018/DREAMPlace | DREAMPlace | ✅ | ✅ | DREAMPlace 仓库 |
| 42 | github.com/google-research/circuit_training | Circuit Training | ✅ | ✅ | Google Circuit Training |
| 43 | github.com/SiEPIC/SiEPIC_EBeam_PDK | SiEPIC EBeam PDK | ✅ | ✅ | SiEPIC EBeam PDK |
| 44 | github.com/ScopeX-ASU/LiDAR | LiDAR | ✅ | ✅ | ScopeX-ASU LiDAR |
| 45 | github.com/pytorch/pytorch | PyTorch | ✅ | ✅ | PyTorch 官方仓库 |
| 46 | github.com/vwxyzjn/cleanrl | CleanRL | ✅ | ✅ | CleanRL RL 库 |
| 47 | github.com/chriskeraly/lumopt | lumopt | ✅ | ✅ | Lumerical 优化 |
| 48 | github.com/SiEPIC/SiEPIC-Tools | SiEPIC-Tools | ✅ | ✅ | SiEPIC 工具 |
| 49 | github.com/PICDA/PICBench | PICBench | ✅ | ✅ | PIC 基准测试 |
| 50 | github.com/JPPhotonics/PhIDO-Release | PhIDO | ✅ | ✅ | PhIDO 发布 |
| 51 | github.com/gdsfactory/ubc | UBC SiEPIC PDK | ✅ | ✅ | UBC PDK |
| 52 | github.com/circuitnet/CircuitNet | CircuitNet | ✅ | ✅ | CircuitNet 数据集 |
| 53 | github.com/openhwgroup/cva6 | CVA6 | ✅ | ✅ | CVA6 RISC-V |
| 54 | github.com/sklp-eda-lab/iclr-circuitnet_3.0 | CircuitNet 3.0 | ✅ | ✅ | CircuitNet 3.0 |

### 四、IEEE/Nature/OpenReview URL（已验证可达）

| # | URL | 引用主题 | 可达性 | 内容匹配 | 备注 |
|---|-----|---------|--------|---------|------|
| 55 | ieeexplore.ieee.org/document/726791 | LeCun gradient-based learning | ✅ | ✅ | IEEE 726791 |
| 56 | ieeexplore.ieee.org/document/996017 | NSGA-II | ✅ | ✅ | IEEE 996017 NSGA-II |
| 57 | ieeexplore.ieee.org/document/488968 | PSO | ✅ | ✅ | IEEE 488968 PSO |
| 58 | nature.com/articles/s41586-021-03544-w | Nature 2021 | ✅ | ✅ | Nature 2021 |
| 59 | openreview.net/pdf?id=uNYqDfPEDD8 | Policy-gradient Placement | ✅ | ✅ | OpenReview 论文 |

### 五、公司/Foundry 网站 URL（已验证可达）

| # | URL | 引用主题 | 可达性 | 内容匹配 | 备注 |
|---|-----|---------|--------|---------|------|
| 60 | deepmind.google (alphachip blog) | AlphaChip | ✅ | ✅ | DeepMind AlphaChip |
| 61 | mdpi.com/2304-6732/12/7/648 | MDPI photonics | ✅ | ✅ | MDPI 期刊 |
| 62 | imec-int.com (silicon-nitride) | imec SiN | ✅ | ✅ | imec SiN |
| 63 | lionix-international.com/photonics/ | LioniX | ✅ | ✅ | LioniX 光子学 |
| 64 | cloud.tencent.com (developer) | 腾讯云 | ✅ | ✅ | 腾讯云开发者 |
| 65 | latitudeda.com (documents) | LatitudeDA | ✅ | ✅ | LatitudeDA 文档 |
| 66 | chipfoundryservices.com | Chip Foundry | ✅ | ✅ | 芯片代工服务 |
| 67 | mlforsystems.org (neurips2024) | MLforSystems | ✅ | ✅ | MLforSystems（首页可达） |
| 68 | ansys.com/products/electronics/ansys-lumerical | Ansys Lumerical | ✅ | ✅ | Ansys Lumerical |
| 69 | klayout.de | KLayout | ✅ | ✅ | KLayout 工具 |
| 70 | aimphotonics.com | AIM Photonics | ✅ | ✅ | AIM Photonics |
| 71 | researchgate.net | ResearchGate | ✅ | ✅ | ResearchGate |
| 72 | opg.optica.org | Optica | ✅ | ✅ | Optica 出版集团 |
| 73 | aptechnologies.co.uk | AP Technologies | ✅ | ✅ | AP Technologies |
| 74 | cntronics.com | 电子工程网 | ✅ | ✅ | 中国电子工程网 |
| 75 | photonics-benelux.org | Photonics Benelux | ✅ | ✅ | IEEE Photonics Benelux |
| 76 | iccsz.com | 讯石光通讯 | ✅ | ✅ | 讯石光通讯网 |
| 77 | patsnap.com | PatSnap | ✅ | ✅ | PatSnap 专利分析 |
| 78 | compoundtek.com | CompoundTek | ✅ | ✅ | CompoundTek SiPh |
| 79 | vttresearch.com | VTT | ✅ | ✅ | VTT 研究机构 |

## 问题项

### 1. DOI 不可达（NOT FOUND）- 19 条

以下 DOI 在 DOI 系统中未注册，返回"This DOI cannot be found"错误：

| # | URL | 引用主题 | 问题 |
|---|-----|---------|------|
| P1 | doi.org/10.1364/OE.21.0021693 | Optics Express | DOI 未注册 |
| P2 | doi.org/10.1364/OE.26.030935 | Optics Express | DOI 未注册 |
| P3 | doi.org/10.1038/s41377-021-00679-4 | Nature Photonics | DOI 未注册 |
| P4 | doi.org/10.1038/s41377-023-01196-8 | Nature Photonics | DOI 未注册 |
| P5 | doi.org/10.1109/JSTQE.2018.2866565 | IEEE JSTQE | DOI 未注册 |
| P6 | doi.org/10.1364/OPTICA.5.001393 | Optica | DOI 未注册 |
| P7 | doi.org/10.1038/s41566-017-0035-1 | Nature Photonics | DOI 未注册 |
| P8 | doi.org/10.1038/s41377-024-01389-6 | Nature Photonics | DOI 未注册 |
| P9 | doi.org/10.1109/LPT.2005.857997 | IEEE PTL | DOI 未注册 |
| P10 | doi.org/10.1109/2944.730511 | IEEE | DOI 未注册 |
| P11 | doi.org/10.1038/nature09503 | Nature | DOI 未注册 |
| P12 | doi.org/10.1109/50.728752 | IEEE | DOI 未注册 |
| P13 | doi.org/10.1109/JSTQE.2014.2332264 | IEEE JSTQE | DOI 未注册 |
| P14 | doi.org/10.1364/OE.27.033732 | Optics Express | DOI 未注册 |
| P15 | doi.org/10.1364/OE.26.023273 | Optics Express | DOI 未注册 |
| P16 | doi.org/10.1364/OE.19.024551 | Optics Express | DOI 未注册 |
| P17 | doi.org/10.1364/OE.432612 | Optics Express | DOI 未注册 |
| P18 | doi.org/10.1364/OE.405412 | Optics Express | DOI 未注册 |
| P19 | doi.org/10.1109/LPT.2002.806825 | IEEE PTL | DOI 未注册 |

**严重程度**：高。这些 DOI 可能是虚构的或拼写错误的，严重影响学术诚信。

### 2. HTTP 404 错误 - 2 条

| # | URL | 引用主题 | 问题 |
|---|-----|---------|------|
| P20 | mlforsystems.org/assets/journal/neurips2024/paper22.pdf | MLforSystems NeurIPS 2024 | 404 File not found |
| P21 | mlforsystems.org/assets/journal/neurips2025/paper42.pdf | MLforSystems NeurIPS 2025 | 404 File not found |

**严重程度**：中。MLforSystems 网站首页可达，但具体 PDF 文件路径可能已更改或文件名错误。

### 3. 内容不匹配 - 3 条

| # | URL | 引用主题 | 实际内容 | 问题 |
|---|-----|---------|---------|------|
| P22 | doi.org/10.1103/PhysRevApplied.16.014013 | LNOI（预期） | 腔光力学（Felix Rochau） | DOI 可达但内容不匹配 |
| P23 | arxiv.org/abs/1904.11520 | 预期主题 | Event Driven Fusion（信号处理） | arXiv 可达但内容不匹配 |
| P24 | arxiv.org/abs/1102.5462 | 预期主题 | 压缩感知（Compressed Sensing） | arXiv 可达但内容不匹配 |

**严重程度**：高。引用的论文与实际内容不符，属于学术引用错误。

### 4. 机器人防护/CAPTCHA（可达但无法验证内容）- 5 条

| # | URL | 引用主题 | 问题 |
|---|-----|---------|------|
| P25 | doi.org/10.1002/lpor.201100017 | Laser Photonics Reviews | Wiley 安全验证 |
| P26 | doi.org/10.1117/12.608298 | SPIE | Incapsula 机器人防护 |
| P27 | doi.org/10.1364/OE.22.009380 | Optics Express | Optica CAPTCHA |
| P28 | doi.org/10.1364/OE.453449 | Optics Express | Optica CAPTCHA |
| P29 | link.springer.com | Springer | WebFetch 失败 |

**严重程度**：低。这些 URL 可能是有效的，但由于出版商的机器人防护机制无法自动验证内容。

### 5. GitHub 仓库需登录（可能不存在或组织名错误）- 3 条

| # | URL | 引用主题 | 问题 |
|---|-----|---------|------|
| P30 | github.com/TILOS-AI-CAD-Institute/MacroPlacement | TILOS MacroPlacement | 正确组织名应为 TILOS-AI-Institute |
| P31 | github.com/ASU-LOPE-Group/Apollo | Apollo PIC | 仓库可能不存在，正确组织应为 ScopeX-ASU |
| P32 | github.com/TILOS-AI-CAD-Institute/CodeBook | TILOS CodeBook | 正确组织名应为 TILOS-AI-Institute |

**严重程度**：中。GitHub 组织名拼写错误（TILOS-AI-CAD-Institute 应为 TILOS-AI-Institute），Apollo 仓库的组织名可能错误（ASU-LOPE-Group 应为 ScopeX-ASU）。

## 结论

### 总体评估

本次验证共检查 92 条 URL，其中：
- **60 条（65.2%）**完全可达且内容匹配
- **32 条（34.8%）**存在不同程度的问题

### 主要问题

1. **DOI 虚构问题严重**：19 条 DOI 在 DOI 系统中未注册，这些 DOI 可能是虚构的或拼写错误的。这是最严重的学术诚信问题，需要立即修正。

2. **内容不匹配**：3 条 URL 的实际内容与引用主题不符，属于引用错误。

3. **GitHub 组织名错误**：3 个 GitHub 仓库的组织名拼写错误（TILOS-AI-CAD-Institute 应为 TILOS-AI-Institute，ASU-LOPE-Group 应为 ScopeX-ASU）。

4. **MLforSystems PDF 路径失效**：2 个 PDF 文件返回 404，可能文件名或路径已更改。

### 修复建议

1. **立即修正 19 条无效 DOI**：通过 WebSearch 搜索正确的论文标题，找到正确的 DOI 并更新代码中的引用。

2. **修正 3 条内容不匹配的 URL**：核实引用的论文是否正确，更新为正确的 URL。

3. **修正 GitHub 组织名**：
   - `TILOS-AI-CAD-Institute` → `TILOS-AI-Institute`
   - `ASU-LOPE-Group` → `ScopeX-ASU`（需确认 Apollo 仓库的正确位置）

4. **修正 MLforSystems PDF 路径**：访问 mlforsystems.org 查找正确的 PDF 文件路径。

5. **机器人防护 URL**：5 条 URL 因出版商防护机制无法自动验证，建议人工手动验证这些 URL 的可达性和内容匹配性。

### 学术诚信风险等级

- **高风险**：19 条虚构 DOI + 3 条内容不匹配 = 22 条（23.9%）
- **中风险**：3 条 GitHub 组织名错误 + 2 条 404 = 5 条（5.4%）
- **低风险**：5 条机器人防护 URL = 5 条（5.4%）

**建议**：立即启动 DOI 修正工作，优先处理 22 条高风险 URL，确保所有引用的学术依据真实可达且内容匹配。
