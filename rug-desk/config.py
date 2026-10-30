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
TICKET_USD = 25             # the smallest ticket. the real size comes from SIZING below
# paper sizing, as % of the balance (bankroll + realized). size.py picks the tier from 6 measured signals.
# aggressive on purpose: paper money, more signal per trade. a 10-loss streak at ~7% x -35% is ~ -25%.
# flat since Oct 19 23:45: the "strong" tickets (8%) lost $109 over 8 trades (-20% each, Gemini's rug at
# $77 among them) while "base" (4%) made +$15 over 7; scores 80+ predicted nothing (FOMO, RAETO, hi).
# bigger tickets on signals nobody has validated only enlarge the losses. raise strong/max again once
# AUDIT's tier breakdown shows the signals earn more, on enough trades
SIZING = {"base": 4, "strong": 4, "max": 4,
          # Oct 28: the "strong" and "max" tiers are no longer bought at all. three looks agree: Oct 19 -$109 over
          # 8 trades, Oct 20-27 -$158 over 20 (base +$170 over 31), shadow replay -10% per token over 12 (base
          # +21% over 21). 2+ heat signals mark a token already at the top of its hype (LMAO: score 100).
          # the skipped ones are followed in shadow ("hot_signals"): the report says if the skip costs money
          "skip_hot": True,
          "score_strong": 75, "score_max": 85,  # score thresholds that count as a signal
          "turnover_hot": 1.0,                  # 1 h volume >= the pool's liquidity
          "organic_avg_trade": 30,              # activity counts only if the average swap is $30+
          # paper only: a token that passed every anti-rug check but scored under MIN_SCORE is bought
          # small, in its own tier. on Oct 19 the score's bot-volume cap held 18 of 23 full passes at 40,
          # and the passes bought on a good score were at -28% median 6 h later: whether the score
          # picks anything is the open question, and small paper trades answer it fastest
          # OFF since Oct 19 23:30: AUDIT's 6 h re-price had the full passes scored under 55 at -85% median,
          # 75% of them down 50% or more (n=8), against -16% for those scored 55+ (n=11). the score protects.
          # the floor above MIN_SCORE switches the tier off; lower it to test again
          "explore": 2, "explore_min_score": 101,
          # Oct 30: tokens killed only for an unlocked LP, replayed in shadow: Robinhood +16.2% a trade over 212
          # (both halves +9.9 / +22.5, 42% winners), BSC -6.6% over 32. on Robinhood Chain the launchpads
          # leave the LP unlocked and a pull shows in the replay (pool drained, sold at what is left). those
          # tokens are now bought small, every other check and the score still applying, only while the
          # shadow book keeps the case: shadow.lp_open_ok() (n, mean without its 5 best, both halves)
          "lp_open": 2}
