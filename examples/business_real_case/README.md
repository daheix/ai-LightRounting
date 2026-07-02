# PoLaRIS 业务侧真实调用示例：100Gbps MZI 调制器设计

对标 **Intel 100G CWDM4 QSFP28 Optical Module**，展示如何用 PoLaRIS 的
8 个独立子模块 + orchestrator 编排层完成完整 PIC 设计流程。

## 电路设计

100Gbps MZI 调制器（5 器件 5 连接）:

```
[GC1] →out→in→ [MMI1] →out1→in→ [PS1] →out→in1→ [MMI2] →out1→in→ [GC2]
                       →out2→in2→───────────────────→
```

| 器件 | 类型 | 参数 | 来源 |
|------|------|------|------|
| GC1/GC2 | grating_coupler | insertion_loss=1.9dB @ 1550nm | SiEPIC EBeam PDK |
| MMI1 | mmi_1x2 | insertion_loss=0.4dB, split_ratio=0.48:0.52 | Soldano & Pennings 1995 |
| PS1 | phase_shifter | neff=2.4, 臂长 100μm | Soref 1993 |
| MMI2 | mmi_2x2 | insertion_loss=0.5dB | SiEPIC EBeam PDK |

画布 500×300μm，工艺节点 220nm SOI，工作波长 1550nm。

## 两种调用方式

### 方式 A：orchestrator 一键调用（推荐）

`run_eda_flow(circuit, output_dir)` 自动执行 9 个 stage:

1. PDK 目录 → 2. 电路验证 → 3. AI 布局 → 4. 智能布线 →
5. 仿真验证 → 6. DRC/LVS → 7. GDS 导出 → 8. 逆向设计 → 9. 量子验证

适合自动化流程（batch 生成、CI 流水线）。

### 方式 B：直接调用 8 个子模块 API（精细控制）

逐步调用 `polaris_core` / `polaris_pdk` / `polaris_place` / `polaris_route` /
`polaris_sim` / `polaris_drc` / `polaris_lvs` / `polaris_inverse` / `polaris_quantum`，
逐步打印中间结果，适合需要自定义处理或调试的场景。

## 运行

### Python 版

```bash
cd /workspace
python examples/business_real_case/main.py
```

输出（示例）:

```
============================================================
PoLaRIS 业务侧真实调用示例：100Gbps MZI 调制器设计
对标：Intel 100G CWDM4 QSFP28 Optical Module
============================================================
输出目录: /workspace/out/business_real_case

============================================================
方式 A: orchestrator 一键调用（推荐，自动化流程）
============================================================
[orchestrator] 9 stage 全流程完成，总耗时 26.45s
  汇总: n_success=9 n_failed=0 n_skipped=0 total_duration=26.45s
  ...
============================================================
方式 B: 直接调用 8 个子模块 API（精细控制）
============================================================
[1/8] polaris_core: 电路构建与验证
  电路 MZI_100G: 5 器件, 5 连接, 画布 500×300μm, λ=1550.0nm
  ...
[8/8] polaris_inverse: JAX Adjoint 逆向设计（n_iterations=10 省时）
  ...
[+] polaris_quantum: 量子光子验证
  ...
```

依赖: `numpy` / `jax` / `klayout`（均已含在 PoLaRIS requirements 中）。

### C 版

```bash
cd /workspace/examples/business_real_case

# 仅验证头文件包含通过（无需链接子模块 C 实现）
make check_headers

# 编译（需链接子模块 C 实现 libpolaris_cabi.so）
make

# 运行（需 libpolaris_cabi.so 在 LD_LIBRARY_PATH 中）
./polaris_business_case
```

**说明**: 当前 PoLaRIS 主路径为 Python，C ABI 头文件先行声明接口
（`modules/*/c_api/*.h`）。`make check_headers` 验证头文件包含通过，
`make` 编译需链接子模块 C 实现（`libpolaris_cabi.so`，待构建）。

## 文件清单

| 文件 | 说明 |
|------|------|
| `main.py` | Python 业务侧调用（方式 A + 方式 B） |
| `main.c` | C 业务侧调用（8 子模块 + orchestrator C ABI） |
| `Makefile` | C 版编译/头文件校验 |
| `README.md` | 本文档 |

## 输出产物

运行后 GDSII 等产物落盘到 `out/business_real_case/`:

- `MZI_100G.gds` — GDSII 版图文件（可被 KLayout 加载）

## 学术诚信（R02）

所有器件参数、物理公式、损耗模型均有文献溯源，详见 `main.py` / `main.c`
文件头 docstring。核心来源:

- Intel 100G CWDM4: https://www.intel.com/content/www/us/en/products/network-io/100g-cwdm4-smsr.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Soref 1993 IEEE Proc. 41(9): https://ieeexplore.ieee.org/document/1148303
- Saleh & Teich, "Fundamentals of Photonics", Wiley 2019, §4.4
- Soldano & Pennings, J. Lightwave Technol. 1995: https://ieeexplore.ieee.org/document/374358
- Shafik et al., IEEE CommSurveys 2016: https://ieeexplore.ieee.org/document/7410082
- Clements et al., Optica 2016: https://opg.optica.org/optica/fulltext.cfm?uri=optica-3-12-1460

## 设计原则

- **禁止 fall-back（R03）**: 任何子模块失败即 raise/返回错误码，不返回假数据
- **不参与 GPU（R04）**: 纯 NumPy/JAX(CPU)/klayout 实现
- **学术诚信（R02）**: 所有参数可溯源
