#!/usr/bin/env python3
"""Write the bench standard files for a ctbench snapshot run.

Builds runs/<run-id>/manifest.json + samples.jsonl (aaronjmars/bench-kit, STANDARD.md,
schemas bench-manifest/1 and bench-sample/1) from data/public/, the same files the
dashboard reads. One subject per token, one sample row per labeled post. Rows carry the
post id and the label fields only, never the post text.

aggregate.py calls write_run() after each token, so a full ./run.sh leaves one run
folder. Human fields (question, summary, verdict, corrections, writeup, ...) already in an
existing manifest are kept. After it runs:  bench-kit stats && bench-kit render

Usage: standard.py [--run-id YYYY-MM-DD-slug] [--slugs a,b,c]
"""
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone

from lib import ROOT, load_cfg

PUB = ROOT / "data" / "public"
RUNS = ROOT / "runs"
POLARITY_SCORE = {"positive": 100, "negative": -100, "mixed": 0}
TWITTER_EPOCH_MS = 1288834974657


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_run_id():
    """CTBENCH_RUN_ID (run.sh sets it once per run) or <today UTC>-sentiment-snapshot."""
    return os.environ.get("CTBENCH_RUN_ID") or datetime.now(timezone.utc).strftime("%Y-%m-%d") + "-sentiment-snapshot"


def posted_at(post_id):
    """X post ids are snowflakes: the top bits are milliseconds since the Twitter epoch."""
    try:
        ms = (int(post_id) >> 22) + TWITTER_EPOCH_MS
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def prompt_sha():
    try:
        out = subprocess.run(["git", "hash-object", "CLASSIFICATION_PROMPT.md"], cwd=ROOT, capture_output=True, text=True, check=True)
        return out.stdout.strip()[:12] or None
    except (OSError, subprocess.CalledProcessError):
        return None


def sample_rows(slug, evidence):
    """One bench-sample/1 row per labeled post, scored the way aggregate.py scores it.

    evaluation.score: +100 positive, -100 negative, 0 mixed for posts counted in the
    headline (signal with a polarity), null otherwise, so the mean of the scored rows is
    sentiment_score. evaluation.is_correct: true when the post is counted, so the share of
    true rows is signal_n / labeled.
    """
    rows = []
    for e in evidence:
        lab = e.get("label") or {}
        s = lab.get("sentiment") or {}
        pol = s.get("polarity", "none")
        if pol not in POLARITY_SCORE:
            pol = "none"
        counted = bool(e.get("signal")) and pol in POLARITY_SCORE
        pid = str(e.get("post_id"))
        rows.append({
            "sample_id": pid,
            "subject": slug,
            "repeat": 1,
            "evaluation": {"score": POLARITY_SCORE[pol] if counted else None, "is_correct": counted},
            "error": None,
            "metadata": {
                "posted_at": posted_at(pid),
                "signal": bool(e.get("signal")),
                "relevant": lab.get("relevant"),
                "bot_or_shill": lab.get("bot_or_shill"),
                "firsthand": lab.get("firsthand"),
                "uncertain": lab.get("uncertain"),
                "polarity": s.get("polarity"),
                "aspect": s.get("aspect"),
                "stance": s.get("stance"),
                "action": lab.get("action"),
            },
        })
    return rows


def metric_config():
    return {
        "sentiment": {
            "metric_name": "Net firsthand sentiment",
            "metric_unit": "points",
            "lower_is_better": False,
            "score_type": "continuous",
            "min_score": -100,
            "max_score": 100,
            "evaluation_description": "100 x (positive - negative) / (positive + negative + mixed) over signal posts "
            "(relevant, firsthand, not bot or shill). Per post +100 / -100 / 0, averaged over the posts counted. "
            "Same number as sentiment_score in data/public, which rounds it to 1 decimal.",
            "metric_parameters": {"from": "score"},
        },
        "signal_share": {
            "metric_name": "Share of labeled posts counted in the score",
            "metric_unit": "share",
            "lower_is_better": False,
            "score_type": "binary",
            "evaluation_description": "signal_n / posts labeled. The rest is off-topic, bot or shill, secondhand, or has no polarity.",
            "metric_parameters": {"from": "is_correct"},
        },
        "signal_posts": {
            "metric_name": "Signal posts counted (signal_n)",
            "metric_unit": "posts",
            "lower_is_better": False,
            "score_type": "continuous",
            "min_score": 0,
            "evaluation_description": "signal_n in data/public: signal posts with a positive, negative or mixed polarity.",
            "metric_parameters": {"from": "external"},
        },
        "posts_labeled": {
            "metric_name": "Posts labeled",
            "metric_unit": "posts",
            "lower_is_better": False,
            "score_type": "continuous",
            "min_score": 0,
            "evaluation_description": "totals.labeled in data/public: posts that came back from the judge with a label.",
            "metric_parameters": {"from": "external"},
        },
    }