LP_OPEN = {"chains": ("robinhood",), "min_n": 100, "drop_best": 5}   # paper only: live.py trades BSC alone
MAX_OPEN = 40               # safety net only: cash runs out first (1000 / 25 = 40)
MAX_ENTRIES_PER_DAY = 40
DAILY_LOSS_HALT_USD = 250   # realized loss today hits this -> no new entries until tomorrow
COOLDOWN_HOURS = 24         # no re-entry into a token you just left
# paper fills pay what a real fill pays, so paper profit is not a fantasy: the pool fee, the price
# impact of a $25 order on the pool (constant-product AMM: ~ order / half the liquidity), and a fixed
# network + priority fee per transaction. a live fill can still be worse (latency, MEV): paper stays a ceiling.
# real-world numbers (Oct 2026): a memecoin swap that lands pays a priority fee plus a Jito tip, ~0.001-0.005 SOL
# (~$0.20-1); 96% of Solana sandwich attacks hit pump.fun/PumpSwap tokens (Bitquery, 6.85M sandwiches in
# a year), so each side also pays ~1% to slippage and MEV even with a tight slippage limit. paper must
# not look better than a real wallet would.
PAPER_COSTS = {"fee_pct": 0.3, "tx_usd": 0.50, "mev_pct": 1.0}
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
    "farm_wallets": 15,         # this many holders with the same bag (within 1%)...
    "farm_pct": 3,              # ...holding this % of supply together -> holder_farm (Helius only)
    "min_liquidity_usd": 15000, # the live graduates that ran on Oct 19 (KIBI, SPORE, Mimi) had $20-30k pools
    "soft_liq_floor_usd": 8000, # thin_pool's floor if the shadow book ever waives it: never under this
    "shadow_pool_per_run": 4,   # SCOUT follows this many pool-rule kills per run in shadow (6 h each)
    "shadow_max_ghosts": 500,   # ...while VIGIE prices fewer ghosts than this
    "max_ticket_share": 0.02,   # your ticket is never more than 2% of the pool (~2% price impact)
    # backtest on 523 graduations (backtest.py, two separate windows on Oct 19): entering at 15 min with the
    # pool rules lost -20.7% a trade (median -46%), on both windows. waiting 60 min and buying only above
    # the graduation price was the one variant near break-even (+2.9%, n=18): the first hour is where
    # snipers, devs and factories dump. it limits losses; it does not prove an edge
    "min_age_min": 60,
    "max_drop_1h_pct": 50,      # a launch already down 50%+ in the last hour is collapsing: buying it is
                                # buying the exits of those dumping (LMAO, Oct 27: -61.9% in the hour before
                                # entry, score 100, then -58% one minute after the buy). shadowed like every kill
    "min_vs_graduation": 1.0,   # early lane: price must be at least this x the pool's price at graduation
    "max_fixed_cost_pct": 5,    # gas paid twice may eat at most this % of the base ticket (kills Ethereum at $25)
    # fake caps: on Oct 19, 20 of 33 graduates with a "real" pool were clones ("US Oil Exchange",
    # "National Oil Dividend Fund", "Ripple USD") showing $10M-$600M caps on $0.2-2M pools that trade
    # ~1% of their pool an hour. the tokens that really ran sat at caps 3-9x their pool, turnover 0.5-15x
    "max_mcap_liq": 12,         # market cap / pool liquidity above this -> fake_cap
    "min_avg_trade_usd": 15,    # 100+ swaps in the hour averaging under this -> micro_trades (bot farm)
    "min_turnover_1h": 0.05,    # a pool that trades under 5% of its size an hour -> dead_volume (the clones: ~1%)
    "max_age_hours": 72,
}

# MOMENTUM: the second lane. tokens older than max_age_hours are not launches any more: they survived.
# they are bought on momentum, not on youth: rising now, on rising volume, with buyers ahead, without
# chasing a vertical candle. a survivor's pool is deep, so its rug risk is lower and its moves are
# tradeable; its LP may sit on Raydium or Meteora, where the desk can't verify a burn, so the pool must
# be deep and old instead. leads come from GeckoTerminal's trending pools and DexScreener's boosts.
MOMENTUM = {
    "min_liq_usd": 100000,      # a survivor's pool
    "min_vol_24h": 300000,
    "min_chg_1h": 3,            # rising over the hour...
    "min_chg_5m": -2,           # ...and not rolling over right now
    "vol_accel": 1.3,           # the last hour's volume >= 1.3x the hourly average of the last 6 h
    "max_chg_1h": 80,           # past this the candle is vertical: buying it is buying someone's exit
    "max_chg_24h": 400,
    "max_top10_pct": 40,        # established tokens carry exchange and team wallets
    "max_wallet_pct": 8,
    "max_mcap_liq": 60,         # a survivor's cap runs 10-50x its pool; the Oct 19 clones ran 150-300x
}

