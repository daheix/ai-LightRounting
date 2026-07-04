# Checklist

## 真实用例统一目录
- [ ] `data/real_circuits/` 目录结构已创建（6 个来源子目录）
- [ ] `scripts/consolidate_real_circuits.py` 已创建
- [ ] 417 个真实用例已合并到统一目录
- [ ] `data/real_circuits/index.json` 已生成（含 name/source/format/path/origin_url/license）
- [ ] 合并后用例数 = 417，无丢失

## 真实用例上传 GitHub
- [ ] 仓库体积检查通过（无超过 100MB 单文件）
- [ ] git add data/real_circuits/ → commit → push origin main 完成
- [ ] GitHub 远端可见真实用例

## 真实用例格式转换
- [ ] `scripts/convert_real_to_polaris.py` 已创建
- [ ] SiEPIC GDS → CircuitSpec 转换可用（klayout 读取）
- [ ] gdsfactory netlist → CircuitSpec 转换可用
- [ ] picbench/lidar JSON → CircuitSpec 转换可用
- [ ] 转换后合法性校验通过
- [ ] 转换报告已生成（成功/失败数 + 失败根因）

## 真实板子端到端测试
- [ ] `scripts/test_real_circuits.py` 已创建
- [ ] 417 个真实用例端到端测试完成
- [ ] 成功率、DRC 通过率、平均损耗、平均耗时已汇报
- [ ] 与程序化 1200 电路结果对比完成
- [ ] 失败用例根因分析完成

## 基于真实板子组合生成
- [ ] `scripts/generate_combination_circuits.py` 已创建
- [ ] 拓扑组件提取完成（MZI/Ring/DC/MMI/Switch/Modulator/WDM）
- [ ] 二元组合 ≥420 个
- [ ] 多元组合 ≥50 个
- [ ] 规模扩展 ≥28 个
- [ ] 总数 ≥500 个组合电路
- [ ] 输出到 `data/benchmarks/combinations/`

## 组合电路测试
- [ ] ≥500 个组合电路端到端测试完成
- [ ] 成功率、DRC 通过率、平均损耗已汇报
- [ ] 失败组合根因分析完成
- [ ] 与真实+程序化结果对比完成

## 商用版最终测试报告
- [ ] `docs/商用版最终测试报告.md` 已生成
- [ ] 总体统计（≥2100 电路）完成
- [ ] 真实/组合/程序化三组对比完成
- [ ] 商用发布结论明确

## 代码提交与操作记录
- [ ] 每个小任务完成后 git add 精确文件 → commit → push origin main
- [ ] `操作记录.md` 已追加本轮记录
- [ ] 无 fall-back 残留（R03）
- [ ] 无 TODO/FIXME/HACK 残留（R05）
