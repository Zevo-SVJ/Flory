# config.py
# every number on the desk lives here. when you retune, you edit this file and nothing else.
import os

HERE = os.path.dirname(os.path.abspath(__file__))

PAPER = True                # week one: fake fills at real prices. flip only after you read the log

# the judge (check 14). "none" = free, code-only desk: 13 checks, no X read.
# "grok" = one paid xAI call per survivor, with X search. needs XAI_API_KEY in .env.
JUDGE = "none"
MODEL = "grok-4.7"          # only used when JUDGE = "grok". check console.x.ai -> Models
GROK_MAX_TURNS = 2          # two rounds of X search, then it has to answer
MIN_CONFIDENCE = 0.7        # Grok says BUY below this -> treated as SKIP

# JUDGE = "none" only: a token that passes all 13 checks gets verdict PASS.
# in paper mode, True paper-buys every PASS so a week of trades.csv measures the filter alone.
PAPER_BUY_ON_PASS = True

# ECHO, the X reader (Claude in Chrome, its own session, instructions in ECHO.md).
#   "gate":    a PASS waits in data/pending.json until ECHO reads X. BUY -> the desk buys, SKIP -> dropped.
#              AUDIT still re-prices the skipped ones, so you learn what the X read was worth.
#   "observe": every PASS is bought at once, ECHO still reads it and its verdict is recorded next to the
#              trade. the dashboard then shows the P&L of ECHO's BUYs vs its SKIPs: what the X read is worth.
# observe in paper: a closed Chrome or a locked screen no longer stops the desk from trading, and every
# PASS becomes a data point. go back to "gate" only once the BUY group clearly beats the SKIP group.
ECHO_MODE = "observe"
ECHO_TIMEOUT_MIN = 60       # no X read after this long -> the PASS is dropped, never bought blind
# paper only: when ECHO itself has gone silent (session closed, usage limit, Mac asleep), the desk keeps
# learning overnight instead of freezing: a PASS this strong is bought without the X read, tagged
# "no X", and AUDIT keeps those trades apart. never used in live mode.
ECHO_SILENT_MIN = 45        # no X read written at all for this long -> ECHO counts as silent
ECHO_FALLBACK_SCORE = 75    # only PASSes scoring at least this are bought while ECHO is silent

# SCORE: how organic a PASS looks (0-100), the way a human would rank survivors. see score.py
MIN_SCORE = 55              # below this a PASS is not bought (still audited)

# training mode: paper money, so the desk takes every token the filter lets through, bounded by
# cash. more trades = more data about the filter. the live numbers go back down before real money.
PAPER_BANKROLL_USD = 1000   # fake starting balance. a new entry needs TICKET_USD of free cash
TICKET_USD = 25             # flat. never sized off the last win
MAX_OPEN = 40               # safety net only: cash runs out first (1000 / 25 = 40)
MAX_ENTRIES_PER_DAY = 40
DAILY_LOSS_HALT_USD = 250   # realized loss today hits this -> no new entries until tomorrow
COOLDOWN_HOURS = 24         # no re-entry into a token you just left
# paper fills pay what a real fill pays, so paper profit is not a fantasy: the pool fee, the price
# impact of a $25 order on the pool (constant-product AMM: ~ order / half the liquidity), and a fixed
# network + priority fee per transaction. a live fill can still be worse (latency, MEV): paper stays a ceiling.
PAPER_COSTS = {"fee_pct": 0.3, "tx_usd": 0.05}
MEGA_PROFIT_PCT = 50        # a sale this far in profit fires the dashboard's MEGA PROFIT card

SOLANA_RPC = "https://api.mainnet-beta.solana.com"   # free public RPC. a free Helius/QuickNode URL also works

FACTS = {                   # the rug filter. code only, no model
    "min_lp_locked_pct": 90,    # biggest pool: LP burned, read on chain. only PumpSwap pools can be
                                # verified for now; any other DEX dies as lp_unverified
    "max_top10_pct": 30,        # top 10 holder wallets, pools and lockers excluded
    "max_dev_pct": 5,           # supply still sitting in the creator wallet (read from the PumpSwap pool)
    "max_wallet_pct": 5,        # no single wallet over this, whoever owns it
    "bundle_same_sol": 3,       # this many top wallets with the exact same SOL balance -> funded together
    "bundle_ladder": 5,         # this many big wallets with bags within 2% of each other -> one hand
    "ladder_min_pct": 0.5,      # a wallet counts in the ladder only above this % of supply
    "min_liquidity_usd": 30000,
    "max_ticket_share": 0.01,   # your ticket is never more than 1% of the pool
    "min_age_min": 30,          # younger than this, every report is still guessing
    "max_age_hours": 72,
}

# exits. no study gives "the" best exit for memecoins (see README, "Exits"), so this is the starting
# profile and the exit lab (exitlab.py) replays alternatives on your own recorded price paths.
EXIT = {
    "liq_drop_pct": 40,                     # pool liquidity down 40% from entry -> out now, always first
    "stop_pct": -35,                        # hard stop from entry
    "ladder": [(100, 0.50), (200, 0.25)],   # +100% sells half, +200% sells a quarter
    "lock_after_pct": 40,                   # once the peak was +40%, a winner may not turn into a loser:
    "lock_floor_pct": 5,                    #   the floor moves to entry +5%
    "arm_pct": 40,                          # the trailing stop arms at a +40% peak (or the first take)
    "trail": "chandelier",                  # "chandelier": k x volatility from the peak; "fixed": trail_pct
    "trail_k": 3,                           # LeBeau's default multiplier
    "trail_min_pct": 15,                    # a calm token still gets 15% of room
    "trail_max_pct": 40,                    # a wild one never more than 40%
    "trail_pct": 30,                        # the fixed trail, and the fallback before there is enough history
    "dump_drop_pct": 30,                    # the textbook dump: price 30% under the peak...
    "dump_volume_ratio": 0.5,               # ...and 5-min volume under half its average of the last hour -> out
    "stall_min": 45,                        # in profit but no new high for 45 min...
    "stall_min_pct": 15,                    # ...while up at least 15%...
    "stall_sell_ratio": 1.5,                # ...and sellers outnumber buyers 1.5:1 over 5 min -> take it
    "time_stop_hours": 6,                   # not up 20% after 6 hours -> out, dead money
    "time_stop_min_pct": 20,
}
EXIT_AUTOTUNE = True        # the lab may switch profiles by itself, only past the bar in exitlab.py

SCHEDULE = {                # used by agents.py: one entry per agent
    "vigie_every_s": 20,        # VIGIE: prices every open position, applies exits, logs the balance
    "scout_every_min": 10,      # SCOUT: pulls fresh leads, GARDE checks each one
    "scan_per_run": 15,         # leads per SCOUT run that reach GARDE (thin pools never count)
    "audit_every_min": 30,      # AUDIT: re-prices old verdicts to see if the filter was right
    "audit_after_hours": 6,
    "report_at": "21:30",       # PLUME: evening report, local time
    "morning_at": "08:00",      # PLUME: what happened overnight, local time
}

DATA = os.environ.get("RUG_DESK_DATA") or os.path.join(HERE, "data")
LOG = os.path.join(DATA, "checks.csv")
POSITIONS = os.path.join(DATA, "positions.json")
TRADES = os.path.join(DATA, "trades.csv")
EVENTS = os.path.join(DATA, "events.jsonl")
AGENTS = os.path.join(DATA, "agents.json")
EQUITY = os.path.join(DATA, "equity.csv")
AUDIT = os.path.join(DATA, "audit.csv")
PATHS = os.path.join(DATA, "paths")          # one price path per traded token, for the exit lab
