"""PoLaRIS Web UI 测试（阶段 F4）。"""

from __future__ import annotations

import json
import time
import urllib.request

import pytest

from polaris.web.server import WebServer, _get_presets, _run_pipeline


def test_get_presets():
    """预设电路列表非空且结构正确。"""
    presets = _get_presets()
    assert len(presets) >= 2
    for p in presets:
        assert "id" in p
        assert "name" in p
        assert "description" in p
        assert "devices" in p
        assert "platform" in p


def test_run_pipeline_mzi():
    """MZI 预设流水线运行成功。"""
    result = _run_pipeline("mzi", "default")
    assert result["success"] is True
    assert result["circuit_name"] == "MZI"
    assert result["n_devices"] == 5
    assert result["n_paths"] >= 1
    assert len(result["placements"]) == 5
    assert result["canvas_w"] == 500
    assert result["canvas_h"] == 300


def test_run_pipeline_ring():
    """Ring 预设流水线运行成功。"""
    result = _run_pipeline("ring", "default")
    assert result["success"] is True
    assert result["n_devices"] == 4
    assert len(result["placements"]) == 4


def test_run_pipeline_invalid_preset():
    """未知预设应抛出 ValueError。"""
    with pytest.raises(ValueError, match="未知预设"):
        _run_pipeline("nonexistent", "default")


def test_web_server_health_endpoint():
    """Web 服务器 /api/health 端点返回正确状态。"""
    server = WebServer(host="127.0.0.1", port=8771)
    server.start(blocking=False)
    try:
        time.sleep(0.3)
        resp = urllib.request.urlopen("http://127.0.0.1:8771/api/health")
        data = json.loads(resp.read().decode())
        assert data["status"] == "ok"
        assert "PoLaRIS" in data["service"]
    finally:
        server.stop()


def test_web_server_presets_endpoint():
    """Web 服务器 /api/presets 端点返回预设列表。"""
    server = WebServer(host="127.0.0.1", port=8772)
    server.start(blocking=False)
    try:
        time.sleep(0.3)
        resp = urllib.request.urlopen("http://127.0.0.1:8772/api/presets")
        data = json.loads(resp.read().decode())
        assert "presets" in data
        assert len(data["presets"]) >= 2
    finally:
        server.stop()


def test_web_server_static_index():
    """Web 服务器返回 index.html 静态文件。"""
    server = WebServer(host="127.0.0.1", port=8773)
    server.start(blocking=False)
    try:
        time.sleep(0.3)
        resp = urllib.request.urlopen("http://127.0.0.1:8773/")
        content = resp.read().decode()
        assert "PoLaRIS" in content
        assert "光弈" in content
    finally:
        server.stop()


def test_web_server_run_endpoint():
    """Web 服务器 /api/run 端点执行流水线。"""
    server = WebServer(host="127.0.0.1", port=8774)
    server.start(blocking=False)
    try:
        time.sleep(0.3)
        body = json.dumps({"preset": "mzi", "router_type": "default"}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8774/api/run",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode())
        assert data["success"] is True
        assert data["result"]["circuit_name"] == "MZI"
    finally:
        server.stop()
