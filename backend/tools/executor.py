import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

from backend.config import settings

logger = logging.getLogger(__name__)


class ToolResult:
    def __init__(self, success: bool, output: str = "", error: str = ""):
        self.success = success
        self.output = output
        self.error = error
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "timestamp": self.timestamp,
        }


class FileSystemTool:
    def __init__(self, base_path: str = ""):
        self.base_path = Path(base_path or settings.PROJECTS_DIR)

    def _resolve(self, path: str) -> Path:
        resolved = (self.base_path / path).resolve()
        if not str(resolved).startswith(str(self.base_path.resolve())):
            raise PermissionError(f"Access denied: path {path} is outside project scope")
        return resolved

    def read_file(self, path: str) -> ToolResult:
        try:
            full = self._resolve(path)
            if not full.exists():
                return ToolResult(False, error=f"File not found: {path}")
            return ToolResult(True, output=full.read_text())
        except Exception as e:
            return ToolResult(False, error=str(e))

    def write_file(self, path: str, content: str) -> ToolResult:
        try:
            full = self._resolve(path)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)
            return ToolResult(True, output=f"File written: {path}")
        except Exception as e:
            return ToolResult(False, error=str(e))

    def list_dir(self, path: str = ".") -> ToolResult:
        try:
            full = self._resolve(path)
            if not full.is_dir():
                return ToolResult(False, error=f"Not a directory: {path}")
            entries = []
            for item in sorted(full.iterdir()):
                entries.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            return ToolResult(True, output=json.dumps(entries, indent=2))
        except Exception as e:
            return ToolResult(False, error=str(e))

    def mkdir(self, path: str) -> ToolResult:
        try:
            full = self._resolve(path)
            full.mkdir(parents=True, exist_ok=True)
            return ToolResult(True, output=f"Directory created: {path}")
        except Exception as e:
            return ToolResult(False, error=str(e))

    def delete(self, path: str) -> ToolResult:
        try:
            full = self._resolve(path)
            if full.is_file():
                full.unlink()
            elif full.is_dir():
                import shutil
                shutil.rmtree(full)
            return ToolResult(True, output=f"Deleted: {path}")
        except Exception as e:
            return ToolResult(False, error=str(e))


class TerminalTool:
    def __init__(self, use_docker: bool = True):
        self.use_docker = use_docker
        self.timeout = settings.DOCKER_TIMEOUT

    def execute(self, command: str, cwd: Optional[str] = None) -> ToolResult:
        if self.use_docker:
            return self._run_in_docker(command, cwd)
        return self._run_local(command, cwd)

    def _run_in_docker(self, command: str, cwd: Optional[str] = None) -> ToolResult:
        try:
            import docker
            client = docker.from_env()
            workdir = cwd or "/workspace"
            volumes = {
                str(Path(settings.PROJECTS_DIR).resolve()): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            }
            container = client.containers.run(
                settings.DOCKER_SANDBOX_IMAGE,
                command=f"sh -c '{command}'",
                working_dir=workdir,
                volumes=volumes,
                remove=True,
                detach=False,
                stdout=True,
                stderr=True,
                mem_limit="512m",
                cpu_period=100000,
                cpu_quota=50000,
                network_disabled=True,
            )
            output = container.decode("utf-8") if isinstance(container, bytes) else str(container)
            return ToolResult(True, output=output)
        except Exception as e:
            logger.warning(f"Docker execution failed, falling back to local: {e}")
            return self._run_local(command, cwd)

    def _run_local(self, command: str, cwd: Optional[str] = None) -> ToolResult:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=cwd or settings.PROJECTS_DIR,
            )
            if result.returncode == 0:
                return ToolResult(True, output=result.stdout)
            return ToolResult(False, output=result.stdout, error=result.stderr)
        except subprocess.TimeoutExpired:
            return ToolResult(False, error=f"Command timed out after {self.timeout}s")
        except Exception as e:
            return ToolResult(False, error=str(e))


class ToolExecutor:
    def __init__(self):
        self.file_system = FileSystemTool()
        self.terminal = TerminalTool(use_docker=True)
        self._log: list[dict] = []

    def execute_tool(self, tool_name: str, agent_id: int, params: dict) -> ToolResult:
        log_entry = {
            "tool": tool_name,
            "agent_id": agent_id,
            "params": params,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            if tool_name == "read_file":
                result = self.file_system.read_file(params["path"])
            elif tool_name == "write_file":
                result = self.file_system.write_file(params["path"], params["content"])
            elif tool_name == "list_dir":
                result = self.file_system.list_dir(params.get("path", "."))
            elif tool_name == "mkdir":
                result = self.file_system.mkdir(params["path"])
            elif tool_name == "delete":
                result = self.file_system.delete(params["path"])
            elif tool_name == "run_command":
                result = self.terminal.execute(params["command"], params.get("cwd"))
            else:
                result = ToolResult(False, error=f"Unknown tool: {tool_name}")

            log_entry["result"] = result.to_dict()
            self._log.append(log_entry)
            return result
        except Exception as e:
            result = ToolResult(False, error=str(e))
            log_entry["result"] = result.to_dict()
            self._log.append(log_entry)
            return result

    def get_logs(self, limit: int = 50) -> list[dict]:
        return self._log[-limit:]


tool_executor = ToolExecutor()
