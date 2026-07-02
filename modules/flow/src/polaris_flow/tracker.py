"""作业追踪器（JobTracker）查询 API。

对齐商业 EDA 工具的作业查询/追踪能力：
- Luceda IPKISS: 设计任务状态查询
- Cadence ADE-XL: 作业历史与结果检索
- Synopsys ICC2: 实现流程状态追踪
- Ansys Lumerical: 仿真任务结果查询

学术来源:
- IPKISS 任务查询: https://docs.lucedaphotonics.com/
- Cadence ADE-XL 作业历史: https://docs.cadence.com/
- Synopsys ICC2 状态追踪: https://www.synopsys.com/
- Ansys Lumerical 结果查询: https://www.ansys.com/products/photonics
- Effective Python 3rd Ed. Item 32（优先抛异常而非返回 None）:
  https://effectivepython.com/
- Real Python: Effectively Raising Exceptions（异常链与 re-raise）:
  https://realpython.com/python-raise-exception/

JobTracker 是只读查询接口，从磁盘工作空间读取作业元数据与阶段输出，
不参与作业执行。供 CLI / Web / 上层编排使用。
"""

from __future__ import annotations

import json
from pathlib import Path


class JobTracker:
    """作业追踪器，提供状态查询、历史记录、阶段结果检索

    通过扫描 base_output_dir 下的作业目录，提供只读查询能力。
    R03 合规契约：文件/目录**缺失**时返回 None / 空列表（合法查询未命中）；
    文件**存在但损坏**（JSON 解析失败、IO 错误）直接 raise 异常，禁止 fall-back
    静默吞没——数据损坏属业务 Bug，必须上抛告警。
    """

    # 阶段 ID → slug 映射（与 STANDARD_STAGES 保持一致）
    STAGE_SLUGS: dict[int, str] = {
        1: "stage1_pdk",
        2: "stage2_circuit",
        3: "stage3_placement",
        4: "stage4_routing",
        5: "stage5_simulation",
        6: "stage6_drc_lvs",
        7: "stage7_gds",
        8: "stage8_opto_electrical",
        9: "stage9_quantum",
        10: "stage10_inverse",
    }

    def __init__(self, base_output_dir: str = "out/jobs"):
        self.base_output_dir = Path(base_output_dir)

    def get_status(self, job_id: str) -> str | None:
        """查询作业状态"""
        meta = self._read_job_metadata(job_id)
        if meta is None:
            return None
        return meta.get("status")

    def get_job(self, job_id: str) -> dict | None:
        """查询作业详情"""
        return self._read_job_metadata(job_id)

    def list_jobs(self, status: str | None = None) -> list[dict]:
        """列出所有作业（可选状态过滤）"""
        jobs: list[dict] = []
        if not self.base_output_dir.exists():
            return []
        for job_dir in sorted(self.base_output_dir.iterdir()):
            if not job_dir.is_dir():
                continue
            meta_path = job_dir / "job.json"
            if not meta_path.exists():
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if status is None or meta.get("status") == status:
                jobs.append(meta)
        return jobs

    def get_stage_result(self, job_id: str, stage_id: int) -> dict | None:
        """查询阶段结果"""
        slug = self.STAGE_SLUGS.get(stage_id)
        if slug is None:
            return None
        path = self.base_output_dir / job_id / "stages" / slug / "output.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def get_history(self, job_id: str) -> list[dict]:
        """查询作业历史（所有阶段结果）"""
        history: list[dict] = []
        for stage_id in range(1, 11):
            result = self.get_stage_result(job_id, stage_id)
            if result is not None:
                history.append({"stage_id": stage_id, "output": result})
        return history

    def _read_job_metadata(self, job_id: str) -> dict | None:
        """读取作业元数据。

        R03 合规：文件缺失返回 None（合法的查询未命中）；
        文件存在但损坏（JSON 解析失败 / IO 错误）直接 raise，禁止 fall-back
        返回 None 掩盖数据损坏（Effective Python Item 32）。
        """
        path = self.base_output_dir / job_id / "job.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
