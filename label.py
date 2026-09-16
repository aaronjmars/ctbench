#!/usr/bin/env python3
"""Label one token's batches by fanning out headless Claude Code subagents (haiku/sonnet).

Passes the token's contract + chain to the labeler so it can reject same-ticker
collisions. No ANTHROPIC_API_KEY: `claude -p` uses the local subscription.

Usage: label.py <token-slug>
"""
import concurrent.futures as cf
import json
import re
import shutil
import subprocess
import sys

from lib import ROOT, get_token, slug_arg, tdir

CONTRACT = (ROOT / "CLASSIFICATION_PROMPT.md").read_text()
FENCE = re.compile(r"^```[a-zA-Z]*\n|\n```$", re.M)


def claude_bin():
    exe = shutil.which("claude")
    if not exe:
        sys.exit("claude CLI not found on PATH")
    return exe


def label_batch(exe, batch_path, tok, model, labels_dir):
    out_path = labels_dir / batch_path.name
    if out_path.exists() and out_path.read_text().strip():
        return batch_path.name, "skip", None
    prompt = (
        f"{CONTRACT}\n\n"
        f"TARGET TOKEN: {tok['name']} (symbol {tok['symbol']}).\n"
        f"Chain: {tok['chain']}. Contract address: {tok['contract']}.\n"
        f"A post is relevant ONLY if it is about THIS token/project (this contract or an "
        f"unambiguous reference to it), NOT another project that happens to share the ticker.\n\n"
        f"Label every post below. Output ONLY JSONL, one object per post.\n\n"
        f"POSTS:\n{batch_path.read_text()}"
    )
    res = subprocess.run([exe, "-p", prompt, "--model", model], capture_output=True, text=True)
    if res.returncode != 0:
        return batch_path.name, None, res.stderr.strip()[:200]

    out = FENCE.sub("", res.stdout.strip())
    labels = []
    for line in out.split("\n"):
        line = line.strip()
        if line.startswith("{"):
            try:
                labels.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    if not labels:
        return batch_path.name, None, "no valid JSONL parsed"
    labels_dir.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f:
        for o in labels:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    return batch_path.name, len(labels), None


def main():
    slug = slug_arg()
    cfg, tok = get_token(slug)
    model = cfg.get("label_model", "haiku")
    exe = claude_bin()
    labels_dir = tdir(slug, "labels")
    batches = sorted(tdir(slug, "batches").glob("batch-*.jsonl"))
    if not batches:
        sys.exit(f"[{slug}] no batches; run build_batches.py first")

    print(f"[{slug}] labeling {len(batches)} batches, model={model}", file=sys.stderr)
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = [ex.submit(label_batch, exe, b, tok, model, labels_dir) for b in batches]
        for fut in cf.as_completed(futs):
            name, n, err = fut.result()
            print(f"  [{slug}] {name}: {'ERR ' + err if err else str(n) + ' labels'}", file=sys.stderr)


if __name__ == "__main__":
    main()
