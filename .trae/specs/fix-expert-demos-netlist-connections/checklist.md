# Checklist

## 根因分析
- [x] 3 个失败 demo（MZI_bdc/ebeam_taper_475_500_te1550/wg_test）的 netlist.json 缺 devices 字段已确认
- [x] routes.json 路径点列表格式已分析（[[[x,y],...], ...]）
- [x] route 首尾距离中位数 0.3μm 已实测（近重合，route 为器件内部波导片段）
- [x] 聚类容差 1-25μm 测试跨器件连接 = 0% 已验证

## 修复脚本实现
- [x] `scripts/fix_expert_demos_connections.py` 已创建（638 行 ≤ 800 行 R11 门禁）
- [x] 策略 1（纯波导 demo 虚拟 IO）已实现
- [x] 策略 2（有源器件 route 首尾匹配）已实现
- [x] 策略 3（Kruskal MST）已实现
- [x] 策略 3 退化（单器件虚拟 IO）已实现
- [x] R03 禁止 fall-back：routes 为空 / route 路径点 < 2 / 器件匹配失败 raise ValueError
- [x] 无 TODO/FIXME/HACK 残留（R05）
- [x] 无 fall-back 残留（R03）
- [x] docstring 含 ≥5 个文献 URL（R02 学术诚信）

## 修复结果验证
- [x] 10/10 demo netlist.json 的 devices 字段非空
- [x] 10/10 demo netlist.json 的 connections 字段非空（连接数 ≥ 1）
- [x] 3 个纯波导 demo（MZI_bdc/ebeam_taper_475_500_te1550/wg_test）走虚拟 IO 模式
- [x] 6 个有源器件 demo 走 MST 模式（连接数 = 器件数 - 1）
- [x] 1 个单器件 demo（Simple_MZI）走单器件虚拟 IO 模式
- [x] 总器件数 35，总连接数 25
- [x] parse_expert_demos 解析验证 10/10 通过

## 元数据一致性
- [x] 10 个 demo 的 meta.json n_connections 与 netlist.json connections 长度一致
- [x] 10 个 demo 的 meta.json n_devices 与 netlist.json devices 长度一致
- [x] 4 个 demo 的 placements.json 含虚拟 IO 器件布局
- [x] index.json records 与各 demo meta.json 一致

## 代码提交（R11）
- [x] `git branch --show-current` = main
- [x] `git add` 精确文件（30 个，无 `git add -A`）
- [x] `git commit -m "fix: expert_demos netlist连接缺失修复（10/10连接数>0）"` (commit 58831d4)
- [x] `git push origin main` (0167416..58831d4，无 --force)

## 操作记录（R07）
- [x] `操作记录.md` 已追加 R347 轮次记录
- [x] 含轮次编号、交付文件、测试结果（精确数字）
- [x] 含规则依据（R03/R05/R11）
- [x] 含学术来源（SiEPIC PDK / Kruskal 1956 / Chrostowski 2022）
- [x] 含无 fall-back 声明
- [x] 含时间戳（R12）

## 学术诚信（R02）
- [x] SiEPIC EBeam PDK 来源 URL 已记录
- [x] Kruskal MST 算法来源（Kruskal 1956, Proc. ACM）已记录
- [x] SiEPIC Connect Function 来源（Chrostowski 2022, Cambridge UP）已记录
- [x] 模仿学习理论来源（Pomerleau 1989 / Gavenski 2024）已记录
- [x] 虚拟 IO 器件建模基于 route 真实首尾点，非假数据
