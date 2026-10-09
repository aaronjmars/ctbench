# ctbench: what to do next

Updated 2026-10-09. Open work, newest first. Method and known flaws: [METHOD.md](METHOD.md).

## 1. Honest copy on the dashboard

The README and the README hero now describe the real posts window (4 to 31 hours per token in the
2026-09-15 snapshot). The live dashboard still says seven days in `index.html`: the meta description,
the "posts read" tooltip, the leaderboard footer ("500 posts / 7 days per token"), the "How it is
read" note ("Capped at 500 posts over seven days per token") and the site footer ("rolling 7 days").
Change that copy, or have `ctbench.js` fill the window from the post times. Not changed in the
bench-standard migration, which kept every dashboard file as is. The GitHub repo description
("judges a week of X posts") says the same and should match the README one-liner.

## 2. Measure the judge

- A/A run: label the same 2026-09-15 posts a second time with the same model and prompt, and record
  the spread per token as the noise band (METHOD.md section 6). Needs the raw batches, which were not
  kept, so rebuild batches from `data/public/<slug>/evidence.json` (post id, text, url, author; post
  time from the post id) or do it on the next collection.
- Second judge: the same posts with `label_model: sonnet`, to see how much the firsthand and bot or
  shill calls move the score.
- Human check: re-read the 116 posts the judge flagged `uncertain` plus a random sample of 50 per
  token, and report agreement in METHOD.md section 4.

## 3. Collection

- Window: either widen it (more pages, or one search per day across the 7 days) or say in every
  output that the window is "latest 500 posts". Record the window per run (the manifest already has
  `env.posts_window_utc`).
- Log the run: model id as resolved by the CLI, collection start and end time, x-cli version and
  twitterapi.io request count and cost. Today the manifest has to infer most of these.
- Keep raw output (or at least the batch files) per run so missing posts can be explained. In the
  2026-09-15 run AI has 498 labels and PONS and PUMP 499, cause unknown.

## 4. Stats

- Intervals treat posts as independent. Cluster by author (some authors post several times) or report
  the number of distinct authors next to n.
- With a second collection, add a `compared_with` entry and read changes only beyond the noise band.

## 5. Bench standard

- `aggregate.py` now writes `runs/<run-id>/manifest.json` + `samples.jsonl` through `standard.py`
  after each token; `run.sh` sets one `CTBENCH_RUN_ID` per sweep. After a sweep: fill question and
  summary in the manifest, then `bench-kit stats && bench-kit render`. Same-day reruns should get a
  new id (`-2`) instead of overwriting the day's run.
- CI runs `bench-kit lint` in warn-only mode. Switch to errors once the dashboard copy (item 1) is
  fixed and a second run has gone through the new path.
