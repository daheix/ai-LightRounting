# SiEPIC openEBL 2024-10 真实流片提交

> 来源: https://github.com/SiEPIC/openEBL-2024-10
>
> 许可: MIT (Copyright © 2024 SiEPIC) — 见 `LICENSE`
>
> 提交截止: 2024-10-12 (openEBL-24-10 run)
>
> 文件数: 264 (选择性提取自原仓库 2020 文件,跳过 1755 个 `.mat` 测量数据以节省空间)

## 来源说明

SiEPIC openEBL 是 UBC SiEPICfab 提供的开放式电子束光刻流片服务,允许全球设计者提交小面积 (605µm × 410µm) EBeam 工艺设计并获取流片测试结果,每年 3 轮。本目录是 2024 年 10 月 run 的全部 GitHub 设计提交。

- 平台: 220nm SOI,100keV EBL (Applied Nanotools / SiEPICfab)
- 层定义: Layer 1 = silicon, Layer 10 = text label (自动测量), Layer 99 = floorplan
- 测量标签格式: `opt_in_[pol]_[wavelength]_openEBL_[yourname]_[deviceID]`

## 目录内容

- `submissions/` — 各设计者提交的 GDS 文件 (EBeam_*.gds),213 个 GDS + 8 个 GDS(大写扩展名)
- `merge/` — 合并后的整片晶圆 GDS (供流片用)
- `framework/` — SiEPIC 验证流程 Python 脚本 (run_verification.py 等)
- `measurements/` — 测量结果 JPEG 图像
- `LICENSE` + `README.md` — 原仓库许可与说明

## 选择性提取声明 (R03 合规)

原仓库含 1755 个 `.mat` 测量数据文件 (数百 MB),本数据集**未包含** `.mat` 文件以节省磁盘空间。如需原始测量数据,请从 GitHub 直接获取。GDS 设计文件 100% 完整保留,无任何 fall-back 或假数据。

## 用途

- 端到端 GDS 验证回归基准 (DRC/LVS/netlist extraction)
- BC/RL 训练的真实版图样本 (213+ 个不同设计师的不同风格)
- 商用版自动布局布线对真实学生/研究者设计的鲁棒性测试

## 引用

```bibtex
@inproceedings{chrostowski2024openebl,
  title={SiEPIC openEBL: remote silicon photonic design, fabrication, testing enabled by open-source PDKs and EDA tools},
  author={Chrostowski, Lukas and others},
  booktitle={SPIE Photonics West},
  year={2024},
  doi={10.1117/12.3076810}
}
@book{chrostowski2015silicon,
  title={Silicon Photonics Design},
  author={Chrostowski, Lukas and Hochberg, Michael},
  publisher={Cambridge University Press},
  year={2015},
  isbn={9781107016838}
}
```
