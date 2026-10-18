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
    python run.py                             # the desk: watch 10m, scan 30m, report 21:30

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
| scan.py | leads: fresh Solana tokens with a paid DexScreener profile |
| report.py | evening report from the CSVs |
| run.py | scheduler (replaces Grok Bot routines) |
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
| 8 | dev wallet > 5% | any single wallet > 5% | stricter stand-in: the dev can't be named |
| 9 | insiders / bundles | same SOL balance in 3+ top wallets; 5+ big wallets within 2% | heuristic, read the kills |
| 10-13 | depth, ticket share, age, sells | DexScreener | yes |
| 14 | X read | you (links in every PASS), or Grok if paid | manual by default |

Public RPC note: `api.mainnet-beta.solana.com` rate-limits hard. If you see `facts failed: ... 429`,
create a free RPC key (Helius or QuickNode) and paste its URL into `SOLANA_RPC` in config.py.
