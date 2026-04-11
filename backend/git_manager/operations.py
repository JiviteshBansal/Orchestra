import os
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from backend.config import settings

logger = logging.getLogger(__name__)


class GitManager:
    def __init__(self, repo_path: Optional[str] = None):
        self.repo_path = Path(repo_path or settings.PROJECTS_DIR)
        self._repo = None

    def _get_repo(self):
        if self._repo is None:
            try:
                import git
                if (self.repo_path / ".git").exists():
                    self._repo = git.Repo(self.repo_path)
                else:
                    self._repo = git.Repo.init(self.repo_path)
                    self._repo.config_writer().set_value("user", "name", settings.GIT_AUTHOR_NAME).release()
                    self._repo.config_writer().set_value("user", "email", settings.GIT_AUTHOR_EMAIL).release()
                    readme = self.repo_path / "README.md"
                    if not readme.exists():
                        readme.write_text("# Orchestra AI Project\n")
                    self._repo.index.add(["README.md"])
                    self._repo.index.commit("Initial commit")
                    logger.info(f"Git repo initialized at {self.repo_path}")
            except ImportError:
                logger.warning("GitPython not available")
                return None
        return self._repo

    def create_branch(self, branch_name: str) -> bool:
        repo = self._get_repo()
        if not repo:
            return False
        try:
            if branch_name in [b.name for b in repo.branches]:
                repo.git.checkout(branch_name)
            else:
                repo.git.checkout("-b", branch_name)
            logger.info(f"Created/switched to branch: {branch_name}")
            return True
        except Exception as e:
            logger.error(f"Branch creation failed: {e}")
            return False

    def commit_files(self, files: list[str], message: str) -> Optional[str]:
        repo = self._get_repo()
        if not repo:
            return None
        try:
            for f in files:
                file_path = self.repo_path / f
                file_path.parent.mkdir(parents=True, exist_ok=True)
                if file_path.exists():
                    repo.index.add([f])
            commit = repo.index.commit(message)
            logger.info(f"Committed: {message} ({commit.hexsha[:8]})")
            return commit.hexsha
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            return None

    def get_current_branch(self) -> str:
        repo = self._get_repo()
        if not repo:
            return "main"
        try:
            return repo.active_branch.name
        except Exception:
            return "detached"

    def list_branches(self) -> list[str]:
        repo = self._get_repo()
        if not repo:
            return []
        return [b.name for b in repo.branches]

    def checkout(self, branch_name: str) -> bool:
        repo = self._get_repo()
        if not repo:
            return False
        try:
            repo.git.checkout(branch_name)
            return True
        except Exception as e:
            logger.error(f"Checkout failed: {e}")
            return False

    def get_diff(self, branch_a: str = "main", branch_b: str = None) -> str:
        repo = self._get_repo()
        if not repo:
            return ""
        try:
            if branch_b:
                return repo.git.diff(branch_a, branch_b)
            return repo.git.diff(branch_a)
        except Exception:
            return ""


class PRManager:
    def __init__(self):
        self._prs: list[dict] = []

    def create_pr(
        self,
        task_id: int,
        branch_name: str,
        title: str,
        what_changed: str,
        why_changed: str,
        how_changed: str,
        test_plan: str,
    ) -> dict:
        pr = {
            "id": len(self._prs) + 1,
            "task_id": task_id,
            "branch_name": branch_name,
            "title": title,
            "what_changed": what_changed,
            "why_changed": why_changed,
            "how_changed": how_changed,
            "test_plan": test_plan,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._prs.append(pr)
        logger.info(f"PR created: #{pr['id']} - {title}")
        return pr

    def get_pr(self, pr_id: int) -> Optional[dict]:
        for pr in self._prs:
            if pr["id"] == pr_id:
                return pr
        return None

    def approve_pr(self, pr_id: int) -> bool:
        pr = self.get_pr(pr_id)
        if pr:
            pr["status"] = "approved"
            return True
        return False

    def merge_pr(self, pr_id: int) -> bool:
        pr = self.get_pr(pr_id)
        if pr and pr["status"] == "approved":
            pr["status"] = "merged"
            return True
        return False

    def list_prs(self, status: Optional[str] = None) -> list[dict]:
        if status:
            return [pr for pr in self._prs if pr["status"] == status]
        return list(self._prs)


git_manager = GitManager()
pr_manager = PRManager()
