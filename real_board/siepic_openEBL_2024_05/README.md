# SiEPIC openEBL 2024-05 真实流片提交

> 来源: https://github.com/SiEPIC/openEBL-2024-05
>
> 许可: MIT (Copyright © 2023 SiEPIC) — 见 `LICENSE`
>
> 提交截止: 2024-05-18 (openEBL-24-05 run)
>
> 文件数: 244 (全量提取)

## 来源说明

SiEPIC openEBL 2024 年 5 月 run 的全部 GitHub 设计提交,与 `siepic_openEBL_2024_10/` 同系列。覆盖 220nm SOI EBeam 工艺,Layer 1/10/99 三层定义。

## 目录内容

- `submissions/` — 设计者提交的 GDS 文件 (EBeam_*.gds)
- `merge/` — 合并后的整片晶圆 GDS
- `framework/` — SiEPIC 验证流程 Python 脚本
- `LICENSE` + `README.md` — 原仓库许可与说明

## 用途

- 端到端 GDS 验证回归基准
- 与 `siepic_openEBL_2024_10/` 配合,提供时间序列上的设计演进样本
- 商用版自动布局布线对真实设计师 GDS 的鲁棒性测试

## 引用

```bibtex
@inproceedings{chrostowski2024openebl,
  title={SiEPIC openEBL: remote silicon photonic design, fabrication, testing enabled by open-source PDKs and EDA tools},
  author={Chrostowski, Lukas and others},
  booktitle={SPIE Photonics West},
  year={2024},
  doi={10.1117/12.3076810}
}
```
