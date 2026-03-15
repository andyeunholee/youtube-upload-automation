"""
Google Sheets Handler
=====================
Google Sheets에서 업로드할 비디오 목록을 읽고, 업로드 상태를 업데이트합니다.
"""

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
from typing import List, Dict, Optional
import config

# Google Sheets API 권한 범위
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class SheetsHandler:
    """Google Sheets 연동 핸들러"""
    
    def __init__(self):
        self.creds = None
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self._authenticate()
        self._open_sheet()
    
    def _authenticate(self):
        """Google Sheets API 인증"""
        token_file = config.TOKEN_FILE.replace('.pickle', '_sheets.pickle')
        
        # 저장된 토큰이 있는지 확인
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                self.creds = pickle.load(token)
        
        # 토큰이 없거나 유효하지 않으면 새로 인증
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.CLIENT_SECRETS_FILE, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # 토큰 저장
            with open(token_file, 'wb') as token:
                pickle.dump(self.creds, token)
        
        # gspread 클라이언트 생성
        self.client = gspread.authorize(self.creds)
    
    def _open_sheet(self):
        """Google Sheets 열기"""
        try:
            self.spreadsheet = self.client.open_by_key(config.GOOGLE_SHEETS_ID)
            self.worksheet = self.spreadsheet.worksheet(config.SHEET_NAME)
            print(f"✅ Google Sheets 연결 성공: {self.spreadsheet.title}")
        except Exception as e:
            print(f"❌ Google Sheets 연결 실패: {e}")
            print(f"   GOOGLE_SHEETS_ID가 올바른지 확인하세요: {config.GOOGLE_SHEETS_ID}")
            raise
    
    def get_all_records(self) -> List[Dict]:
        """모든 레코드 가져오기"""
        try:
            records = self.worksheet.get_all_records()
            return records
        except Exception as e:
            print(f"❌ 레코드 읽기 실패: {e}")
            return []
    
    def get_pending_videos(self) -> List[Dict]:
        """업로드 대기 중인 비디오 목록 가져오기"""
        all_records = self.get_all_records()
        pending = []
        
        for idx, record in enumerate(all_records, start=2):  # 헤더는 1행
            status = record.get(config.COLUMN_STATUS, "")
            if status == config.STATUS_PENDING:
                record['_row_number'] = idx  # 행 번호 저장 (업데이트용)
                pending.append(record)
        
        return pending
    
    def update_status(self, row_number: int, status: str, 
                     video_url: Optional[str] = None,
                     error_message: Optional[str] = None):
        """업로드 상태 업데이트"""
        try:
            # Status 컬럼 찾기
            headers = self.worksheet.row_values(1)
            status_col = headers.index(config.COLUMN_STATUS) + 1
            
            # Status 업데이트
            self.worksheet.update_cell(row_number, status_col, status)
            
            # Video URL 업데이트 (있는 경우)
            if video_url and config.COLUMN_VIDEO_URL in headers:
                url_col = headers.index(config.COLUMN_VIDEO_URL) + 1
                self.worksheet.update_cell(row_number, url_col, video_url)
            
            # Error Message 업데이트 (있는 경우)
            if error_message and config.COLUMN_ERROR_MESSAGE in headers:
                error_col = headers.index(config.COLUMN_ERROR_MESSAGE) + 1
                self.worksheet.update_cell(row_number, error_col, error_message)
            
            print(f"✅ 행 {row_number} 상태 업데이트: {status}")
        except Exception as e:
            print(f"❌ 상태 업데이트 실패 (행 {row_number}): {e}")

    def update_thumbnail_file(self, row_number: int, thumbnail_filename: str) -> bool:
        """
        'Thumbnail File' 컬럼에 생성된 썸네일 파일명을 기록합니다.

        Args:
            row_number:         Google Sheets 행 번호 (헤더 포함 1-indexed)
            thumbnail_filename: 저장할 썸네일 파일명 (basename only)

        Returns:
            True if updated successfully, False otherwise.
        """
        try:
            headers = self.worksheet.row_values(1)
            if config.COLUMN_THUMBNAIL_FILE not in headers:
                print(f"⚠️  '{config.COLUMN_THUMBNAIL_FILE}' 컬럼을 찾을 수 없습니다.")
                return False

            col_index = headers.index(config.COLUMN_THUMBNAIL_FILE) + 1
            self.worksheet.update_cell(row_number, col_index, thumbnail_filename)
            print(f"✅ Sheets 업데이트: 행 {row_number}, Thumbnail File = {thumbnail_filename}")
            return True

        except Exception as e:
            print(f"⚠️  Thumbnail File 컬럼 업데이트 실패 (행 {row_number}): {e}")
            return False

    def create_template_sheet(self):
        """템플릿 시트 생성 (헤더 행)"""
        try:
            headers = [
                config.COLUMN_STATUS,
                config.COLUMN_VIDEO_FILE,
                config.COLUMN_THUMBNAIL_FILE,
                config.COLUMN_TITLE,
                config.COLUMN_DESCRIPTION,
                config.COLUMN_TAGS,
                config.COLUMN_CATEGORY,
                config.COLUMN_PRIVACY,
                config.COLUMN_VIDEO_URL,
                config.COLUMN_ERROR_MESSAGE
            ]
            
            # 첫 행에 헤더 추가
            self.worksheet.update('A1:J1', [headers])
            
            # 예시 데이터 추가
            example = [
                config.STATUS_PENDING,
                "FINAL-VIDEO-JHU.mp4",
                "Thumbnail final.jpg",
                "존스 홉킨스 대학교 소개",
                "존스 홉킨스 대학교에 대한 소개 영상입니다.",
                "JHU, Johns Hopkins, 대학교, 미국대학",
                "27",  # Education
                "unlisted",
                "",
                ""
            ]
            self.worksheet.update('A2:J2', [example])
            
            print("✅ 템플릿 시트 생성 완료!")
        except Exception as e:
            print(f"❌ 템플릿 생성 실패: {e}")


if __name__ == "__main__":
    """테스트 코드"""
    print("=== Google Sheets 연동 테스트 ===")
    
    # Google Sheets ID 확인
    if not config.GOOGLE_SHEETS_ID:
        print("❌ config.py에서 GOOGLE_SHEETS_ID를 설정해주세요!")
        print("   Google Sheets URL에서 ID를 복사하세요:")
        print("   https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
        exit(1)
    
    try:
        handler = SheetsHandler()
        
        # 모든 레코드 출력
        print("\n📋 모든 레코드:")
        records = handler.get_all_records()
        for record in records:
            print(f"  - {record}")
        
        # 대기 중인 비디오 출력
        print("\n⏳ 업로드 대기 중인 비디오:")
        pending = handler.get_pending_videos()
        for video in pending:
            print(f"  - 행 {video['_row_number']}: {video.get(config.COLUMN_TITLE)}")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
