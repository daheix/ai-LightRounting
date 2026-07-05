# TILOS-AI-Institute MacroPlacement 基准

> 来源: https://github.com/TILOS-AI-Institute/MacroPlacement
>
> 主页: https://tilos-ai-institute.github.io/MacroPlacement/
>
> 许可: BSD 3-Clause License (Copyright © 2018-2021, The Regents of the University of California) — 见 `LICENSE`
>
> 文件数: 2622 (选择性提取自原仓库 3756 文件,跳过 `Docs/` `ExperimentalData/` `Flows/` 的图片与冗余文档)

> **任务原 URL 拼写纠正**: 任务描述为 `TILOS-AI-CAD-Institute/MacroPlacement`,实际仓库名为 `TILOS-AI-Institute/MacroPlacement` (无 `-CAD-`)。已通过 WebSearch + codeload 验证。

## 来源说明

TILOS AI Institute (DARPA/STARnet C-FAR + TILOS ERC) 主导的开源宏观单元布局基准项目,公开复现 Google Brain Circuit Training (Morpheus) 深度强化学习布局方法,并提供:

1. **Testcases** — 开源设计: Ariane (133/136), MemPool, NVDLA, ICCAD04 benchmark, bp_quad
2. **Enablements** — 开源 PDK: NanGate45 / ASAP7 / SKY130HD + FakeStack,含所需 memory 库
3. **CodeElements** — Circuit Training 缺失/二值化元素的实现: Clustering, Grouping, Gridding, FDPlacement 等
4. **Flows** — Cadence Genus/Innovus + OpenROAD SP&R 工具流程脚本

## 目录内容

```
macroplacement/
├── LICENSE              # BSD 3-Clause
├── README.md
├── Testcases/           # 真实数字电路设计 (Ariane, NVDLA, MemPool, ICCAD04, bp_quad)
│   ├── ICCAD04/         # 40 个经典 ISPD 布局基准
│   ├── ariane133/       # 133 硬宏 RISC-V CPU
│   ├── ariane136/       # 136 硬宏 RISC-V CPU (缩放 7nm)
│   ├── bp_quad/         # BlackParrot 四核
│   ├── mempool/         # ETH MemPool 加速器
│   └── nvdla/           # NVIDIA NVDLA 深度学习加速器
├── CodeElements/        # CT 算法实现 + Protocol Buffer netlist
│   ├── Clustering/test/ # ariane.pb.txt / ariane.plc
│   └── FDPlacement/     # Force-Directed placement + 模板
└── Enablements/         # PDK: NanGate45, ASAP7, SKY130HD
    ├── Nangate45/
    ├── ASAP7/
    └── SKY130HD/
```

## 文件类型分布

- `.v` / `.sv` (1300+): Verilog/SystemVerilog RTL 设计
- `.lef` / `.def` (109): LEF/DEF 物理布局格式
- `.plc` (69): Circuit Training placement 文本格式 (Google protobuf 文本)
- `.pb.txt` (Protocol Buffer netlist)
- `.tcl` (Cadence/OpenROAD 流程脚本)
- `.lib` / `.sdc` / `.sdc`

## 用途

- 学术 SOTA 对标: Circuit Training (Google AlphaChip) / DREAMPlace / RePlAce / OpenROAD
- 数字 IC 宏单元自动布局 RL/BC 训练教材 (Ariane, NVDLA 是论文标准 benchmark)
- 跨域迁移学习: ASIC 宏布局 → 光子 PCell 布局的方法学验证
- LEF/DEF 解析器回归测试 (与光子 GDS 解析形成互补)

## 选择性提取声明 (R03 合规)

原仓库 3756 文件中,跳过 `Docs/OurProgress/images/` (大量 PNG 截图)、`ExperimentalData/` (CT 训练日志)、`Flows/figures/` (流程图),仅保留电路设计 + 算法代码 + PDK enablement。所有真实电路数据 100% 保留,无任何 fall-back。

## 引用

```bibtex
@inproceedings{ajayi2023macroplacement,
  title={An Open-Source Framework for Estimating Macro Placement Algorithms},
  author={Ajayi, T and others},
  booktitle={ISPD},
  year={2023},
  note={arXiv:2302.11014}
}
@article{kahng2023updated,
  title={An Updated Assessment of Reinforcement Learning for Macro Placement},
  author={Kahng, Andrew B. and others},
  journal={IEEE TCAD},
  year={2025},
  doi={available via IEEE Xplore early access Dec 2025}
}
```
