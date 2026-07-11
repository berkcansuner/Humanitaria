"""Throwaway feasibility spike (Phase B): which endpoint/URL returns a valid image?

Tries Gemini image generation two ways × two base URLs, prints which combination
returns a decodable PNG. NOT production code — its OUTCOME (recorded in the task
report) decides how rag/report_images.generate_image is implemented in Task 2.

Run locally:  python scripts/spike_image_gen.py
Needs GEMINI_API_KEY in .env; also set SPIKE_GATEWAY_URL to the prod Cloudflare AI
Gateway base (…/gemini/google-ai-studio/v1beta/openai/) to test the gateway path.
"""
import base64
import os

from config import get_settings

PROMPT = "A muted editorial illustration, abstract humanitarian theme, no text, no people."
MODEL = "gemini-3.1-flash-image"


def _try_openai_compat(base_url: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=30)
    resp = client.images.generate(model=MODEL, prompt=PROMPT, response_format="b64_json")
    return resp.data[0].b64_json


def _try_native_rest(base_url: str, api_key: str) -> str:
    import httpx
    url = f"{base_url.rstrip('/')}/models/{MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": PROMPT}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    r = httpx.post(url, params={"key": api_key}, json=body, timeout=60)
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    for p in parts:
        if "inlineData" in p:
            return p["inlineData"]["data"]
    raise RuntimeError("no inlineData in native response")


def _ok(b64: str) -> bool:
    try:
        raw = base64.b64decode(b64)
        return raw[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1")  # PNG or JPEG
    except Exception:
        return False


def main():
    s = get_settings()
    key = s.GEMINI_API_KEY
    openai_base = s.GEMINI_BASE_URL                        # …/v1beta/openai/
    native_base = openai_base.replace("/openai/", "/").rstrip("/")  # …/v1beta
    gateway_openai = os.environ.get("SPIKE_GATEWAY_URL", "")

    combos = [
        ("openai_compat / direct openai base", lambda: _try_openai_compat(openai_base, key)),
        ("native_rest / direct native base", lambda: _try_native_rest(native_base, key)),
    ]
    if gateway_openai:
        combos.append(("openai_compat / GATEWAY", lambda: _try_openai_compat(gateway_openai, key)))
        gw_native = gateway_openai.replace("/openai/", "/").rstrip("/")
        combos.append(("native_rest / GATEWAY", lambda: _try_native_rest(gw_native, key)))

    for label, fn in combos:
        try:
            b64 = fn()
            print(f"[{'OK ' if _ok(b64) else 'BAD'}] {label} — {len(b64)} b64 chars")
        except Exception as e:
            print(f"[ERR] {label} — {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
