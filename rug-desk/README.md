# RUG DESK — self-hosted, no Grok Bot

The desk from @0xboan's article, rebuilt as plain Python you run on your own machine.
Grok Bot only supplied a hosted computer and a chat; `run.py` replaces its routines,
`notify.py` replaces the chat (terminal + `data/desk.log` + optional free Telegram).

    code kills, (optionally) Grok reads X, you sign.

## What it costs

| piece | cost |
|---|---|
| limits, contract facts (Solana chain + GoPlus), pool (DexScreener), scanner, exits, report | free |
| check 14, Grok reading X | **paid** xAI API, per call. Off by default (`JUDGE = "none"`) |

With `JUDGE = "none"` a token that survives every code check gets verdict `PASS`.
In paper mode it is paper-bought (`PAPER_BUY_ON_PASS = True`), so a week of
`data/trades.csv` tells you what the code filter alone is worth. In live mode a PASS
only posts an approval line telling you to read X yourself before you buy.

## Setup (5 minutes)

    # Python 3.10+
    cd rug-desk
    pip install -r requirements.txt
    python -m unittest discover -s tests      # 17 offline tests, should print OK
    python check.py <any Solana mint>         # one verdict, as JSON
    python run.py                             # the desk: 6 agents, paper bankroll $1000
    python dashboard.py                       # private dashboard on http://localhost:8765

