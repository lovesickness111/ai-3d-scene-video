"""Search the internet via a DeepSeek-Flash-compatible chat completion API.

Reads credentials from the repo-root .env file (DEEPSEEK_API_KEY,
DEEPSEEK_BASE_URL, DEEPSEEK_MODEL). Run with -I to avoid loading code from
an untrusted current directory:

    python -I .claude/skills/web-search/search.py "your query"
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_PATH = REPO_ROOT / ".env"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"


def load_env(path: Path) -> dict:
    env = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    if len(sys.argv) < 2:
        print(json.dumps({"error": "missing query argument"}))
        return 1
    query = " ".join(sys.argv[1:])

    env = load_env(ENV_PATH)
    api_key = env.get("DEEPSEEK_API_KEY")
    base_url = env.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = env.get("DEEPSEEK_MODEL", DEFAULT_MODEL)

    if not api_key or api_key.strip() in ("", "your_api_key_here"):
        print(json.dumps({
            "error": "DEEPSEEK_API_KEY chưa được điền trong .env. "
                     "Thêm dòng DEEPSEEK_API_KEY=<key thật> vào file .env ở gốc repo."
        }))
        return 1

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Ban la tro ly tim kiem internet. Tra loi ngan gon, "
                           "kem nguon/link tham khao khi co the.",
            },
            {"role": "user", "content": query},
        ],
    }

    request = urllib.request.Request(
        url=f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(json.dumps({"error": f"HTTP {exc.code}: {detail}"}))
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"error": f"request failed: {exc}"}))
        return 1

    try:
        answer = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(json.dumps({"error": "unexpected response shape", "raw": body}))
        return 1

    print(json.dumps({"query": query, "answer": answer, "model": model}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
