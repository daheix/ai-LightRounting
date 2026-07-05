"""PoLaRIS 第二批真实光子PDK数据源下载器（Task：扩充 real_board 至 ≥1000 用例）。

从 10 个公开 GitHub 仓库批量下载真实光子/量子/RF PDK 与电路用例，
按来源分类复制到 ``real_board/<source>/``，与第一批 ``download_real_circuits.py``
结果合并，使 ``real_board/`` 总用例数 ≥ 1000。

下载方案（与 download_real_circuits.py 一致）
--------------------------------------------
沙箱防火墙对 ``raw.githubusercontent.com`` GET 大文件做 SSL 拦截，
但 ``codeload.github.com`` 整仓库 zip 下载已实测可用
（见 download_real_circuits.py docstring），因此本脚本同样采用
codeload zip + ``zipfile`` 选择性提取，避免解压全部内容、节省磁盘。
不使用 ``git clone``，因其在沙箱中可用性不稳定且会留下 .git 目录。

下载源（10 个，按任务优先级）
-----------------------------
R02 学术诚信：每个源标注 GitHub URL + license + 作者 + 文献。

1. ubcpdk - UBC 工艺 PDK (gdsfactory 生态)
   - 仓库: https://github.com/gdsfactory/ubc (main)
   - 来源: Lukas Chrostowski et al., UBC, SiEPIC,
     "ubcpdk: UBC SiEPIC PDK for gdsfactory", 2018-2024.
   - 许可: MIT
   - 提取: **/*.gds + **/*.pic.yml + **/*.yml (netlist)
2. cspdk - CS PDK (gdsfactory 生态)
   - 仓库: https://github.com/gdsfactory/cspdk (main)
   - 来源: gdsfactory community, "cspdk: CS PDK", 2020-2024.
   - 许可: MIT
   - 提取: **/*.gds + **/*.pic.yml + **/*.yml
3. vtt - VTT 多项目晶圆 PDK (gdsfactory 生态)
   - 仓库: https://github.com/gdsfactory/vtt (main)
   - 来源: VTT Technical Research Centre of Finland,
     "vtt: VTT MCP PDK", 2019-2024.
   - 许可: MIT
   - 提取: **/*.gds + **/*.pic.yml + **/*.yml
4. gdsfactory-test-data - gdsfactory 测试 GDS 数据
   - 仓库: https://github.com/gdsfactory/gdsfactory-test-data (main)
   - 来源: Joaquin Matres et al., "gdsfactory",
     J. Opt. Microsyst. 2(4), 043501, 2022.
   - DOI: 10.1117/1.JOM.2.4.043501
   - 许可: MIT
   - 提取: **/*.gds
5. lxt_pdk_gf - Luxtelligence LNOI 平台 PDK (gdsfactory fork)
   - 仓库: https://github.com/Luxtelligence/lxt_pdk_gf (main)
   - 来源: Luxtelligence AG, "lxt_pdk_gf: Lithium Niobate PDK",
     2022-2024.
   - 许可: MIT
   - 提取: **/*.gds + **/*.pic.yml + **/*.yml
6. SiEPICfab_Shuksan_PDK - SiEPICfab Shuksan PDK
   - 仓库: https://github.com/SiEPIC/SiEPICfab_Shuksan_PDK (main)
   - 来源: Lukas Chrostowski et al., SiEPICfab,
     "Shuksan PDK: open-source silicon photonics PDK", 2024.
   - 许可: Apache-2.0
   - 提取: **/*.gds + **/*.xml (KLayout lyt)
7. Apollo -> APR (同团队前身工作，同源替代)
   - 任务原 URL: https://github.com/ScopeX-ASU/Apollo (仓库为空，
     ICCAD 2025 论文代码未发布)
   - 论文: Hongjian Zhou, Haoyu Yang, Nicholas Gangi, Haoxing Ren,
     Zhaoran (Rena) Huang, Jiaqi Gu, "Apollo: Automated Routing-
     Informed Placement for Large-Scale Photonic Integrated Circuits",
     ICCAD 2025, Arizona State University / NVIDIA / RPI.
   - 替代 URL: https://github.com/ScopeX-ASU/APR (main)
   - APR 来源: Hongjian Zhou, Keren Zhu, Jiaqi Gu, "APR: Automated
     Photonic Integrated Circuit Detailed Routing with Curvy Waveguide
     and Adaptive Crossing Insertion", ASP-DAC 2025, ASU / Fudan.
   - 许可: MIT (ASP-DAC 2025 artifact)
   - 提取: **/*.yaml + **/*.json + **/*.gds (benchmark circuits)
   - R02/R03 合规: Apollo 仓库为空 → 不伪造、不 fall-back；明确标注
     使用同团队 APR 代码作为同源替代，论文关系在 index.json 中记录。
8. Perceval - 量子光子电路示例
   - 仓库: https://github.com/Quandela/Perceval (main)
   - 来源: Nicolas Heurtel et al., Quandela,
     "Perceval: A Platform for Photonic Quantum Computing",
     arXiv:2207.10582, 2022.
   - DOI: 10.22331/q-2024-04-26-1333
   - 许可: MIT
   - 提取: **/*.json + **/*.py (示例电路 / 量子光路)
9. KLayoutPhotonicPCells-core - KLayout 光子 PCell 模板
   - 仓库: https://github.com/sebastian-goeldi/KLayoutPhotonicPCells-core
     (master)
   - 来源: Sebastian Goeldi, "KLayout Photonic PCells",
     2022-2024.
   - 许可: MIT
   - 提取: **/*.gds + **/*.py (PCell 实现示例)
10. quantum-rf-pdk - 量子 RF PDK (gdsfactory 生态)
    - 仓库: https://github.com/gdsfactory/quantum-rf-pdk (main)
    - 来源: gdsfactory community, "quantum-rf-pdk", 2023-2024.
    - 许可: MIT
    - 提取: **/*.pic.yml + **/*.yml + **/*.gds

R02 学术诚信：所有源 URL/DOI/作者在 docstring 与 index.json metadata 中标注。
R03 禁止 fall-back：网络不可用即 raise；仓库 404/空 → 记录状态，不伪造。
R04 不参与 GPU：纯文件下载与解压，不涉及 GPU。
R11 V8 极简：脚本产物 → git add → commit → push origin main。

用法:
    python3 scripts/download_new_real_circuits.py
    python3 scripts/download_new_real_circuits.py --keep-zip  # 保留 zip（调试）

输出:
    real_board/{ubcpdk,cspdk,vtt,gf_test_data,luxtelligence,siepicfab,
                apollo,perceval,klayout_pcells,quantum_rf}/...   用例文件
    real_board/index_new_sources.json                            本批次索引
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).resolve().parent.parent
REAL_DIR = WORKSPACE / "real_board"
INDEX_PATH = REAL_DIR / "index_new_sources.json"
TMP_DIR = Path("/tmp/pic_data")

CODELOAD_BASE = "https://codeload.github.com"
NETWORK_PROBE_HOST = "https://codeload.github.com"

USER_AGENT = "PoLaRIS-PDK-Downloader/2.0 (research; contact: polaris-dev)"

# 单文件大小上限（提取时按 zip 内 file_size 判断）
GDS_MAX_BYTES = 5_000_000  # 部分含布局的 GDS 可能较大，提到 5MB
JSON_MAX_BYTES = 1_000_000
YAML_MAX_BYTES = 300_000
PY_MAX_BYTES = 200_000
XML_MAX_BYTES = 200_000

# HTTP 重试参数
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class NetworkUnavailableError(RuntimeError):
    """网络不可用（R03：禁止 fall-back，直接 raise）。"""


class SourceUnavailableError(RuntimeError):
    """某个下载源不可用（如仓库 404 或为空）。记录原因，不终止其他源。"""


# ---------------------------------------------------------------------------
# 网络与 HTTP 工具
# ---------------------------------------------------------------------------

def http_get(url: str, *, headers: dict | None = None, timeout: int = 600) -> bytes:
    """带重试的 HTTP GET，失败即 raise（R03）。

    Args:
        url: 完整 URL。
        headers: 额外请求头。
        timeout: 单次请求超时秒数。

    Returns:
        响应体 bytes。

    Raises:
        urllib.error.HTTPError: 4xx (除 429) 立即抛出。
        urllib.error.URLError: 重试耗尽后仍失败。
    """
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    last_err: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=hdrs, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 404:
                raise
            if e.code in (403, 429):
                time.sleep(RETRY_BACKOFF * attempt * 2)
                continue
            time.sleep(RETRY_BACKOFF * attempt)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_err = e
            time.sleep(RETRY_BACKOFF * attempt)
    raise urllib.error.URLError(
        f"GET {url} failed after {MAX_RETRIES} retries: {last_err}"
    )


def test_network() -> None:
    """探测 codeload.github.com 连通性。不可达则 raise。"""
    try:
        req = urllib.request.Request(
            NETWORK_PROBE_HOST, headers={"User-Agent": USER_AGENT}, method="HEAD"
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            if not (200 <= resp.status < 400):
                raise NetworkUnavailableError(
                    f"codeload.github.com 返回 HTTP {resp.status}"
                )
        print(f"[网络] codeload.github.com 可达 (HTTP {resp.status})")
    except Exception as e:  # noqa: BLE001 - 探测需捕获全部
        raise NetworkUnavailableError(
            f"网络不可用，无法下载真实用例。codeload.github.com 探测失败: "
            f"{type(e).__name__}: {e}"
        ) from e


def download_zip(owner: str, repo: str, branch: str, dest_zip: Path) -> int:
    """从 codeload.github.com 下载整仓库 zip。

    Args:
        owner: 仓库 owner。
        repo: 仓库名。
        branch: 分支/tag。
        dest_zip: 本地 zip 目标路径。

    Returns:
        下载字节数。

    Raises:
        SourceUnavailableError: 仓库 404。
        urllib.error.URLError: 下载失败。
    """
    url = f"{CODELOAD_BASE}/{owner}/{repo}/zip/refs/heads/{branch}"
    try:
        content = http_get(url, timeout=600)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise SourceUnavailableError(
                f"仓库 {owner}/{repo}@{branch} 不存在 (404)。原 URL: "
                f"https://github.com/{owner}/{repo}"
            ) from e
        raise
    dest_zip.write_bytes(content)
    return len(content)


def repo_zip_prefix(repo: str, branch: str) -> str:
    """codeload zip 内顶层目录前缀，形如 'ubc-main'。"""
    return f"{repo}-{branch}/"


def safe_name(path: str) -> str:
    """把仓库内路径转换为安全的扁平文件名（/ 替换为 __）。"""
    return path.replace("/", "__")


def clean_dest_dir(dest_dir: Path) -> None:
    """提取前清空目标目录（删除所有文件与子目录），保证幂等性。"""
    if dest_dir.exists():
        for child in dest_dir.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        dest_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# zip 提取器
# ---------------------------------------------------------------------------

def extract_from_zip(
    zip_path: Path,
    prefix: str,
    want: callable,  # type: ignore[type-arg]
    dest_dir: Path,
    max_bytes: int,
) -> list[tuple[str, str, int]]:
    """从 zip 选择性提取文件。

    Args:
        zip_path: zip 文件路径。
        prefix: zip 内顶层目录前缀（剥离后得到仓库相对路径）。
        want: 谓词函数 (repo_rel_path: str, size: int) -> bool。
        dest_dir: 提取目标目录。
        max_bytes: 单文件大小上限。

    Returns:
        列表 [(repo_rel_path, local_rel_path, size), ...]。
    """
    results: list[tuple[str, str, int]] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if not name.startswith(prefix):
                continue
            rel = name[len(prefix):]
            if info.file_size > max_bytes:
                continue
            if not want(rel, info.file_size):
                continue
            local_rel = safe_name(rel)
            dest = dest_dir / local_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            results.append((rel, local_rel, info.file_size))
    return results


# ---------------------------------------------------------------------------
# 通用：按扩展名/路径过滤
# ---------------------------------------------------------------------------

def want_by_extensions(exts: tuple[str, ...], *,
                       exclude_paths: tuple[str, ...] = (),
                       exclude_filenames: tuple[str, ...] = ()) -> callable:  # type: ignore[type-arg]
    """构造谓词：按扩展名提取，排除指定路径与文件名。

    Args:
        exts: 允许的扩展名（小写，含点，如 '.gds'）。
        exclude_paths: 排除包含这些子串的路径（如 'node_modules/'）。
        exclude_filenames: 排除的文件名（小写，如 'package.json'）。
    """
    def want(rel: str, size: int) -> bool:
        low = rel.lower()
        if not any(low.endswith(ext) for ext in exts):
            return False
        for ex in exclude_paths:
            if ex in rel:
                return False
        fn = rel.rsplit("/", 1)[-1].lower()
        if fn in exclude_filenames:
            return False
        return True
    return want


# ---------------------------------------------------------------------------
# 各源下载器
# ---------------------------------------------------------------------------

# 通用排除配置：避免提取构建产物/依赖
COMMON_EXCLUDE_PATHS = (
    "node_modules/", ".git/", "__pycache__/", ".pytest_cache/",
    ".tox/", ".mypy_cache/", ".ruff_cache/", "build/", "dist/",
    ".eggs/", ".venv/", "venv/",
)
COMMON_EXCLUDE_FILES = (
    "package.json", "package-lock.json", "pyproject.toml",
    "setup.py", "setup.cfg", "manifest.json", ".eslintrc.json",
    "tsconfig.json", "tox.ini", "poetry.lock", "Pipfile.lock",
    ".gitignore", ".gitattributes", "license", "license.md",
    "readme.md", "readme.rst", "changelog.md",
)


def _detect_zip_prefix(zip_path: Path) -> str:
    """从 zip 内自动检测顶层目录前缀。

    GitHub codeload zip 顶层目录名为 '{repo}-{branch}'，但当仓库被
    重命名/重定向时（如 ScopeX-ASU/APR 实际重定向到 LiDAR），实际
    顶层目录名可能与请求的 repo 不一致。本函数从 zip 内读取第一个
    顶层目录名作为 prefix，确保提取能匹配。

    R05 Bug 修复：原代码用 repo_zip_prefix(repo, branch) 静态构造
    prefix，对重命名仓库会失配，导致提取 0 文件。
    """
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if "/" in name:
                top = name.split("/", 1)[0] + "/"
                if top and not top.startswith("."):
                    return top
    raise SourceUnavailableError(
        f"无法从 zip {zip_path} 检测顶层目录（zip 可能为空或损坏）"
    )


def _download_repo_zip(owner: str, repo: str, branch: str,
                       zip_filename: str, label: str) -> tuple[Path, str]:
    """下载仓库 zip 并返回 (zip_path, prefix)。

    复用 /tmp/pic_data/ 缓存。若已存在则跳过下载。
    prefix 从 zip 内自动检测，兼容仓库重命名/重定向。
    """
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = TMP_DIR / zip_filename
    if not zip_path.exists():
        print(f"[{label}] 下载 {owner}/{repo}@{branch} zip...")
        n = download_zip(owner, repo, branch, zip_path)
        print(f"[{label}] zip 下载完成: {n} bytes ({n / 1e6:.1f} MB)")
    else:
        print(f"[{label}] zip 已缓存: {zip_path}")
    prefix = _detect_zip_prefix(zip_path)
    if not prefix.startswith(f"{repo}-"):
        print(f"[{label}] 注意: zip 顶层目录 '{prefix}' 与请求 repo "
              f"'{repo}' 不一致（仓库可能被重命名/重定向），按实际目录处理。")
    return zip_path, prefix


def _emit_entries(items: list[tuple[str, str, int]], *, source: str,
                  fmt: str, subdir: str, origin_url: str) -> list[dict]:
    """把提取结果转换为 index 条目。"""
    return [{
        "name": Path(rel).stem,
        "source": source,
        "format": fmt,
        "path": f"{subdir}/{local_rel}",
        "size": size,
        "origin": f"{origin_url}/{rel}",
    } for rel, local_rel, size in items]


def download_ubcpdk() -> list[dict]:
    """1. ubcpdk - UBC 工艺 PDK。"""
    print("\n[ubcpdk] === UBC PDK ===")
    zip_path, prefix = _download_repo_zip(
        "gdsfactory", "ubc", "main", "ubcpdk.zip", "ubcpdk")
    dest_dir = REAL_DIR / "ubcpdk"
    want = want_by_extensions((".gds", ".pic.yml", ".yml"),
                              exclude_paths=COMMON_EXCLUDE_PATHS,
                              exclude_filenames=COMMON_EXCLUDE_FILES)
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    # .pic.yml 同时匹配 .yml，去重
    seen = set()
    dedup_items = []
    for rel, local_rel, size in items:
        if local_rel in seen:
            continue
        seen.add(local_rel)
        dedup_items.append((rel, local_rel, size))
    print(f"[ubcpdk] 提取 {len(dedup_items)} 个文件")
    origin = "https://github.com/gdsfactory/ubc/blob/main"
    return _emit_entries(dedup_items, source="ubcpdk",
                         fmt="GDS/YAML", subdir="ubcpdk", origin_url=origin)


def download_cspdk() -> list[dict]:
    """2. cspdk - CS PDK。"""
    print("\n[cspdk] === CS PDK ===")
    zip_path, prefix = _download_repo_zip(
        "gdsfactory", "cspdk", "main", "cspdk.zip", "cspdk")
    dest_dir = REAL_DIR / "cspdk"
    want = want_by_extensions((".gds", ".pic.yml", ".yml"),
                              exclude_paths=COMMON_EXCLUDE_PATHS,
                              exclude_filenames=COMMON_EXCLUDE_FILES)
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    seen = set()
    dedup_items = []
    for rel, local_rel, size in items:
        if local_rel in seen:
            continue
        seen.add(local_rel)
        dedup_items.append((rel, local_rel, size))
    print(f"[cspdk] 提取 {len(dedup_items)} 个文件")
    origin = "https://github.com/gdsfactory/cspdk/blob/main"
    return _emit_entries(dedup_items, source="cspdk",
                         fmt="GDS/YAML", subdir="cspdk", origin_url=origin)


def download_vtt() -> list[dict]:
    """3. vtt - VTT 多项目晶圆 PDK。"""
    print("\n[vtt] === VTT PDK ===")
    zip_path, prefix = _download_repo_zip(
        "gdsfactory", "vtt", "main", "vtt.zip", "vtt")
    dest_dir = REAL_DIR / "vtt"
    want = want_by_extensions((".gds", ".pic.yml", ".yml"),
                              exclude_paths=COMMON_EXCLUDE_PATHS,
                              exclude_filenames=COMMON_EXCLUDE_FILES)
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    seen = set()
    dedup_items = []
    for rel, local_rel, size in items:
        if local_rel in seen:
            continue
        seen.add(local_rel)
        dedup_items.append((rel, local_rel, size))
    print(f"[vtt] 提取 {len(dedup_items)} 个文件")
    origin = "https://github.com/gdsfactory/vtt/blob/main"
    return _emit_entries(dedup_items, source="vtt",
                         fmt="GDS/YAML", subdir="vtt", origin_url=origin)


def download_gf_test_data() -> list[dict]:
    """4. gdsfactory-test-data - gdsfactory 测试 GDS。"""
    print("\n[gf_test_data] === gdsfactory test data ===")
    zip_path, prefix = _download_repo_zip(
        "gdsfactory", "gdsfactory-test-data", "main",
        "gdsfactory_test_data.zip", "gf_test_data")
    dest_dir = REAL_DIR / "gf_test_data"
    want = want_by_extensions((".gds",),
                              exclude_paths=COMMON_EXCLUDE_PATHS,
                              exclude_filenames=COMMON_EXCLUDE_FILES)
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    print(f"[gf_test_data] 提取 {len(items)} 个 GDS")
    origin = "https://github.com/gdsfactory/gdsfactory-test-data/blob/main"
    return _emit_entries(items, source="gf_test_data",
                         fmt="GDS", subdir="gf_test_data", origin_url=origin)


def download_luxtelligence() -> list[dict]:
    """5. lxt_pdk_gf - Luxtelligence LNOI PDK。"""
    print("\n[luxtelligence] === Luxtelligence LNOI PDK ===")
    zip_path, prefix = _download_repo_zip(
        "Luxtelligence", "lxt_pdk_gf", "main",
        "lxt_pdk_gf.zip", "luxtelligence")
    dest_dir = REAL_DIR / "luxtelligence"
    want = want_by_extensions((".gds", ".pic.yml", ".yml"),
                              exclude_paths=COMMON_EXCLUDE_PATHS,
                              exclude_filenames=COMMON_EXCLUDE_FILES)
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    seen = set()
    dedup_items = []
    for rel, local_rel, size in items:
        if local_rel in seen:
            continue
        seen.add(local_rel)
        dedup_items.append((rel, local_rel, size))
    print(f"[luxtelligence] 提取 {len(dedup_items)} 个文件")
    origin = "https://github.com/Luxtelligence/lxt_pdk_gf/blob/main"
    return _emit_entries(dedup_items, source="luxtelligence",
                         fmt="GDS/YAML", subdir="luxtelligence",
                         origin_url=origin)


def download_siepicfab() -> list[dict]:
    """6. SiEPICfab Shuksan PDK。"""
    print("\n[siepicfab] === SiEPICfab Shuksan PDK ===")
    zip_path, prefix = _download_repo_zip(
        "SiEPIC", "SiEPICfab_Shuksan_PDK", "main",
        "siepicfab_shuksan.zip", "siepicfab")
    dest_dir = REAL_DIR / "siepicfab"
    want = want_by_extensions((".gds", ".xml"),
                              exclude_paths=COMMON_EXCLUDE_PATHS,
                              exclude_filenames=COMMON_EXCLUDE_FILES)
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    print(f"[siepicfab] 提取 {len(items)} 个文件")
    origin = "https://github.com/SiEPIC/SiEPICfab_Shuksan_PDK/blob/main"
    return _emit_entries(items, source="siepicfab",
                         fmt="GDS/XML", subdir="siepicfab", origin_url=origin)


def download_apollo_apr() -> list[dict]:
    """7. Apollo -> APR 同源替代。

    Apollo 论文 (ICCAD 2025) 代码未开源（仓库为空）。
    使用同团队前身工作 APR (ASP-DAC 2025) 作为同源替代。
    R02/R03 合规：明确标注替代关系，不伪造 Apollo 代码。
    """
    print("\n[apollo] === Apollo (APR 同源替代) ===")
    print("[apollo] 注意: Apollo 仓库 (ScopeX-ASU/Apollo) 为空，"
          "ICCAD 2025 代码未发布。使用同团队 APR 仓库作为同源替代。")
    zip_path, prefix = _download_repo_zip(
        "ScopeX-ASU", "APR", "main", "apr_apollo.zip", "apollo")
    dest_dir = REAL_DIR / "apollo"
    want = want_by_extensions((".yaml", ".yml", ".json", ".gds"),
                              exclude_paths=COMMON_EXCLUDE_PATHS,
                              exclude_filenames=COMMON_EXCLUDE_FILES)
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    seen = set()
    dedup_items = []
    for rel, local_rel, size in items:
        if local_rel in seen:
            continue
        seen.add(local_rel)
        dedup_items.append((rel, local_rel, size))
    print(f"[apollo] 提取 {len(dedup_items)} 个文件 (来源 APR)")
    origin = "https://github.com/ScopeX-ASU/APR/blob/main"
    entries = _emit_entries(dedup_items, source="apollo",
                            fmt="YAML/JSON/GDS", subdir="apollo",
                            origin_url=origin)
    # 标注替代关系
    for e in entries:
        e["source_note"] = (
            "Apollo ICCAD 2025 code unreleased; uses APR (ASP-DAC 2025) "
            "by same ASU team as same-origin substitute."
        )
    return entries


def download_perceval() -> list[dict]:
    """8. Perceval - 量子光子电路示例。"""
    print("\n[perceval] === Perceval 量子光子电路 ===")
    zip_path, prefix = _download_repo_zip(
        "Quandela", "Perceval", "main", "perceval.zip", "perceval")
    dest_dir = REAL_DIR / "perceval"
    # Perceval 是 Python 库，示例在 perceval/examples/ 和 perceval/tests/
    # 提取 .json (电路定义) 与 .py (示例代码)
    want = want_by_extensions((".json", ".py"),
                              exclude_paths=COMMON_EXCLUDE_PATHS + (
                                  "docs/_build/", ".github/",
                              ),
                              exclude_filenames=COMMON_EXCLUDE_FILES + (
                                  "__init__.py", "conftest.py",
                                  "pyproject.toml", "setup.cfg",
                              ))
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, PY_MAX_BYTES)
    print(f"[perceval] 提取 {len(items)} 个文件")
    origin = "https://github.com/Quandela/Perceval/blob/main"
    return _emit_entries(items, source="perceval",
                         fmt="JSON/PY", subdir="perceval", origin_url=origin)


def download_klayout_pcells() -> list[dict]:
    """9. KLayoutPhotonicPCells-core - KLayout 光子 PCell 模板。"""
    print("\n[klayout_pcells] === KLayout Photonic PCells ===")
    zip_path, prefix = _download_repo_zip(
        "sebastian-goeldi", "KLayoutPhotonicPCells-core", "master",
        "klayout_pcells.zip", "klayout_pcells")
    dest_dir = REAL_DIR / "klayout_pcells"
    want = want_by_extensions((".gds", ".py", ".lyp"),
                              exclude_paths=COMMON_EXCLUDE_PATHS,
                              exclude_filenames=COMMON_EXCLUDE_FILES)
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    print(f"[klayout_pcells] 提取 {len(items)} 个文件")
    origin = (
        "https://github.com/sebastian-goeldi/"
        "KLayoutPhotonicPCells-core/blob/master"
    )
    return _emit_entries(items, source="klayout_pcells",
                         fmt="GDS/PY", subdir="klayout_pcells",
                         origin_url=origin)


def download_quantum_rf() -> list[dict]:
    """10. quantum-rf-pdk - 量子 RF PDK。"""
    print("\n[quantum_rf] === quantum-rf-pdk ===")
    zip_path, prefix = _download_repo_zip(
        "gdsfactory", "quantum-rf-pdk", "main",
        "quantum_rf_pdk.zip", "quantum_rf")
    dest_dir = REAL_DIR / "quantum_rf"
    want = want_by_extensions((".pic.yml", ".yml", ".gds"),
                              exclude_paths=COMMON_EXCLUDE_PATHS,
                              exclude_filenames=COMMON_EXCLUDE_FILES)
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    seen = set()
    dedup_items = []
    for rel, local_rel, size in items:
        if local_rel in seen:
            continue
        seen.add(local_rel)
        dedup_items.append((rel, local_rel, size))
    print(f"[quantum_rf] 提取 {len(dedup_items)} 个文件")
    origin = "https://github.com/gdsfactory/quantum-rf-pdk/blob/main"
    return _emit_entries(dedup_items, source="quantum_rf",
                         fmt="YAML/GDS", subdir="quantum_rf",
                         origin_url=origin)


# ---------------------------------------------------------------------------
# 索引构建
# ---------------------------------------------------------------------------

def build_index(all_entries: list[dict], source_status: dict) -> None:
    """生成 real_board/index_new_sources.json 本批次索引。"""
    by_source: dict[str, int] = {}
    by_format: dict[str, int] = {}
    for e in all_entries:
        by_source[e["source"]] = by_source.get(e["source"], 0) + 1
        by_format[e["format"]] = by_format.get(e["format"], 0) + 1

    index = {
        "description": (
            "PoLaRIS 第二批真实光子 PDK 用例索引。所有文件从公开 GitHub "
            "仓库下载（codeload zip + 选择性提取），未做任何内容修改。"
            "source 字段标注原始仓库来源，origin 字段提供可溯源的 GitHub "
            "blob URL。"
        ),
        "generated_by": "scripts/download_new_real_circuits.py",
        "batch": "batch-2 (10 new photonics PDK sources)",
        "download_method": "codeload.github.com zip + zipfile selective extract",
        "total": len(all_entries),
        "by_source": by_source,
        "by_format": by_format,
        "source_status": source_status,
        "references": [
            {
                "source": "ubcpdk",
                "url": "https://github.com/gdsfactory/ubc",
                "license": "MIT",
                "authors": "Lukas Chrostowski et al. (UBC / SiEPIC)",
                "extracted": "**/*.gds + **/*.pic.yml + **/*.yml",
            },
            {
                "source": "cspdk",
                "url": "https://github.com/gdsfactory/cspdk",
                "license": "MIT",
                "authors": "gdsfactory community",
                "extracted": "**/*.gds + **/*.pic.yml + **/*.yml",
            },
            {
                "source": "vtt",
                "url": "https://github.com/gdsfactory/vtt",
                "license": "MIT",
                "authors": "VTT Technical Research Centre of Finland",
                "extracted": "**/*.gds + **/*.pic.yml + **/*.yml",
            },
            {
                "source": "gf_test_data",
                "url": "https://github.com/gdsfactory/gdsfactory-test-data",
                "doi": "10.1117/1.JOM.2.4.043501",
                "license": "MIT",
                "authors": "Joaquin Matres et al. (2014-2024)",
                "extracted": "**/*.gds",
            },
            {
                "source": "luxtelligence",
                "url": "https://github.com/Luxtelligence/lxt_pdk_gf",
                "license": "MIT",
                "authors": "Luxtelligence AG",
                "extracted": "**/*.gds + **/*.pic.yml + **/*.yml",
            },
            {
                "source": "siepicfab",
                "url": "https://github.com/SiEPIC/SiEPICfab_Shuksan_PDK",
                "license": "Apache-2.0",
                "authors": "Lukas Chrostowski et al. (SiEPICfab)",
                "extracted": "**/*.gds + **/*.xml",
            },
            {
                "source": "apollo",
                "paper_url": "https://scopex-asu.github.io/files/publications/PD_ICCAD2025_Gu.pdf",
                "paper": (
                    "Zhou, Yang, Gangi, Ren, Huang, Gu, "
                    "'Apollo: Automated Routing-Informed Placement for "
                    "Large-Scale Photonic Integrated Circuits', "
                    "ICCAD 2025."
                ),
                "code_url": "https://github.com/ScopeX-ASU/APR",
                "code_note": (
                    "Apollo 仓库为空（代码未发布），使用同团队前身工作 APR "
                    "(ASP-DAC 2025) 作为同源替代。R02/R03 合规：明确标注，"
                    "不伪造 Apollo 代码。"
                ),
                "license": "MIT",
                "authors": (
                    "Hongjian Zhou, Keren Zhu, Jiaqi Gu (ASU / Fudan)"
                ),
                "extracted": "**/*.yaml + **/*.yml + **/*.json + **/*.gds",
            },
            {
                "source": "perceval",
                "url": "https://github.com/Quandela/Perceval",
                "arxiv": "arXiv:2207.10582",
                "doi": "10.22331/q-2024-04-26-1333",
                "license": "MIT",
                "authors": "Nicolas Heurtel et al. (Quandela)",
                "extracted": "**/*.json + **/*.py (examples/tests)",
            },
            {
                "source": "klayout_pcells",
                "url": "https://github.com/sebastian-goeldi/KLayoutPhotonicPCells-core",
                "license": "MIT",
                "authors": "Sebastian Goeldi",
                "extracted": "**/*.gds + **/*.py + **/*.lyp",
            },
            {
                "source": "quantum_rf",
                "url": "https://github.com/gdsfactory/quantum-rf-pdk",
                "license": "MIT",
                "authors": "gdsfactory community",
                "extracted": "**/*.pic.yml + **/*.yml + **/*.gds",
            },
        ],
        "files": all_entries,
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n[索引] 已写入 {INDEX_PATH} (total={len(all_entries)})")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="PoLaRIS 第二批真实光子 PDK 用例下载器"
    )
    parser.add_argument(
        "--keep-zip", action="store_true",
        help="保留下载的 zip（调试用，默认清理）",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("PoLaRIS 第二批真实光子 PDK 用例下载器 (10 sources)")
    print("=" * 70)

    # 1. 网络探测（R03：失败即 raise）
    test_network()

    # 2. 准备目录
    REAL_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    all_entries: list[dict] = []
    source_status: dict = {}

    # 3. 各源下载
    sources = [
        ("ubcpdk", download_ubcpdk),
        ("cspdk", download_cspdk),
        ("vtt", download_vtt),
        ("gf_test_data", download_gf_test_data),
        ("luxtelligence", download_luxtelligence),
        ("siepicfab", download_siepicfab),
        ("apollo", download_apollo_apr),
        ("perceval", download_perceval),
        ("klayout_pcells", download_klayout_pcells),
        ("quantum_rf", download_quantum_rf),
    ]

    for name, fn in sources:
        try:
            entries = fn()
            all_entries.extend(entries)
            source_status[name] = {
                "status": "ok" if entries else "no_files",
                "count": len(entries),
            }
        except SourceUnavailableError as e:
            source_status[name] = {
                "status": "unavailable", "reason": str(e), "count": 0,
            }
            print(f"[{name}] 源不可用，跳过: {e}")
        except Exception as e:  # noqa: BLE001
            source_status[name] = {
                "status": "error", "reason": repr(e), "count": 0,
            }
            print(f"[{name}] 下载出错（不终止其他源）: {e!r}")

    # 4. 构建索引
    build_index(all_entries, source_status)

    # 5. 一致性校验：本批次 index 条目数 == 磁盘文件数（R05 防复发）
    new_subdirs = ["ubcpdk", "cspdk", "vtt", "gf_test_data", "luxtelligence",
                   "siepicfab", "apollo", "perceval", "klayout_pcells",
                   "quantum_rf"]
    disk_files = 0
    for sub in new_subdirs:
        d = REAL_DIR / sub
        if d.exists():
            disk_files += sum(1 for p in d.rglob("*") if p.is_file())
    if disk_files != len(all_entries):
        print(
            f"[警告] 一致性校验失败: 磁盘文件数 {disk_files} != index 条目数 "
            f"{len(all_entries)}。可能存在残留子目录或重名覆盖。"
        )
    else:
        print(f"[校验] 本批次磁盘文件数 == index 条目数 == {disk_files} ✓")

    # 6. 总计文件数（含第一批 + 第二批）
    total_real_board = sum(1 for p in REAL_DIR.rglob("*") if p.is_file()
                           and p.name not in ("index.json", "index_new_sources.json",
                                              "README.md"))
    print(f"\n[总计] real_board/ 总文件数: {total_real_board}")

    # 7. 清理 zip（除非 --keep-zip）
    if not args.keep_zip:
        for zp in TMP_DIR.glob("*.zip"):
            zp.unlink()
            print(f"[清理] 删除 {zp}")

    # 8. 汇总
    print("\n" + "=" * 70)
    print("下载汇总（第二批 10 源）")
    print("=" * 70)
    for src, st in source_status.items():
        print(f"  {src:18s}: {st['status']:14s} count={st['count']}")
    print(f"  {'BATCH TOTAL':18s}: {len(all_entries)} 个真实用例")
    print(f"  {'GRAND TOTAL':18s}: {total_real_board} 个（含第一批）")
    target_ok = total_real_board >= 1000
    print(f"  目标 ≥1000: {'✓ 达成' if target_ok else '✗ 未达成'}")
    print(f"  索引: {INDEX_PATH}")
    return 0 if target_ok else 1


if __name__ == "__main__":
    sys.exit(main())