def write_run(run_id=None, slugs=None, touch=False):
    """Create or refresh runs/<run_id>/ from data/public for the given token slugs.

    Tokens already in the run and not in slugs are kept, so aggregate.py can add one token
    at a time. touch=True stamps finished_at with the current time (aggregate.py does this).
    Returns the run directory.
    """
    run_id = run_id or default_run_id()
    cfg = load_cfg()
    toks = {t["slug"]: t for t in cfg["tokens"]}
    slugs = list(slugs or [])
    rdir = RUNS / run_id
    rdir.mkdir(parents=True, exist_ok=True)
    mpath, spath = rdir / "manifest.json", rdir / "samples.jsonl"
    m = json.loads(mpath.read_text()) if mpath.exists() else {}
    old_rows = []
    if spath.exists():
        old_rows = [json.loads(x) for x in spath.read_text().splitlines() if x.strip()]

    rows_by = {}
    for r in old_rows:
        rows_by.setdefault(r["subject"], []).append(r)
    summaries = {}
    for slug in list(rows_by) + slugs:
        summaries[slug] = json.loads((PUB / slug / "summary.json").read_text())
    for slug in slugs:
        rows_by[slug] = sample_rows(slug, json.loads((PUB / slug / "evidence.json").read_text()))

    order = sorted(rows_by, key=lambda x: -summaries[x]["sentiment_score"])
    rows = [r for slug in order for r in rows_by[slug]]

    model = cfg.get("label_model", "haiku")
    commit = (m.get("revision") or {}).get("commit") or git_commit()
    subjects_prev = {s["name"]: s for s in m.get("subjects", [])}
    subjects = []
    for slug in order:
        if slug in subjects_prev:
            subjects.append(subjects_prev[slug])
            continue
        tok = toks.get(slug, {})
        subjects.append({
            "name": slug,
            "model_info": {"id": model, "developer": "anthropic", "inference_platform": "claude-code-cli"},
            "harness": {"name": "ctbench", "version": commit},
            "generation_args": {"label_model": model, "token": {k: tok.get(k) for k in ("symbol", "name", "chain", "contract")}},
            "version_unknown_reason": "claude CLI model alias; the exact snapshot it resolved to is not logged",
        })

    results = dict(m.get("evaluation_results") or {})
    for slug in order:
        s = summaries[slug]
        n = s["totals"].get("labeled", 0)
        res = dict(results.get(slug) or {})
        res["sentiment"] = res.get("sentiment") or {"score": s["sentiment_score"]}
        res["signal_share"] = res.get("signal_share") or {"score": round(s["signal_n"] / n, 4) if n else None}
        res["signal_posts"] = {"score": s["signal_n"]}
        res["posts_labeled"] = {"score": n}
        results[slug] = res

    n_done = len(rows)
    n_plan = len(order) * cfg["collect"]["max_pages"] * 20
    window = {}
    for slug in order:
        ts = sorted(r["metadata"]["posted_at"] for r in rows_by[slug] if r["metadata"]["posted_at"])
        window[slug] = [ts[0], ts[-1]] if ts else None
    names = ", ".join(toks.get(x, {}).get("symbol", x) for x in order)
    started = m.get("started_at") or now_iso()

    new = {
        "schema_version": "bench-manifest/1",
        "id": run_id,
        "bench": "ctbench",
        "question": m.get("question") or f"What is the firsthand sentiment on X for {names} in the posts collected on {started[:10]}?",
        "title": m.get("title") or "crypto twitter sentiment snapshot",
        "headline": m.get("headline", True),
        "started_at": started,
        "finished_at": m.get("finished_at"),
        "revision": m.get("revision") or {"repo": "aaronjmars/ctbench", "commit": commit, "dirty": None},
        "command": m.get("command") or "./run.sh",
        "setup": m.get("setup", "standard"),
        "setup_notes": m.get("setup_notes"),
        "env": {**(m.get("env") or {}), "collect": cfg["collect"], "batch_size": cfg.get("batch_size"), "posts_window_utc": window},
        "eval_library": {"name": "ctbench", "version": commit or "unknown"},
        "interaction_type": "single_turn",
        "source_data": {
            **(m.get("source_data") or {}),
            "dataset_name": "x-posts-by-token",
            "version": (m.get("source_data") or {}).get("version", "1-A"),
            "n_planned": n_plan,
            "n_completed": n_done,
        },
        "subjects": subjects,
        "repeats": {"planned": 1, "completed": 1, "aggregation": "mean"},
        "llm_scoring": m.get("llm_scoring") or {
            "judges": [{"model_info": {"id": model, "developer": "anthropic"}}],
            "votes": 1,
            "input_prompt_sha": prompt_sha(),
            "agreement": None,
        },
        "metric_config": metric_config(),
        "primary_metric": "sentiment",
        "evaluation_results": results,
        "errors": {
            **(m.get("errors") or {}),
            "n": 0,
            "of": n_done,
            "counted_as": "excluded",
        },
        "cost": m.get("cost") or {
            "usd": None,
            "basis": "subscription",
            "note": "labeling on a Claude subscription; twitterapi.io collection is billed per request and was not logged",
        },
        "decision_rule": m.get("decision_rule"),
        "verdict": m.get("verdict", "SNAPSHOT"),
        "status": m["status"] if m.get("status") not in (None, "partial") else ("complete" if set(order) >= set(toks) else "partial"),
        "summary": m.get("summary"),
        "compared_with": m.get("compared_with", []),
        "raw": m.get("raw") or {"kept": False, "reason": "raw corpus, batches and label files are gitignored; data/public keeps every label by post id"},
        "writeup": m.get("writeup") or "https://ctbench.vercel.app",
        "superseded_by": m.get("superseded_by"),
        "corrections": m.get("corrections", []),
        "lint_ignore": m.get("lint_ignore", []),
    }
    if touch or not m:
        new["finished_at"] = now_iso()
    mpath.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n")
    spath.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    return rdir


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run-id", default=None, help="run folder name (default: $CTBENCH_RUN_ID or <today>-sentiment-snapshot)")
    ap.add_argument("--slugs", default=None, help="comma separated token slugs (default: every token in data/public/index.json)")
    a = ap.parse_args()
    slugs = a.slugs.split(",") if a.slugs else [e["slug"] for e in json.loads((PUB / "index.json").read_text())]
    rdir = write_run(a.run_id, slugs)
    print(f"wrote {rdir.relative_to(ROOT)}/manifest.json + samples.jsonl; next: bench-kit stats && bench-kit render")


if __name__ == "__main__":
    main()
