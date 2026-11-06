# seeds

`factory_wallets.json`: 129 wallets that sold in the one-block dumps of FOMO (4cxTftMa…, Oct 19 2026,
slot 458785212) and Gemini (7f5ko3QH…). The same wallets traded Apple, MrBeast, NVIDIA, Gemini, Hermès
and GTA 6 Coin tokens that all ended at ~$1,880 of liquidity: one factory, one reused wallet pool.
smart.py counts each as a wallet with two rugs; 5 of them among a token's holders kill it.
Rebuilt by hand from chain data; the desk adds its own on every rug (data/smart.json).

`backtest_oct19.jsonl`: 518 pump.fun graduations of Oct 18-19 2026 replayed from the chain by
backtest.py (pool price every 6 min for 7 h, average swap size at 15/30/60/120 min). The desk's
cumulative backtest starts from these; every automatic run adds fresh graduations to
data/backtest_rows.jsonl, so the sample grows without reading these pools again.
