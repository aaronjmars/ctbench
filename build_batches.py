#!/usr/bin/env python3
"""Dedupe + slim + split one token's corpus into data/<slug>/batches/*.jsonl + manifest.

Usage: build_batches.py <token-slug>
"""
import json

from lib import get_token, slug_arg, tdir


def slim(tw):
    a = tw.get("author", {}) or {}
    return {
        "post_id": str(tw.get("id")),
        "text": tw.get("text", ""),
        "url": tw.get("url", ""),
        "created_at": tw.get("created_at", ""),
        "is_reply": tw.get("is_reply", False),
        "author": {"username": a.get("username", ""), "verified": a.get("verified", False),
                   "followers": a.get("followers")},
        "metrics": tw.get("metrics", {}),
    }


def main():
    slug = slug_arg()
    cfg, _ = get_token(slug)
    size = cfg.get("batch_size", 100)

    raw = tdir(slug, "raw", "corpus.jsonl")
    seen, posts = set(), []
    for line in raw.read_text().split("\n"):
        if not line.strip():
            continue
        tw = json.loads(line)
        pid = str(tw.get("id"))
        if not pid or pid in seen:
            continue
        seen.add(pid)
        posts.append(slim(tw))

    bdir = tdir(slug, "batches")
    bdir.mkdir(parents=True, exist_ok=True)
    for old in bdir.glob("batch-*.jsonl"):
        old.unlink()

    manifest = {"slug": slug, "posts": len(posts), "batch_size": size, "batches": []}
    for i in range(0, len(posts), size):
        chunk = posts[i:i + size]
        fname = f"batch-{i // size:03d}.jsonl"
        with (bdir / fname).open("w") as f:
            for p in chunk:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        manifest["batches"].append({"file": fname, "posts": len(chunk)})
    (bdir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[{slug}] {len(posts)} unique posts -> {len(manifest['batches'])} batches")


if __name__ == "__main__":
    main()
