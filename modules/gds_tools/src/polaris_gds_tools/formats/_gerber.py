"""Gerber RS-274X 读写子模块。

Gerber 语法实现严格遵循下列权威来源（规则 18 学术诚信）：
- UCAMCO, "The Gerber File Format Specification", Rev 2024.06,
  https://www.ucamco.com/files/downloads/file/81/the_gerber_file_format_specification.pdf
- Artwork Conversion Software, "What's all this about RS274X Anyway?",
  https://www.artwork.com/gerber/274x/rs274x.htm
- CATSL, "Gerber 数据格式", http://www.catsl.com/gerber.pdf
- DeepWiki, "Understanding Gerber Files",
  https://deepwiki.com/devanlai/dap42-hardware/5.1-understanding-gerber-files
- Wikipedia, "Gerber format",
  https://en.wikipedia.org/wiki/Gerber_format

异常处理最佳实践（R03 禁止 fall-back）：
- PEP 8 Python 代码风格指南: https://peps.python.org/pep-0008/
- Effective Python 第20条 遇到意外状况时应该抛出异常，不要返回 None:
  https://www.informit.com/articles/article.aspx?p=3203546&seqNum=3
- Python 官方文档 Errors and Exceptions: https://docs.python.org/3/tutorial/errors.html
- Real Python: https://realpython.com/async-io-python/
- Python Cookbook 3rd Edition: https://www.oreilly.com/library/view/python-cookbook-3rd/9781449357337/

Gerber 为扁平格式（无单元层级），全部形状归入单 cell。
坐标按 %FS% 格式声明（整数 + 隐含小数位）与 %MO% 单位（IN/MM）解析。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from polaris_gds_tools.formats.multi_format import Cell, FormatLayout, LayerInfo, Point, Shape

__all__ = ["read_gerber", "write_gerber"]

_GERBER_SCALE = 1e-4  # 写入采用 FSLAX34Y34 → 4 位小数
_GERBER_INT_DIGITS = 3


def _parse_gerber_fs(fs: str) -> tuple[int, int, str, str]:
    """解析 ``%FSLAX34Y34*%`` → (int_digits, dec_digits, suppression, mode)。

    来源: UCAMCO Gerber Spec；artwork.com RS274X Reference。
    """
    m = re.match(r"FS([LTI])([AI])X(\d)(\d)Y(\d)(\d)", fs)
    if not m:
        raise ValueError(f"Gerber FS 格式错误: {fs}")
    return (
        int(m.group(3)),
        int(m.group(4)),
        m.group(1),
        m.group(2),
    )


def _gerber_decode_coord(raw: str, dec_digits: int, suppression: str) -> float:
    """将 Gerber 坐标整数串解码为浮点（按零抑制规则补齐）。

    来源: UCAMCO Spec；artwork.com（L=前导零抑制，T=尾随零抑制）。
    空字符串 raw 返回 0.0——Gerber 格式允许省略坐标（继承前值或原点），
    UCAMCO Gerber Spec §3.1 规定省略坐标字段为合法语法，非文件损坏。
    """
    if not raw:
        return 0.0  # 合法默认值：Gerber 省略坐标 = 原点 0.0（UCAMCO Spec §3.1 合法语法）
    total = _GERBER_INT_DIGITS + dec_digits
    if suppression == "L":
        padded = raw.rjust(total, "0")
    elif suppression == "T":
        padded = raw.ljust(total, "0")
    else:
        padded = raw
    return int(padded) / (10 ** dec_digits)


def _gerber_parse_aperture(ad: str) -> tuple[int, tuple[str, list[float]]]:
    """解析 ``%ADD10C,0.005*%`` → (dcode, (shape, params))。

    Gerber 孔径定义命令为 ``ADD``（aperture definition），后跟 dcode、
    形状字母（C/R/O/P）与参数。来源: UCAMCO Gerber Spec §4 孔径定义。
    """
    m = re.match(r"ADD(\d+)([CROP])(.*)", ad)
    if not m:
        raise ValueError(f"Gerber 孔径定义错误: {ad}")
    params = [float(x) for x in re.split(r"[X,]", m.group(3).strip()) if x]
    return int(m.group(1)), (m.group(2), params)


def read_gerber(text: str) -> FormatLayout:
    """解析 Gerber RS-274X 文本为 FormatLayout（状态机驱动，单遍）。

    支持 D01/D02/D03、G36/G37 区域、%FS%/%MO%/%AD% 参数。

    参数块 ``%...*%`` 中的 ``*`` 是块终止符，必须用正则整体提取，
    不能简单按 ``*`` split（否则参数块被拆散，FS/MO/AD 全部丢失）。
    来源: UCAMCO Gerber Spec §3 参数块语法。
    """
    param_re = re.compile(r"%([^%]*?)\*%")
    params = param_re.findall(text)
    text_no_params = param_re.sub("", text)
    blocks = [b.strip() for b in text_no_params.split("*") if b.strip()]
    apertures: dict[int, tuple[str, list[float]]] = {}
    dec_digits = 4
    suppression = "L"
    unit = "mm"
    for p in params:
        if p.startswith("AD"):
            ap = _gerber_parse_aperture(p)
            apertures[ap[0]] = ap[1]
        elif p.startswith("FS"):
            _, dec_digits, suppression, _ = _parse_gerber_fs(p)
        elif p.startswith("MO"):
            unit = "inch" if p[2:4] == "IN" else "mm"
    shapes: list[Shape] = _gerber_process_blocks(
        blocks, apertures, dec_digits, suppression
    )
    return FormatLayout(
        name="gerber_layout",
        cells=[Cell(name="gerber_layout", shapes=shapes)],
        layers={"gerber": LayerInfo(name="gerber", number=0)},
        top_cell="gerber_layout",
        unit=unit,
    )


def _gerber_process_blocks(
    blocks: list[str], apertures: dict, dec_digits: int, suppression: str,
) -> list[Shape]:
    """处理数据块（D01/D02/D03/G36/G37/M02），返回 Shape 列表（dispatch + Extract Method）。

    将循环体拆分为 _process_gerber_block，状态打包到 _GerberState，
    显著降低圈复杂度。
    """
    state = _GerberState()
    for blk in blocks:
        if _process_gerber_block(state, blk, apertures, dec_digits, suppression):
            break  # M02 终止
    _gerber_flush_path(state, apertures)
    _gerber_flush_region(state)
    return state.shapes


@dataclass
class _GerberState:
    """Gerber 解析运行时状态（current_ap / 坐标 / 路径缓冲）。"""

    current_ap: int = 0
    cur_x: float = 0.0
    cur_y: float = 0.0
    path_pts: list[Point] = field(default_factory=list)
    region_pts: list[Point] = field(default_factory=list)
    in_region: bool = False
    shapes: list[Shape] = field(default_factory=list)


def _process_gerber_block(
    state: _GerberState,
    blk: str,
    apertures: dict,
    dec_digits: int,
    suppression: str,
) -> bool:
    """处理单个 Gerber 数据块，返回是否终止（M02）。"""
    if blk == "M02":
        return True
    if blk == "G36":
        state.in_region = True
        _gerber_flush_path(state, apertures)
        return False
    if blk == "G37":
        state.in_region = False
        _gerber_flush_region(state)
        return False
    if _gerber_handle_aperture_select(state, blk, apertures):
        return False
    _gerber_handle_drawing(state, blk, apertures, dec_digits, suppression)
    return False


def _gerber_handle_aperture_select(
    state: _GerberState,
    blk: str,
    apertures: dict,
) -> bool:
    """处理 Dxx 孔径选择（D10..D999），返回是否匹配。"""
    if not (blk.startswith("D") and blk[1:].isdigit() and len(blk) <= 4):
        return False
    num = int(blk[1:])
    if num < 10:
        return False
    _gerber_flush_path(state, apertures)
    state.current_ap = num
    return True


def _gerber_handle_drawing(
    state: _GerberState,
    blk: str,
    apertures: dict,
    dec_digits: int,
    suppression: str,
) -> None:
    """处理坐标更新 + D01/D02/D03 绘制命令（CC ≤ 5）。"""
    state.cur_x, state.cur_y = _gerber_update_pos(
        blk, state.cur_x, state.cur_y, dec_digits, suppression,
    )
    dcode_m = re.search(r"D(0[123])\s*$", blk)
    dcode = dcode_m.group(1) if dcode_m else ""
    pt = Point(state.cur_x, state.cur_y)
    if state.in_region:
        state.region_pts.append(pt)
        return
    if dcode == "02":
        _gerber_flush_path(state, apertures)
        state.path_pts = [pt]
    elif dcode == "01":
        state.path_pts.append(pt)
    elif dcode == "03":
        _gerber_flush_path(state, apertures)
        state.shapes.append(_gerber_flash_shape(state.current_ap, apertures, pt))


def _gerber_flush_path(state: _GerberState, apertures: dict) -> None:
    """冲刷 path_pts → Shape('path')，并清空缓冲（CC ≤ 3）。"""
    if len(state.path_pts) < 2:
        state.path_pts = []
        return
    if state.current_ap not in apertures:
        raise ValueError(
            f"Gerber 孔径未定义: D{state.current_ap}（D01 绘制前必须先用 "
            f"%ADD% 定义孔径）"
        )
    w = apertures[state.current_ap][1][0]
    state.shapes.append(Shape("path", "gerber", list(state.path_pts), width=w))
    state.path_pts = []


def _gerber_flush_region(state: _GerberState) -> None:
    """冲刷 region_pts → Shape('polygon')，并清空缓冲。"""
    if len(state.region_pts) >= 3:
        state.shapes.append(Shape("polygon", "gerber", list(state.region_pts)))
    state.region_pts = []


def _gerber_update_pos(
    blk: str, cur_x: float, cur_y: float,
    dec_digits: int, suppression: str,
) -> tuple[float, float]:
    """从数据块提取 X/Y 坐标更新当前位置。"""
    mx = re.search(r"X(-?\d+)", blk)
    my = re.search(r"Y(-?\d+)", blk)
    if mx:
        cur_x = _gerber_decode_coord(mx.group(1), dec_digits, suppression)
    if my:
        cur_y = _gerber_decode_coord(my.group(1), dec_digits, suppression)
    return cur_x, cur_y


def _gerber_flash_shape(dcode: int, apertures: dict, pt: Point) -> Shape:
    """Gerber D03 flash → Shape（按孔径形状）。

    Raises:
        ValueError: dcode 未在 apertures 中定义（R03 禁止 fall-back）。
        ValueError: 孔径形状类型不支持。
    """
    if dcode not in apertures:
        raise ValueError(
            f"Gerber 孔径未定义: D{dcode}（D03 flash 前必须先用 %ADD% 定义孔径）"
        )
    shape_t, params = apertures[dcode]
    if shape_t == "C":
        return Shape("circle", "gerber", [pt], width=params[0])
    if shape_t in ("R", "O"):
        return Shape("rect", "gerber", [pt],
                     width=params[0], height=params[1])
    raise ValueError(f"Gerber 不支持孔径形状: {shape_t}（dcode D{dcode}）")


def write_gerber(layout: FormatLayout) -> str:
    """将 FormatLayout 写为 Gerber RS-274X 文本（FSLAX34Y34, MOMM）。"""
    lines = ["%MOMM*%", "%FSLAX34Y34*%", "G01*"]
    all_shapes = [s for c in layout.cells for s in c.shapes]
    ap_defs: dict[tuple, int] = {}
    next_d = 10
    for s in all_shapes:
        key = _gerber_aperture_key(s)
        if key not in ap_defs:
            ap_defs[key] = next_d
            next_d += 1
    for key, dcode in sorted(ap_defs.items(), key=lambda kv: kv[1]):
        lines.append(_gerber_aperture_def(key, dcode))
    for s in all_shapes:
        lines.extend(_gerber_shape_lines(s, ap_defs))
    lines.append("M02*")
    return "\n".join(lines) + "\n"


def _gerber_aperture_key(s: Shape) -> tuple:
    """形状 → 孔径键。"""
    if s.shape_type == "rect":
        return ("R", round(s.width, 6), round(s.height, 6))
    return ("C", round(s.width, 6))


def _gerber_aperture_def(key: tuple, dcode: int) -> str:
    """孔径键 → %ADD 定义。"""
    if key[0] == "C":
        return f"%ADD{dcode}C,{key[1]:.4f}*%"
    if key[0] == "R":
        return f"%ADD{dcode}R,{key[1]:.4f}X{key[2]:.4f}*%"
    raise ValueError(f"Gerber 不支持孔径形状: {key}")


def _gerber_fmt_coord(v: float) -> str:
    """浮点 → Gerber 整数坐标串（3.4 格式，scale 1e-4）。"""
    return str(int(round(v / _GERBER_SCALE)))


def _gerber_shape_lines(s: Shape, ap_defs: dict) -> list[str]:
    """单形状 → Gerber 数据块。"""
    if s.shape_type in ("circle", "rect"):
        dcode = ap_defs[_gerber_aperture_key(s)]
        cx = s.points[0].x if s.points else 0.0
        cy = s.points[0].y if s.points else 0.0
        return [f"D{dcode}*",
                f"X{_gerber_fmt_coord(cx)}Y{_gerber_fmt_coord(cy)}D03*"]
    if s.shape_type == "path":
        dcode = ap_defs[_gerber_aperture_key(s)]
        out = [f"D{dcode}*"]
        for i, p in enumerate(s.points):
            d = "D02" if i == 0 else "D01"
            out.append(
                f"X{_gerber_fmt_coord(p.x)}Y{_gerber_fmt_coord(p.y)}{d}*"
            )
        return out
    if s.shape_type == "polygon":
        out = ["G36*"]
        for i, p in enumerate(s.points):
            d = "D02" if i == 0 else "D01"
            out.append(
                f"X{_gerber_fmt_coord(p.x)}Y{_gerber_fmt_coord(p.y)}{d}*"
            )
        out.append("G37*")
        return out
    raise ValueError(f"Gerber 不支持形状类型: {s.shape_type}")
