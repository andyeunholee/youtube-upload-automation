"""
YouTube Video Uploader
======================
YouTube Data API v3를 사용하여 비디오를 업로드합니다.
"""

import os
import pickle
import time
from typing import Optional, Dict
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import config

# YouTube API 권한 범위
# youtube 스코프는 youtube.upload 의 상위 집합 (업로드 + 커뮤니티 포스트 등 포함)
SCOPES = ['https://www.googleapis.com/auth/youtube']


class YouTubeUploader:
    """YouTube 비디오 업로드 핸들러"""
    
    def __init__(self, channel_name: str = "default"):
        self.youtube = None
        self.channel_name = channel_name
        self._authenticate()
    
    
    @staticmethod
    def get_available_channels() -> list:
        """저장된 토큰 파일을 검색하여 이용 가능한 채널 목록 반환"""
        base_dir = os.path.dirname(config.TOKEN_FILE)
        channels = []
        
        # 기본 패턴: token_youtube_{channel}.pickle 또는 token_youtube.pickle (default)
        for filename in os.listdir(base_dir):
            if filename.startswith('token_youtube_') and filename.endswith('.pickle'):
                # token_youtube_CHANNEL.pickle -> CHANNEL
                channel = filename.replace('token_youtube_', '').replace('.pickle', '')
                channels.append(channel)
            elif filename == 'token_youtube.pickle':
                # 레거시 호환성
                if 'default' not in channels:
                    channels.append('default')
                    
        return sorted(channels)

    def _get_token_path(self) -> str:
        """채널별 토큰 파일 경로 반환"""
        if self.channel_name == "default":
            # 기존 호환성 유지
            return config.TOKEN_FILE.replace('.pickle', '_youtube.pickle')
        else:
            # 새로운 채널: token_youtube_{name}.pickle
            dir_path = os.path.dirname(config.TOKEN_FILE)
            return os.path.join(dir_path, f"token_youtube_{self.channel_name}.pickle")

    def _ensure_client_secrets(self):
        """cloud 환경에서 client_secrets.json을 secrets에서 생성합니다."""
        if os.path.exists(config.CLIENT_SECRETS_FILE):
            return
        try:
            import streamlit as st, json
            raw = st.secrets.get("CLIENT_SECRETS_JSON", "")
            if raw:
                os.makedirs(os.path.dirname(config.CLIENT_SECRETS_FILE), exist_ok=True)
                with open(config.CLIENT_SECRETS_FILE, "w") as f:
                    json.dump(json.loads(raw), f)
        except Exception:
            pass

    def _load_token_from_secrets(self) -> object:
        """Streamlit secrets의 [tokens] 섹션에서 토큰을 로드합니다."""
        try:
            import streamlit as st, base64
            tokens = st.secrets.get("tokens", {})
            token_b64 = tokens.get(self.channel_name, "")
            if token_b64:
                return pickle.loads(base64.b64decode(token_b64))
        except Exception:
            pass
        return None

    def _authenticate(self):
        """YouTube API 인증"""
        creds = None
        token_file = self._get_token_path()

        # 1) 로컬 토큰 파일
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)

        # 2) Streamlit secrets (클라우드)
        if not creds:
            creds = self._load_token_from_secrets()

        # 3) 갱신 또는 재인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # 갱신된 토큰을 로컬에 저장 (로컬 실행 시)
                try:
                    with open(token_file, 'wb') as token:
                        pickle.dump(creds, token)
                except Exception:
                    pass
            else:
                self._ensure_client_secrets()
                if not os.path.exists(config.CLIENT_SECRETS_FILE):
                    raise Exception(
                        "인증 토큰이 없습니다.\n"
                        "로컬에서 auth_youtube.py를 실행한 후 generate_secrets.py로 "
                        "Streamlit secrets를 업데이트하세요."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.CLIENT_SECRETS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)

        self.youtube = build('youtube', 'v3', credentials=creds)
        print("✅ YouTube API 인증 성공")
    
    def upload_video(self, 
                    video_path: str,
                    title: str,
                    description: str = "",
                    tags: Optional[list] = None,
                    category: str = config.DEFAULT_CATEGORY,
                    privacy: str = config.DEFAULT_PRIVACY,
                    thumbnail_path: Optional[str] = None) -> Dict:
        """
        비디오 업로드
        
        Args:
            video_path: 비디오 파일 경로
            title: 비디오 제목
            description: 비디오 설명
            tags: 태그 리스트
            category: 카테고리 ID
            privacy: 공개 범위 (public/unlisted/private)
            thumbnail_path: 썸네일 파일 경로 (선택)
        
        Returns:
            업로드 결과 {'video_id': str, 'video_url': str}
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"비디오 파일을 찾을 수 없습니다: {video_path}")
        
        # 비디오 메타데이터 설정
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': category
            },
            'status': {
                'privacyStatus': privacy,
                'selfDeclaredMadeForKids': False  # 아동용 콘텐츠 아님
            }
        }
        
        # 비디오 파일 업로드
        print(f"📤 비디오 업로드 시작: {os.path.basename(video_path)}")
        print(f"   제목: {title}")
        print(f"   공개 범위: {privacy}")
        
        media = MediaFileUpload(
            video_path,
            chunksize=1024*1024,  # 1MB chunks
            resumable=True
        )
        
        try:
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            last_progress = 0
            
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    if progress != last_progress:
                        print(f"   업로드 진행률: {progress}%")
                        last_progress = progress
            
            video_id = response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            print(f"✅ 비디오 업로드 완료!")
            print(f"   Video ID: {video_id}")
            print(f"   URL: {video_url}")
            
            # 썸네일 업로드 (있는 경우)
            if thumbnail_path:
                self.upload_thumbnail(video_id, thumbnail_path)
            
            return {
                'video_id': video_id,
                'video_url': video_url
            }
        
        except HttpError as e:
            error_msg = f"YouTube API 오류: {e}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"업로드 실패: {e}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
    
    def upload_thumbnail(self, video_id: str, thumbnail_path: str):
        """
        썸네일 업로드
        
        Args:
            video_id: YouTube 비디오 ID
            thumbnail_path: 썸네일 파일 경로
        """
        if not os.path.exists(thumbnail_path):
            print(f"⚠️  썸네일 파일을 찾을 수 없습니다: {thumbnail_path}")
            return
        
        try:
            print(f"🖼️  썸네일 업로드 시작: {os.path.basename(thumbnail_path)}")
            
            request = self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            )
            
            response = request.execute()
            print(f"✅ 썸네일 업로드 완료")
        
        except HttpError as e:
            print(f"⚠️  썸네일 업로드 실패: {e}")
        except Exception as e:
            print(f"⚠️  썸네일 업로드 오류: {e}")
    
    # YouTube InnerTube API (웹 프론트엔드 내부 API)
    _INNERTUBE_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
    _INNERTUBE_CLIENT = {
        "clientName": "WEB",
        "clientVersion": "2.20240924.02.00",
        "hl": "en",
        "gl": "US",
    }

    def _get_creds(self):
        """인증 정보를 반환하고 필요시 갱신합니다."""
        from google.auth.transport.requests import Request as AuthRequest
        creds = self.youtube._http.credentials
        if not creds.valid:
            creds.refresh(AuthRequest())
        return creds

    def _innertube_headers(self, creds) -> dict:
        return {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
            "X-Goog-AuthUser": "0",
            "X-Origin": "https://www.youtube.com",
        }

    def _upload_community_image(self, image_path: str) -> Optional[str]:
        """커뮤니티 포스트용 이미지를 InnerTube API로 업로드합니다."""
        try:
            import requests

            creds = self._get_creds()

            ext = os.path.splitext(image_path)[1].lower()
            content_type = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
            }.get(ext, "image/jpeg")

            with open(image_path, "rb") as f:
                image_data = f.read()

            headers = {
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": content_type,
                "X-Goog-AuthUser": "0",
                "X-Origin": "https://www.youtube.com",
            }
            response = requests.post(
                f"https://www.youtube.com/upload/community_post_image"
                f"?key={self._INNERTUBE_KEY}",
                data=image_data,
                headers=headers,
            )
            if response.status_code in (200, 201):
                data = response.json()
                image_id = (data.get("imageAssetId") or data.get("assetId")
                            or data.get("id") or data.get("imageId"))
                print(f"  커뮤니티 이미지 업로드 완료: {image_id}")
                return image_id
            else:
                print(f"  커뮤니티 이미지 업로드 실패: {response.status_code} {response.text[:300]}")
                return None
        except Exception as e:
            print(f"  커뮤니티 이미지 업로드 오류: {e}")
            return None

    def post_community_post(
        self,
        text: str,
        image_paths: Optional[list] = None,
    ) -> Dict:
        """
        YouTube Community Posts (Posts 탭) 에 게시물을 올립니다.
        YouTube Data API v3에 communityPosts 공개 엔드포인트가 없으므로
        InnerTube API를 사용합니다.

        Args:
            text: 게시글 텍스트
            image_paths: 이미지 파일 경로 리스트 (선택사항, 최대 10개)

        Returns:
            {'post_id': str, 'type': str}
        """
        import requests

        creds = self._get_creds()

        # 이미지 업로드
        image_asset_ids = []
        if image_paths:
            for path in image_paths[:10]:
                if path and os.path.exists(path):
                    asset_id = self._upload_community_image(path)
                    if asset_id:
                        image_asset_ids.append(asset_id)

        # InnerTube body 구성
        body: dict = {
            "context": {"client": self._INNERTUBE_CLIENT},
            "postText": text,
        }
        if image_asset_ids:
            body["imageAssets"] = image_asset_ids

        post_type = "imagePost" if image_asset_ids else "textPost"

        response = requests.post(
            f"https://www.youtube.com/youtubei/v1/community/create_post"
            f"?key={self._INNERTUBE_KEY}",
            json=body,
            headers=self._innertube_headers(creds),
        )
        if response.status_code in (200, 201):
            data = response.json()
            post_id = data.get("id", "")
            print(f"✅ Community Post 완료: {post_id} ({post_type})")
            return {"post_id": post_id, "type": post_type}
        else:
            raise Exception(
                f"Community Post API 오류: {response.status_code}\n{response.text[:500]}"
            )

    def get_video_info(self, video_id: str) -> Dict:
        """비디오 정보 조회"""
        try:
            request = self.youtube.videos().list(
                part='snippet,status,statistics',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                return response['items'][0]
            return {}
        except Exception as e:
            print(f"❌ 비디오 정보 조회 실패: {e}")
            return {}


if __name__ == "__main__":
    """테스트 코드"""
    print("=== YouTube 업로드 테스트 ===")
    
    # 테스트 파일 경로
    test_video = os.path.join(config.VIDEOS_DIR, "FINAL-VIDEO-JHU.mp4")
    test_thumbnail = os.path.join(config.THUMBNAILS_DIR, "Thumbnail final.jpg")
    
    if not os.path.exists(test_video):
        print(f"❌ 테스트 비디오를 찾을 수 없습니다: {test_video}")
        exit(1)
    
    try:
        uploader = YouTubeUploader()
        
        # 비디오 업로드 테스트
        result = uploader.upload_video(
            video_path=test_video,
            title="[테스트] 존스 홉킨스 대학교 소개",
            description="이것은 자동 업로드 테스트입니다.\n\nJohns Hopkins University 소개 영상.",
            tags=["JHU", "Johns Hopkins", "대학교", "테스트"],
            category="27",  # Education
            privacy="unlisted",
            thumbnail_path=test_thumbnail if os.path.exists(test_thumbnail) else None
        )
        
        print("\n✅ 테스트 완료!")
        print(f"   비디오 URL: {result['video_url']}")
    
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
