<p align="center">
  <img src="docs/assets/hero.svg?v=3" alt="ctbench - crypto twitter sentiment bench. Firsthand opinion on X about a token, judged one post at a time, scoring the signal and setting aside the hype, shilling and bots." width="100%" />
</p>

<p align="center">
  <strong>Live dashboard&nbsp;&rarr;</strong>&nbsp;
  <a href="https://ctbench.vercel.app"><strong>ctbench.vercel.app</strong></a>
  &nbsp;&nbsp;&#183;&nbsp;&nbsp;
  <strong>Star us&nbsp;&#10084;&nbsp;&#8594;</strong>&nbsp;
  <a href="https://github.com/aaronjmars/ctbench/stargazers">GitHub</a>
</p>

<p align="center">
  <strong>Crypto twitter sentiment, one post at a time.</strong><br>
  Reads the latest X posts about a token (up to about 500, searched up to 7 days back), has an LLM
  judge every post individually, and renders a static dashboard where every label is auditable by
  post id. The published snapshot (2026-09-15) covers the last 4 to 31 hours of posts per token.
</p>

<div align="center">

[![stars](https://img.shields.io/github/stars/aaronjmars/ctbench?style=flat-square&label=stars&color=F4EFE1&labelColor=0d0c0a&logo=github&logoColor=F4EFE1)](https://github.com/aaronjmars/ctbench/stargazers)
[![forks](https://img.shields.io/github/forks/aaronjmars/ctbench?style=flat-square&label=forks&color=F4EFE1&labelColor=0d0c0a&logo=github&logoColor=F4EFE1)](https://github.com/aaronjmars/ctbench/network/members)
[![live](https://img.shields.io/badge/demo-ctbench.vercel.app-2b4bd6?style=flat-square&labelColor=0d0c0a)](https://ctbench.vercel.app)
[![license](https://img.shields.io/badge/license-MIT-F4EFE1?style=flat-square&labelColor=0d0c0a)](LICENSE)

</div>

## Status

Updated 2026-10-09. State: snapshot. One collection so far, on 2026-09-15, for six tokens (STONK, AI,
cashcat, PONS, PUMP, ANSEM); it is what the live dashboard shows. Every number is recorded in
[`runs/`](runs/INDEX.md) in the [bench-kit](https://github.com/aaronjmars/bench-kit) results format.
Next: make the dashboard copy match the real posts window, then a second collection with an A/A
label rerun to measure judge noise (details in [NEXT.md](NEXT.md)).

## Latest result

<!-- bench:latest:start -->
Run 2026-09-15-sentiment-snapshot (2026-09-15): What is the firsthand sentiment on X for STONK, AI, cashcat, PONS, PUMP and ANSEM in the latest posts collected on 2026-09-15?
Tasks: x-posts-by-token v1-A, 2996 of 3000 tasks x 1 repeats. Judge: haiku x1, prompt sha 5d2265c06d54.

| Subject | sentiment (points), mean [95% CI] | n tasks | cost/task | time/task |
|---|---|---|---|---|
| stonk | 82.759 [72.936, 92.581] | 87 | n/a | n/a |
| ai | 80.435 [71.451, 89.418] | 138 | n/a | n/a |
| cashcat | 54.167 [35.41, 72.923] | 72 | n/a | n/a |
| pons | 54.098 [33.949, 74.247] | 61 | n/a | n/a |
| pump | 48.649 [29.132, 68.166] | 74 | n/a | n/a |
| ansem | 43.2 [27.721, 58.679] | 125 | n/a | n/a |

Verdict: SNAPSHOT. Status: complete.
Summary: Net firsthand sentiment (signal posts only): STONK +82.8 (n=87), AI +80.4 (n=138), cashcat +54.2 (n=72), PONS +54.1 (n=61), PUMP +48.6 (n=74), ANSEM +43.2 (n=125), out of 498 to 500 posts labeled per token. One collection, one label pass: a snapshot, not a ranking test. The STONK and AI intervals sit above PUMP and ANSEM; cashcat, PONS, PUMP and ANSEM overlap each other. Intervals treat posts as independent, so they are optimistic. The posts span 2026-09-14T17:08Z to 2026-09-15T23:31Z (4 to 31 hours per token), not seven days.
Every run: RESULTS.md.
<!-- bench:latest:end -->

Sentiment is net firsthand opinion from -100 to +100; n tasks is the number of signal posts counted.
How it is measured and its limits: [METHOD.md](METHOD.md).

## How it works

`run.sh` chains four standard-library Python scripts. Run them by hand to inspect any stage:

```bash
python3 collect.py       <slug>   # x-cli search      -> data/<slug>/raw/corpus.jsonl
python3 build_batches.py <slug>   # dedupe/slim/split -> data/<slug>/batches/*.jsonl
python3 label.py         <slug>   # claude subagents  -> data/<slug>/labels/*.jsonl
python3 aggregate.py     <slug>   # roll up           -> data/public/<slug>/*.json + index.json
```

- **Collection** pulls posts from X through the [twitterapi.io](https://twitterapi.io) API (not the
  official X API), searching `(cashtag OR contract-address)`.
- **Labeling** fans out up to 4 `claude -p --model haiku|sonnet` subagents at once and **skips batches
  already labeled**, so re-running is cheap and resumable. The judge is told the contract + chain and
  rejects posts about other projects that share the ticker.
- **Aggregation** writes the two files the dashboard reads (`summary.json`, `evidence.json`) and merges
  the token into the leaderboard `index.json`.

After the last step, `aggregate.py` also refreshes the run record in `runs/<run-id>/` (`manifest.json`
plus `samples.jsonl`, one row per labeled post, post id and label only) through `standard.py`.
Metrics, judge, known flaws and changelog: [METHOD.md](METHOD.md).

## Run it

### Requirements

- **Python 3** - standard library only, nothing to `pip install`.
- **A [twitterapi.io](https://twitterapi.io) API key** in `TWITTER_API_KEY` - collection reads X through
  twitterapi.io, the only paid dependency (billed per request, ~1 page ~ 20 posts). Plus the `x-cli`
  collector on your PATH.
- **Claude Code** (`claude` on your PATH), logged in. Labeling uses your Claude subscription, so no API
  key is needed: `npm i -g @anthropic-ai/claude-code`, then run `claude` once to sign in.

### Quick start

```bash
export TWITTER_API_KEY=...     # your twitterapi.io key

./run.sh                       # collect + label every token in tokens.json,
                               # then serve the dashboard on a random port
```

`run.sh` prints a `http://localhost:<port>` link when it starts serving. Open it.

```bash
./run.sh ansem                 # run the pipeline for a single token by slug
./run.sh serve                 # just serve the existing dashboard, no collection
```

### Record and check a run

`./run.sh` writes every token of one sweep into `runs/<YYYY-MM-DD>-sentiment-snapshot/` (set
`CTBENCH_RUN_ID` to pick the name). Then fill in the human fields of its `manifest.json` (question,
summary) and regenerate the result docs with [bench-kit](https://github.com/aaronjmars/bench-kit):

```bash
uv tool install git+https://github.com/aaronjmars/bench-kit@v0.2.0
bench-kit stats && bench-kit render && bench-kit lint
python3 standard.py --run-id <run-id>   # rebuild a run record from data/public alone
```

## Layout

| path | what |
|---|---|
| `collect.py`, `build_batches.py`, `label.py`, `aggregate.py`, `lib.py` | the pipeline (standard-library Python) |
| `standard.py` | writes the bench-kit run record (`runs/<id>/manifest.json` + `samples.jsonl`) from `data/public/` |
| `run.sh` | runs the pipeline for one or every token, or serves the dashboard |
| `tokens.json` | tokens and pipeline settings |
| `CLASSIFICATION_PROMPT.md` | the judge's labeling contract |
| `index.html`, `ctbench.js`, `*.css` | the static dashboard (deployed to Vercel, see `vercel.json` and `.vercelignore`) |
| `data/public/` | what the dashboard reads: leaderboard plus per-token summary and evidence |
| `runs/<id>/` | one folder per collection: `manifest.json` (source of truth for results) and `samples.jsonl` |
| `RESULTS.md`, `runs/INDEX.md` | generated by `bench-kit render`; do not edit by hand |
| `METHOD.md`, `NEXT.md` | benchmark card and changelog; open work |
| `docs/assets/` | README images |

### Data layout

```
data/
  <slug>/
    raw/corpus.jsonl        raw x-cli output
    batches/batch-*.jsonl   slimmed, split for labeling
    labels/batch-*.jsonl    one label object per post
  public/
    index.json              leaderboard (all tokens)
    <slug>/summary.json     scores, aspect + stance breakdowns
    <slug>/evidence.json    every post with its label
```

Only `data/public/` is committed; `raw/`, `batches/` and `labels/` are gitignored (large and rebuildable).

## Preview

Ranked sentiment leaderboard - net firsthand opinion per token:

![Sentiment leaderboard](docs/assets/preview-sentiment.png)

The homepage: wordmark, tagline and a live mural of the public conversation.

![Homepage and public conversation mural](docs/assets/preview-top.png)

## What it does

ctbench scores the **signal** - people with real exposure saying what they actually think - and
sets aside the hype, shilling and bots that make up most of the volume. It is a crypto rewrite of
[nicodunks/xbench](https://github.com/nicodunks/xbench): same shape (collect &rarr; label &rarr;
aggregate &rarr; static dashboard), pointed at tokens instead of AI models.

- **Auditable by post id** - every headline number traces back to the exact posts and labels behind it.
- **Contract-disambiguated collection** - the search is `(cashtag OR contract-address)`, so the contract
  keeps `$AI` or `$PUMP` from dragging in every unrelated project that shares the ticker.
- **Judged one post at a time** - Claude Code subagents label each post for relevance, bot/shill,
  firsthand exposure, polarity, aspect, stance and stated action.
- **Multi-token leaderboard** - every token is one row in `tokens.json`; drill into any of them.
- **No API keys for the LLM** - labeling runs on your local Claude subscription, not `ANTHROPIC_API_KEY`.

## Track your own token

Add an entry to `tokens` in `tokens.json`:

```json
{
  "slug": "mytoken",           // short id, used for folder + URL (a-z0-9-)
  "symbol": "MYTOKEN",         // ticker, shown in the UI as $MYTOKEN
  "name": "My Token",          // display name
  "chain": "solana",           // "solana" or "evm" (passed to the judge)
  "contract": "So1111...",     // the token's contract address (disambiguates)
  "cashtags": ["$MYTOKEN"]     // one or more cashtags to search
}
```

Then run it:

```bash
./run.sh mytoken
./run.sh serve                 # refresh the dashboard
```

The `contract` is searched alongside the cashtag and handed to the judge, which drops off-contract posts.

## Configuration (`tokens.json`)

Global keys sit next to `tokens`:

| key                     | default  | meaning                                                   |
|-------------------------|----------|-----------------------------------------------------------|
| `collect.since_days`    | `7`      | how far back to search                                    |
| `collect.max_pages`     | `25`     | page cap per token (~20 posts/page, so ~500 posts)        |
| `collect.drop_retweets` | `true`   | add `-is:retweet` to the query                            |
| `batch_size`            | `100`    | posts per labeling batch (one `claude` call each)         |
| `label_model`           | `haiku`  | `haiku` (cheap, fast) or `sonnet` (stricter, slower)      |

## Scoring

`sentiment_score` (-100..100) counts **signal only**: posts that are relevant + firsthand + non-shill.
Shill/bot and pure hype are tracked and shown in the evidence, but excluded from the headline. The score
is `100 * (positive - negative) / (positive + negative + mixed)` over that signal set, so a small `n`
means a noisier number.

## The judge

`CLASSIFICATION_PROMPT.md` is the full contract the LLM follows. For each post it decides: relevant,
bot/shill, firsthand, polarity (positive/negative/mixed/none), aspect (`price | narrative | momentum |
tech | tokenomics | community | safety | other`), stance (holder/trader/builder/observer) and any stated
action. Edit that file to change what the judge looks for; the dashboard picks up new aspects
automatically. `aggregate.py` normalizes any off-schema label back to a safe default.

## Using the official X API instead

`collect.py` is the **only** X-specific step. It writes `data/<slug>/raw/corpus.jsonl` - one JSON post
per line - and everything downstream (`build_batches.py` &rarr; `label.py` &rarr; `aggregate.py`) is
source-agnostic. To run on the official X API rather than twitterapi.io, skip `collect.py` and produce
that same file yourself, then run the remaining three scripts.

Query the [recent search endpoint](https://docs.x.com/x-api/posts/recent-search)
`GET https://api.x.com/2/tweets/search/recent` with a bearer token. It covers the last 7 days, which
matches the default window:

```bash
curl -H "Authorization: Bearer $X_BEARER_TOKEN" -G \
  "https://api.x.com/2/tweets/search/recent" \
  --data-urlencode 'query=($MYTOKEN OR "0xcontract...") -is:retweet' \
  --data-urlencode 'max_results=100' \
  --data-urlencode 'tweet.fields=created_at,public_metrics,referenced_tweets' \
  --data-urlencode 'expansions=author_id' \
  --data-urlencode 'user.fields=username,verified,public_metrics'
```

Note: `-is:retweet` is a valid v2 operator and `$CASHTAG` is the cashtag operator (needs a paid/Pro
tier). Drop the `since:` operator the pipeline uses for twitterapi.io - on v2 you pass `start_time`
instead. Paginate with `meta.next_token`.

Map each returned post into the shape `build_batches.py` reads and append one JSON object per line to
`data/<slug>/raw/corpus.jsonl`:

```jsonc
{
  "id": "2099982036660269282",                 // required
  "text": "$MYTOKEN looking strong",           // required
  "url": "https://x.com/<username>/status/2099982036660269282",
  "created_at": "2026-09-15T18:04:22.000Z",
  "is_reply": false,                            // referenced_tweets has type "replied_to"
  "author": {                                   // from the expanded users list, joined on author_id
    "username": "someone",                      // required
    "verified": false,
    "followers": 1234                           // user.public_metrics.followers_count
  },
  "metrics": { "like_count": 5, "retweet_count": 1 }  // tweet.public_metrics
}
```

Only `id`, `text` and `author.username` are load-bearing; the rest degrade gracefully (empty / `false`).
Then finish the pipeline:

```bash
python3 build_batches.py <slug>
python3 label.py <slug>
python3 aggregate.py <slug>
./run.sh serve            # refresh the dashboard
```

## Dashboard

Static: `index.html` + `ctbench.js`, reading `data/public/`. Serve it over HTTP (`./run.sh serve`, or any
static server) - opening `index.html` from `file://` will not work because it `fetch()`es the JSON. Layout
is a ranked sentiment leaderboard, a "who is talking" stance panel, an aspect radar comparing tokens, a
per-token praise/complaint book, a filterable evidence strip, and a methods chapter. Charts have hover
tooltips; the whole thing is mobile friendly.

`xbench.css` and `swiss.css` are adapted verbatim from nicodunks/xbench (MIT); `redesign.css`,
`index.html` and `ctbench.js` are this repo's.

## Notes and gotchas

- `collect.py` uses `--max-pages` (never `--all`). It grabs the most recent ~500 posts, which tend to
  cluster into the last day or two, so there is not a clean 7-day spread. In the 2026-09-15 snapshot the
  posts span 4 to 31 hours per token (2026-09-14T17:08Z to 2026-09-15T23:31Z overall). `aggregate.py`
  still emits daily buckets for when you widen the window.
- twitterapi.io is per-request; deep sweeps add up. `search` authors do not carry a follower count or
  profile image.
- Labeling spends Claude subscription quota, not API credit. `haiku` is the cheap default; switch
  `label_model` to `sonnet` for stricter judging.

## License

MIT (see [`LICENSE`](LICENSE)). Built on [nicodunks/xbench](https://github.com/nicodunks/xbench) (MIT).

---

Built by [Aaron Elijah Mars](https://aaronjmars.com), founder of Aeon and MiroShark &#183; [@aaronjmars](https://github.com/aaronjmars)
