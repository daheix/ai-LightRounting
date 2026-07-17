"""修复 3dtool/ 死引用（R02 学术诚信 / R03 禁止假数据）。

事实核查（2026-07-17）:
- /workspace/3dtool 目录不存在，git 历史无记录（git log --all -- 3dtool 为空）
- 3dtool/INVENTORY.md 内容已迁移为 2026-2028开发计划/三方库清单与商用许可分析.md
  （该文档标题即"三方库完整清单与商用许可分析（INVENTORY.md）"）
- 3dtool/ALGORITHMS.md（8 求解器公式手册）内容已分散并入 A01-A09 聚类文档:
  §1 RCWA→A01, §2 EME→A02, §3 BPM→A03, §4 HEAT→A07, §5 DDM→A08,
  §6 FDE→A04, §7 FDFD→A05, §8 2.5D-FDTD→A06, 附录C Yee网格→A09

替换策略:
1. 功能清单与实现/ 内: ALGORITHMS 章节引用 → 对应 A0x 聚类文档（同目录相对引用）
2. 功能清单与实现/ 内: INVENTORY → ../三方库清单与商用许可分析.md
3. 三方库清单与商用许可分析.md 内部: [ALGORITHMS.md#x](ALGORITHMS.md) → 功能清单与实现/A0x
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path("/workspace")
FEAT = ROOT / "2026-2028开发计划" / "功能清单与实现"
INV_DOC = ROOT / "2026-2028开发计划" / "三方库清单与商用许可分析.md"

stats = {"algo": 0, "inv": 0, "appendix": 0}
changed: list[str] = []

# ---- 功能清单与实现/ 目录内替换（按特异性降序） ----
FEAT_RULES: list[tuple[str, str]] = [
    # 带章节的具体引用 → 对应 A0x 文档
    ("`3dtool/ALGORITHMS.md` §8（2.5D-FDTD 共享 Yee 网格）",
     "`A06-2.5D-FDTD变分FDTD.md`（Yee 网格共享见 `A09-FDTD时域有限差分.md`）"),
    ("`3dtool/ALGORITHMS.md` §4（HEAT）", "`A07-HEAT热传导求解.md`"),
    ("`3dtool/ALGORITHMS.md` §5（DDM）", "`A08-DDM漂移扩散求解.md`"),
    ("`3dtool/ALGORITHMS.md` §1.5/§2.5", "`C03-Redheffer星积S矩阵级联.md`"),
    ("`3dtool/ALGORITHMS.md` 第 2 节", "`A02-EME本征模展开.md`"),
    ("`3dtool/ALGORITHMS.md` 第 3 节", "`A03-BPM光束传播.md`"),
    ("`3dtool/ALGORITHMS.md` 第 6 节", "`A04-FDE本征模求解.md`"),
    ("`3dtool/ALGORITHMS.md` 第 7 节", "`A05-FDFD频域有限差分.md`"),
    ("`3dtool/ALGORITHMS.md` 第 8 节", "`A06-2.5D-FDTD变分FDTD.md`"),
    ("`3dtool/ALGORITHMS.md` §1", "`A01-RCWA严格耦合波分析.md`"),
    ("`3dtool/ALGORITHMS.md` §4", "`A07-HEAT热传导求解.md`"),
    ("`3dtool/ALGORITHMS.md` §5", "`A08-DDM漂移扩散求解.md`"),
    # 描述性引用
    ("`3dtool/ALGORITHMS.md`（8 求解器公式手册）",
     "A01-A09 求解器聚类文档（公式手册内容已并入各聚类）"),
    ("`3dtool/ALGORITHMS.md`（求解器公式手册）",
     "A01-A09 求解器聚类文档"),
    ("`3dtool/INVENTORY.md`（102 三方库）",
     "`../三方库清单与商用许可分析.md`（102 三方库）"),
    ("`3dtool/INVENTORY.md`（102 库）",
     "`../三方库清单与商用许可分析.md`（102 库）"),
    # 00-算法聚类清单.md 正文引用
    ("对应 ALGORITHMS.md 8 求解器", "对应 A01-A09 求解器聚类"),
    ("ALGORITHMS.md 已完成公式推导与文献溯源",
     "A01-A09 聚类文档已完成公式推导与文献溯源"),
    ("按 ALGORITHMS.md 公式手册逐一实现 A01-A09",
     "按各聚类文档公式逐一实现 A01-A09"),
    ("求解器算法公式来源 `3dtool/ALGORITHMS.md`，已溯源",
     "求解器算法公式来源 A01-A09 聚类文档文献章节，已溯源"),
    ("三方库清单依据 `3dtool/INVENTORY.md`",
     "三方库清单依据 `../三方库清单与商用许可分析.md`"),
    # 附录 C（Yee 网格共享）
    ("ALGORITHMS.md 附录 C 共享组件", "`A09-FDTD时域有限差分.md` §2 Yee 网格共享组件"),
    ("ALGORITHMS.md 附录 C", "`A09-FDTD时域有限差分.md` §2"),
    # 剩余单独引用 → 00-算法聚类清单.md
    ("`3dtool/ALGORITHMS.md`", "`00-算法聚类清单.md`"),
    ("`3dtool/INVENTORY.md`", "`../三方库清单与商用许可分析.md`"),
]

for md in sorted(FEAT.glob("*.md")):
    text = md.read_text(encoding="utf-8")
    orig = text
    for old, new in FEAT_RULES:
        if old in text:
            n = text.count(old)
            text = text.replace(old, new)
            if "INVENTORY" in old:
                stats["inv"] += n
            elif "附录" in old:
                stats["appendix"] += n
            else:
                stats["algo"] += n
    if text != orig:
        md.write_text(text, encoding="utf-8")
        changed.append(f"功能清单与实现/{md.name}")

# ---- 三方库清单与商用许可分析.md 内部死链接 ----
INV_RULES: list[tuple[str, str]] = [
    ("[ALGORITHMS.md#1-rcwa](ALGORITHMS.md)",
     "[A01-RCWA严格耦合波分析.md](功能清单与实现/A01-RCWA严格耦合波分析.md)"),
    ("[ALGORITHMS.md#eme](ALGORITHMS.md)",
     "[A02-EME本征模展开.md](功能清单与实现/A02-EME本征模展开.md)"),
    ("[ALGORITHMS.md#bpm](ALGORITHMS.md)",
     "[A03-BPM光束传播.md](功能清单与实现/A03-BPM光束传播.md)"),
    ("[ALGORITHMS.md#heat](ALGORITHMS.md)",
     "[A07-HEAT热传导求解.md](功能清单与实现/A07-HEAT热传导求解.md)"),
    ("[ALGORITHMS.md#ddm](ALGORITHMS.md)",
     "[A08-DDM漂移扩散求解.md](功能清单与实现/A08-DDM漂移扩散求解.md)"),
    ("[ALGORITHMS.md#fde](ALGORITHMS.md)",
     "[A04-FDE本征模求解.md](功能清单与实现/A04-FDE本征模求解.md)"),
    ("[ALGORITHMS.md#fdfd](ALGORITHMS.md)",
     "[A05-FDFD频域有限差分.md](功能清单与实现/A05-FDFD频域有限差分.md)"),
    ("[ALGORITHMS.md#25d-fdtd](ALGORITHMS.md)",
     "[A06-2.5D-FDTD变分FDTD.md](功能清单与实现/A06-2.5D-FDTD变分FDTD.md)"),
    ("ALGORITHMS.md（核心求解器算法公式手册）",
     "功能清单与实现/A01-A09（核心求解器算法公式已并入各聚类文档）"),
    ("指向 ALGORITHMS.md 的对应章节", "指向 功能清单与实现/ 对应聚类文档"),
    ("指向 ALGORITHMS.md", "指向 功能清单与实现/"),
    ("详见 ALGORITHMS.md 对应章节", "详见 功能清单与实现/ 对应聚类文档"),
    ("详见 ALGORITHMS.md", "详见 功能清单与实现/A01-A09"),
    ("（ALGORITHMS.md#FDFD）", "（功能清单与实现/A05-FDFD频域有限差分.md）"),
    ("（ALGORITHMS.md#FDE）", "（功能清单与实现/A04-FDE本征模求解.md）"),
    ("（ALGORITHMS.md#2.5d-fdtd）", "（功能清单与实现/A06-2.5D-FDTD变分FDTD.md）"),
]

if INV_DOC.exists():
    text = INV_DOC.read_text(encoding="utf-8")
    orig = text
    for old, new in INV_RULES:
        if old in text:
            stats["algo"] += text.count(old)
            text = text.replace(old, new)
    if text != orig:
        INV_DOC.write_text(text, encoding="utf-8")
        changed.append("三方库清单与商用许可分析.md")

print(f"修改文件数: {len(changed)}")
print(f"ALGORITHMS 引用替换: {stats['algo']}  INVENTORY 引用替换: {stats['inv']}  附录C: {stats['appendix']}")
for f in changed:
    print(f"  {f}")
