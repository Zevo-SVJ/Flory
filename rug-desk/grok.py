# grok.py
# check 14, optional and paid. the only file that holds the xAI key.
# never imported unless config.JUDGE = "grok".
import json, datetime, requests
from config import MODEL, GROK_MAX_TURNS
import env

URL = "https://api.x.ai/v1/responses"


def _key() -> str:
    k = env.get("XAI_API_KEY")
    if not k:
        raise RuntimeError("no XAI_API_KEY in the environment or in .env")
    return k


def _text(resp: dict) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"]
    parts = []
    for item in resp.get("output") or []:
        if item.get("type") == "message":
            for c in item.get("content") or []:
                if c.get("type") in ("output_text", "text"):
                    parts.append(c.get("text") or "")
    return "\n".join(parts)


def ask(system: str, payload: dict, read_x: bool = False) -> dict:
    """One call, JSON in, JSON out. Anything that isn't JSON raises, and a raise is a SKIP upstream."""
    body = {"model": MODEL,
            "input": [{"role": "system", "content": system},
                      {"role": "user", "content": json.dumps(payload)}]}
    if read_x:
        since = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
        body["tools"] = [{"type": "x_search", "from_date": since}]
        body["max_turns"] = GROK_MAX_TURNS
    r = requests.post(URL, timeout=180, json=body,
                      headers={"Authorization": f"Bearer {_key()}"})
    r.raise_for_status()
    text = _text(r.json())
    start, end = text.find("{"), text.rfind("}")
    if start == -1:
        raise ValueError(f"no json in answer: {text[:200]}")
    return json.loads(text[start:end + 1])
