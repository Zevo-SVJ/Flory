# Anti-Rug (bot payant)

Un bot Telegram à part du desk : on lui colle l'adresse d'un token, il répond en quelques secondes avec les
contrôles anti-rug du desk (contrat, holders, bundles, liquidité, devs blacklistés), en français ou en anglais.

- Gratuit : 3 lectures par jour. Pro : illimité pendant 30 jours, payé en Telegram Stars (/pro).
- Il réutilise le code du desk (`../rug-desk`) en lecture seule. Ses données et son `.env` sont à lui.
- Il ne trade jamais.

## Lancer

```
cd ~/Documents/rug-desk-run/antirug-bot
read -rs T && echo "ANTIRUG_BOT_TOKEN=$T" >> .env && chmod 600 .env      # le token d'un NOUVEAU bot (@BotFather)
python3 bot.py
```
Puis, dans Telegram, envoie au nouveau bot `/owner <code affiché au démarrage>` : tu reçois /stats et les paiements.

## Fichiers

| fichier | rôle |
|---|---|
| bot.py | le bot : lectures, quota gratuit, paiement Stars, /start /pro /status /terms /paysupport, /stats (propriétaire) |
| tgpro.py | abonnement Pro et quota du jour |
| texts.py | tous les messages, FR et EN |
| posts.py | brouillons de posts X tirés des vraies données du desk : `python3 posts.py` (24 h) ou `python3 posts.py 168` |
| local.py | dossiers et réglages |

Réglages possibles dans `.env` : `TG_FREE_PER_DAY=3`, `TG_PRO_STARS=500`, `TG_PRO_DAYS=30`, `ANTIRUG_DAILY_CAP=500`,
`ANTIRUG_PER_HOUR=50`.

Tests : `python3 -m pytest -q tests`
