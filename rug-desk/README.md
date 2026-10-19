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
