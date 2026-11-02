# texts.py
# everything the bot says, in French and in English (Telegram's language_code: "fr..." gets French, the rest
# English). the French flag labels are the desk's own (tgbot.LABELS), read, never changed.

EN = {
    "mint_open": "the creator can still print tokens (mint authority open)",
    "freeze_open": "the creator can freeze your wallet (freeze authority open)",
    "lp_unlocked": "the liquidity is not burned: it can be pulled",
    "dev_holds": "the dev holds more than 5% of the supply",
    "dev_rugged_before": "this dev already has a token that collapsed (blacklist)",
    "top10_heavy": "the top 10 holders own too much of the supply",
    "whale": "a single wallet holds more than 5%",
    "bundle_same_sol": "bundle: holders with the exact same SOL balance",
    "bundle_ladder": "bundle: identical token bags",
    "holder_farm": "wallet farm: hundreds of identical bags",
    "fake_cap": "market cap inflated against a tiny pool",
    "micro_trades": "bot volume: average trades of a few dollars",
    "nobody_can_sell": "likely honeypot: buys, no sells",
    "hot_signals": "already at the top of its hype: such buys lost every time",
    "falling_knife": "already down 50%+ in the last hour",
    "serial_farm": "name recycled by a rug factory (dead namesakes)",
    "copycat": "copy of a bigger, active ticker",
    "factory_wallets": "wallets known from rug factories hold this token",
    "jup_sus": "Jupiter flags it as suspicious",
    "serial_dev": "serial launcher dev (dozens of tokens)",
    "inorganic_volume": "inorganic volume according to Jupiter",
    "low_organic": "low Jupiter organic score",
    "rug_funder": "holders funded by a wallet already tied to a rug",
    "funded_cluster": "one wallet funded a large share of the holders",
    "fresh_wallets": "holders are mostly brand-new wallets",
    "lp_unverified": "liquidity cannot be verified",
    "dev_unknown": "creator not found",
    "no_holders": "holders unreadable",
    "fees_eat_ticket": "network fees too heavy for a small ticket",
    "danger:honeypot": "HONEYPOT: you can buy, not sell",
    "danger:high_tax": "buy or sell tax above 10%",
    "danger:cannot_sell_all": "you cannot sell everything",
    "danger:cannot_buy": "buying blocked by the contract",
    "danger:hidden_owner": "hidden owner in the contract",
    "danger:selfdestruct": "the contract can self-destruct",
    "danger:tax_modifiable": "the owner can change the tax",
    "danger:tax_per_wallet": "tax adjustable wallet by wallet",
    "danger:trading_cooldown": "forced delay between two trades",
    "danger:creator_made_honeypots": "this creator already made honeypots",
    "danger:closed_source": "contract source code not published",
}
NOTES_EN = {"fake_cap": "market cap far above its biggest pool's liquidity",
            "whale": "one wallet holds more than 5% (often an exchange)",
            "top10_heavy": "concentrated top 10 (often exchanges)"}

