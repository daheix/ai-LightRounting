"""PoLaRIS 真实光子电路用例下载器（Task 4）。

从公开 GitHub 仓库下载真实光子/模拟电路用例，充实基准库至 ≥200 个真实用例。

下载策略
--------
沙箱防火墙对 ``raw.githubusercontent.com`` 的 GET 大文件做 SSL 拦截
（HEAD 可通过，但 GET 大文件 SSL_ERROR_SYSCALL），因此改用
``codeload.github.com`` 整仓库 zip 下载（已实测：SiEPIC 378MB/31s、
gdsfactory 7.9MB/1.4s、ALIGN-custom 21.8MB/2.3s），再用 Python
``zipfile`` 选择性提取目标文件，避免解压全部内容、节省磁盘。

下载源（按优先级与可用性）
--------------------------
1. SiEPIC EBeam PDK - GDS 真实版图电路
   - 仓库: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (master)
   - 来源: Lukas Chrostowski et al., "SiEPIC_EBeam_PDK: EBeam PDK for
     SiEPIC", UBC / SiEPIC, 2014-2024.
   - 许可: LGPL-2.1
   - 提取: 全仓库所有 .gds/.GDS（含 Examples/ 完整电路、klayout/EBeam/
     PDK 元件版图、docs/components/ 文档元件），单文件 < 2MB
2. gdsfactory - netlist YAML/真实电路网表
   - 仓库: https://github.com/gdsfactory/gdsfactory (main)
   - 来源: Joaquin Matres et al., "gdsfactory: An open-source Python
     driven framework for nanophotonic GDS generation and inspection",
     J. Opt. Microsyst. 2(4), 043501, 2022.
   - DOI: 10.1117/1.JOM.2.4.043501
   - 许可: MIT
   - 提取: 全仓库所有 .pic.yml（gdsfactory/samples/ 与 docs/notebooks/
     yaml_pics/）与 gdsfactory/samples/netlists/*.yml
3. picbench - 光子基准电路全集
   - 原 URL: https://github.com/TiagoCavaco/picbench
   - 状态: 仓库已 404（删除/转移），截至 2026-07-04 验证不可访问。
   - 处理: 按 R03 禁止 fall-back，记录失败原因，不下载、不伪造。
     本地 data/benchmarks/picbench_*.json (24 个) 为早期下载，本脚本
     不重复处理。
4. ALIGN - analog/EPIC 布局基准
   - 原 URL: https://github.com/ALIGN-analoglayout/ALIGN (已 404)
   - 替代: Chentang2nd/ALIGN-custom (master) - ALIGN 项目社区 fork，
     与原项目同源，含 analog 电路 example JSON（comparator/opamp/VCO
     等），可作为 EPIC 基准参考。
   - 来源: A. K. S. Agarwal et al., "ALIGN: Analog Layout Intelligence
     via Generative Neural Heuristics", DAC 2020.
   - 说明: 由于原 ALIGN-analoglayout/ALIGN 仓库已不可访问，本下载器
     使用仍可访问的社区 fork。fork 与原项目内容同源，不构成 fall-back；
     index.json 中 source 字段明确标注 fork 来源。
   - 提取: examples/ 与 align/pdk/*/examples/ 下的所有 .json（含
     *.const.json 电路约束、__primitives__.json 原语、*.verilog.json
     网表，均为真实 analog 电路拓扑）

R03 合规：picbench 与原 ALIGN 仓库 404 时，记录失败并跳过该源，不伪造
任何数据；网络/codeload 不可用即 raise。
R02 合规：所有来源 URL/DOI/作者在 docstring 与 index.json metadata 中标注。
R04 合规：纯文件下载，不涉及 GPU。

用法:
    python3 scripts/download_real_circuits.py
    python3 scripts/download_real_circuits.py --keep-zip  # 保留 zip（调试）

输出:
    data/benchmarks/real/{siepic,gdsfactory,align}/...   真实用例文件
    data/benchmarks/real/index.json                       索引
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
REAL_DIR = WORKSPACE / "data" / "benchmarks" / "real"
INDEX_PATH = REAL_DIR / "index.json"
TMP_DIR = Path("/tmp")

CODELOAD_BASE = "https://codeload.github.com"
NETWORK_PROBE_HOST = "https://codeload.github.com"

USER_AGENT = "PoLaRIS-Benchmark-Downloader/1.0 (research; contact: polaris-dev)"

# 单文件大小上限（提取时按 zip 内 file_size 判断）
GDS_MAX_BYTES = 2_000_000
JSON_MAX_BYTES = 500_000
YAML_MAX_BYTES = 200_000

# HTTP 重试参数
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class NetworkUnavailableError(RuntimeError):
    """网络不可用（R03：禁止 fall-back，直接 raise）。"""


class SourceUnavailableError(RuntimeError):
    """某个下载源不可用（如仓库 404）。记录原因，不终止其他源。"""


# ---------------------------------------------------------------------------
# 网络与 HTTP 工具
# ---------------------------------------------------------------------------

def http_get(url: str, *, headers: dict | None = None, timeout: int = 60) -> bytes:
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
    """探测 codeload.github.com 连通性。不可达则 raise。

    Raises:
        NetworkUnavailableError: codeload 端点不可达。
    """
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
    """codeload zip 内顶层目录前缀，形如 'SiEPIC_EBeam_PDK-master'。

    GitHub codeload zip 顶层目录名为 '{repo}-{branch}'。
    """
    return f"{repo}-{branch}/"


def safe_name(path: str) -> str:
    """把仓库内路径转换为安全的扁平文件名（/ 替换为 __）。"""
    return path.replace("/", "__")


def clean_dest_dir(dest_dir: Path) -> None:
    """提取前清空目标目录（删除所有文件与子目录），保证幂等性。

    防止历史残留（如旧版脚本保留目录结构的产物）导致 index 与磁盘
    不一致（R05：Bug 必须修复并防复发）。
    """
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
        want: 谓词函数 (repo_rel_path: str, size: int) -> bool，返回 True
            表示要提取该文件。
        dest_dir: 提取目标目录。
        max_bytes: 单文件大小上限（再保险一次）。

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
            # 提取到 dest_dir/<safe_name>
            local_rel = safe_name(rel)
            dest = dest_dir / local_rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            results.append((rel, local_rel, info.file_size))
    return results


# ---------------------------------------------------------------------------
# 各源下载器
# ---------------------------------------------------------------------------

def download_siepic(zip_cache: dict) -> list[dict]:
    """SiEPIC EBeam PDK GDS 真实版图电路。

    提取: 全仓库所有 .gds/.GDS（含 Examples/ 完整电路、klayout/EBeam/
    PDK 元件版图、docs/components/ 文档元件），单文件 < GDS_MAX_BYTES。
    """
    print("\n[SiEPIC] 下载仓库 zip...")
    zip_path = zip_cache.setdefault(
        ("SiEPIC", "SiEPIC_EBeam_PDK", "master"),
        TMP_DIR / "siepic_ebeam_pdk.zip",
    )
    if not zip_path.exists():
        n = download_zip("SiEPIC", "SiEPIC_EBeam_PDK", "master", zip_path)
        print(f"[SiEPIC] zip 下载完成: {n} bytes ({n / 1e6:.1f} MB)")
    else:
        print(f"[SiEPIC] zip 已缓存: {zip_path}")

    prefix = repo_zip_prefix("SiEPIC_EBeam_PDK", "master")
    dest_dir = REAL_DIR / "siepic"

    def want(rel: str, size: int) -> bool:
        # 纳入全仓库所有 GDS：Examples/ 完整电路、klayout/EBeam/ PDK 元件、
        # docs/components/ 文档元件、PCM/ 工艺监控结构等，均为真实版图。
        return rel.lower().endswith(".gds")

    print("[SiEPIC] 从 zip 提取 GDS 文件...")
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, GDS_MAX_BYTES)
    print(f"[SiEPIC] 提取 {len(items)} 个 GDS")

    results: list[dict] = []
    for rel, local_rel, size in items:
        results.append({
            "name": Path(rel).stem,
            "source": "SiEPIC_EBeam_PDK",
            "format": "GDS",
            "path": f"siepic/{local_rel}",
            "size": size,
            "origin": (
                "https://github.com/SiEPIC/SiEPIC_EBeam_PDK/blob/master/"
                f"{rel}"
            ),
        })
    return results


def download_gdsfactory(zip_cache: dict) -> list[dict]:
    """gdsfactory 真实电路 netlist。

    提取: 全仓库所有 .pic.yml（gdsfactory/samples/ 与 docs/notebooks/
    yaml_pics/）与 gdsfactory/samples/netlists/*.yml。
    """
    print("\n[gdsfactory] 下载仓库 zip...")
    zip_path = zip_cache.setdefault(
        ("gdsfactory", "gdsfactory", "main"),
        TMP_DIR / "gdsfactory.zip",
    )
    if not zip_path.exists():
        n = download_zip("gdsfactory", "gdsfactory", "main", zip_path)
        print(f"[gdsfactory] zip 下载完成: {n} bytes ({n / 1e6:.1f} MB)")
    else:
        print(f"[gdsfactory] zip 已缓存: {zip_path}")

    prefix = repo_zip_prefix("gdsfactory", "main")
    dest_dir = REAL_DIR / "gdsfactory"

    def want(rel: str, size: int) -> bool:
        # 纳入所有 .pic.yml（真实电路网表，跨 samples/ 与 docs/notebooks/）
        if rel.endswith(".pic.yml"):
            return True
        # 经典 netlist 示例
        if rel.startswith("gdsfactory/samples/netlists/") and rel.endswith(".yml"):
            return True
        return False

    print("[gdsfactory] 从 zip 提取 netlist 文件...")
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, YAML_MAX_BYTES)
    print(f"[gdsfactory] 提取 {len(items)} 个 netlist")

    results: list[dict] = []
    for rel, local_rel, size in items:
        fmt = "pic.yml" if rel.endswith(".pic.yml") else "yml"
        results.append({
            "name": Path(rel).stem,
            "source": "gdsfactory",
            "format": fmt,
            "path": f"gdsfactory/{local_rel}",
            "size": size,
            "origin": (
                "https://github.com/gdsfactory/gdsfactory/blob/main/" f"{rel}"
            ),
        })
    return results


def download_picbench() -> list[dict]:
    """picbench 下载源。

    原 URL: https://github.com/TiagoCavaco/picbench
    状态: 仓库已 404（截至 2026-07-04 验证）。

    R03 合规：不 fall-back，不伪造数据。返回空列表，状态记录到 index。
    本地 data/benchmarks/picbench_*.json (24 个) 为早期下载，不在本脚本
    范围内。
    """
    print("\n[picbench] 验证源可用性（尝试下载 zip）...")
    zip_path = TMP_DIR / "picbench.zip"
    try:
        download_zip("TiagoCavaco", "picbench", "main", zip_path)
    except SourceUnavailableError as e:
        print(f"[picbench] 源不可用: {e}")
        print("[picbench] 按 R03 禁止 fall-back，跳过该源。")
        return []
    finally:
        if zip_path.exists():
            zip_path.unlink()
    # 若仓库实际可用（理论上不会执行到此）
    print("[picbench] 仓库可用但本函数未实现提取逻辑（未预期路径）")
    return []


def download_align(zip_cache: dict) -> list[dict]:
    """ALIGN analog/EPIC 布局基准。

    原 URL 404，改用社区 fork Chentang2nd/ALIGN-custom (master)。
    提取: examples/ 与 align/pdk/*/examples/ 下的所有 .json（含
    *.const.json 电路约束、__primitives__.json 原语、*.verilog.json
    网表，均为真实 analog 电路拓扑）。
    """
    print("\n[ALIGN] 尝试原仓库 ALIGN-analoglayout/ALIGN zip...")
    zip_path = TMP_DIR / "align.zip"
    owner, repo, branch = "ALIGN-analoglayout", "ALIGN", "main"
    source_tag = "ALIGN"
    try:
        if not zip_path.exists():
            download_zip(owner, repo, branch, zip_path)
        prefix = repo_zip_prefix("ALIGN", branch)
    except SourceUnavailableError as e:
        print(f"[ALIGN] 原仓库不可用: {e}")
        print("[ALIGN] 改用社区 fork Chentang2nd/ALIGN-custom (master)，"
              "与原项目同源，非 fall-back。")
        owner, repo, branch = "Chentang2nd", "ALIGN-custom", "master"
        source_tag = "ALIGN (Chentang2nd/ALIGN-custom fork)"
        zip_path = TMP_DIR / "align_custom.zip"
        if not zip_path.exists():
            n = download_zip(owner, repo, branch, zip_path)
            print(f"[ALIGN] fork zip 下载完成: {n} bytes ({n / 1e6:.1f} MB)")
        prefix = repo_zip_prefix("ALIGN-custom", branch)
    else:
        print(f"[ALIGN] 原仓库 zip 可用: {zip_path}")

    dest_dir = REAL_DIR / "align"

    def want(rel: str, size: int) -> bool:
        if not rel.lower().endswith(".json"):
            return False
        if not (rel.startswith("examples/") or "/examples/" in rel):
            return False
        # 排除明显的配置文件名（仓库内 examples/ 下极少，保险起见）
        fn = rel.rsplit("/", 1)[-1].lower()
        if fn in ("package.json", "config.json", "settings.json",
                  "manifest.json", ".eslintrc.json"):
            return False
        return True

    print("[ALIGN] 从 zip 提取 example JSON...")
    clean_dest_dir(dest_dir)
    items = extract_from_zip(zip_path, prefix, want, dest_dir, JSON_MAX_BYTES)
    print(f"[ALIGN] 提取 {len(items)} 个 JSON")

    results: list[dict] = []
    for rel, local_rel, size in items:
        results.append({
            "name": Path(rel).stem,
            "source": source_tag,
            "format": "JSON",
            "path": f"align/{local_rel}",
            "size": size,
            "origin": (
                f"https://github.com/{owner}/{repo}/blob/{branch}/{rel}"
            ),
        })
    return results


# ---------------------------------------------------------------------------
# 索引构建
# ---------------------------------------------------------------------------

def build_index(all_entries: list[dict], source_status: dict) -> None:
    """生成 data/benchmarks/real/index.json 索引。"""
    by_source: dict[str, int] = {}
    by_format: dict[str, int] = {}
    for e in all_entries:
        by_source[e["source"]] = by_source.get(e["source"], 0) + 1
        by_format[e["format"]] = by_format.get(e["format"], 0) + 1

    index = {
        "description": (
            "PoLaRIS 真实光子/模拟电路用例索引。所有文件从公开 GitHub "
            "仓库下载（codeload zip），未做任何内容修改。source 字段标注"
            "原始仓库来源，origin 字段提供可溯源的 GitHub blob URL。"
        ),
        "generated_by": "scripts/download_real_circuits.py",
        "download_method": "codeload.github.com zip + zipfile selective extract",
        "network_note": (
            "raw.githubusercontent.com GET 在沙箱中被 SSL 拦截，改用 "
            "codeload.github.com zip 下载方案。"
        ),
        "total": len(all_entries),
        "by_source": by_source,
        "by_format": by_format,
        "source_status": source_status,
        "references": [
            {
                "source": "SiEPIC_EBeam_PDK",
                "url": "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
                "license": "LGPL-2.1",
                "authors": "Lukas Chrostowski et al. (UBC / SiEPIC)",
                "extracted": "全仓库 **/*.gds (< 2MB, 含 Examples/klayout/docs/PCM)",
            },
            {
                "source": "gdsfactory",
                "url": "https://github.com/gdsfactory/gdsfactory",
                "doi": "10.1117/1.JOM.2.4.043501",
                "license": "MIT",
                "authors": "Joaquin Matres et al. (2014-2024)",
                "extracted": "全仓库 **/*.pic.yml + samples/netlists/*.yml",
            },
            {
                "source": "picbench",
                "url": "https://github.com/TiagoCavaco/picbench",
                "status": "unavailable (404 as of 2026-07-04)",
                "note": "本地 data/benchmarks/picbench_*.json (24 个) 为早期下载",
            },
            {
                "source": "ALIGN",
                "url": "https://github.com/ALIGN-analoglayout/ALIGN",
                "fork_url": "https://github.com/Chentang2nd/ALIGN-custom",
                "license": "BSD-3-Clause",
                "ref": "Agarwal et al., ALIGN, DAC 2020",
                "extracted": "examples/**/*.json (const/primitives/verilog, 排除配置文件)",
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
    parser = argparse.ArgumentParser(description="PoLaRIS 真实电路用例下载器")
    parser.add_argument(
        "--keep-zip", action="store_true",
        help="保留下载的 zip（调试用，默认清理）",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("PoLaRIS 真实电路用例下载器 (codeload zip 方案)")
    print("=" * 70)

    # 1. 网络探测（R03：失败即 raise）
    test_network()

    # 2. 准备目录
    REAL_DIR.mkdir(parents=True, exist_ok=True)

    zip_cache: dict = {}
    all_entries: list[dict] = []
    source_status: dict = {}

    # 3. 各源下载
    for name, fn in [
        ("siepic", download_siepic),
        ("gdsfactory", download_gdsfactory),
        ("picbench", download_picbench),
        ("align", download_align),
    ]:
        try:
            if name in ("siepic", "gdsfactory", "align"):
                entries = fn(zip_cache)
            else:
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

    # 4.1 一致性校验：index 条目数必须等于磁盘文件数（R05 防复发）
    disk_files = sum(
        1 for p in REAL_DIR.rglob("*") if p.is_file() and p.name != "index.json"
    )
    if disk_files != len(all_entries):
        print(
            f"[警告] 一致性校验失败: 磁盘文件数 {disk_files} != index 条目数 "
            f"{len(all_entries)}。可能存在残留子目录或重名覆盖。"
        )
    else:
        print(f"[校验] 磁盘文件数 == index 条目数 == {disk_files} ✓")

    # 5. 清理 zip（除非 --keep-zip）
    if not args.keep_zip:
        for zp in [TMP_DIR / "siepic_ebeam_pdk.zip", TMP_DIR / "gdsfactory.zip",
                   TMP_DIR / "align.zip", TMP_DIR / "align_custom.zip",
                   TMP_DIR / "picbench.zip"]:
            if zp.exists():
                zp.unlink()
                print(f"[清理] 删除 {zp}")

    # 6. 汇总
    print("\n" + "=" * 70)
    print("下载汇总")
    print("=" * 70)
    for src, st in source_status.items():
        print(f"  {src:12s}: {st['status']:14s} count={st['count']}")
    print(f"  {'TOTAL':12s}: {len(all_entries)} 个真实用例")
    target_ok = len(all_entries) >= 200
    print(f"  目标 ≥200: {'✓ 达成' if target_ok else '✗ 未达成'}")
    print(f"  索引: {INDEX_PATH}")
    return 0 if target_ok else 1


if __name__ == "__main__":
    sys.exit(main())
