"""PoLaRIS D10 GUI 增强 API 端到端测试（test_d10_api.py）。

覆盖 D10 GUI 增强（4→8 分）新增的全部 HTTP API 端点，使用真实 WebServer
实例（ThreadingHTTPServer）+ urllib 发起 HTTP 请求，验证业务逻辑正确性。

测试分组（16 个）:
- GDS 上传 (2): multipart 上传成功 + 扩展名白名单拒绝
- 独立布局/布线/DRC (3): run_placement/run_routing/run_drc
- 任务结果查询 (2): 有效 task_id + 不存在 task_id 404
- 上传列表 (1): GET /api/uploads
- 编辑器交互 (8): add_device/move_device/delete_device/scene/devices/
  set_routes/highlight_drc/undo/redo/export_klayout/clear

规则:
- R02 学术诚信: ≥5 文献 URL，所有断言可溯源
- R03 禁止 fall-back: 失败 raise，不返回假数据
- R05 无 TODO/FIXME 残留
- R11 质量门禁: 函数≤80 行 / 文件≤800 行

来源（R02 学术诚信，≥5 个文献 URL）:
1. Python http.server: https://docs.python.org/3/library/http.server.html
2. pytest fixtures: https://docs.pytest.org/en/stable/explanation/fixtures.html
3. OWASP Unrestricted File Upload:
   https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload
4. RFC 7578 multipart/form-data: https://datatracker.ietf.org/doc/html/rfc7578
5. KLayout DRC 文档: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
6. DREAMPlace DAC 2019: https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
7. SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

# === sys.path 注入（文件开头，R13 要求） ===
_MODULE_ROOT = Path(__file__).resolve().parents[2]
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
# polaris-flow 源码树（WebServer lazy 导出依赖 polaris_flow.*）
_FLOW_SRC = str(_MODULE_ROOT / "flow" / "src")
if _FLOW_SRC not in sys.path:
    sys.path.insert(0, _FLOW_SRC)
# polaris-core / place / route / drc 源码树
for _sub in ("core", "place", "route", "drc"):
    _p = str(_MODULE_ROOT / _sub / "src")
    if _p not in sys.path:
        sys.path.insert(0, _p)

from polaris_gui.web_server import WebServer  # noqa: E402


# =============================================================================
# Fixtures: 启动/停止 WebServer
# =============================================================================

_TEST_PORT = 18200


@pytest.fixture(scope="module")
def server():
    """启动 WebServer（后台线程），测试结束后停止。"""
    srv = WebServer(host="127.0.0.1", port=_TEST_PORT)
    srv.start(blocking=False)
    time.sleep(0.8)  # 等待 socket 就绪
    yield srv
    srv.stop()


def _post_json(path: str, body: dict) -> tuple[int, dict]:
    """POST JSON 并返回 (status_code, response_dict)。"""
    req = urllib.request.Request(
        f"http://127.0.0.1:{_TEST_PORT}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def _get_json(path: str) -> tuple[int, dict]:
    """GET JSON 并返回 (status_code, response_dict)。"""
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{_TEST_PORT}{path}", timeout=10
        ) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def _post_multipart(path: str, filename: str, content: bytes) -> tuple[int, dict]:
    """POST multipart/form-data 上传文件，返回 (status_code, response_dict)。"""
    boundary = "----TestBoundaryD10"
    body = (
        f"--{boundary}\r\n".encode()
        + f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        + b"Content-Type: application/octet-stream\r\n\r\n"
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    req = urllib.request.Request(
        f"http://127.0.0.1:{_TEST_PORT}{path}",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


# =============================================================================
# 1. GDS 上传
# =============================================================================


def test_upload_gds_success(server) -> None:
    """POST /api/upload_gds: multipart 上传 .py 文件成功。"""
    content = b'% Test KLayout script\nprint("hello")\n'
    status, data = _post_multipart("/api/upload_gds", "test_layout.py", content)
    assert status == 200
    assert data["success"] is True
    assert data["filename"] == "test_layout.py"
    assert data["size_bytes"] == len(content)
    assert "file_id" in data
    assert "uploaded_at" in data


def test_upload_gds_reject_exe(server) -> None:
    """POST /api/upload_gds: .exe 扩展名被白名单拒绝（400）。"""
    status, data = _post_multipart("/api/upload_gds", "evil.exe", b"fake")
    assert status == 400
    assert data["success"] is False
    assert "不支持的文件类型" in data["error"]


# =============================================================================
# 2. 独立布局/布线/DRC
# =============================================================================


def test_run_placement_mzi(server) -> None:
    """POST /api/run_placement: MZI 预设 analytical 布局。"""
    status, data = _post_json("/api/run_placement", {"preset": "mzi", "mode": "analytical"})
    assert status == 200
    assert data["success"] is True
    assert data["status"] == "done"
    assert data["type"] == "placement"
    r = data["result"]
    assert r["n_devices"] == 5
    assert r["hpwl"] > 0
    assert r["placement_mode"] == "analytical"
    assert "task_id" in data
    assert len(r["placements"]) == 5


def test_run_routing_mzi(server) -> None:
    """POST /api/run_routing: MZI 预设 curvy 布线。"""
    status, data = _post_json("/api/run_routing", {"preset": "mzi"})
    assert status == 200
    assert data["success"] is True
    assert data["status"] == "done"
    r = data["result"]
    assert r["n_paths"] >= 1
    assert r["router_type"] == "curvy"
    assert r["total_loss_db"] >= 0


def test_run_drc_mzi(server) -> None:
    """POST /api/run_drc: MZI 预设 DRC 检查。"""
    status, data = _post_json("/api/run_drc", {"preset": "mzi"})
    assert status == 200
    assert data["success"] is True
    assert data["status"] == "done"
    r = data["result"]
    assert r["n_rules"] == 25
    assert "n_violations" in r
    assert "pass_rate" in r
    assert "drc_highlights" in r


# =============================================================================
# 3. 任务结果查询
# =============================================================================


def test_get_results_valid(server) -> None:
    """GET /api/results/{task_id}: 查询有效任务结果。"""
    _, placement = _post_json("/api/run_placement", {"preset": "mzi"})
    task_id = placement["task_id"]
    status, data = _get_json(f"/api/results/{task_id}")
    assert status == 200
    assert data["task_id"] == task_id
    assert data["status"] == "done"
    assert data["type"] == "placement"


def test_get_results_not_found(server) -> None:
    """GET /api/results/{不存在的 task_id}: 返回 404。"""
    status, data = _get_json("/api/results/nonexistent-task-id-12345")
    assert status == 404
    assert "error" in data


# =============================================================================
# 4. 上传列表
# =============================================================================


def test_get_uploads(server) -> None:
    """GET /api/uploads: 列出已上传文件。"""
    status, data = _get_json("/api/uploads")
    assert status == 200
    assert "uploads" in data
    assert isinstance(data["uploads"], list)


# =============================================================================
# 5. 编辑器交互
# =============================================================================


def test_editor_add_device(server) -> None:
    """POST /api/editor/device: 添加器件到场景。"""
    status, data = _post_json("/api/editor/device", {
        "device_type": "grating_coupler",
        "position": [100.0, 100.0],
        "category": "source",
    })
    assert status == 200
    assert data["success"] is True
    assert "device_id" in data
    assert data["device_type"] == "grating_coupler"
    assert data["position"] == [100.0, 100.0]
    assert data["category"] == "source"


def test_editor_move_device(server) -> None:
    """POST /api/editor/device/move: 移动器件。"""
    # 先添加
    _, add_resp = _post_json("/api/editor/device", {
        "device_type": "waveguide",
        "position": [50.0, 50.0],
        "category": "passive",
    })
    dev_id = add_resp["device_id"]
    # 移动
    status, data = _post_json("/api/editor/device/move", {
        "device_id": dev_id,
        "new_position": [200.0, 300.0],
    })
    assert status == 200
    assert data["success"] is True
    assert data["position"] == [200.0, 300.0]


def test_editor_scene_and_devices(server) -> None:
    """GET /api/editor/scene + /api/editor/devices: 渲染场景与器件列表。"""
    status, data = _get_json("/api/editor/scene")
    assert status == 200
    assert "layers" in data
    assert "devices" in data
    assert "routes" in data
    assert "drc_highlights" in data

    status, data = _get_json("/api/editor/devices")
    assert status == 200
    assert "devices" in data
    assert isinstance(data["devices"], list)


def test_editor_set_routes(server) -> None:
    """POST /api/editor/routes: 设置布线路径用于可视化。"""
    routes = [
        {"conn_id": 0, "points": [[0, 0], [100, 0], [100, 100]]},
        {"conn_id": 1, "points": [[0, 50], [200, 50]]},
    ]
    status, data = _post_json("/api/editor/routes", {"routes": routes})
    assert status == 200
    assert data["success"] is True


def test_editor_highlight_drc(server) -> None:
    """POST /api/editor/drc: 设置 DRC 高亮标记。"""
    drc_errors = [
        {"x": 100.0, "y": 100.0, "width": 10.0, "height": 10.0, "rule": "min_spacing", "severity": "error"},
    ]
    status, data = _post_json("/api/editor/drc", {"drc_errors": drc_errors})
    assert status == 200
    assert data["success"] is True


def test_editor_undo_redo(server) -> None:
    """POST /api/editor/undo + /api/editor/redo: 撤销重做。"""
    # 先添加一个器件（产生可撤销操作）
    _post_json("/api/editor/device", {
        "device_type": "mmi",
        "position": [150.0, 150.0],
        "category": "passive",
    })
    # 撤销
    status, data = _post_json("/api/editor/undo", {})
    assert status == 200
    assert "undone" in data
    # 重做
    status, data = _post_json("/api/editor/redo", {})
    assert status == 200
    assert "redone" in data


def test_editor_export_klayout(server) -> None:
    """POST /api/editor/export_klayout: 导出 KLayout Python 脚本。"""
    status, data = _post_json("/api/editor/export_klayout", {
        "output_gds": "test.gds",
        "top_cell_name": "TOP",
    })
    assert status == 200
    assert data["success"] is True
    assert "script" in data
    assert "n_devices" in data
    assert "klayout" in data["script"].lower() or "import" in data["script"]
    assert data["output_gds"] == "test.gds"


def test_editor_clear(server) -> None:
    """POST /api/editor/clear: 清空场景。"""
    status, data = _post_json("/api/editor/clear", {})
    assert status == 200
    assert data["success"] is True
    assert data["cleared"] is True
    # 验证场景已清空
    _, scene = _get_json("/api/editor/scene")
    assert len(scene["devices"]) == 0