S = {
    "fr": {
        "head": {"red": "🔴 RISQUE ÉLEVÉ", "yellow": "🟡 INCERTAIN", "green": "🟢 aucun signal d'usine à rug détecté"},
        "green_note": "Pas de piège trouvé : ça ne dit rien du prix de demain.",
        "notes": "À savoir (token établi, pas un signal de rug) : ",
        "pool": "pool {} k$", "age_m": "âge {} min", "age_h": "âge {} h", "age_d": "âge {} j", "top10": "top 10 {} %",
        "chain": "chaîne : {}",
        "start": ("🛡 Anti-Rug : colle l'adresse (CA) d'un token et je te dis en quelques secondes s'il ressemble à "
                  "une arnaque.\n\nJe lis le contrat (honeypot, taxes, mint, freeze), les holders (bundles, fermes de "
                  "wallets, devs déjà blacklistés) et la liquidité. Solana, BNB Chain, Base, Ethereum, Robinhood Chain "
                  "et d'autres.\n\nGratuit : {free} lectures par jour. Illimité : /pro\n\n"
                  "Lecture automatique, elle peut se tromper. Pas un conseil financier."),
        "quota": ("Tu as utilisé tes {free} lectures gratuites du jour.\n\n"
                  "Passe en Pro pour des lectures illimitées pendant {days} jours : /pro"),
        "rate": "Limite : {n} lectures par heure. Réessaie dans quelques minutes.",
        "cap": "Le bot a atteint sa limite du jour. Réessaie demain.",
        "error": "{ca}… : lecture impossible ({e}). Est-ce bien l'adresse d'un token ?",
        "left": "\n\n{n} lecture(s) gratuite(s) restante(s) aujourd'hui · illimité : /pro",
        "thanks": "✅ Merci ! Pro actif jusqu'au {until}. Colle autant de CA que tu veux.",
        "status_pro": "Pro actif jusqu'au {until}.",
        "status_free": "Gratuit : {used}/{free} lectures utilisées aujourd'hui. Illimité : /pro",
        "terms": ("Conditions\n• Le bot lit des données publiques (blockchain, DexScreener, RugCheck, GoPlus…) et "
                  "applique des règles automatiques. Il peut se tromper : un token « vert » peut chuter, un « rouge » "
                  "peut monter.\n• Ce n'est pas un conseil financier. Tu es seul responsable de tes trades.\n"
                  "• Pro : accès illimité pendant {days} jours à partir du paiement, sans renouvellement automatique.\n"
                  "• Remboursement : sur demande via /paysupport dans les 48 h si le service n'a pas fonctionné."),
        "support": "Un souci avec un paiement ? Écris ici ce qui s'est passé (date, montant) : on te répond et on "
                   "rembourse si le service n'a pas fonctionné.",
        "support_ok": "Message transmis. On revient vers toi rapidement.",
    },
    "en": {
        "head": {"red": "🔴 HIGH RISK", "yellow": "🟡 UNCERTAIN", "green": "🟢 no rug-factory signal found"},
        "green_note": "No trap found: that says nothing about tomorrow's price.",
        "notes": "Good to know (established token, not a rug signal): ",
        "pool": "pool ${}k", "age_m": "age {} min", "age_h": "age {} h", "age_d": "age {} d", "top10": "top 10 {}%",
        "chain": "chain: {}",
        "start": ("🛡 Anti-Rug: paste a token address (CA) and I'll tell you in seconds whether it looks like a "
                  "scam.\n\nI read the contract (honeypot, taxes, mint, freeze), the holders (bundles, wallet farms, "
                  "blacklisted devs) and the liquidity. Solana, BNB Chain, Base, Ethereum, Robinhood Chain and more."
                  "\n\nFree: {free} checks a day. Unlimited: /pro\n\n"
                  "Automated reading, it can be wrong. Not financial advice."),
        "quota": "You've used your {free} free checks today.\n\nGo Pro for unlimited checks for {days} days: /pro",
        "rate": "Limit: {n} checks an hour. Try again in a few minutes.",
        "cap": "The bot hit its daily limit. Try again tomorrow.",
        "error": "{ca}…: could not read it ({e}). Is it a token address?",
        "left": "\n\n{n} free check(s) left today · unlimited: /pro",
        "thanks": "✅ Thanks! Pro active until {until}. Paste as many CAs as you like.",
        "status_pro": "Pro active until {until}.",
        "status_free": "Free: {used}/{free} checks used today. Unlimited: /pro",
        "terms": ("Terms\n• The bot reads public data (blockchain, DexScreener, RugCheck, GoPlus…) and applies "
                  "automatic rules. It can be wrong: a \"green\" token can dump, a \"red\" one can pump.\n"
                  "• Not financial advice. You alone are responsible for your trades.\n"
                  "• Pro: unlimited access for {days} days from payment, no automatic renewal.\n"
                  "• Refunds: on request via /paysupport within 48 h if the service did not work."),
        "support": "A problem with a payment? Write what happened here (date, amount): we'll answer and refund "
                   "if the service did not work.",
        "support_ok": "Message sent. We'll get back to you soon.",
    },
}


def lang(code: str | None) -> str:
    return "fr" if (code or "").lower().startswith("fr") else "en"
