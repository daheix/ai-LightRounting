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

from polaris.io.multi_format import Cell, FormatLayout, LayerInfo, Point, Shape

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
    """
    if not raw:
        return 0.0
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
    """处理数据块（D01/D02/D03/G36/G37/M02），返回 Shape 列表。"""
    shapes: list[Shape] = []
    current_ap = 0
    cur_x = 0.0
    cur_y = 0.0
    path_pts: list[Point] = []
    region_pts: list[Point] = []
    in_region = False

    def flush_path() -> None:
        nonlocal path_pts
        if len(path_pts) >= 2:
            if current_ap not in apertures:
                raise ValueError(
                    f"Gerber 孔径未定义: D{current_ap}（D01 绘制前必须先用 "
                    f"%ADD% 定义孔径）"
                )
            w = apertures[current_ap][1][0]
            shapes.append(Shape("path", "gerber", list(path_pts), width=w))
        path_pts = []

    def flush_region() -> None:
        nonlocal region_pts
        if len(region_pts) >= 3:
            shapes.append(Shape("polygon", "gerber", list(region_pts)))
        region_pts = []

    for blk in blocks:
        if blk == "M02":
            break
        if blk == "G36":
            in_region = True
            flush_path()
            continue
        if blk == "G37":
            in_region = False
            flush_region()
            continue
        if blk.startswith("D") and blk[1:].isdigit() and len(blk) <= 4:
            num = int(blk[1:])
            if num >= 10:
                flush_path()
                current_ap = num
                continue
        cur_x, cur_y = _gerber_update_pos(blk, cur_x, cur_y,
                                          dec_digits, suppression)
        dcode_m = re.search(r"D(0[123])\s*$", blk)
        dcode = dcode_m.group(1) if dcode_m else ""
        pt = Point(cur_x, cur_y)
        if in_region:
            region_pts.append(pt)
            continue
        if dcode == "02":
            flush_path()
            path_pts = [pt]
        elif dcode == "01":
            path_pts = path_pts or []
            path_pts.append(pt)
        elif dcode == "03":
            flush_path()
            shapes.append(_gerber_flash_shape(current_ap, apertures, pt))
    flush_path()
    flush_region()
    return shapes


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
