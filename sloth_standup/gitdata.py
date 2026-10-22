"""Collect recent git activity from local repos. Pure git, no network."""
import datetime as dt
import shutil
import subprocess
from pathlib import Path

MAX_STAT_CHARS = 2500


def _git(args, cwd):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


def default_since():
    """Monday looks back to Friday, other days look back one day."""
    return "3 days ago" if dt.date.today().weekday() == 0 else "1 day ago"


def _gh_prs(repo):
    r = subprocess.run(
        ["gh", "pr", "list", "--author", "@me", "--json", "number,title",
         "--jq", '.[] | "#\\(.number) \\(.title)"'],
        cwd=repo, capture_output=True, text=True, encoding="utf-8",
        errors="replace")
    return r.stdout.strip() if r.returncode == 0 else ""


def collect_repo(path, since, author=""):
    repo = Path(path).expanduser()
    if not (repo / ".git").exists():
        return None

    base = ["log", f"--since={since}", "--no-merges"]
    if author:
        base.append(f"--author={author}")

    commits = _git(base + ["--pretty=format:%h %s"], repo)
    stat = _git(base + ["--stat", "--pretty=format:"], repo)[:MAX_STAT_CHARS]
    uncommitted = _git(["status", "--short"], repo)
    branch = _git(["branch", "--show-current"], repo)

    prs = _gh_prs(repo) if shutil.which("gh") else ""

    if not (commits or uncommitted or prs):
        return None
    return {"name": repo.name, "branch": branch, "commits": commits,
            "stat": stat, "uncommitted": uncommitted, "prs": prs}


def _compact(commits, limit=12):
    """Drop hashes and duplicate messages, keep the newest few."""
    seen, out = set(), []
    for line in commits.splitlines():
        msg = line.split(" ", 1)[-1]
        if msg not in seen:
            seen.add(msg)
            out.append(msg)
    return out[:limit]


def build_prompt(data):
    blocks = []
    for d in data:
        commits = "\n".join(f"- {m}" for m in _compact(d["commits"])) or "- (none)"
        wip = "\n".join(d["uncommitted"].splitlines()[:8]) or "(none)"
        blocks.append(
            f"Project: {d['name']}\n"
            f"Current branch: {d['branch'] or 'unknown'}\n"
            f"Commits:\n{commits}\n"
            f"Uncommitted files:\n{wip}\n"
            f"Open PRs: {d['prs'] or '(none)'}\n")
    return "GIT ACTIVITY:\n\n" + "\n".join(blocks)[:6000]