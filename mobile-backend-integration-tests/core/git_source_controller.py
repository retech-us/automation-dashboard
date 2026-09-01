import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional


class GitSourceController:
    """
    Manages dynamic Git branch selection, remote fetching, and metadata tracking
    for Android and iOS mobile production codebases.
    """

    def __init__(self, android_repo_path: Optional[Path] = None, ios_repo_path: Optional[Path] = None):
        cur = Path(__file__).resolve().parent
        android_p = None
        ios_p = None
        for p in [cur.parent.parent.parent, cur.parent.parent, cur.parent]:
            if (p / "android-rebotics").exists():
                android_p = p / "android-rebotics"
            if (p / "ios-rebotics").exists():
                ios_p = p / "ios-rebotics"
        self.android_repo = android_repo_path or android_p or Path("/Users/vipin.nair1/sympohonyworkspace/android-rebotics")
        self.ios_repo = ios_repo_path or ios_p or Path("/Users/vipin.nair1/sympohonyworkspace/ios-rebotics")

    def _run_git(self, repo_path: Path, args: List[str]) -> str:
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
        cmd = ["git"] + args
        result = subprocess.run(cmd, cwd=str(repo_path), capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed in {repo_path.name}: {' '.join(cmd)}\nError: {result.stderr}")
        return result.stdout.strip()

    def get_repo_info(self, platform: str) -> Dict[str, str]:
        repo_path = self.android_repo if platform.lower() == "android" else self.ios_repo
        try:
            branch = self._run_git(repo_path, ["branch", "--show-current"])
            commit_hash = self._run_git(repo_path, ["rev-parse", "--short", "HEAD"])
            commit_msg = self._run_git(repo_path, ["log", "-1", "--pretty=%B"]).split("\n")[0]
            commit_date = self._run_git(repo_path, ["log", "-1", "--pretty=%cd", "--date=short"])
            origin_url = self._run_git(repo_path, ["config", "--get", "remote.origin.url"])
            return {
                "platform": platform.lower(),
                "repo_path": str(repo_path),
                "origin_url": origin_url,
                "branch": branch or "DETACHED_HEAD",
                "commit": commit_hash,
                "commit_message": commit_msg,
                "commit_date": commit_date,
            }
        except Exception as e:
            return {
                "platform": platform.lower(),
                "error": str(e),
                "branch": "unknown",
                "commit": "unknown",
                "commit_message": "unknown",
                "commit_date": "unknown",
            }

    def checkout_branch(self, platform: str, branch_name: str, sync_remote: bool = True) -> Dict[str, str]:
        repo_path = self.android_repo if platform.lower() == "android" else self.ios_repo
        print(f"  📦 [{platform.upper()}] Switching code to branch '{branch_name}' in {repo_path.name}...")

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

        info = self.get_repo_info(platform)
        print(f"     ✅ Checked out {platform.upper()} commit: [{info['commit']}] {info['commit_message']} ({info['commit_date']})")
        return info

    def list_branches(self, platform: str, max_count: int = 15) -> List[str]:
        repo_path = self.android_repo if platform.lower() == "android" else self.ios_repo
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
