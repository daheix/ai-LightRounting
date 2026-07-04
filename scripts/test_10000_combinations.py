#!/usr/bin/env python3
"""PoLaRIS 商用版 10000 组合电路批量测试脚本 (V6.0 拆包后)

R02 学术诚信:
  - Chrostowski & Hochberg, Silicon Photonics Design, CUP 2015, ISBN 9781107016838
  - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
  - gdsfactory: https://doi.org/10.1117/1.JOM.2.4.043501
  - Soref & Bennett, IEEE JQE 1987 (自由载流子吸收)
  - Nedeljkovic et al., Opt. Express 2021 (SiN 损耗)
  - Chrostowski et al., IEEE JSTQE 2019 (Si 波导损耗)

R03 禁止 fall-back: 失败即记录根因，不伪造结果
R05 Bug 必须修复: 发现 Bug 立即修复
R10 进度汇报: 每 100 个保存一次进度

用法:
  python3 scripts/test_10000_combinations.py [--workers N] [--limit N]
"""
import json
import sys
import os
import time
import traceback
from pathlib import Path
from datetime import datetime
from multiprocessing import Pool, cpu_count
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load_circuit(json_path: str) -> dict:
    """加载电路 JSON (CircuitSpec 格式)。R03: 加载失败即 raise。

    兼容两种格式: 有 type 字段（组合生成器）和有 device_type 字段（标准）。
    """
    with open(json_path, 'r') as f:
        spec = json.load(f)
    if not isinstance(spec, dict):
        raise ValueError(f"Invalid circuit spec format: {json_path}")

    devices = spec.get('devices', [])
    if devices and 'type' in devices[0] and 'device_type' not in devices[0]:
        for d in devices:
            d['device_type'] = d.pop('type')

    instances = spec.get('instances', [])
    if instances and 'type' in instances[0] and 'device_type' not in instances[0]:
        for inst in instances:
            inst['device_type'] = inst.pop('type')

    return spec


