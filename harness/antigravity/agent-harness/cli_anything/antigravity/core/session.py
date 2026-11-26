"""Stateful session manager with atomic mutate/undo/redo and locked JSON persistence."""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable


def _locked_save_json(path: str, data: Any, **dump_kwargs: Any) -> None:
    """Atomically write JSON with exclusive file locking (open r+, lock, truncate inside lock)."""
    abs_path = os.path.abspath(path)
    try:
        f = open(abs_path, "r+", encoding="utf-8")
    except FileNotFoundError:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        f = open(abs_path, "w", encoding="utf-8")
    with f:
        locked = False
        try:
            import fcntl

            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            locked = True
        except (ImportError, OSError):
            locked = False
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, **dump_kwargs)
            f.write("\n")
            f.flush()
        finally:
            if locked:
                import fcntl

                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class Session:
    """Holds the active `.agyproj.json` manifest, undo/redo history, and dirty flag."""

    MAX_HISTORY = 50

    def __init__(self) -> None:
        self.project: dict[str, Any] | None = None
        self.project_path: str | None = None
        self._undo_stack: list[tuple[str, dict[str, Any]]] = []
        self._redo_stack: list[tuple[str, dict[str, Any]]] = []
        self._history_log: list[dict[str, str]] = []
        self._modified: bool = False

    def has_project(self) -> bool:
        """Return True if a project manifest is loaded."""
        return self.project is not None

    def require_project(self) -> dict[str, Any]:
        """Return the loaded project manifest or raise RuntimeError."""
        if self.project is None:
            raise RuntimeError(
                "No project loaded. Run `project new` or pass `--project <file.agyproj.json>`."
            )
        return self.project

    def set_project(self, project: dict[str, Any], path: str | None = None) -> None:
        """Load a project manifest into the session and clear undo/redo history."""
        self.project = copy.deepcopy(project)
        self.project_path = os.path.abspath(path) if path else None
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._history_log.clear()
        self._modified = False

    def snapshot(self, description: str) -> None:
        """Record a deep-copy undo checkpoint."""
        proj = self.require_project()
        self._undo_stack.append((description, copy.deepcopy(proj)))
        if len(self._undo_stack) > self.MAX_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._history_log.append(
            {"action": description, "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        self._modified = True

    def mutate(self, description: str, fn: Callable[[dict[str, Any]], Any]) -> Any:
        """Execute a state mutation atomically, rolling back cleanly on exception."""
        proj = self.require_project()
        prev_project = copy.deepcopy(proj)
        prev_modified = self._modified
        try:
            result = fn(proj)
        except Exception:
            self.project = prev_project
            self._modified = prev_modified
            raise
        self._undo_stack.append((description, prev_project))
        if len(self._undo_stack) > self.MAX_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._history_log.append(
            {"action": description, "timestamp": datetime.now(timezone.utc).isoformat()}
        )
        self._modified = True
        return result

    def undo(self) -> str:
        """Restore the previous project snapshot."""
        if not self._undo_stack or self.project is None:
            raise RuntimeError("Nothing to undo.")
        desc, prev_state = self._undo_stack.pop()
        self._redo_stack.append((desc, copy.deepcopy(self.project)))
        self.project = prev_state
        self._modified = True
        return desc

    def redo(self) -> str:
        """Re-apply the most recently undone snapshot."""
        if not self._redo_stack or self.project is None:
            raise RuntimeError("Nothing to redo.")
        desc, next_state = self._redo_stack.pop()
        self._undo_stack.append((desc, copy.deepcopy(self.project)))
        self.project = next_state
        self._modified = True
        return desc

    def save_session(self, path: str | None = None) -> str:
        """Persist the active project manifest via `_locked_save_json`."""
        proj = self.require_project()
        target = os.path.abspath(path) if path else self.project_path
        if not target:
            raise RuntimeError("No save path specified. Pass a path or load with --project.")
        _locked_save_json(target, proj, indent=2, ensure_ascii=False)
        self.project_path = target
        self._modified = False
        return target

    def status(self) -> dict[str, Any]:
        """Return a structured summary of session state."""
        return {
            "has_project": self.has_project(),
            "project_name": self.project.get("name") if self.project else None,
            "project_path": self.project_path,
            "scope": self.project.get("scope") if self.project else None,
            "modified": self._modified,
            "undo_depth": len(self._undo_stack),
            "redo_depth": len(self._redo_stack),
            "history_count": len(self._history_log),
            "skills_count": len(self.project.get("skills", [])) if self.project else 0,
            "rules_count": len(self.project.get("rules", [])) if self.project else 0,
            "agents_count": len(self.project.get("agents", [])) if self.project else 0,
        }

    def history(self) -> list[dict[str, str]]:
        """Return the mutation history list."""
        return list(self._history_log)


_SESSION = Session()


def get_session() -> Session:
    """Return the process-wide CLI session singleton."""
    return _SESSION


def reset_session() -> Session:
    """Reset the singleton session (primarily for tests)."""
    global _SESSION
    _SESSION = Session()
    return _SESSION
