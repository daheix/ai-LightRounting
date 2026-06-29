"""P1-B R03 fall-back 修复回归测试（flow + pipeline 子包）。

本测试固化 R03「失败即 raise，禁止静默兜底」的 7 处修复，防止 fall-back 复发。

修复清单（文件:行号 + 根因 + 修复）:
- #v3.3-F-1  flow/recipe.py:_coerce_scalar  except pass 死代码 → 移除，非 str 输入自然抛 AttributeError
- #v3.3-F-2  flow/tracker.py:list_jobs      except continue 跳过损坏 JSON → 移除，损坏文件 raise
- #v3.3-F-3  flow/tracker.py:_read_job_metadata except return None → 移除，损坏文件 raise（缺失仍 None）
- #v3.3-F-4  flow/scheduler.py:_execute_job  except RuntimeError 仅 logger.error → 追加 raise
- #v3.3-P-3  pipeline/training.py:_load_benchmarks 缺失目录 return [] → raise FileNotFoundError
- #v3.3-P-4  pipeline/training.py:_load_benchmarks except logger.warning 跳过损坏文件 → 移除，raise
- #v3.3-P-5  pipeline/training.py:_parse_benchmark_json 空基准 return None → raise ValueError

合法 return None/[]（不修改，本测试固化其行为）:
- tracker 查询未命中返回 None / 空列表（文件缺失）
- ipkiss_flow 器件无模型返回 None（可选字段）
- curvy_router 布线失败返回 None（控制流信号，由 unrouted 列表处理）
- integrated 空电路返回 {}（n_dev==0）
- scheduler 阶段执行失败标记 FAILED 并返回 False（proper error handling）

学术来源 (R02 ≥5):
- Effective Python 3rd Ed. Item 32（优先抛异常而非返回 None）
  https://effectivepython.com/
- Real Python: Effectively Raising Exceptions（fail-fast / 异常链）
  https://realpython.com/python-raise-exception/
- pytest raises 文档（异常断言）
  https://docs.pytest.org/en/stable/how-to/assert.html#assertions-about-expected-exceptions
- Python 官方异常处理教程（EAFP vs LBYL）
  https://docs.python.org/3/tutorial/errors.html
- SiEPIC EBeam PDK（基准数据格式）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- GDSFactory netlist 格式（instances/connections/routes）
  https://gdsfactory.github.io/gdsfactory/

约束:
- 使用 pytest + tmp_path，不污染工作区
- 禁止 fall-back：测试失败时不降低断言标准（R03）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polaris.data.specs import CircuitSpec
from polaris.flow.job import Job, JobStatus
from polaris.flow.recipe import Recipe, _coerce_scalar
from polaris.flow.scheduler import JobScheduler
from polaris.flow.tracker import JobTracker
from polaris.flow.workspace import Workspace
from polaris.pipeline.training import (
    TrainingPipeline,
    _parse_benchmark_json,
)


# =============================================================================
# 辅助函数
# =============================================================================


def _make_job(tmp_path: Path, job_id: str = "fb_test", enabled_stages=None) -> Job:
    """构造绑定临时工作空间的 Job。"""
    recipe = Recipe()
    if enabled_stages is not None:
        recipe.enabled_stages = enabled_stages
    ws = Workspace(str(tmp_path), job_id)
    return Job(job_id=job_id, recipe=recipe, workspace=ws)


def _write_benchmark(path: Path, *, instances=None, connections=None, routes=None,
                     name=None) -> None:
    """写一个 GDSFactory 格式基准 JSON。"""
    payload = {
        "source": "GDSFactory",
        "name": name or path.stem,
        "instances": instances or {},
        "connections": connections or [],
    }
    if routes is not None:
        payload["routes"] = routes
    path.write_text(json.dumps(payload), encoding="utf-8")


# =============================================================================
# #v3.3-F-1: flow/recipe.py _coerce_scalar 移除 except pass 死代码
# =============================================================================


class TestCoerceScalarNoFallback:
    """_coerce_scalar 不再静默吞非 str 输入（R03）。"""

    def test_coerce_int(self):
        """整数字符串转 int。"""
        assert _coerce_scalar("42") == 42
        assert isinstance(_coerce_scalar("0"), int)

    def test_coerce_float(self):
        """浮点字符串转 float。"""
        assert _coerce_scalar("3.14") == 3.14
        assert isinstance(_coerce_scalar("0.0"), float)

    def test_coerce_str_passthrough(self):
        """非数字字符串原样返回。"""
        assert _coerce_scalar("mzi") == "mzi"
        assert _coerce_scalar("SOI") == "SOI"

    def test_coerce_non_str_raises(self):
        """非字符串输入违反类型契约，必须抛 AttributeError（禁止 fall-back）。

        原 except (ValueError, AttributeError): pass 会静默返回 None/原值，
        现已移除——None.isdigit() 自然抛 AttributeError 上抛告警。
        """
        with pytest.raises(AttributeError):
            _coerce_scalar(None)  # type: ignore[arg-type]
        with pytest.raises(AttributeError):
            _coerce_scalar(123)  # type: ignore[arg-type]


# =============================================================================
# #v3.3-F-2 / #v3.3-F-3: flow/tracker.py 损坏 JSON 必须 raise
# =============================================================================


class TestTrackerCorruptJsonRaises:
    """JobTracker 对损坏 JSON 抛异常（R03），对缺失返回 None/[]（合法保留）。"""

    @staticmethod
    def _make_valid_job_dir(base: Path, job_id: str, status: str = "completed") -> Path:
        ws = Workspace(str(base), job_id)
        ws.write_job_metadata({
            "job_id": job_id, "status": status,
            "current_stage": 10, "progress": "10/10",
            "submit_time": "2024-01-01T12:00:00",
        })
        return Path(str(base)) / job_id

    def test_list_jobs_corrupt_json_raises(self, tmp_path):
        """list_jobs 遇损坏 job.json 必须 raise（原 continue 静默跳过是 fall-back）。"""
        self._make_valid_job_dir(tmp_path, "good_job", "completed")
        # 写一个损坏的 job.json
        bad_dir = tmp_path / "bad_job"
        bad_dir.mkdir()
        (bad_dir / "job.json").write_text("{不是合法 JSON", encoding="utf-8")

        tracker = JobTracker(base_output_dir=str(tmp_path))
        # 损坏文件必须上抛，禁止静默跳过
        with pytest.raises(json.JSONDecodeError):
            tracker.list_jobs()

    def test_read_job_metadata_corrupt_raises(self, tmp_path):
        """_read_job_metadata 文件存在但损坏必须 raise（原 return None 是 fall-back）。"""
        bad_dir = tmp_path / "corrupt_job"
        bad_dir.mkdir()
        (bad_dir / "job.json").write_text("<<<坏数据>>>", encoding="utf-8")

        tracker = JobTracker(base_output_dir=str(tmp_path))
        with pytest.raises(json.JSONDecodeError):
            tracker._read_job_metadata("corrupt_job")

    def test_get_status_corrupt_raises(self, tmp_path):
        """get_status 经 _read_job_metadata，损坏文件应 raise。"""
        bad_dir = tmp_path / "c2"
        bad_dir.mkdir()
        (bad_dir / "job.json").write_text("not json", encoding="utf-8")
        tracker = JobTracker(base_output_dir=str(tmp_path))
        with pytest.raises(json.JSONDecodeError):
            tracker.get_status("c2")

    def test_missing_file_returns_none(self, tmp_path):
        """合法查询未命中：文件缺失返回 None（非 fall-back，保留）。"""
        tracker = JobTracker(base_output_dir=str(tmp_path))
        assert tracker.get_status("nonexistent") is None
        assert tracker.get_job("nonexistent") is None
        assert tracker.get_stage_result("nonexistent", 1) is None
        assert tracker.get_history("nonexistent") == []

    def test_missing_basedir_returns_empty(self, tmp_path):
        """合法空查询：base_output_dir 不存在返回空列表（保留）。"""
        tracker = JobTracker(base_output_dir=str(tmp_path / "no_such_dir"))
        assert tracker.list_jobs() == []

    def test_valid_jobs_still_listed(self, tmp_path):
        """回归：有效作业仍可正常列出（修复未破坏正常路径）。"""
        self._make_valid_job_dir(tmp_path, "j1", "completed")
        self._make_valid_job_dir(tmp_path, "j2", "failed")
        tracker = JobTracker(base_output_dir=str(tmp_path))
        jobs = tracker.list_jobs()
        assert len(jobs) == 2
        assert {j["job_id"] for j in jobs} == {"j1", "j2"}


# =============================================================================
# #v3.3-F-4: flow/scheduler.py 状态转换失败必须 re-raise
# =============================================================================


class TestSchedulerStateTransitionReraise:
    """_execute_job 内状态转换 RuntimeError 必须 re-raise（R03）。"""

    def test_normal_failure_marks_job_failed(self, tmp_path):
        """回归：阶段执行失败时作业正常标记 FAILED（修复未破坏正常失败路径）。"""
        def failing_executor(recipe, workspace, prev_outputs):
            raise ValueError("故意失败")

        scheduler = JobScheduler(
            max_workers=1, stage_executors={1: failing_executor},
        )
        try:
            job = _make_job(tmp_path, "normal_fail", enabled_stages=[1])
            scheduler.submit(job)
            # 等待终态
            import time
            deadline = time.time() + 5.0
            while time.time() < deadline and job.status not in (
                JobStatus.FAILED, JobStatus.COMPLETED, JobStatus.CANCELLED,
            ):
                time.sleep(0.05)
            assert job.status == JobStatus.FAILED
            assert job.error is not None
        finally:
            scheduler.shutdown()

    def test_state_transition_failure_reraises(self, tmp_path, monkeypatch):
        """状态转换失败（mark_failed 抛 RuntimeError）必须 re-raise，禁止静默吞没。

        通过 monkeypatch 让 mark_failed 抛 RuntimeError，触发 _execute_job 内层
        except RuntimeError。原实现仅 logger.error 后吞没；R03 修复后必须 re-raise。
        直接调用 _execute_job 观察异常上抛。
        """
        def boom(self, error=None):
            raise RuntimeError("模拟状态转换失败")

        monkeypatch.setattr(Job, "mark_failed", boom)

        def failing_executor(recipe, workspace, prev_outputs):
            raise ValueError("触发外层 except")

        scheduler = JobScheduler(
            max_workers=1, stage_executors={1: failing_executor},
        )
        try:
            job = _make_job(tmp_path, "reraise_test", enabled_stages=[1])
            # 直接调用 _execute_job（绕过线程池），观察 re-raise
            with pytest.raises(RuntimeError, match="模拟状态转换失败"):
                scheduler._execute_job(job)
        finally:
            scheduler.shutdown()


# =============================================================================
# #v3.3-P-3 / #v3.3-P-4 / #v3.3-P-5: pipeline/training.py 基准加载
# =============================================================================


class TestTrainingBenchmarksNoFallback:
    """基准加载三处 fall-back 修复（R03）。"""

    def test_load_benchmarks_missing_dir_raises(self, tmp_path):
        """#v3.3-P-3: 基准目录不存在 raise FileNotFoundError（原 return [] 是 fall-back）。"""
        with pytest.raises(FileNotFoundError, match="基准目录不存在"):
            TrainingPipeline._load_benchmarks(str(tmp_path / "nonexistent"))

    def test_load_benchmarks_corrupt_file_raises(self, tmp_path):
        """#v3.3-P-4: 损坏基准文件 raise（原 except logger.warning 静默跳过是 fall-back）。"""
        (tmp_path / "broken.json").write_text("<<<不是 JSON>>>", encoding="utf-8")
        with pytest.raises((json.JSONDecodeError, ValueError)):
            TrainingPipeline._load_benchmarks(str(tmp_path))

    def test_parse_benchmark_empty_raises(self, tmp_path):
        """#v3.3-P-5: 空基准（无器件无连接）raise ValueError（原 return None 是 fall-back）。"""
        empty_path = tmp_path / "empty.json"
        _write_benchmark(empty_path, instances={}, connections=[])
        with pytest.raises(ValueError, match="无器件且无连接"):
            _parse_benchmark_json(empty_path)

    def test_parse_benchmark_valid(self, tmp_path):
        """回归：有效 GDSFactory 基准仍可正常解析为 CircuitSpec。"""
        valid_path = tmp_path / "valid.json"
        _write_benchmark(
            valid_path,
            name="valid_circuit",
            instances={
                "mmi_long": {"component": "mmi1x2", "settings": {"width_mmi": 4.5}},
                "mmi_short": {"component": "mmi1x2", "settings": {"width_mmi": 4.5}},
            },
            routes={
                "optical": {
                    "routing_strategy": "route_bundle_all_angle",
                    "links": {"mmi_short,o1": "mmi_long,o1"},
                }
            },
        )
        circuit = _parse_benchmark_json(valid_path)
        assert isinstance(circuit, CircuitSpec)
        assert circuit.name == "valid_circuit"
        assert len(circuit.devices) >= 1

    def test_load_benchmarks_empty_existing_dir_returns_empty(self, tmp_path):
        """合法空输入：目录存在但无基准文件返回空列表（非 fall-back，保留）。

        注：index.json 已被过滤；目录存在但空属合法状态，返回 [] 由上层
        TrainingPipeline.train() 决定是否终止训练。
        """
        (tmp_path / "index.json").write_text("{}", encoding="utf-8")
        circuits = TrainingPipeline._load_benchmarks(str(tmp_path))
        assert circuits == []

    def test_load_benchmarks_valid_files(self, tmp_path):
        """回归：有效基准目录仍可正常加载（修复未破坏正常路径）。"""
        _write_benchmark(
            tmp_path / "a.json",
            instances={"d1": {"component": "mmi1x2", "settings": {}}},
            routes={"optical": {"links": {"d1,o1": "d2,o1"}}},
        )
        _write_benchmark(
            tmp_path / "b.json",
            instances={"d2": {"component": "mmi1x2", "settings": {}}},
        )
        circuits = TrainingPipeline._load_benchmarks(str(tmp_path))
        assert len(circuits) == 2
        assert all(isinstance(c, CircuitSpec) for c in circuits)


# =============================================================================
# 合法 return None/[] 行为固化（确认未被误改）
# =============================================================================


class TestLegitimateReturnsPreserved:
    """确认合法的 return None/[] 未被误改为 raise（避免过度修改）。"""

    def test_tracker_stage_result_missing_returns_none(self, tmp_path):
        """get_stage_result 文件缺失返回 None（合法查询未命中）。"""
        tracker = JobTracker(base_output_dir=str(tmp_path))
        assert tracker.get_stage_result("any", 1) is None
        # 无效阶段 ID 返回 None
        assert tracker.get_stage_result("any", 99) is None

    def test_recipe_yaml_roundtrip_preserved(self, tmp_path):
        """回归：Recipe YAML 序列化往返仍正常（_coerce_scalar 修复未破坏）。"""
        recipe = Recipe(preset_id="ring", platform="SiN", enabled_stages=[1, 2, 3])
        yaml_str = recipe.to_yaml()
        recipe2 = Recipe.from_yaml(yaml_str)
        assert recipe2.preset_id == "ring"
        assert recipe2.platform == "SiN"
        assert recipe2.enabled_stages == [1, 2, 3]
