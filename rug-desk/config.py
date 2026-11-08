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
          "lp_open": 2, "closed_bsc": 2}
LP_OPEN = {"chains": ("robinhood", "base"), "min_n": 100, "drop_best": 5}   # paper only: live.py trades BSC alone
# Nov 8: base joins as a candidate (lp_unlocked on base: n=16, +32.6%, median +20.4%, 81% won). it opens by
# itself only once shadow.lp_open_ok("base") holds: 100+ tokens, positive without the 5 best, both halves.
# BSC stays out: lp_unlocked there is -23.3% over 93
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
    # ...plus this many launches under min_age_min on fresh_chains. 0 since Nov 2: buying them lost on BSC
    # (-70.1% a trade, n 172) and on Robinhood (-7.9%, n 344): the 60 min rule stays (diag --entree)
    "shadow_fresh_per_run": 0,
    "fresh_chains": ("robinhood", "bsc"),
    "study_per_run": 3,         # ...and GARDE runs its other checks on this many of them, for the data only
                                # (check.study: never bought, written to study.csv, read by learn.py)
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
    # Nov 1 (diag --profil, every shadow token replayed with the desk's exits and costs): on the EVM chains a
    # launch whose cap is 4-12x its pool lost on BSC (-13.1% a trade, n 69, halves -21.1/-5.4, -19.6 without
    # its top 3) and on Robinhood (-7.2%, n 69, halves -5.6/-8.8, -16.1 without its top 3): the same on two
    # chains and both halves. the lower ratios held up better. the shadow sample keeps following fake_cap,
    # so the soft-rule waiver lifts this if it turns out wrong
    "max_mcap_liq_evm": 4,
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
# chains whose tokens GARDE still judges and the shadow book still follows, but the paper desk no longer buys.
# Oct 31, Skide's call: Solana after graduation was 0 wins in 4 trades under the rules in force (-$121: fone,
# HOTBOT, LMAO, iCat -99.7% dumped by a wallet farm), and every Solana group in the shadow book loses. its
# passes stay shadowed as "pass" (diag.py --entonnoir, PAR CHAÎNE): they say when to buy there again.
# Solana launches themselves are tested by the dry sniper (snipelab.py)
# a chain here buys again by itself as soon as its shadowed passes pay: shadow.chain_ok() (20+, positive on
# average and without the 3 best, both halves), and stops again when they no longer do
NO_BUY_CHAINS = ("solana",)
# a chain whose tokens behave apart gets its own exits. Oct 28: on 322 replayed pump.fun graduations the
# config exits (stop -35%, early ladder, lock, trail, 6 h clock) beat "regles B" for every one of the 11
# entry rules on the same tokens, by 3 to 24 points per trade: Solana graduates that fall keep falling,
# so B's -50% stop and 24 h patience cost money there. B stays for the other chains (+$134 vs +$22)
EXIT_BY_CHAIN = {"solana": "config"}
EXIT_AUTOTUNE = False       # since Oct 20 VIGIE's self-review switches profiles (reviews.py, coach.py): it learns
                            # from every shadowed token, ten times the trades, under stricter guards