Optional `.env` (copy `.env.example`, never commit it):
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` → alerts on your phone, free.
- `XAI_API_KEY` + `JUDGE = "grok"` in config.py → turns on check 14.

## Files

| file | job |
|---|---|
| config.py | every number. you edit it, the code never does |
| book.py | limits, positions, trades. `python book.py add/close/show` for live fills |
| facts.py | contract facts: chain + GoPlus (Rugcheck's domain died in Oct 2026) |
| market.py | checks 10-13 (pool) |
| grok.py, prompts.py | check 14, only loaded when `JUDGE = "grok"` |
| check.py | one mint in, one verdict out |
| watch.py | exits: liquidity pull, stop, ladder, trail, time stop |
| scan.py | leads: six DexScreener feeds plus the DexScreener search (trending tickers + rotating words), PumpSwap pools in the age window |
| report.py | evening report from the CSVs |
| run.py, agents.py | the desk as 6 agents: VIGIE (exits, 20 s), SCOUT (leads, 10 min), GARDE (13 checks), AUDIT (was the filter right, 30 min), PLUME (21:30 report); ECHO is the Claude-in-Chrome X reader |
| audit.py | re-prices every verdict 6 h later: killed tokens that crashed vs passed ones, and ECHO's BUY vs SKIP |
| score.py | ranks every PASS 0-100 like a careful human: holders, distribution, dev, two-way trading, activity, bot volume, age, liquidity margin. below MIN_SCORE it is not bought |
| pending.py | ECHO_MODE = "observe" (paper default): every PASS is bought at once and queued for ECHO, whose verdict is recorded next to the trade. "gate": a PASS waits for ECHO's BUY |
| grads.py | SCOUT's main source: every pump.fun graduation to PumpSwap, read from pump.fun's migration account on chain (~40 an hour) |
| size.py | paper ticket per PASS, % of the balance: base 4%, strong 8% (2-3 signals), max 14% (4+). signals: score 75+, score 85+, 1 h volume >= pool, buyers leading 5 min, smart wallets, ECHO's X narrative. P&L by tier in the evening report |
| health.py | did the desk run all night: pauses (Mac asleep, desk stopped) in data/pauses.csv plus macOS's own sleep log. `python3 health.py` |
| ECHO.md | the X reader's instructions. run it from a local Claude session with Claude in Chrome: `/loop 10m Lis et applique ~/Documents/rug-desk-run/rug-desk/ECHO.md` |
| events.py | the event log and agent status the dashboard reads |
| ruggers.py | the desk's own creator blacklist: a token that collapses (-90% at audit, or a pulled pool) blacklists its creator, and GARDE kills that wallet's next tokens |
| dashboard.py + .html | private dashboard: `python3 dashboard.py`, then http://localhost:8765 |
| data/ | checks.csv, trades.csv, positions.json, desk.log |

## Rules that are in the code
- A failed source is a SKIP. Null is not clean: a missing field kills the token.
- The desk never holds a wallet key. Live mode prints "SELL NOW in your wallet" / approval lines; you sign.
- Paper fills happen at the screen price. Real fills are worse. Treat paper PnL as a ceiling.

Not financial advice. Most memecoins go to zero; this filter removes obvious rugs, it does not create an edge.

## The filter, check by check

Rugcheck (the article's source) stopped resolving in October 2026. Facts now come from
the Solana chain itself and GoPlus, both free, no key.

| # | check | source | status |
|---|---|---|---|
| 1 | already rugged | pool checks (liquidity, pool gone) | indirect |
| 2 | mint authority open | chain + GoPlus | yes |
| 3 | freeze authority open | chain + GoPlus | yes |
| 4 | Token-2022 traps (permanent delegate, closable, transfer hook/fee, upgradable) | GoPlus | yes, replaces Rugcheck's danger flags |
| 5 | risk score | - | **not checked** (Rugcheck-only) |
| 6 | LP burned | chain, PumpSwap pools | yes for PumpSwap; other DEXes die as `lp_unverified` |
| 7 | top 10 wallets > 30% | GoPlus holders, pools excluded on chain | yes |
| 8 | dev wallet > 5% | creator read from the PumpSwap pool on chain, its balance via RPC | yes for PumpSwap; plus no single wallet > 5% |
| 9b | copycat | DexScreener search: a bigger token launched this week under the same ticker | the copy is killed |
| 9 | insiders / bundles | same SOL balance in 3+ top wallets; 5+ big wallets within 2% | heuristic, read the kills |
| 10-13 | depth, ticket share, age, sells | DexScreener | yes |
| 14 | X read | you (links in every PASS), or Grok if paid | manual by default |

Public RPC note: `api.mainnet-beta.solana.com` rate-limits hard. If you see `facts failed: ... 429`,
create a free RPC key (Helius or QuickNode) and paste its URL into `SOLANA_RPC` in config.py.

## Exits

No study gives the best exit for memecoins; the evidence is thin and partly conflicting. What it does support:

- volatility-adjusted trailing stops (LeBeau's Chandelier Exit, ATR x 3) over fixed-percent trails, to avoid noise exits:
  [volatilitybox](https://volatilitybox.com/research/volatility-adjusted-stop-losses/),
  [stratbase](https://stratbase.ai/en/blog/average-true-range-trailing-stop),
  [trendrider (counter-evidence)](https://trendrider.net/blog/stop-loss-strategies-crypto-trading-2026)
- the dump phase of a meme pump: >30% under the peak with volume below half of the pump's:
  [arXiv 2507.01963](https://arxiv.org/html/2507.01963v2)
- selling into strength in tiers, and leaving on a stall:
  [odin.tools](https://odin.tools/blog/pump-fun-autosell-take-profit-stop-loss-2026),
  [thrive](https://thrive.fi/blog/trading/memecoin-trading-strategy-risk-management-guide)

So `exits.py` runs that as the starting profile (liquidity, stop, ladder, lock, Chandelier trail, dump, stall, time),
VIGIE records every traded token's price path during the trade and 6 h after, and `exitlab.py` replays a dozen
alternative profiles on those real paths every 30 minutes. With `EXIT_AUTOTUNE`, the desk switches profile by itself
only when a candidate wins on both halves of at least 30 trades by a clear margin (data/exit_profile.json).

## Rug factories (Oct 19)

Two paper rugs in one day, FOMO (-$25) and Gemini (-$74), came from the same factory. Read on chain:
18 "Gemini" and 14 "FOMO" graduated within 24 h, each pumped for ~1 h by hundreds of fresh wallets buying
the same small bag ($4-9 swaps; FOMO's pool went from 67 to 503 SOL in a straight line), then sold in
one block (FOMO: slot 458785212, 505 SOL -> 87 SOL), every one ending at -95.7%. No wallet ever held
more than 0.05%, so no top-10 or bundle check could see it. The dump takes one block: no exit is fast
enough, the only defense is not buying. What the desk checks now:

| kill | what it reads | FOMO / Gemini | real runners (UHI, XBT, HOOT, KIBI, SPORE) |
|---|---|---|---|
| micro_trades | average swap over the last hour, 100+ swaps | $4-9 | $40-75 |
| serial_farm | 2+ older PumpSwap namesakes, dead, with bot-sized swaps | 13-17 | 0 (their copies came after them) |
| holder_farm | every holder (Helius DAS): biggest group of identical bags | hundreds x 0.046% | none |
| fake_cap / dead_volume | cap vs pool, pool turnover | | |
| stale_data | the pool's SOL read on chain vs DexScreener | | |

VIGIE also reads each PumpSwap position's pool vaults on chain every 20 s, so a drained pool is sold
on the next tick even when DexScreener lags or drops the pair. ECHO can answer SCAM (concrete evidence on
X): the desk sells at once.

## The team

A job is an agent only when it needs its own clock, its own failure domain or its own tools; the rest
are functions. Five pass the bar (PLUME, a scheduled report, is now AUDIT's job):

| agent | why it is separate | runs |
|---|---|---|
| VIGIE | the only latency-critical job: positions re-priced on chain every 20 s, whatever the others wait on | its own thread; restarted by the main loop if it dies, and it warns if the main loop stalls 5 min |
| SCOUT | cheap and broad, the funnel's first cut | every 3 min |
| GARDE | expensive and deep: checks, deep read, the buy (cost asymmetry with SCOUT) | per lead, + ECHO's reads every 30 s |
| ECHO | the only job that needs a model and a browser | its own Claude session |
| AUDIT | the slow learning loop and the reports | every 30 min, reports at 21:30 and 08:00 |

How they work as one (following "share context" and "one writer at a time"):
- **one book, one writer at a time**: book.LOCK around every buy and sale, so VIGIE's thread and GARDE
  can never overwrite each other; a sale on a position already closed is a no-op
- **a shared dossier per token** (dossier.py, data/dossiers/): SCOUT's source, GARDE's verdict and every
  measure, ECHO's read, VIGIE's sale, AUDIT's 6 h price. ECHO's queue carries GARDE's case in one line;
  the dashboard shows the dossier when you click a token
- **a rug reaches every agent** (agents.on_rug): holders remembered at once, creator and cluster funder
  blacklisted, and any other open position sharing 5+ holders or the funder is sold (contagion)

## Two lanes

| lane | what | sources | rules |
|---|---|---|---|
| early | launches, 15 min to 72 h, PumpSwap | pump.fun graduations on chain, DexScreener feeds | everything above, LP burn and creator verified on chain |
| momentum | survivors older than 72 h, any DEX | GeckoTerminal trending (5 min, 1 h), Jupiter top organic score (1 h), DexScreener boosts | pool $100k+, $300k+ a day, +3% over 1 h and not falling over 5 min, hourly volume 1.3x its 6 h average, buyers ahead, not past +80% in 1 h |

On Oct 19 afternoon BONK, POPCAT, Fartcoin, PNUT, GOAT, MOODENG, MEW, SPX and TROLL all sat within 1%
over the hour: a quiet day for survivors is a day the momentum lane buys nothing, by design.

Free sources: DexScreener, GeckoTerminal (~10 calls a minute, no key), GoPlus, pump.fun's migration
account, Jupiter (free key on its Developer Platform, JUPITER_KEY in .env; without it the old keyless
host), Helius (free RPC + DAS), Solana Tracker (free key, 2,500 a month, capped at 75 a day).

## The deep read (GARDE, last stage)

Only for tokens that passed everything above and score high enough to be bought, cheapest first.
Any source that fails or has no key is skipped: unknown is never a kill.

| step | source | kills |
|---|---|---|
| factory wallets | the desk's memory (smart.py + seeds/factory_wallets.json) | 5+ holders that held 2+ rugs and no winner |
| Jupiter | lite-api.jup.ag, free, no key | isSus, creator with 20+ launches, < 10% organic volume |
| funding clusters | your RPC (Helius) | 3+ top holders funded by one non-exchange wallet holding 10%+; 60%+ in fresh wallets; a funder from an earlier rug |
| Solana Tracker | data.solanatracker.io, key in .env as SOLANATRACKER_KEY (2,500 free requests) | rugged, bundlers > 15%, insiders > 15%, snipers > 25% |

Every value is logged in checks.csv with the verdict, so AUDIT can say within a week which cut kills
crashers and which kills winners. A rug (VIGIE) marks every holder wallet at once, and the cluster's funder.

Not wired: Bubblemaps (API keys come with its paid Pro plan), GMGN (no public API), RugCheck (dead).

## Backtest (Oct 19): what the history says

`python3 backtest.py 300` replays pump.fun graduations from the chain (pool reserves every 6 min for 7 h),
applies the pool rules and the active exit engine, with real costs (0.3% fee x2, 1% MEV x2, $0.50 tx x2:
about 5% of a $50 ticket per round trip). `BT_WINDOW=14,22` picks graduations 14-22 h old.

539 graduations, two windows, net return per trade, active exit:

| entry rule | n | mean | 95% CI | half 1 / half 2 |
|---|---|---|---|---|
| old desk (15 min + rules) | 38 | -22.4% | [-43.9, +1.4] | -19.5 / -25.0 |
| wait 30 min | 32 | -21.5% | [-44.9, +4.9] | -3.1 / -34.1 |
| wait 60 min | 20 | -4.9% | [-29.5, +23.5] | -21.2 / +8.5 |
| **desk now: 60 min + above graduation price** | 18 | +2.9% | [-21.0, +30.9] | -18.2 / +19.9 |

The old entry lost on both halves: it was removed. The new one roughly breaks even and its interval
holds zero: **no edge is proven.** With a ~72% standard deviation per trade, telling +5% from 0 takes
about 800 trades. Run the backtest again on your Mac (Helius key) to add data; trust nothing below 200.

## Overnight

`./start.sh` runs the desk and the dashboard, restarts either one 10 s after a crash, and keeps the Mac and
its screen awake while it runs (a screen that turns off is what locks the Mac). Every pause is logged and
shown in the journal and the morning brief, with macOS's reason. What can still stop the night, and what the desk does about it:

| what | effect | what the desk does |
|---|---|---|
| lid closed, or Mac on battery | macOS sleeps, everything pauses | start.sh warns on battery. `sudo pmset -a disablesleep 1` stops lid-close sleep (`0` to undo) |
| screen locks | Chrome, so ECHO, can stall | caffeinate -d keeps the screen on; in observe mode trading never waits for ECHO anyway |
| macOS update restart | everything stops | turn off automatic restarts for updates |
| a crash in the desk or the dashboard | one process dies | start.sh restarts it in 10 s, state is on disk |
| ECHO's session closes or hits its usage limit | no X reads | observe mode: trading goes on, the dashboard's ECHO card turns red. gate mode: after 45 min of silence, only PASSes scoring 75+ are bought, tagged NO_X |
| DexScreener or the RPC down | no prices / no facts | positions held and retried every 20 s; tokens skipped, retried later |
| public RPC rate limits (429) | some tokens skipped | a free Helius RPC URL in SOLANA_RPC removes most of them |

PLUME posts a morning brief at 08:00: what was bought, sold and killed overnight, and whether ECHO went silent.

## Real money

`edge.py` is the go-live gate, on the dashboard header and in every evening report. Real money only when:
at least 50 closed paper trades (costs included), the 95% bootstrap interval of the average trade is entirely
above zero, and the worst drawdown stayed under 30% of the bankroll. It then suggests a first ticket: a quarter
of the Kelly fraction, capped at 5% of the bankroll (and the 1% pool rule still applies).

Base rates, so the gate is not optional: ~74% of Solana memecoin buyers end with less SOL after fees, the
consistently profitable window is the first seconds after launch, which belongs to snipers
([Bitquery via Decrypt](https://decrypt.co/337157/solana-dex-traders-decline-meme-coin-scams)), and ~0.4% of
pump.fun wallets had realized more than $10k ([Dune via Cointelegraph](https://cointelegraph.com/news/pump-fun-crypto-traders-majority-do-not-realize-profits-dune-data)).
