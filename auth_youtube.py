"""
YouTube OAuth 인증 헬퍼
브라우저에서 자동으로 인증 페이지를 엽니다.

사용법:
  python auth_youtube.py                    # default 채널
  python auth_youtube.py 채널이름           # 특정 채널 (예: 엔디쌤tv)
"""

import pickle
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
import config

SCOPES = ['https://www.googleapis.com/auth/youtube']

def authenticate(channel_name: str = "default"):
    """YouTube API 인증"""
    base_dir = os.path.dirname(config.TOKEN_FILE)
    if channel_name == "default":
        token_file = config.TOKEN_FILE.replace('.pickle', '_youtube.pickle')
    else:
        token_file = os.path.join(base_dir, f"token_youtube_{channel_name}.pickle")

    print(f"📺 채널: {channel_name}")
    print(f"📁 토큰 파일: {token_file}\n")

    creds = None
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    if creds and creds.valid:
        print(f"✅ 이미 유효한 인증 토큰이 있습니다: {token_file}")
        return

    if creds and creds.expired and creds.refresh_token:
        print("🔄 토큰이 만료되어 갱신을 시도합니다...")
        try:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            print("✅ 토큰 갱신 완료!")
            return
        except Exception as e:
            print(f"⚠️ 토큰 갱신 실패: {e}")

    print("🔐 YouTube OAuth 인증을 시작합니다...")
    print("   브라우저가 자동으로 열립니다.")
    print("   Google 계정으로 로그인하고 권한을 승인하세요.\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        config.CLIENT_SECRETS_FILE, SCOPES)

    # 브라우저 자동 열기 (포트 8090 사용)
    creds = flow.run_local_server(port=8090, open_browser=True)

    # 토큰 저장
    with open(token_file, 'wb') as token:
        pickle.dump(creds, token)

    print("\n✅ 인증 완료!")
    print(f"   토큰 저장: {token_file}")
    print(f"\n💡 앱에서 '{channel_name}' 채널로 선택하여 업로드하세요.")

if __name__ == "__main__":
    ch = sys.argv[1] if len(sys.argv) > 1 else "default"
    authenticate(ch)
