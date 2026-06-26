# 规则 R20：3dtool 大文件管理规范（强制）

## 20.1 单文件大小限制

- `3dtool/` 目录下**单个文件大小上限为 100 MB**（含 wheel 包、分卷片段、复刻品源码、文档等所有文件）
- 超过 100 MB 的文件必须按以下方式处理：
  1. **wheel 包**：使用 `gzip + split` 分卷为 ≤20 MB 片段存放到 `3dtool/wheels/parts/`（规则 5.1.1）
  2. **数据文件**：拆分为多个小文件，或使用 Git LFS 管理
  3. **模型 checkpoint**：存放至 `checkpoints/` 并加入 `.gitignore`，不提交到 git
  4. **二进制资源**：压缩后仍超 100 MB 的，必须使用外部存储（OSS/S3/HuggingFace Hub）并在 README 标注下载方式

## 20.2 检查命令

```bash
# 检查 3dtool/ 下超过 100MB 的文件
find 3dtool/ -type f -size +100M -exec ls -lh {} \;
# 检查全部超 100MB 文件（不含 .git/）
find . -path ./.git -prune -o -type f -size +100M -print
```

## 20.3 处理流程

1. **新增文件前预估**：下载/生成大文件前先预估大小，超 100 MB 直接走分卷/外部存储
2. **定期巡检**：CI 中执行检查命令，发现超限文件立即告警
3. **历史文件整改**：已存在的超限文件须在下一个版本前完成整改
4. **例外白名单**：仅 `3dtool/wheels/parts/` 下的分卷片段允许 ≤20 MB（更严格），无任何文件可超 100 MB

## 20.4 禁止行为

- ❌ 禁止提交 >100 MB 的文件到 git（GitHub 会拒绝，且克隆/拉取极慢）
- ❌ 禁止用 `git add -A` 一次性添加大量大文件
- ❌ 禁止将模型 checkpoint（`.pt`/`.pth`/`.json` >100 MB）提交到 git
- ❌ 禁止在 `3dtool/` 下存放视频/数据集等非工具类大文件

来源: GitHub 文件大小限制 https://docs.github.com/en/repositories/working-with-files/managing-large-files | Git LFS https://git-lfs.com/ | split 分卷 https://www.gnu.org/software/coreutils/manual/html_node/split-invocation.html
