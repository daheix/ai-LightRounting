# 3dtool 分片仓库 (daheix/3dtool)

本仓库仅存放 **3dtool-appimage 统一 AppDir 的分片压缩包** 及配套脚本。

主仓库 `daheix/ai-ddr5` 不直接保存大文件,通过 clone 本仓库 + 运行恢复脚本
重建 `3dtool/3dtool-appimage/` 工作目录。

## 仓库结构

```
3dtool/                                # 本仓库的子目录 (与主仓库路径一致)
├── appimage-parts/                    # 分片压缩包 (17 片, 共 1.6G, 每片 ≤95M)
│   ├── 3dtool-appimage.tar.gz.part_aa
│   ├── 3dtool-appimage.tar.gz.part_ab
│   ├── ...
│   ├── 3dtool-appimage.tar.gz.part_aq
│   └── parts.md5                      # 分片 MD5 校验和
├── scripts/
│   └── restore_3dtool_appimage.sh     # 跨仓库恢复脚本
└── tools/
    ├── build_3dtool_appimage.sh       # 重新构建统一 AppDir 的脚本
    └── build_openems_appimage.sh
```

## 统一 AppDir 包含的工具

`3dtool-appimage/` 自包含以下工具链 (无需外部依赖):
- Python 3.14
- C++ / Fortran 工具链
- Java JRE
- KiCad (含 ngspice、pcbnew、eeschema 等)
- openEMS / ElmerFEM
- 各类 .so 共享库

通过 `AppRun <tool> [args]` 统一调用, `AppRun check` 自检 25 项工具。

## 在主仓库 ai-ddr5 中恢复

```bash
# 1. 在主仓库 ai-ddr5 工作目录中, clone 本分片仓库到临时目录
cd /path/to/ai-ddr5
git clone https://github.com/daheix/3dtool.git /tmp/3dtool-parts

# 2. 运行恢复脚本, 指定目标路径 3dtool/3dtool-appimage
bash /tmp/3dtool-parts/3dtool/scripts/restore_3dtool_appimage.sh 3dtool/3dtool-appimage

# 3. 清理临时仓库 (分片已解压, 无需保留)
rm -rf /tmp/3dtool-parts

# 4. 验证
bash 3dtool/3dtool-appimage/AppRun check
```

## 校验分片完整性

```bash
cd 3dtool/appimage-parts
md5sum -c parts.md5
```

## 重新构建 (可选)

若需从源码重新构建统一 AppDir (而非用分片), 使用:
```bash
bash 3dtool/tools/build_3dtool_appimage.sh
```

## 分片说明

- 单文件 ≤95M, 满足 GitHub 100M 单文件限制
- 17 个分片, 合并后为 `3dtool-appimage.tar.gz` (1.6G)
- tar 包内顶层目录为 `3dtool-appimage/`, 解压即得可用 AppDir
- kicad/torch 等已包含在统一 AppDir 内, 不再单独存放分片
