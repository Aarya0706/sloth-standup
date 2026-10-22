"""Run an open-weight model in-process with llama.cpp. No server, no API key."""
import sys

from .gitdata import _compact

DEFAULT_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
DEFAULT_FILE = "*q4_k_m.gguf"

SYSTEM = (
    "You summarize a developer's git commits for ONE project. "
    "Write 2 or 3 items separated by semicolons. Each item is at most 8 words. "
    "Merge similar commits into one item. "
    "Use only the commits given. Never invent work."
)

GRAMMAR = r'''
root ::= item ("; " item){1,2}
verb ::= "Fixed" | "Added" | "Refactored" | "Updated" | "Improved" | "Removed" | "Tested" | "Documented"
item ::= verb " " [a-zA-Z0-9 _/()#,-]{8,60}
'''



def _load(cfg):
    try:
        from llama_cpp import Llama, LlamaGrammar
    except ImportError:
        sys.exit("llama-cpp-python is not installed. Run: pip install -r requirements.txt")

    kwargs = {"n_ctx": 4096, "verbose": False}
    if cfg.get("model_path"):
        llm = Llama(model_path=cfg["model_path"], **kwargs)
    else:
        llm = Llama.from_pretrained(
            repo_id=cfg.get("model_repo", DEFAULT_REPO),
            filename=cfg.get("model_file", DEFAULT_FILE), **kwargs)
    return llm, LlamaGrammar.from_string(GRAMMAR)


def _summarize(llm, grammar, d):
    commits = "\n".join(f"- {m}" for m in _compact(d["commits"], limit=10))
    if not commits:
        return None
    out = llm.create_chat_completion(
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user",
                   "content": f"Project: {d['name']}\nCommits:\n{commits}"}],
        temperature=0.2, max_tokens=140, repeat_penalty=1.15, grammar=grammar)
    return out["choices"][0]["message"]["content"].strip()


def _today(d):
    """Built from facts, not generated, so it can't be invented."""
    items = []
    if d["uncommitted"]:
        n = len(d["uncommitted"].splitlines())
        items.append(f"finish {n} uncommitted file(s)")
    if d["prs"]:
        items.append("follow up on open PRs")
    if d["branch"] and d["branch"] not in ("main", "master"):
        items.append(f"continue {d['branch']}")
    return "; ".join(items)


def standup(data, cfg):
    llm, grammar = _load(cfg)
    done, nxt = [], []
    for d in data:
        s = _summarize(llm, grammar, d)
        if s:
            done.append(f"- {d['name']}: {s}")
        t = _today(d)
        if t:
            nxt.append(f"- {d['name']}: {t}")
    return ("Yesterday:\n" + "\n".join(done or ["- (nothing committed)"]) +
            "\n\nToday:\n" + "\n".join(nxt or ["- (nothing queued)"]))