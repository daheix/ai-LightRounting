# AGENTS.md — PoLaRIS 智能体上下文规则

> PoLaRIS（光弈）光电子AI智能布局布线引擎。所有规则必须严格遵守。

## 1. 启动第一件事
```bash
nohup bash scripts/keepalive.sh > /dev/null 2>&1 &  # 保活防超时
git branch --show-current  # 必须在 main
ps aux | grep auto_commit  # V8 每 6 分钟自动提交
ps aux | grep keepalive   # 保活脚本在运行
```

## 2. 分支与提交（V8 极简）
- **只用 main 分支**，禁止 dev/feature/worktree
- 每个小任务完成后：`git add <精确文件名>` → `git commit -m "<type>: <简述>"` → `git push origin main`
- 禁止：`git add -A` / `--force` / 分支切换

## 3. 任务派发前核查（防止重复造轮子）
必须依次执行：
```bash
git log --all --oneline --follow -- <文件>  # 查 git 历史
grep <功能名> 操作记录.md                     # 查操作记录
ls <目标路径>                               # 查现有文件
```
git 有 commit + 操作记录有 → 跳过；目标文件存在 → 必须 Read 后再决定。

## 4. 操作记录
每任务完成后 **5 分钟内**追加到 `操作记录.md`：轮次编号、交付文件、测试结果（精确数字）、规则依据。

## 5. 禁止 fall-back（R03）
失败即 raise，禁止静默兜底。禁止 `except: pass` / `return None` / `return []`。

## 6. 学术诚信（R02）
所有参数/公式必须有文献溯源（作者、年份、URL），创新点标注 `*创新*`。

## 7. Bug 处理（R05）
发现即修，附回归测试，禁止 TODO/FIXME/HACK 残留到提交。

## 8. 质量门禁
函数≤80行 / 文件≤800行 / 圈复杂度≤15 / 测试覆盖率≥90%。

## 9. GPU 战略（R04，不可撤销）
不参与 GPU 计算。禁止 CuPy/CUDA/ROCm。纯 NumPy/SciPy/JAX(CPU)。

## 10. 磁盘空间
日志上限 10MB（RotatingFileHandler）。空间不足时删：swiftly(6.5G)/mise(3.0G)/rustup(1.8G)。

## 11. 监控脚本
- `scripts/auto_commit.py V8`：每 6 分钟检测变更→提交→push
- `scripts/keepalive.sh`：每 5 分钟 touch 防超时

## 12. 关键文件
- `操作记录.md`：所有操作记录
- `.trae/rules/R11-工作流规范.md`：V8 完整规则
- `src/polaris/`：源代码
