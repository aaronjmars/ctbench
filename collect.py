#!/usr/bin/env python3
"""Collect X posts for ONE token via x-cli (twitterapi.io) -> data/<slug>/raw/corpus.jsonl.

Query = (cashtags OR contract-address). The contract address is a strong
disambiguator against same-ticker collisions ($AI, $PUMP, ...).

Usage: collect.py <token-slug>
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from lib import get_token, slug_arg, tdir


def find_x_cli():
    exe = shutil.which("x-cli") or "/opt/homebrew/bin/x-cli"
    if not os.path.exists(exe):
        sys.exit("x-cli binary not found on PATH or /opt/homebrew/bin")
    return exe


def build_query(cfg, tok):
    terms = list(tok.get("cashtags", []))
    if tok.get("contract"):
        terms.append(f'"{tok["contract"]}"')
    q = "(" + " OR ".join(terms) + ")"
    if cfg["collect"].get("drop_retweets", True):
        q += " -is:retweet"
    since = (datetime.now(timezone.utc) - timedelta(days=cfg["collect"]["since_days"])).date().isoformat()
    return q + f" since:{since}"


def main():
    slug = slug_arg()
    cfg, tok = get_token(slug)
    exe = find_x_cli()
    query = build_query(cfg, tok)
    print(f"[{slug}] query: {query}", file=sys.stderr)

    if "TWITTER_API_KEY" not in os.environ:
        sys.exit("TWITTER_API_KEY not set")
    # --max-pages caps the sweep (do NOT pass --all, which removes the cap)
    cmd = [exe, "search", query, "--json", "--max-pages", str(cfg["collect"]["max_pages"])]
    res = subprocess.run(cmd, capture_output=True, text=True, env=dict(os.environ))
    if res.returncode != 0:
        sys.exit(f"x-cli failed: {res.stderr.strip()}")
    if res.stderr.strip():
        print(res.stderr.strip(), file=sys.stderr)

    tweets = json.loads(res.stdout).get("tweets", [])
    out = tdir(slug, "raw", "corpus.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f:
        for tw in tweets:
            f.write(json.dumps(tw, ensure_ascii=False) + "\n")
    print(f"[{slug}] wrote {len(tweets)} posts -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
