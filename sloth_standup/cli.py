import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from .gitdata import build_prompt, collect_repo, default_since

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(prog="sloth_standup",
                                 description="Local git standup bot.")
    ap.add_argument("--config", default=str(ROOT / "config.json"))
    ap.add_argument("--since", help='e.g. "2 days ago"')
    ap.add_argument("--repo", action="append", help="repo path (repeatable)")
    ap.add_argument("--author", help="git author filter")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the git data, skip the model")
    args = ap.parse_args()

    cfg = {}
    cfg_path = Path(args.config)
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    repos = args.repo or cfg.get("repos")
    if not repos:
        sys.exit("No repos. Copy config.example.json to config.json and edit it.")

    since = args.since or default_since()
    author = args.author if args.author is not None else cfg.get("author", "")
    data = [d for d in (collect_repo(r, since, author) for r in repos) if d]
    if not data:
        print("No activity found. Enjoy the nap.")
        return

    if args.dry_run:
        print(build_prompt(data))
        return

    from .llm import standup
    summary = standup(data, cfg)

    out_dir = ROOT / cfg.get("output_dir", "standups")
    out_dir.mkdir(exist_ok=True)
    out = out_dir / f"{dt.date.today().isoformat()}.md"
    out.write_text(summary + "\n", encoding="utf-8")
    print(summary)
    print(f"\n(saved to {out})")