"""作业工作空间（Workspace）目录结构管理。

对齐商业 EDA 工具的工作空间/项目目录管理：
- Luceda IPKISS: 项目目录结构（含 netlist/layout/simulation 子目录）
- Cadence ADE-XL: 作业运行目录（含 logs/results/data 子目录）
- Synopsys ICC2: 实现工作目录（含 reports/logs/results）
- Ansys Lumerical: 仿真项目目录（含脚本/结果/日志）

R03 合规契约：所有 JSON 写入采用原子写入（临时文件 + os.replace），
禁止非原子 ``path.write_text()`` 导致调度器 worker 写入与 Web API
handler 读取的竞态条件（读取方读到空文件/半写入内容触发
JSONDecodeError）。原子的 ``os.replace`` 在 POSIX 下是 ``rename(2)``
系统调用，目标文件要么是旧内容要么是新内容，永不部分写入。

学术来源:
- IPKISS 项目结构: https://docs.lucedaphotonics.com/
- Cadence ADE-XL 运行目录: https://docs.cadence.com/
- Synopsys ICC2 工作目录: https://www.synopsys.com/
- Ansys Lumerical 项目目录: https://www.ansys.com/products/photonics
- POSIX rename(2) 原子性: https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html
- Python os.replace 文档: https://docs.python.org/3/library/os.html#os.replace
- atomicwrites 库设计: https://github.com/untitaker/python-atomicwrites

每个作业拥有独立的工作空间，目录结构如下:
    <output_dir>/<job_id>/
        job.json              # 作业元数据
        logs/job.jsonl        # 结构化日志（JSONL）
        reports/summary.json  # 汇总报告
        gds/layout.gds        # GDS 文件
        inputs/               # 输入文件
        stages/
            stage1_pdk/output.json
            stage2_circuit/output.json
            ... (共 10 个阶段子目录)
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Workspace:
    """作业工作空间，管理目录结构

    在构造时自动创建标准目录结构，提供阶段输出、元数据、日志、报告的读写方法。
    """

    output_dir: str  # 根输出目录
    job_id: str  # 作业 ID
    base_path: Path = field(init=False)

    def __post_init__(self):
        self.base_path = Path(self.output_dir) / self.job_id
        self._init_dirs()

    def _init_dirs(self) -> None:
        """创建标准目录结构"""
        # 主目录
        (self.base_path / "inputs").mkdir(parents=True, exist_ok=True)
        (self.base_path / "logs").mkdir(parents=True, exist_ok=True)
        (self.base_path / "stages").mkdir(parents=True, exist_ok=True)
        (self.base_path / "reports").mkdir(parents=True, exist_ok=True)
        (self.base_path / "gds").mkdir(parents=True, exist_ok=True)
        # 10 个阶段子目录
        stage_slugs = [
            "stage1_pdk", "stage2_circuit", "stage3_placement", "stage4_routing",
            "stage5_simulation", "stage6_drc_lvs", "stage7_gds",
            "stage8_opto_electrical", "stage9_quantum", "stage10_inverse",
        ]
        for slug in stage_slugs:
            (self.base_path / "stages" / slug).mkdir(parents=True, exist_ok=True)

    def stage_dir(self, stage_slug: str) -> Path:
        """获取阶段输出目录"""
        return self.base_path / "stages" / stage_slug

    def _atomic_write_json(self, path: Path, data: dict) -> Path:
        """原子写入 JSON 文件（临时文件 + os.replace 原子替换）。

        解决调度器 worker 写入与 Web API handler 读取的竞态条件：
        非原子 ``path.write_text()`` 会先截断文件再写入，期间读取方
        会读到空文件或半写入内容，触发 ``JSONDecodeError``。原子写入
        保证读取方要么看到旧文件要么看到新文件，永不看到中间态。

        实现步骤：
        1. ``tempfile.mkstemp`` 在目标同目录创建唯一临时文件（同文件系统）
        2. 写入内容 + ``flush`` + ``fsync``（确保持久化到磁盘）
        3. ``os.replace`` 原子替换目标文件（POSIX ``rename(2)``）

        R03 合规：临时文件清理失败不静默吞没，``re-raise`` 让上层决策。

        来源:
        - POSIX rename(2) 原子性:
          https://pubs.opengroup.org/onlinepubs/9699919799/functions/rename.html
        - Python os.replace 文档:
          https://docs.python.org/3/library/os.html#os.replace
        - atomicwrites 库设计:
          https://github.com/untitaker/python-atomicwrites
        - SQLite WAL 原子提交（同类原理）: https://www.sqlite.org/wal.html
        - Effective Python Item 32: 优先抛异常而非返回 None
        """
        content = json.dumps(data, ensure_ascii=False, indent=2, default=str)
        fd, tmp_name = tempfile.mkstemp(
            dir=path.parent, prefix=path.name + ".", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        return path

    def write_stage_output(self, stage_slug: str, data: dict) -> Path:
        """写入阶段输出 JSON（原子写入）"""
        path = self.stage_dir(stage_slug) / "output.json"
        return self._atomic_write_json(path, data)

    def read_stage_output(self, stage_slug: str) -> dict | None:
        """读取阶段输出 JSON，不存在返回 None"""
        path = self.stage_dir(stage_slug) / "output.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_job_metadata(self, job_dict: dict) -> Path:
        """写入作业元数据 job.json（原子写入）"""
        path = self.base_path / "job.json"
        return self._atomic_write_json(path, job_dict)

    def read_job_metadata(self) -> dict | None:
        """读取作业元数据，不存在返回 None"""
        path = self.base_path / "job.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def write_log(self, message: str, level: str = "INFO") -> None:
        """追加日志（JSONL 格式）"""
        log_path = self.base_path / "logs" / "job.jsonl"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def write_report(self, report: dict) -> Path:
        """写入汇总报告（原子写入）"""
        path = self.base_path / "reports" / "summary.json"
        return self._atomic_write_json(path, report)

    def gds_path(self, filename: str = "layout.gds") -> Path:
        """获取 GDS 文件路径"""
        return self.base_path / "gds" / filename
