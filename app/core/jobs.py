import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("clockchain.jobs")


@dataclass
class Job:
    id: str
    query: str
    preset: str = "balanced"
    status: str = "pending"  # pending, processing, completed, failed
    path: str | None = None
    error: str | None = None
    created_at: str = ""
    completed_at: str | None = None
    flash_response: dict | None = None
    user_id: str | None = None
    visibility: str = "private"

    def to_dict(self) -> dict:
        return {
            "job_id": self.id,
            "status": self.status,
            "path": self.path,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class JobManager:
    def __init__(self, graph_manager, flash_client):
        self.graph_manager = graph_manager
        self.flash_client = flash_client
        self.jobs: dict[str, Job] = {}
        self.queue: asyncio.Queue = asyncio.Queue()

    def create_job(
        self,
        query: str,
        preset: str = "balanced",
        user_id: str | None = None,
        visibility: str = "private",
    ) -> Job:
        job = Job(
            id=str(uuid.uuid4()),
            query=query,
            preset=preset,
            user_id=user_id,
            visibility=visibility,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    async def process_job(self, job: Job):
        job.status = "processing"
        try:
            result = await self.flash_client.generate_sync(job.query, job.preset)

            flash_id = result.get("id") or result.get("timepoint_id")
            name = result.get("name", job.query)
            slug = result.get("slug", "")
            year = result.get("year", 0)
            month = result.get("month", "")
            day = result.get("day", 0)
            time_str = result.get("time", "0000")
            country = result.get("country", "unknown")
            region = result.get("region", "unknown")
            city = result.get("city", "unknown")

            from app.core.url import build_path, slugify, MONTH_TO_NUM
            if isinstance(month, int):
                month_num = month
            else:
                month_num = MONTH_TO_NUM.get(str(month).lower(), 1)

            if not slug:
                slug = slugify(name)

            path = build_path(year, month_num, day, time_str, country, region, city, slug)

            await self.graph_manager.add_node(
                path,
                type="event",
                name=name,
                year=year,
                month=str(month).lower() if isinstance(month, str) else month,
                month_num=month_num,
                day=day,
                time=time_str,
                country=country,
                region=region,
                city=city,
                slug=slug,
                layer=2,
                visibility=job.visibility,
                created_by=job.user_id or "system",
                tags=result.get("tags", []),
                one_liner=result.get("one_liner", ""),
                figures=result.get("figures", []),
                flash_timepoint_id=flash_id,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            # Save scene to disk
            self._save_scene(path, result)

            await self.graph_manager.save()

            job.path = path
            job.flash_response = result
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc).isoformat()
            logger.info("Job %s completed: %s", job.id, path)

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc).isoformat()
            logger.error("Job %s failed: %s", job.id, e)

    def _save_scene(self, path: str, scene_data: dict):
        data_dir = self.graph_manager.data_dir
        segments = path.strip("/").split("/")
        scene_dir = data_dir / "scenes" / "/".join(segments)
        scene_dir.mkdir(parents=True, exist_ok=True)
        scene_file = scene_dir / "scene.json"
        with open(scene_file, "w") as f:
            json.dump(scene_data, f, indent=2, default=str)
        logger.info("Scene saved to %s", scene_file)
