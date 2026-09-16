"""Shared helpers for the ctbench pipeline (multi-token)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_cfg():
    return json.loads((ROOT / "tokens.json").read_text())


def get_token(slug):
    cfg = load_cfg()
    for t in cfg["tokens"]:
        if t["slug"] == slug:
            return cfg, t
    sys.exit(f"unknown token slug: {slug}. known: {[t['slug'] for t in cfg['tokens']]}")


def tdir(slug, *parts):
    p = ROOT / "data" / slug
    for x in parts:
        p = p / x
    return p


def slug_arg():
    if len(sys.argv) < 2:
        sys.exit(f"usage: {Path(sys.argv[0]).name} <token-slug>")
    return sys.argv[1]
