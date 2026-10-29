import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional


class GitSourceController:
    """
    Manages dynamic Git branch selection, remote fetching, and metadata tracking
    for Android and iOS mobile production codebases.
    """

    def __init__(
        self,
        android_repo_path: Optional[Path] = None,
        ios_repo_path: Optional[Path] = None,
        backend_repo_path: Optional[Path] = None,
    ):
        cur = Path(__file__).resolve().parent
        android_p = None
        ios_p = None
        backend_p = None
        for p in [cur.parent.parent.parent, cur.parent.parent, cur.parent]:
            if (p / "android-rebotics").exists():
                android_p = p / "android-rebotics"
            if (p / "ios-rebotics").exists():
                ios_p = p / "ios-rebotics"
            if (p / "rebotics-management-django").exists():
                backend_p = p / "rebotics-management-django"
        self.android_repo = android_repo_path or android_p or Path("/Users/vipin.nair1/sympohonyworkspace/android-rebotics")
        self.ios_repo = ios_repo_path or ios_p or Path("/Users/vipin.nair1/sympohonyworkspace/ios-rebotics")
        self.backend_repo = backend_repo_path or backend_p or Path("/Users/vipin.nair1/sympohonyworkspace/rebotics-management-django")

    def _get_repo_path(self, target: str) -> Path:
        normalized = target.strip().lower()
        if normalized in ("android", "android-rebotics"):
            return self.android_repo
        elif normalized in ("ios", "ios-rebotics"):
            return self.ios_repo
        elif normalized in ("backend", "rebotics-management-django", "django"):
            return self.backend_repo
        raise ValueError(f"Unknown repository target: '{target}'. Expected 'backend', 'android', or 'ios'.")

    def _run_git(self, repo_path: Path, args: List[str]) -> str:
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
        cmd = ["git"] + args
        result = subprocess.run(cmd, cwd=str(repo_path), capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed in {repo_path.name}: {' '.join(cmd)}\nError: {result.stderr}")
        return result.stdout.strip()

    def get_repo_info(self, platform_or_repo: str) -> Dict[str, str]:
        repo_path = self._get_repo_path(platform_or_repo)
        try:
            branch = self._run_git(repo_path, ["branch", "--show-current"])
            full_sha = self._run_git(repo_path, ["rev-parse", "HEAD"])
            commit_hash = full_sha[:8]
            commit_msg = self._run_git(repo_path, ["log", "-1", "--pretty=%B"]).split("\n")[0]
            commit_author = self._run_git(repo_path, ["log", "-1", "--pretty=%an <%ae>"])
            commit_date = self._run_git(repo_path, ["log", "-1", "--pretty=%cd", "--date=short"])
            origin_url = self._run_git(repo_path, ["config", "--get", "remote.origin.url"])
            return {
                "platform": platform_or_repo.lower(),
                "repo_path": str(repo_path),
                "repo_name": repo_path.name,
                "origin_url": origin_url,
                "branch": branch or "DETACHED_HEAD",
                "commit": commit_hash,
                "commit_full_sha": full_sha,
                "commit_author": commit_author,
                "commit_message": commit_msg,
                "commit_date": commit_date,
            }
        except Exception as e:
            return {
                "platform": platform_or_repo.lower(),
                "repo_path": str(repo_path),
                "repo_name": repo_path.name,
                "error": str(e),
                "branch": "unknown",
                "commit": "unknown",
                "commit_full_sha": "unknown",
                "commit_author": "unknown",
                "commit_message": "unknown",
                "commit_date": "unknown",
            }

    def resolve_revision(self, repo_name: str, branch: Optional[str] = None, commit: Optional[str] = "auto") -> Dict[str, Any]:
        """
        Resolves the exact immutable commit SHA, author, and branch without switching
        the local working tree if in read-only mode.
        """
        try:
            repo_path = self._get_repo_path(repo_name)
        except (ValueError, FileNotFoundError) as ve:
            return {
                "repo_name": repo_name,
                "target_ref": commit if commit and commit.lower() != "auto" else (branch or "HEAD"),
                "error": str(ve),
                "resolved_cleanly": False,
            }

        target_ref = "HEAD"
        if commit and commit.lower() != "auto":
            target_ref = commit
        elif branch and branch != "current":
            target_ref = branch

        try:
            full_sha = self._run_git(repo_path, ["rev-parse", target_ref])
            commit_hash = full_sha[:8]
            commit_msg = self._run_git(repo_path, ["log", "-1", "--pretty=%B", full_sha]).split("\n")[0]
            commit_author = self._run_git(repo_path, ["log", "-1", "--pretty=%an <%ae>", full_sha])
            commit_date = self._run_git(repo_path, ["log", "-1", "--pretty=%cd", "--date=iso", full_sha])
            current_branch = self._run_git(repo_path, ["branch", "--show-current"])
            return {
                "repo_name": repo_path.name,
                "repo_path": str(repo_path),
                "target_ref": target_ref,
                "resolved_sha": full_sha,
                "short_sha": commit_hash,
                "commit_message": commit_msg,
                "commit_author": commit_author,
                "commit_date": commit_date,
                "current_branch": current_branch or "DETACHED_HEAD",
                "selected_branch": branch or current_branch or "HEAD",
                "resolved_cleanly": True,
            }
        except Exception as e:
            return {
                "repo_name": repo_path.name,
                "repo_path": str(repo_path),
                "target_ref": target_ref,
                "error": str(e),
                "resolved_cleanly": False,
            }

    def checkout_branch(self, platform_or_repo: str, branch_name: str, sync_remote: bool = True) -> Dict[str, str]:
        repo_path = self._get_repo_path(platform_or_repo)
        print(f"  📦 [{platform_or_repo.upper()}] Switching code to branch '{branch_name}' in {repo_path.name}...")

        if sync_remote:
            print(f"     Fetching latest updates from remote...")
            self._run_git(repo_path, ["fetch", "origin"])

        # Checkout branch
        try:
            self._run_git(repo_path, ["checkout", branch_name])
        except RuntimeError:
            # If not found locally, try checkout from origin
            self._run_git(repo_path, ["checkout", "-b", branch_name, f"origin/{branch_name}"])

        if sync_remote:
            try:
                self._run_git(repo_path, ["pull", "--ff-only", "origin", branch_name])
            except Exception:
                pass  # Ignore if detached or already up to date

        info = self.get_repo_info(platform_or_repo)
        print(f"     ✅ Checked out {platform_or_repo.upper()} commit: [{info['commit']}] {info['commit_message']} ({info['commit_date']})")
        return info

    def list_branches(self, platform_or_repo: str, max_count: int = 15) -> List[str]:
        repo_path = self._get_repo_path(platform_or_repo)
        self._run_git(repo_path, ["fetch", "--prune", "origin"])
        output = self._run_git(repo_path, ["branch", "-r"])
        branches = []
        for line in output.split("\n"):
            line = line.strip()
            if "->" in line:
                continue
            if line.startswith("origin/"):
                branches.append(line.replace("origin/", ""))
        return branches[:max_count]