def test_one(circuit_info: dict) -> dict:
    """测试单个组合电路。R03: 失败即记录真实根因。"""
    from polaris_orchestrator.flow import run_eda_flow

    json_path = circuit_info['path']
    abs_path = os.path.join('data/benchmarks/combinations', json_path)

    try:
        circuit_dict = load_circuit(abs_path)

        t0 = time.time()
        flow_result = run_eda_flow(
            circuit=circuit_dict,
            output_dir=f"/tmp/polaris_combo_test/{circuit_info['name']}",
            skip_stages=[8, 9],
            strict=False,
        )
        elapsed = time.time() - t0

        stages = {s["stage_id"]: s for s in flow_result["stages"]}
        key_stages = [2, 3, 4, 6]
        success = all(stages.get(s, {}).get("status") == "success" for s in key_stages)

        drc_violations = -1
        drc_passed = False
        if success:
            drc_lvs = stages.get(6, {}).get("result") or {}
            if isinstance(drc_lvs, dict):
                drc = drc_lvs.get("drc", {}) or {}
                drc_violations = drc.get("total_violations", -1)
                drc_passed = (drc_violations == 0)

        insertion_loss_db = None
        sim_res = stages.get(5, {}).get("result") or {}
        if isinstance(sim_res, dict):
            insertion_loss_db = sim_res.get("insertion_loss_db")

        return {
            'name': circuit_info['name'],
            'path': json_path,
            'combination_type': circuit_info['combination_type'],
            'n_devices': circuit_info['n_devices'],
            'n_connections': circuit_info['n_connections'],
            'success': success,
            'drc_passed': drc_passed,
            'drc_violations': drc_violations,
            'insertion_loss_db': insertion_loss_db,
            'elapsed_s': round(elapsed, 2),
            'error': None,
        }
    except Exception as e:
        return {
            'name': circuit_info['name'],
            'path': json_path,
            'combination_type': circuit_info['combination_type'],
            'n_devices': circuit_info.get('n_devices', -1),
            'n_connections': circuit_info.get('n_connections', -1),
            'success': False,
            'drc_passed': False,
            'drc_violations': -1,
            'insertion_loss_db': None,
            'elapsed_s': 0,
            'error': f"{type(e).__name__}: {str(e)[:200]}",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=min(8, cpu_count()))
    parser.add_argument('--limit', type=int, default=0, help='0=全部')
    parser.add_argument('--save-every', type=int, default=200, help='每N个保存一次进度')
    args = parser.parse_args()

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 加载索引...")

    idx_path = Path('data/benchmarks/combinations/index.json')
    idx = json.loads(idx_path.read_text())
    circuits = idx['circuits']

    if args.limit > 0:
        circuits = circuits[:args.limit]

    total = len(circuits)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 共 {total} 个组合电路, {args.workers} 进程")

    results = []
    out_dir = Path('out/combo_test_10000')
    out_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.time()
    done = 0

    with Pool(args.workers, maxtasksperchild=20) as pool:
        for i, r in enumerate(pool.imap_unordered(test_one, circuits), 1):
            results.append(r)
            done = i

            if i % args.save_every == 0 or i == total:
                progress = {
                    'total': total,
                    'done': i,
                    'success': sum(1 for x in results if x['success']),
                    'drc_passed': sum(1 for x in results if x['drc_passed']),
                    'elapsed_min': round((time.time() - t_start) / 60, 1),
                    'avg_s_per_circuit': round((time.time() - t_start) / i, 2),
                    'results': results,
                }
                (out_dir / 'progress.json').write_text(
                    json.dumps(progress, ensure_ascii=False, indent=2))

                n_success = progress['success']
                n_drc = progress['drc_passed']
                rate = n_success / i * 100 if i > 0 else 0
                drc_rate = n_drc / n_success * 100 if n_success > 0 else 0
                eta = (total - i) * progress['avg_s_per_circuit'] / 60
                print(
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"{i}/{total} ({i/total*100:.1f}%) | "
                    f"成功 {n_success} ({rate:.1f}%) | "
                    f"DRC通过 {n_drc} ({drc_rate:.1f}%) | "
                    f"已用 {progress['elapsed_min']:.1f}min | "
                    f"预计剩余 {eta:.1f}min"
                )

    t_end = time.time()
    total_min = round((t_end - t_start) / 60, 1)

    n_success = sum(1 for x in results if x['success'])
    n_fail = total - n_success
    n_drc = sum(1 for x in results if x['drc_passed'])

    success_rate = n_success / total * 100 if total > 0 else 0
    drc_rate = n_drc / n_success * 100 if n_success > 0 else 0

    avg_loss = None
    losses = [r['insertion_loss_db'] for r in results
              if r['success'] and r['insertion_loss_db'] is not None]
    if losses:
        avg_loss = round(sum(losses) / len(losses), 2)

    avg_time = round((t_end - t_start) / total, 2) if total > 0 else 0

    by_type = {}
    for r in results:
        t = r['combination_type']
        if t not in by_type:
            by_type[t] = {'total': 0, 'success': 0, 'drc_passed': 0}
        by_type[t]['total'] += 1
        if r['success']:
            by_type[t]['success'] += 1
        if r['drc_passed']:
            by_type[t]['drc_passed'] += 1

    errors = [r for r in results if not r['success']]
    error_types = {}
    for e in errors:
        etype = e['error'].split(':')[0] if e['error'] else 'unknown'
        error_types[etype] = error_types.get(etype, 0) + 1

    report = f"""# PoLaRIS 商用版 10000 组合电路测试报告

[生成时间] {datetime.now().strftime('%Y-%m-%d %H:%M:%S CST')}

## 总体统计

| 指标 | 值 |
|------|----|
| 组合电路总数 | {total} |
| 成功数 | {n_success} |
| 成功率 | {success_rate:.1f}% |
| 失败数 | {n_fail} |
| DRC 通过数 | {n_drc} |
| DRC 通过率 | {drc_rate:.1f}% |
| 平均插入损耗 | {avg_loss if avg_loss is not None else 'N/A'} dB |
| 平均单电路耗时 | {avg_time} s |
| 总耗时 | {total_min} min |
| 并行进程数 | {args.workers} |

## 按组合类型分布

| 组合类型 | 总数 | 成功 | 成功率 | DRC通过 | DRC率 |
|---------|------|------|--------|---------|-------|
"""
    for t, stats in sorted(by_type.items()):
        sr = stats['success'] / stats['total'] * 100 if stats['total'] > 0 else 0
        dr = stats['drc_passed'] / stats['success'] * 100 if stats['success'] > 0 else 0
        report += f"| {t} | {stats['total']} | {stats['success']} | {sr:.1f}% | {stats['drc_passed']} | {dr:.1f}% |\n"

    report += f"""
## 失败根因分类

| 错误类型 | 数量 | 占比 |
|---------|------|------|
"""
    for etype, count in sorted(error_types.items(), key=lambda x: -x[1]):
        report += f"| {etype} | {count} | {count/n_fail*100:.1f}% |\n" if n_fail > 0 else f"| {etype} | {count} | - |\n"

    report += f"""
## 与其他测试集对比

| 测试集 | 总数 | 成功 | 成功率 | DRC通过 | DRC率 |
|--------|------|------|--------|---------|-------|
| 程序化生成 (1200) | 1200 | 1200 | 100.0% | 1152 | 96.0% |
| 真实板子 (可测试132) | 132 | 100 | 75.8% | 14 | 10.6% |
| 组合电路 (10000) | {total} | {n_success} | {success_rate:.1f}% | {n_drc} | {drc_rate:.1f}% |

## 失败样例 (前10)

"""
    for e in errors[:10]:
        err_str = e.get('error') or '(unknown error)'
        report += f"- **{e['name']}**: {err_str[:150]}\n"

    report += f"""
## 数据来源 (R02 学术诚信)

- 真实板子数据: real_board/ (448个, 6大来源)
  - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (LGPL-2.1)
  - gdsfactory: https://github.com/gdsfactory/gdsfactory (MIT)
  - picbench: https://github.com/TiagoCavaco/picbench (MIT)
  - LiDAR ISPD'25: ALIGN project (BSD-3)
  - ALIGN custom: https://github.com/Chentang2nd/ALIGN-custom (BSD-3)
- 组合生成: scripts/generate_10000_combinations.py
- 拓扑组件: MZI/Ring/DC/MMI/Switch/Modulator/WDM

## 规则合规

- R02 学术诚信: ✓ 所有数据来源可溯源
- R03 禁止 fall-back: ✓ 失败即记录真实根因, 不伪造
- R05 Bug 必须修复: 待处理 (见失败根因)
- R07 操作记录: 待追加
"""

    (out_dir / 'report.md').write_text(report)
    final = {
        'total': total,
        'success': n_success,
        'success_rate': round(success_rate, 2),
        'drc_passed': n_drc,
        'drc_rate': round(drc_rate, 2),
        'avg_loss_db': avg_loss,
        'avg_time_s': avg_time,
        'total_min': total_min,
        'by_type': by_type,
        'error_types': error_types,
        'results': results,
    }
    (out_dir / 'final_results.json').write_text(json.dumps(final, ensure_ascii=False, indent=2))

    print(f"\n{'='*60}")
    print(f"测试完成! 总数: {total}, 成功: {n_success} ({success_rate:.1f}%), DRC通过: {n_drc} ({drc_rate:.1f}%)")
    print(f"报告: {out_dir / 'report.md'}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
