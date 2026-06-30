"""R333 源文件冒烟测试。"""
import sys
sys.path.insert(0, '/workspace/src')

import klayout.db as db
import tempfile, os
from pathlib import Path

from polaris.verification.gdsii_layout_merger import (
    merge_gdsii, generate_merge_report, MergeReport, MergedCellInfo,
)


def make_gds(name, layer=1, dt=0, offset_x=0, offset_y=0):
    """创建简单 GDSII。"""
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(name)
    li = ly.layer(layer, dt)
    pts = [
        db.Point(offset_x, offset_y),
        db.Point(offset_x + 10000, offset_y),
        db.Point(offset_x + 10000, offset_y + 5000),
        db.Point(offset_x, offset_y + 5000),
    ]
    top.shapes(li).insert(db.Polygon(pts))
    p = tempfile.mktemp(suffix='.gds')
    ly.write(p)
    return p


def main():
    # 创建 3 个 GDSII 文件
    g1 = make_gds('CELL_A', layer=1)
    g2 = make_gds('CELL_B', layer=2)
    g3 = make_gds('CELL_C', layer=3)

    # 测试 1: 基本合并（无偏移）
    print("=== 测试 1: 基本合并（无偏移） ===")
    out1 = tempfile.mktemp(suffix='.gds')
    report = merge_gdsii([g1, g2, g3], out1, top_cell_name='MERGED')
    assert isinstance(report, MergeReport)
    assert report.top_cell_name == 'MERGED'
    assert report.input_files == [g1, g2, g3]
    assert len(report.merged_cells) == 3
    assert report.merged_cells[0].source_top_cell == 'CELL_A'
    assert report.merged_cells[1].source_top_cell == 'CELL_B'
    assert report.merged_cells[2].source_top_cell == 'CELL_C'
    assert report.total_instance_count == 3
    assert report.all_cell_count == 4  # MERGED + 3 源 cell
    print(f"  top_cell_name: {report.top_cell_name}")
    print(f"  total_instance_count: {report.total_instance_count}")
    print(f"  all_cell_count: {report.all_cell_count}")
    print(f"  bbox_um: {report.bounding_box_um}")

    # 验证: 重新读入检查 wrapper 是唯一顶层 cell
    verify = db.Layout()
    verify.read(out1)
    top_cells = [verify.cell(ci).name for ci in verify.each_top_cell()]
    assert top_cells == ['MERGED'], f"Expected ['MERGED'], got {top_cells}"
    all_cells = [verify.cell(ci).name for ci in verify.each_cell_top_down()]
    print(f"  Verify top cells: {top_cells}")
    print(f"  Verify all cells: {all_cells}")
    assert 'CELL_A' in all_cells
    assert 'CELL_B' in all_cells
    assert 'CELL_C' in all_cells
    print("  ✓ 验证通过")

    # 测试 2: 带偏移合并
    print("\n=== 测试 2: 带偏移合并 ===")
    out2 = tempfile.mktemp(suffix='.gds')
    offsets = [(0.0, 0.0), (20.0, 0.0), (0.0, 30.0)]
    report2 = merge_gdsii([g1, g2, g3], out2, offsets_um=offsets)
    assert report2.merged_cells[0].offset_um == (0.0, 0.0)
    assert report2.merged_cells[1].offset_um == (20.0, 0.0)
    assert report2.merged_cells[2].offset_um == (0.0, 30.0)
    # bbox 应包含所有源 cell 的合并范围
    # CELL_A: (0, 0) - (10, 5)
    # CELL_B: (20, 0) - (30, 5)
    # CELL_C: (0, 30) - (10, 35)
    xmin, ymin, xmax, ymax = report2.bounding_box_um
    print(f"  bbox_um: ({xmin:.3f}, {ymin:.3f}) - ({xmax:.3f}, {ymax:.3f})")
    assert xmin == 0.0
    assert ymin == 0.0
    assert xmax == 30.0
    assert ymax == 35.0
    print("  ✓ 验证通过")

    # 测试 3: 单文件合并
    print("\n=== 测试 3: 单文件合并 ===")
    out3 = tempfile.mktemp(suffix='.gds')
    report3 = merge_gdsii([g1], out3, top_cell_name='SINGLE_WRAP')
    assert report3.top_cell_name == 'SINGLE_WRAP'
    assert len(report3.merged_cells) == 1
    assert report3.total_instance_count == 1
    print("  ✓ 验证通过")

    # 测试 4: 报告生成
    print("\n=== 测试 4: 报告生成 ===")
    out4 = tempfile.mktemp(suffix='.gds')
    text_report = generate_merge_report(
        [g1, g2], out4, output_format='text'
    )
    assert 'GDSII 版图合并报告' in text_report
    assert 'CELL_A' in text_report
    print("  ✓ text 报告 OK")

    out5 = tempfile.mktemp(suffix='.gds')
    md_report = generate_merge_report(
        [g1, g2], out5, output_format='markdown'
    )
    assert '# GDSII 版图合并报告' in md_report
    assert '|---|' in md_report
    print("  ✓ markdown 报告 OK")

    out6 = tempfile.mktemp(suffix='.gds')
    json_report = generate_merge_report(
        [g1, g2], out6, output_format='json'
    )
    import json
    data = json.loads(json_report)
    assert data['top_cell_name'] == 'MERGED'
    assert len(data['merged_cells']) == 2
    print("  ✓ json 报告 OK")

    # 测试 5: 错误处理
    print("\n=== 测试 5: 错误处理 ===")
    # 空 input_paths
    try:
        merge_gdsii([], tempfile.mktemp(suffix='.gds'))
        print("  ✗ 应该 raise ValueError")
    except ValueError as e:
        print(f"  ✓ 空 input_paths 正确 raise: {e}")

    # 文件不存在
    try:
        merge_gdsii(['/nonexistent.gds'], tempfile.mktemp(suffix='.gds'))
        print("  ✗ 应该 raise FileNotFoundError")
    except FileNotFoundError as e:
        print(f"  ✓ 文件不存在正确 raise: {e}")

    # offsets_um 长度不匹配
    try:
        merge_gdsii([g1, g2], tempfile.mktemp(suffix='.gds'),
                    offsets_um=[(0.0, 0.0)])
        print("  ✗ 应该 raise ValueError")
    except ValueError as e:
        print(f"  ✓ offsets_um 长度不匹配正确 raise: {e}")

    # top_cell_name 空
    try:
        merge_gdsii([g1], tempfile.mktemp(suffix='.gds'), top_cell_name='')
        print("  ✗ 应该 raise ValueError")
    except ValueError as e:
        print(f"  ✓ top_cell_name 空正确 raise: {e}")

    # 不支持的格式
    try:
        generate_merge_report([g1], tempfile.mktemp(suffix='.gds'),
                              output_format='xml')
        print("  ✗ 应该 raise ValueError")
    except ValueError as e:
        print(f"  ✓ 不支持的格式正确 raise: {e}")

    # 清理
    for f in [g1, g2, g3, out1, out2, out3, out4, out5, out6]:
        if os.path.exists(f):
            os.unlink(f)
    print("\n=== 所有冒烟测试通过 ===")


if __name__ == '__main__':
    main()
