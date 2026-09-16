#!/usr/bin/env python3
"""Aggregate one token's labels -> data/public/<slug>/{summary,evidence}.json and
merge its headline into data/public/index.json (the leaderboard).

Headline score counts signal only: relevant + firsthand + non-shill.

Usage: aggregate.py <token-slug>
"""
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone

from lib import ROOT, get_token, slug_arg, tdir


def post_date(created_at):
    """Twitter stamp 'Tue Sep 15 19:38:52 +0000 2026' -> 'YYYY-MM-DD' (UTC)."""
    if not created_at:
        return None
    try:
        dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None

PUB = ROOT / "data" / "public"


def read_jsonl(path, key):
    out = {}
    for line in path.read_text().split("\n"):
        if line.strip():
            o = json.loads(line)
            out[str(o[key])] = o
    return out


def main():
    slug = slug_arg()
    _, tok = get_token(slug)

    labels = {}
    for f in sorted(tdir(slug, "labels").glob("batch-*.jsonl")):
        labels.update(read_jsonl(f, "post_id"))
    posts = {}
    for f in sorted(tdir(slug, "batches").glob("batch-*.jsonl")):
        posts.update(read_jsonl(f, "post_id"))

    pol, aspect, stance, action, totals = Counter(), Counter(), Counter(), Counter(), Counter()
    aspect_pol = defaultdict(Counter)
    daily = defaultdict(Counter)  # date -> {positive,negative,mixed} for signal posts
    evidence = []

    for pid, lab in labels.items():
        post = posts.get(pid, {})
        s = lab.get("sentiment", {}) or {}
        rel, shill, fh = lab.get("relevant"), lab.get("bot_or_shill"), lab.get("firsthand")
        totals["labeled"] += 1
        totals["relevant"] += 1 if rel else 0
        totals["shill"] += 1 if shill else 0
        totals["firsthand"] += 1 if fh else 0

        signal = rel and not shill and fh
        if signal:
            p = s.get("polarity", "none")
            if p not in ("positive", "negative", "mixed"):
                p = "none"
            pol[p] += 1
            if p in ("positive", "negative", "mixed"):
                aspect[s.get("aspect", "other")] += 1
                aspect_pol[s.get("aspect", "other")][p] += 1
            st = s.get("stance", "observer")
            if st not in ("holder", "trader", "builder", "observer"):
                st = "observer"
            stance[st] += 1
            act = lab.get("action", "none")
            if act not in ("buy", "sell", "hold", "entry", "exit", "none"):
                act = "none"
            action[act] += 1
            d = post_date(post.get("created_at"))
            if d and p in ("positive", "negative", "mixed"):
                daily[d][p] += 1

        evidence.append({
            "post_id": pid, "url": post.get("url", ""),
            "author": (post.get("author", {}) or {}).get("username", ""),
            "text": post.get("text", ""), "signal": bool(signal), "label": lab,
        })

    denom = pol["positive"] + pol["negative"] + pol["mixed"]
    score = round(100 * (pol["positive"] - pol["negative"]) / denom, 1) if denom else 0.0

    summary = {
        "slug": slug, "token": tok["symbol"], "name": tok["name"],
        "chain": tok["chain"], "contract": tok["contract"],
        "totals": dict(totals), "sentiment_score": score, "signal_n": denom,
        "polarity": dict(pol), "aspect": dict(aspect),
        "aspect_polarity": {k: dict(v) for k, v in aspect_pol.items()},
        "stance": dict(stance), "action": dict(action),
        "daily": [
            {"date": d, "positive": c.get("positive", 0),
             "negative": c.get("negative", 0), "mixed": c.get("mixed", 0)}
            for d, c in sorted(daily.items())
        ],
    }

    odir = PUB / slug
    odir.mkdir(parents=True, exist_ok=True)
    (odir / "summary.json").write_text(json.dumps(summary, indent=2))
    (odir / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False))

    # merge leaderboard index
    idx_path = PUB / "index.json"
    idx = {}
    if idx_path.exists():
        idx = {e["slug"]: e for e in json.loads(idx_path.read_text())}
    idx[slug] = {"slug": slug, "token": tok["symbol"], "name": tok["name"],
                 "chain": tok["chain"], "sentiment_score": score, "signal_n": denom,
                 "totals": dict(totals)}
    idx_path.write_text(json.dumps(sorted(idx.values(), key=lambda e: -e["sentiment_score"]), indent=2))

    print(f"[{slug}] score {score} (signal n={denom}), polarity {dict(pol)}")


if __name__ == "__main__":
    main()