# events whose date is known in advance: SCOUT searches their words on DexScreener every run while the window
# is open, and tags what it finds with the event's name (its own line in SCOUT's source ranking and in the
# shadow book). nothing is loosened: the copies die on copycat and serial_farm, the insiders on dev_holds and
# top10 (GTAVI, Aug 2026: $25M cap on leaked footage, the leaker sold hours before Rockstar's reveal)
EVENT_WATCH = {
    # opened Nov 2, not Nov 12: Skide's screenshots that evening showed the run already on (GTA6 +3,459% to
    # $12.9M, GTA6CAT +3,328% to $10.7M, CYBERLEEK, Dacity), 17 days before the release
    # sell_by: every position bought for the event is sold by then, whatever its exits say. event coins top
    # out on the eve and fall on the day ("sell the news"): $TRUMP peaked the day before the inauguration,
    # then -50% after it and -75% in two weeks; GTAVI's own creator sold hours before Rockstar's reveal
    "GTA VI": {"from": "2026-11-02", "to": "2026-11-30", "sell_by": "2026-11-19 06:00",   # release Nov 19
               "words": ["gta", "gtavi", "gta6", "vicecity", "vice city", "lucia", "leonida", "rockstar", "cyberleek"],
               # a found pair counts only if its name or symbol carries one of these: on Nov 3 the search
               # word "vice" brought AMD, SU, Ryzen (an AMD run, nothing to do with GTA): $4.5M of the
               # $5.3M "GTA heat" that night, and they would have been bought as GTA tokens
               "match": ["gta", "vicecity", "vice city", "leonida", "lucia", "rockstar", "cyberleek"]},
}
# a token found by an event's search may be bought on any chain, NO_BUY_CHAINS included, in its own small
# tier ("event", % of the balance), every check still applying: an event is another population than the
# chain's everyday launches, and the paper desk is where to learn what it is worth
EVENT_TIER_PCT = 2
# Nov 8 checkpoint: a base-tier token under 3 h old is not bought. real trades: < 3 h -$137 over 19 (32% won),
# 3-12 h +$73 over 11; shadow book: < 3 h -4.1% over 7802 tokens, 3-12 h -0.8%, 12-36 h +1.8%, > 36 h +1.7%.
# lp_open (bought on confirmation: FLORA was 2 h old, +16.7%) and the event tier keep their own rules.
# the skipped ones are shadowed as "young_base": the shadow book lifts the rule by itself if they pay
# (20+, +5% a trade, both halves, above the noise), like any soft rule
BASE_MIN_AGE_MIN = 180
# Nov 8: BSC tokens killed only for an unpublished contract (GoPlus "closed_source", no other danger), pool
# $15-150k: 65 shadowed, +63.7% mean, median +30%, +38.3% without the 5 best, halves +60 / +67, and all 65
# sellable with a sell tax <= 10% when honeypot.is simulated a buy and a sale. the likely reason: BSC launchpad
# tokens come from a factory and are not verified one by one, so GoPlus reads them as closed source.
# they are bought small, in their own tier, past the score / age / heat gates (the shadow population had
# none), only once honeypot.is says they sell at a tax <= LIVE max_sell_tax_pct at the moment of the buy.
# judged on its own real trades at each checkpoint: stopped (on=False) if 20+ of them average below zero
CLOSED_BSC = {"on": True, "chains": ("bsc",), "min_liq": 15000, "max_liq": 150000}
# Nov 3, Skide: 95% of the GTA tokens are copies and rugs, the few clean ones with real holders run far.
# three things, paper only, every check still applying:
# 1. a GTA token GARDE turned down for a state that can mend (holders too concentrated, no momentum yet,
#    a thin pool, a low score...) is checked again every EVENT_RETRY_MIN while the window is open: the
#    holders of the good one settle in after the first hour. a hard kill (honeypot, copycat, serial farm,
#    a dev who rugged before, an X scam) stays final
EVENT_RETRY_MIN = 45
EVENT_PER_RUN = 5           # of SCOUT's scan_per_run slots, the event's tokens take up to this many first
EVENT_RETRY = ("top10_heavy", "no_momentum", "dead_volume", "micro_trades", "fake_cap", "whale", "falling_knife",
               "overextended", "stale_data", "thin_pool", "too_fresh", "no_pool", "no_price", "no_holders",
               "below_graduation", "funded_cluster", "dev_holds")
# 2. the heat of the event: the 1 h volume of every pair its words find on DexScreener, read every SCOUT run.
#    a news (a Rockstar post, a trailer, a leak) shows there first, before a token stands out: when the heat
#    is ratio x its median of the last 24 h (and at least min_usd), SCOUT re-checks every event token at once
#    and Telegram says so. ECHO adds what it reads on X (data/event_news.txt, ECHO.md)
EVENT_HEAT = {"ratio": 3.0, "min_usd": 200000, "min_readings": 20, "alert_every_h": 2}
# 3. a GTA position that proves itself is held for the event instead of hours: once it took its first profit
#    (+100%), after an hour held, with its pool 1.5x what it was at the buy and buyers still ahead over 5 min,
#    the rest switches to these exits: more profit at x5 and x10, a 40% trail from the peak, a floor at +50%,
#    no clock, and everything out by the event's sell_by
EVENT_RUNNER = {"min_hours": 1, "liq_mult": 1.5}
EVENT_RUNNER_EXIT = {"ladder": [(100, 0.50), (400, 0.15), (900, 0.15)], "trail": "fixed", "trail_pct": 40,
                     "lock_after_pct": 100, "lock_floor_pct": 50, "stall_min": 10 ** 9, "dump_drop_pct": 100,
                     "fade_ratio": None, "time_stop_hours": 10 ** 9}

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
