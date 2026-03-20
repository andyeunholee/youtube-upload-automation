"""
YouTube Auto Upload - Configuration File
========================================
로컬 실행: 값을 직접 입력하거나 .streamlit/secrets.toml 사용
클라우드: Streamlit Cloud 대시보드의 Secrets에서 자동으로 읽음
"""

import os


def _secret(key: str, default: str = "") -> str:
    """Streamlit secrets → 환경변수 → default 순서로 값을 읽습니다."""
    try:
        import streamlit as st
        val = st.secrets.get(key, "")
        if val:
            return val
    except Exception:
        pass
    return os.environ.get(key, default)


# API Keys (Streamlit Secrets에 등록된 값을 사용하며, 로컬에서는 환경변수 또는 secrets.toml을 사용하세요)
YOUTUBE_API_KEY = _secret("YOUTUBE_API_KEY", "")
GEMINI_API_KEY  = _secret("GEMINI_API_KEY",  "")

# ============================
# File Paths
# ============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, "client_secrets.json")
VIDEOS_DIR          = os.path.join(BASE_DIR, "videos")
THUMBNAILS_DIR      = os.path.join(BASE_DIR, "thumbnails")

# OAuth 2.0 토큰 저장 위치
TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")

# 썸네일 블랭크 프레임 파일
THUMBNAIL_FRAME_FILE = os.path.join(THUMBNAILS_DIR, "Thumbnail-Final-Frame.png")

# ============================
# YouTube Upload Defaults
# ============================
DEFAULT_CATEGORY = "27"    # 27 = Education
DEFAULT_PRIVACY  = "private"

# 고정 업로드 채널 이름 (auth_youtube.py 실행 시 사용한 채널 이름과 일치해야 함)
# "default" = token_youtube.pickle 사용
# 다른 이름 = token_youtube_{이름}.pickle 사용
DEFAULT_CHANNEL  = _secret("DEFAULT_CHANNEL", "엔디쌤tv")

# ============================
# Thumbnail Settings
# ============================
THUMBNAIL_WIDTH   = 1280
THUMBNAIL_HEIGHT  = 720
THUMBNAIL_QUALITY = 95

THUMBNAIL_DEFAULT_TEXT_COLOR    = "#FFFFFF"
THUMBNAIL_DEFAULT_OUTLINE_COLOR = "#003087"
THUMBNAIL_OUTLINE_WIDTH         = 8

# 폰트 우선순위 (Windows → Linux/Cloud 순서)
THUMBNAIL_FONT_PATHS = [
    # Windows
    "C:/Windows/Fonts/ariblk.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/malgunbd.ttf",
    "C:/Windows/Fonts/malgun.ttf",
    # Linux (Streamlit Cloud - Ubuntu)
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]
