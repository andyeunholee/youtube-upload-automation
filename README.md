# YouTube Auto Upload 🎬

Google Sheets를 사용하여 YouTube 비디오를 자동으로 업로드하는 Python 스크립트입니다.

## 📁 폴더 구조

```
Youtube_Auto/
├── client_secrets.json          # OAuth 2.0 인증 파일
├── My YouTube Uploads.gsheet    # 업로드 메타데이터 관리
├── config.py                    # 설정 파일
├── sheets_handler.py            # Google Sheets 연동
├── youtube_uploader.py          # YouTube 업로드 핵심
├── main.py                      # 메인 스크립트
├── requirements.txt             # 필요한 패키지
├── videos/                      # 업로드할 비디오 파일
│   └── FINAL-VIDEO-JHU.mp4
└── thumbnails/                  # 썸네일 파일
    └── Thumbnail final.jpg
```

## 🚀 빠른 시작

### 1️⃣ Google Sheets API 활성화

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 기존 프로젝트(`blog-11292025`) 선택
3. **API 및 서비스** > **라이브러리** 클릭
4. "Google Sheets API" 검색 → **사용 설정** 클릭

### 2️⃣ 필요한 패키지 설치

```bash
cd "g:\My Drive\Youtube_Auto"
pip install -r requirements.txt
```

### 3️⃣ Google Sheets 설정

1. **Google Sheets 열기**: `My YouTube Uploads.gsheet` 파일 열기
2. **Sheets ID 복사**: URL에서 ID 복사
   ```
   https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit
   ```
3. **config.py 수정**: `GOOGLE_SHEETS_ID`에 복사한 ID 붙여넣기
   ```python
   GOOGLE_SHEETS_ID = "1a2b3c4d5e6f7g8h9i0j..."
   ```

### 4️⃣ Google Sheets 템플릿 생성 (처음만)

```bash
python sheets_handler.py
```

이 명령어를 실행하면:
- OAuth 인증 창이 열림 → Google 계정으로 로그인
- Google Sheets에 헤더와 예시 데이터가 자동 생성됨

### 5️⃣ Google Sheets에 업로드 정보 입력

| Status  | Video File           | Thumbnail File      | Title                | Description          | Tags                     | Category | Privacy  | Video URL | Error Message |
|---------|----------------------|---------------------|----------------------|----------------------|--------------------------|----------|----------|-----------|---------------|
| Pending | FINAL-VIDEO-JHU.mp4  | Thumbnail final.jpg | 존스 홉킨스 대학교 소개 | JHU 소개 영상입니다. | JHU,Johns Hopkins,대학교 | 27       | unlisted |           |               |

**컬럼 설명:**
- **Status**: `Pending` (업로드 대기), `Complete` (완료), `Error` (오류)
- **Video File**: `videos/` 폴더 안의 비디오 파일명
- **Thumbnail File**: `thumbnails/` 폴더 안의 썸네일 파일명 (선택)
- **Title**: 비디오 제목 (필수)
- **Description**: 비디오 설명
- **Tags**: 태그 (쉼표로 구분)
- **Category**: 카테고리 ID (기본값: 22)
  - `1` = Film & Animation
  - `10` = Music
  - `15` = Pets & Animals
  - `17` = Sports
  - `22` = People & Blogs
  - `27` = Education
  - `28` = Science & Technology
- **Privacy**: 공개 범위
  - `public` = 공개
  - `unlisted` = 일부 공개 (링크가 있는 사람만)
  - `private` = 비공개
- **Video URL**: 업로드 후 자동 기록됨
- **Error Message**: 오류 발생 시 자동 기록됨

### 6️⃣ 업로드 실행

```bash
python main.py
```

## 🛠️ 사용 방법

### 단일 비디오 업로드 테스트

```bash
python youtube_uploader.py
```

### Google Sheets 연결 테스트

```bash
python sheets_handler.py
```

### 배치 업로드 (메인 스크립트)

```bash
python main.py
```

## 📝 주의사항

### OAuth 인증
- 첫 실행 시 브라우저에서 Google 계정 인증 필요
- 인증 후 토큰 파일이 자동 생성됨:
  - `token_youtube.pickle` (YouTube API)
  - `token_sheets.pickle` (Google Sheets API)

### API 할당량
- YouTube Data API v3는 일일 업로드 할당량이 있습니다
- 기본 할당량: 하루 10,000 units
- 비디오 업로드: 약 1,600 units/비디오

### 파일 크기 제한
- YouTube 비디오 최대 크기: 256GB 또는 12시간
- 썸네일 최대 크기: 2MB
- 썸네일 권장 해상도: 1280x720 (16:9 비율)

## 🔧 문제 해결

### "GOOGLE_SHEETS_ID를 설정해주세요" 오류
- `config.py`에서 `GOOGLE_SHEETS_ID` 값을 설정하세요
- Google Sheets URL에서 ID를 복사하세요

### "Google Sheets 연결 실패" 오류
- Google Sheets API가 활성화되어 있는지 확인
- Google Sheets ID가 올바른지 확인
- Google Sheets 공유 권한 확인 (본인 계정으로 접근 가능한지)

### "비디오 파일을 찾을 수 없습니다" 오류
- `videos/` 폴더에 파일이 있는지 확인
- Google Sheets의 파일명이 정확한지 확인 (대소문자 구분)

### OAuth 인증 오류
- `client_secrets.json` 파일이 있는지 확인
- YouTube Data API v3가 활성화되어 있는지 확인
- Google Cloud Console에서 OAuth 동의 화면이 구성되어 있는지 확인

## 📚 추가 정보

### YouTube API 문서
- [YouTube Data API v3](https://developers.google.com/youtube/v3)
- [Videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert)

### Google Sheets API 문서
- [Google Sheets API](https://developers.google.com/sheets/api)

## 🎯 다음 단계

1. Google Sheets API 활성화
2. `config.py`에서 `GOOGLE_SHEETS_ID` 설정
3. 패키지 설치: `pip install -r requirements.txt`
4. Google Sheets 템플릿 생성: `python sheets_handler.py`
5. Google Sheets에 업로드 정보 입력
6. 업로드 실행: `python main.py`

## 📧 문의

문제가 발생하거나 도움이 필요하시면 언제든지 알려주세요! 🚀
