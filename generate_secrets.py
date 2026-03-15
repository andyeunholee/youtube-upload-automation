"""
Streamlit Cloud Secrets 생성 도우미
=====================================
이 스크립트를 로컬에서 실행하면 Streamlit Cloud에 붙여넣을
secrets.toml 내용을 자동으로 출력합니다.

실행:
    python generate_secrets.py
"""

import os
import base64
import json
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

lines = []

# ── GEMINI / YOUTUBE API 키 (config.py 의 default 값을 직접 파싱) ─────────────
import re
config_path = os.path.join(BASE_DIR, "config.py")
try:
    with open(config_path, encoding="utf-8") as f:
        src = f.read()
    _gemini  = re.search(r'GEMINI_API_KEY\s*=\s*_secret\([^,]+,\s*"([^"]+)"', src)
    _youtube = re.search(r'YOUTUBE_API_KEY\s*=\s*_secret\([^,]+,\s*"([^"]+)"', src)
    lines.append(f'GEMINI_API_KEY  = "{_gemini.group(1) if _gemini else "YOUR_GEMINI_KEY"}"')
    lines.append(f'YOUTUBE_API_KEY = "{_youtube.group(1) if _youtube else "YOUR_YOUTUBE_KEY"}"')
except Exception as e:
    lines.append(f'# config.py 파싱 실패: {e}')

lines.append("")

# ── client_secrets.json ──────────────────────────────────────────────────────
secrets_file = os.path.join(BASE_DIR, "client_secrets.json")
if os.path.exists(secrets_file):
    with open(secrets_file, "r", encoding="utf-8") as f:
        raw = json.load(f)
    compact = json.dumps(raw, separators=(",", ":"))
    lines.append(f"CLIENT_SECRETS_JSON = '{compact}'")
else:
    lines.append("# client_secrets.json 파일을 찾을 수 없습니다.")

lines.append("")

# ── OAuth 토큰 (pickle → base64) ─────────────────────────────────────────────
pickle_files = glob.glob(os.path.join(BASE_DIR, "token_youtube*.pickle"))
if pickle_files:
    lines.append("[tokens]")
    for pf in sorted(pickle_files):
        fname = os.path.basename(pf)
        # token_youtube_채널명.pickle  또는  token_youtube.pickle
        if fname == "token_youtube.pickle":
            channel = "default"
        else:
            channel = fname.replace("token_youtube_", "").replace(".pickle", "")
        with open(pf, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        lines.append(f'"{channel}" = "{b64}"')
else:
    lines.append("# token_youtube*.pickle 파일을 찾을 수 없습니다.")

# ── 출력 ──────────────────────────────────────────────────────────────────────
output = "\n".join(lines)
print("=" * 60)
print("아래 내용을 Streamlit Cloud → App settings → Secrets 에 붙여넣으세요")
print("=" * 60)
print(output)
print("=" * 60)

# .streamlit/secrets.toml 파일에도 저장
out_path = os.path.join(BASE_DIR, ".streamlit", "secrets.toml")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    f.write(output + "\n")
print(f"\n✅ .streamlit/secrets.toml 에도 저장되었습니다: {out_path}")
