"""
Global-Wawe / Stark-Core - Multi-Agent Task Coordinator & Long-Running Job Supervisor (Stage 4)
Handles:
1. Long-Running Job Execution & Background Worker Supervision
2. Real-time Progress Tracking (0-100%), Elapsed Time, Step Milestones
3. Multi-Agent Parallel Task Coordination (System, Code, Content, Research, Assistant)
4. Job Cancellation, Status Querying, and Completion Event Notifications
5. Audit trail & error diagnostic capture
"""

import time
import uuid
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("Jarvis.TaskCoordinator")

class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ManagedJob:
    def __init__(self, job_id: str, title: str, specialist: str, target_func: Callable, args: tuple = (), kwargs: dict = None):
        self.job_id = job_id
        self.title = title
        self.specialist = specialist
        self.target_func = target_func
        self.args = args or ()
        self.kwargs = kwargs or {}
        
        self.status = JobStatus.QUEUED
        self.progress_pct = 0
        self.current_step = "Kuyrukta bekliyor"
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.cancel_requested = False
        self.cancel_event = threading.Event()
        self.thread: Optional[threading.Thread] = None

    def to_dict(self) -> Dict[str, Any]:
        elapsed = 0.0
        if self.started_at:
            end = self.completed_at or time.time()
            elapsed = round(end - self.started_at, 2)

        return {
            "job_id": self.job_id,
            "title": self.title,
            "specialist": self.specialist,
            "status": self.status,
            "progress_pct": self.progress_pct,
            "current_step": self.current_step,
            "elapsed_seconds": elapsed,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "has_result": self.result is not None
        }


class TaskCoordinator:
    def __init__(self, max_workers: int = 6):
        self.jobs: Dict[str, ManagedJob] = {}
        self.lock = threading.RLock()
        self.listeners: List[Callable[[Dict[str, Any]], None]] = []
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="JarvisWorker")

    def spawn_job(
        self,
        title: str,
        specialist: str,
        target_func: Callable,
        args: tuple = (),
        kwargs: dict = None
    ) -> Dict[str, Any]:
        """
        Dispatches a task to run asynchronously in a supervised worker pool with bounded capacity.
        """
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        job = ManagedJob(
            job_id=job_id,
            title=title,
            specialist=specialist,
            target_func=target_func,
            args=args,
            kwargs=kwargs
        )

        with self.lock:
            # Memory Hygiene: Prune completed jobs if over 100 entries
            if len(self.jobs) >= 100:
                terminal_ids = [
                    jid for jid, j in self.jobs.items()
                    if j.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)
                ]
                terminal_ids.sort(key=lambda jid: self.jobs[jid].started_at or 0)
                for tid in terminal_ids[:20]:
                    del self.jobs[tid]

            self.jobs[job_id] = job

        self.executor.submit(self._execute_supervised_job, job)

        logger.info(f"[TaskCoordinator] Spawned {job_id} ('{title}') on specialist '{specialist}'")
        return job.to_dict()

    def _execute_supervised_job(self, job: ManagedJob):
        job.started_at = time.time()
        job.status = JobStatus.RUNNING
        job.progress_pct = 5
        job.current_step = "Başlatılıyor..."

        def progress_callback(pct: int, step_desc: str):
            if job.cancel_requested or job.cancel_event.is_set():
                raise InterruptedError("Görev kullanıcı tarafından iptal edildi.")
            job.progress_pct = max(0, min(100, pct))
            job.current_step = step_desc
            self._notify_listeners(job)

        try:
            # Pass progress_callback if target_func supports it
            kwargs = dict(job.kwargs)
            if "progress_callback" in job.target_func.__code__.co_varnames:
                kwargs["progress_callback"] = progress_callback

            result = job.target_func(*job.args, **kwargs)
            if job.cancel_requested or job.cancel_event.is_set():
                job.status = JobStatus.CANCELLED
                job.current_step = "İptal edildi"
                job.error = "Görev tamamlanmadan önce iptal edildi."
            else:
                job.result = result
                job.status = JobStatus.COMPLETED
                job.progress_pct = 100
                job.current_step = "Tamamlandı"
            job.completed_at = time.time()
            logger.info(f"[TaskCoordinator] Job {job.job_id} status: {job.status}")
        except InterruptedError as ie:
            job.status = JobStatus.CANCELLED
            job.error = str(ie)
            job.completed_at = time.time()
            logger.warning(f"[TaskCoordinator] Job {job.job_id} cancelled.")
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = time.time()
            logger.error(f"[TaskCoordinator] Job {job.job_id} failed: {e}")
        finally:
            self._notify_listeners(job)

    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return {"success": False, "error": f"Görev bulunamadı: {job_id}"}
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                return {"success": False, "error": f"Görev zaten sonlanmış: {job.status}"}

            job.cancel_requested = True
            job.cancel_event.set()
            job.current_step = "İptal ediliyor..."
            return {"success": True, "message": f"Görev iptal isteği gönderildi: {job_id}"}

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            job = self.jobs.get(job_id)
            return job.to_dict() if job else None

    def list_jobs(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.lock:
            jobs_list = [j.to_dict() for j in self.jobs.values()]
            if status:
                return [j for j in jobs_list if j["status"] == status]
            return sorted(jobs_list, key=lambda x: x["started_at"] or 0, reverse=True)

    def add_listener(self, listener_func: Callable[[Dict[str, Any]], None]):
        self.listeners.append(listener_func)

    def _notify_listeners(self, job: ManagedJob):
        data = job.to_dict()
        for l in self.listeners:
            try:
                l(data)
            except Exception as e:
                logger.warning(f"Listener error: {e}")


task_coordinator = TaskCoordinator()
