# ctbench method

Benchmark card for ctbench, in the shape of the [bench-kit](https://github.com/aaronjmars/bench-kit)
standard (STANDARD.md section 6). Results live in `runs/<id>/manifest.json` and are rendered into
[RESULTS.md](RESULTS.md). Open work: [NEXT.md](NEXT.md).

## 1. Goal and scope

ctbench is a measurement, not a contest between models. It reads recent X posts about a crypto
token and reports how the people with real exposure feel about it (net firsthand sentiment), with
every label traceable to a post id. It serves a reader who wants the signal in crypto twitter
without the hype, shilling and bots.

- Subject type: a **token**. Each token is one subject in the run manifest.
- Instrument: the ctbench pipeline (`collect.py`, `build_batches.py`, `label.py`, `aggregate.py`)
  with one LLM judge. The judge model is recorded on every subject, but it is held fixed inside a
  run; comparing judges is not what a run does.
- Verdict: always `SNAPSHOT`. A run has one collection and one label pass, so it ranks nothing
  with confidence and has no decision rule.

## 2. Tasks and data

- Task = one X post. Subject = the token it was collected for. `runs/<id>/samples.jsonl` has one
  row per labeled post: the post id, the label fields and the post time decoded from the post id.
  Post text, author and URL stay in `data/public/<slug>/evidence.json` and are not copied.
- Source: X search through [twitterapi.io](https://twitterapi.io) with the `x-cli` collector. Query
  `(cashtags OR "contract-address") -is:retweet since:<today - 7 days>`, capped at 25 pages (about
  500 posts) per token, newest first. Posts are deduplicated by id and split into batches of 100.
- Tokens: the six in `tokens.json` (STONK, AI, cashcat, PONS, PUMP, ANSEM), picked by hand. There
  is no sampling rule for which tokens get tracked.
- Window: the search reaches 7 days back, but the 500-post cap is hit first. In the 2026-09-15 run
  the posts span 2026-09-14T17:08Z to 2026-09-15T23:31Z: ANSEM 4.2 h, PONS 7.5 h, STONK 8.0 h,
  AI 18.5 h, cashcat 24.9 h, PUMP 30.1 h (per-token windows are in the manifest under
  `env.posts_window_utc`). Busy tokens get a shorter window.
- Size of the 2026-09-15 run: 2,996 posts labeled of a 3,000 cap (498 to 500 per token).
- Solvability check: none. There is no human-labeled reference set yet (NEXT.md).
- Task-set name in manifests: `x-posts-by-token`, version `1-A` (section 10).

Why subjects are tokens and tasks are posts: the token is the unit every result is reported for (the
leaderboard), and the post is the unit the judge scores, so per-post rows let `bench-kit stats`
recompute every headline number. Tokens do not share posts, so there are no paired comparisons, and
the number of rows differs a little per token (498 to 500). bench-kit expects the same row count
for every subject, so `.bench-lint-ignore` turns off that one samples check (BL004 on
`runs/*/samples.jsonl`). The checks that recompute the manifest numbers from the samples still run.

## 3. Metrics

Signal post = relevant to this token, not bot or shill, and firsthand (the author holds, trades or
builds on it, or reports a concrete result).

| id | what | unit | better | from |
|---|---|---|---|---|
| `sentiment` (primary) | 100 x (positive - negative) / (positive + negative + mixed) over signal posts. Per post: +100 positive, -100 negative, 0 mixed; signal posts with no polarity and all other posts are not counted. | points, -100 to 100 | higher means more positive | samples (`evaluation.score`) |
| `signal_share` | share of labeled posts counted in `sentiment` | share | n/a | samples (`evaluation.is_correct`) |
| `signal_posts` | `signal_n` in `data/public`: posts counted in `sentiment` | posts | n/a | external |
| `posts_labeled` | `totals.labeled` in `data/public` | posts | n/a | external |

`data/public` rounds `sentiment` to 1 decimal; the manifest keeps 4. Intervals are 95%: a t interval
over the per-post scores for `sentiment`, a Wilson interval for `signal_share`. Both treat posts as
independent, which they are not (section 8), so read them as optimistic. "higher is better" in the
manifest only sets the sort direction; a higher score is not a better token.

## 4. Judge

- Model: Claude Haiku through the Claude Code CLI (`claude -p --model haiku`), on a Claude
  subscription. For the 2026-09-15 run this is inferred from `label_model` in `tokens.json` at the
  data commit; the run did not log the model or the exact snapshot the `haiku` alias resolved to.
- Prompt: `CLASSIFICATION_PROMPT.md` ("Crypto Sentiment Classification Contract v1", git blob
  `5d2265c06d54`), plus the token name, symbol, chain and contract, and an instruction to reject
  same-ticker projects.
- Calls: one call per batch of 100 posts, up to 4 in parallel, one vote per post. Batches that
  already have labels are skipped on rerun.
- `aggregate.py` maps off-schema polarity, stance and action values to safe defaults.
- Agreement: not measured. No second judge and no human re-read yet. The judge flagged 116 of 2,996
  posts as `uncertain` (56 of them for cashcat), and 42 cashcat labels have no `uncertain` field.

## 5. Baselines

None. A trivial keyword baseline (count positive and negative words) and a stricter judge
(`label_model: sonnet`) on the same posts are the obvious ones (NEXT.md).

## 6. Noise band

Not measured. No A/A run exists (the same posts labeled twice with the same model and prompt), so
the judge's run-to-run spread is unknown. Until it is, differences between tokens smaller than the
intervals in RESULTS.md, and any change between two collections, are not readable.

## 7. Fairness and leak register

- The judge sees each post's text, URL, author handle, verified flag, follower count (empty from
  search), reply flag and engagement counts, plus the token's name, symbol, chain and contract.
  It has no web access and sees no price data.
- There is no ground truth, so there is nothing to leak. Bias risk instead: the judge sees the
  author handle and engagement, which could sway the bot or shill call.
- Same-ticker collisions (`$AI`, `$PUMP`) are handled by putting the contract in the query and by the
  judge's relevance call. Share of posts judged relevant: ANSEM 100%, PONS 95%, STONK 99%, PUMP 84%,
  AI 88%, cashcat 86%.

## 8. Known flaws and their estimated impact

1. **Window is hours, not a week.** The 500-post cap means 4 to 31 hours per token, and the windows
   differ by token, so tokens are compared over different time spans. The README and the README hero
   used to say seven days; fixed 2026-10-09 (correction in the run manifest). The dashboard said the
   same and was fixed the same day; it now shows each token's window, read from the post ids.
2. **Small signal sets.** 61 to 138 signal posts per token; interval half-widths are 9 to 20 points.
3. **Posts are not independent.** Some authors post many times (one cashcat author has 9 of 76 signal
   posts) and replies cluster in threads. Intervals that treat posts as independent are too narrow.
4. **One judge pass, unvalidated.** No A/A run, no human check, no second model. The firsthand and
   bot or shill calls decide what counts, and both are judgement calls.
5. **Judge model not logged.** The model is inferred and the alias snapshot is unknown.
6. **Missing posts.** AI has 498 labels, PONS and PUMP 499. Raw files were not kept, so it is unknown
   whether the collector returned fewer posts or the judge dropped some.
7. **Collection order.** Tokens are collected one after another, in `tokens.json` order. In the
   2026-09-15 run the newest post per token goes from 21:51Z (ANSEM, first) to 23:31Z (cashcat,
   last), so the sweep took about 1.7 hours and later tokens include later posts.

## 9. Out of scope

- Not a price signal and not investment advice.
- Not a comparison of LLM judges or prompts.
- Not a weekly view, and not a ranking with confidence: one snapshot cannot say one token is
  better liked than another unless the intervals are far apart, and even then see section 8.

## 10. Changelog

### [1-A] - 2026-09-15

- First collection: six tokens, Classification Contract v1, Claude Haiku judge (inferred), batch size
  100, 25-page cap, retweets dropped. Run `2026-09-15-sentiment-snapshot`.

Not a task-set change: on 2026-10-09 the repo adopted the bench-kit results standard (run manifest
and samples backfilled from `data/public`, which `aggregate.py` reproduces byte for byte from the
committed labels; README and hero wording on the posts window corrected).
