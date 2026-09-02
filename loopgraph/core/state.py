"""
LoopGraph Core Data Models and State Definitions.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class Task:
    id: str
    title: str
    why: str = ""
    acceptance: List[str] = field(default_factory=list)
    priority: int = 99
    effort: str = "M"
    status: TaskStatus = TaskStatus.TODO
    depends_on: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    last_feedback: str = ""
    assigned_node: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value if isinstance(self.status, TaskStatus) else self.status
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Task:
        raw_status = data.get("status", "todo")
        try:
            status = TaskStatus(raw_status)
        except ValueError:
            status = TaskStatus.TODO
        
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            why=data.get("why", ""),
            acceptance=data.get("acceptance", []) or [],
            priority=int(data.get("priority", 99)),
            effort=data.get("effort", "M"),
            status=status,
            depends_on=data.get("depends_on", []) or [],
            retry_count=int(data.get("retry_count", 0)),
            max_retries=int(data.get("max_retries", 3)),
            last_feedback=data.get("last_feedback", ""),
            assigned_node=data.get("assigned_node"),
            created_at=data.get("created_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class ProjectState:
    project_path: Path
    vision: str = ""
    tasks: List[Task] = field(default_factory=list)
    current_task: Optional[Task] = None
    tokens_used: int = 0
    iteration: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_task(self, task_id: str) -> Optional[Task]:
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        task = self.get_task(task_id)
        if task:
            task.status = status

    def get_pending_tasks(self) -> List[Task]:
        done_ids = {t.id for t in self.tasks if t.status == TaskStatus.DONE}
        pending = []
        for t in self.tasks:
            if t.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
                # Check if all dependencies are satisfied
                if all(dep in done_ids for dep in t.depends_on):
                    pending.append(t)
        # Sort by priority ascending (1 is highest), then ID
        return sorted(pending, key=lambda x: (x.priority, x.id))

    def save_checkpoint(self, path: Optional[Path] = None) -> Path:
        target = path or (self.project_path / ".loopgraph" / "checkpoint.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "project_path": str(self.project_path.resolve()),
            "tokens_used": self.tokens_used,
            "iteration": self.iteration,
            "tasks": [t.to_dict() for t in self.tasks],
            "current_task_id": self.current_task.id if self.current_task else None,
            "metadata": self.metadata,
        }
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return target

    @classmethod
    def load_checkpoint(cls, checkpoint_path: Path) -> ProjectState:
        data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        proj_dir = Path(data["project_path"])
        tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        current_id = data.get("current_task_id")
        current_task = next((t for t in tasks if t.id == current_id), None)
        
        return cls(
            project_path=proj_dir,
            tasks=tasks,
            current_task=current_task,
            tokens_used=data.get("tokens_used", 0),
            iteration=data.get("iteration", 0),
            metadata=data.get("metadata", {}),
        )
