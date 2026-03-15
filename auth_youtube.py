"""
YouTube OAuth 인증 헬퍼
브라우저에서 자동으로 인증 페이지를 엽니다.
"""

import pickle
import os
from google_auth_oauthlib.flow import InstalledAppFlow
import config

SCOPES = ['https://www.googleapis.com/auth/youtube']

def authenticate():
    """YouTube API 인증"""
    token_file = config.TOKEN_FILE.replace('.pickle', '_youtube.pickle')
    
    if os.path.exists(token_file):
        print(f"✅ 이미 인증된 토큰이 있습니다: {token_file}")
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
            print(f"   유효 여부: {creds.valid}")
            return
    
    print("🔐 YouTube OAuth 인증을 시작합니다...")
    print("   브라우저가 자동으로 열립니다.")
    print("   Google 계정으로 로그인하고 권한을 승인하세요.\n")
    
    flow = InstalledAppFlow.from_client_secrets_file(
        config.CLIENT_SECRETS_FILE, SCOPES)
    
    # 브라우저 자동 열기 (포트 8080 사용)
    creds = flow.run_local_server(port=8080, open_browser=True)
    
    # 토큰 저장
    with open(token_file, 'wb') as token:
        pickle.dump(creds, token)
    
    print("\n✅ 인증 완료!")
    print(f"   토큰 저장: {token_file}")

if __name__ == "__main__":
    authenticate()