# the deep read, for tokens that passed every check above (jup.py, cluster.py, stracker.py).
# thresholds are first guesses from the sources named in each file: every value is logged with the
# verdict, so AUDIT can tell within a week which ones kill crashers and which ones kill winners.
DEEP = {
    "max_factory_wallets": 5,       # holders that held 2+ earlier rugs and no winner (smart.py) -> factory_wallets
    "max_dev_mints": 20,            # Jupiter: the creator launched this many tokens -> serial_dev
    "min_organic_vol_share": 10,    # Jupiter: under 10% of the hour's volume organic, 50+ traders -> inorganic_volume
    "min_organic_score": 0,         # Jupiter organicScore: logged only until AUDIT shows a useful cut
    "max_cluster_pct": 10,          # 3+ top holders funded by one (non-exchange) wallet, 10%+ of supply
    "max_fresh_pct": 60,            # top holders in wallets under 100 transactions old
    "max_bundlers_pct": 15,         # Solana Tracker: supply still held by launch-bundle wallets
    "max_insiders_pct": 15,         # Solana Tracker: supply held by wallets linked to the creator
    "max_snipers_pct": 25,          # Solana Tracker: supply held by first-block buyers
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
# a chain whose tokens behave apart gets its own exits. Oct 28: on 322 replayed pump.fun graduations the
# config exits (stop -35%, early ladder, lock, trail, 6 h clock) beat "regles B" for every one of the 11
# entry rules on the same tokens, by 3 to 24 points per trade: Solana graduates that fall keep falling,
# so B's -50% stop and 24 h patience cost money there. B stays for the other chains (+$134 vs +$22)
EXIT_BY_CHAIN = {"solana": "config"}
EXIT_AUTOTUNE = False       # since Oct 20 VIGIE's self-review switches profiles (reviews.py, coach.py): it learns
                            # from every shadowed token, ten times the trades, under stricter guards

SCHEDULE = {                # used by agents.py: one entry per agent
    "vigie_every_s": 20,        # VIGIE: prices every open position, applies exits, logs the balance
    "scout_every_min": 3,       # SCOUT: pulls fresh leads (pump.fun graduations first), GARDE checks each one
    "scan_per_run": 15,         # leads per SCOUT run that reach GARDE (thin pools never count)
    "audit_every_min": 30,      # AUDIT: re-prices old verdicts to see if the filter was right
    "audit_after_hours": 6,
    "report_at": "21:30",       # PLUME: evening report, local time
    "morning_at": "08:00",      # PLUME: what happened overnight, local time
    # the cumulative backtest (backtest.py --accumulate), started by AUDIT in a child process.
    # each run: fresh pump.fun graduations replayed from the chain (Helius only, ~50 calls each) and the
    # momentum sightings old enough to be judged (GeckoTerminal, free)
    "backtest_every_h": 6,
    "backtest_n": 40,           # graduations per run: ~3% of them are entries under the current rule
    "backtest_momentum_n": 40,
    "trend_every_min": 5,       # TREND: the majors book (majors.py), prices topped up every 15 min
}

# the rules the real-money decision judges: every trade opened before this ran under rules that no longer
# exist (15 min entry, Solana only, the copycat bug, no explore tier). they stay in the files and in the
# all-time lines of the reports; the go-live gate, the projection and the review count only these
RULES_SINCE = "2026-10-20 00:00"     # Oct 19 23:45: no sale on an ECHO SKIP, explore tier off, flat tickets

# REAL MONEY (live.py). the paper desk keeps deciding everything; live.py copies its buys and sells on these
# chains into a dedicated wallet whose key is in .env (LIVE_KEY, made by `python3 live.py new-wallet`).
# LIVE=off|dry|on in .env: dry quotes every order on the real chain without sending anything.
# every number below is a hard cap the code checks before signing anything
LIVE = {
    "chains": ("bsc",),         # BNB Chain only: the best paper chain (8 trades, +33.7%), gas in cents
    "ticket_usd": 13,           # one real buy (about 12 EUR), whatever the paper ticket was
    "max_tx_usd": 20,           # a buy above this is refused: a bug never spends more than this at once
    "max_open": 3,              # real positions at once; the paper desk keeps all of its own
    "max_buys_day": 8,          # a loop that buys again and again stops here
    "stop_pct": -30,            # wallet value 30% under its start: no more buys, sells go on, alert
    "gas_reserve_usd": 1.0,     # BNB always kept for the sells
    "slippage_bps": 1000,       # 10% on a buy
    "sell_slippage_bps": 1500,  # 15% on a sell; 20% (KyberSwap's cap) on the retry and on a rug exit
    "max_sell_tax_pct": 10,     # honeypot.is: a token taxing sells above this is never bought for real
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

# snipelab.py, the dry sniper (Oct 28): nothing is bought, it measures what sniping pump.fun launches would
# earn at the speed this desk can reach. the rule (min_n entries, interval above 0, both halves) is in the file
SNIPE = {
    "latency_s": 2,             # our entry: the first trade at least 2 s after we saw the launch (never block 0)
    "follow_min": 30,           # each followed launch is watched for 30 min, then replayed with the Solana exits
    "sample_every": 5,          # 1 launch in 5 that pass the launch filters is followed (thousands launch a day)
    "max_tracked": 40,          # at most this many followed at once on the one websocket
    "max_dev_buy_pct": 10,      # the creator bought more than 10% of the supply in its launch -> skipped
    "ticket_sol": 0.25,
    "curve_fee_pct": 1.25,      # pump.fun's bonding-curve fee, each side
    "tip_sol": 0.001,           # a Jito tip / priority fee, each side
    "min_n": 300,
}
