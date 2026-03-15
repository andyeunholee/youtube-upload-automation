"""
YouTube Auto Upload - Main Script
==================================
Google Sheets에서 업로드 대기 중인 비디오를 읽어 자동으로 YouTube에 업로드합니다.
"""

import os
import sys
import time
from typing import Dict
import config
from sheets_handler import SheetsHandler
from youtube_uploader import YouTubeUploader
from thumbnail_generator import generate_thumbnail


def parse_tags(tags_string: str) -> list:
    """태그 문자열을 리스트로 변환 (YouTube 제한: 전체 약 500자)"""
    if not tags_string:
        return []
    
    # 1. 콤마로 분리 및 공백 제거
    raw_tags = [tag.strip() for tag in tags_string.split(',') if tag.strip()]
    
    valid_tags = []
    current_length = 0
    
    for tag in raw_tags:
        # 2. 유효하지 않은 문자 제거 (꺽쇠 등)
        clean_tag = tag.replace('<', '').replace('>', '')
        
        # 3. 단일 태그 길이 제한 (YouTube는 단일 태그도 너무 길면 거부할 수 있음)
        if len(clean_tag) > 100:
            clean_tag = clean_tag[:100]
            
        # 4. 전체 길이 체크 (안전하게 400자 정도로 제한)
        # YouTube API는 태그들을 합친 전체 길이를 체크함
        if current_length + len(clean_tag) + 1 > 450:
            print(f"⚠️  태그 길이 제한(500자)에 근접하여 일부 태그가 제외되었습니다: {clean_tag}...")
            break
            
        if clean_tag:
            valid_tags.append(clean_tag)
            current_length += len(clean_tag) + 1  # 공백/구분자 고려
            
    return valid_tags


def get_file_path(filename: str, file_type: str) -> str:
    """
    파일 경로 생성
    
    Args:
        filename: 파일명
        file_type: 'video' 또는 'thumbnail'
    
    Returns:
        전체 파일 경로
    """
    if file_type == 'video':
        return os.path.join(config.VIDEOS_DIR, filename)
    elif file_type == 'thumbnail':
        return os.path.join(config.THUMBNAILS_DIR, filename)
    else:
        raise ValueError(f"알 수 없는 파일 타입: {file_type}")


def ensure_thumbnail(sheets: SheetsHandler, video_data: Dict) -> Dict:
    """
    'Thumbnail File' 컬럼이 비어 있으면 썸네일을 자동 생성합니다.
    생성 성공 시 Google Sheets와 video_data dict를 모두 업데이트합니다.
    생성 실패 시 video_data를 그대로 반환 (업로드는 계속 진행).

    Args:
        sheets:     SheetsHandler 인스턴스
        video_data: 비디오 메타데이터 dict

    Returns:
        (업데이트된) video_data dict
    """
    thumbnail_filename = video_data.get(config.COLUMN_THUMBNAIL_FILE, "").strip()
    if thumbnail_filename:
        return video_data  # 이미 썸네일 있음, 건너뜀

    video_filename = video_data.get(config.COLUMN_VIDEO_FILE, "").strip()
    if not video_filename:
        return video_data  # 비디오 파일명 없음

    video_path = get_file_path(video_filename, 'video')
    if not os.path.exists(video_path):
        return video_data  # 비디오 파일이 로컬에 없음

    title = video_data.get(config.COLUMN_TITLE, "").strip() or video_filename
    row_number = video_data['_row_number']

    print(f"\n🎨 썸네일 자동 생성 중: {video_filename}")
    generated_filename = generate_thumbnail(
        video_path=video_path,
        title=title,
        output_dir=config.THUMBNAILS_DIR
    )

    if generated_filename:
        sheets.update_thumbnail_file(row_number, generated_filename)
        video_data[config.COLUMN_THUMBNAIL_FILE] = generated_filename
    else:
        print(f"  ⚠️  썸네일 생성 실패 - 썸네일 없이 업로드를 계속합니다.")

    return video_data


def upload_single_video(sheets: SheetsHandler,
                       uploader: YouTubeUploader, 
                       video_data: Dict) -> bool:
    """
    단일 비디오 업로드
    
    Args:
        sheets: Google Sheets 핸들러
        uploader: YouTube 업로더
        video_data: 비디오 메타데이터
    
    Returns:
        업로드 성공 여부
    """
    row_number = video_data['_row_number']
    
    try:
        # 1. 비디오 파일 경로 확인
        video_filename = video_data.get(config.COLUMN_VIDEO_FILE, "").strip()
        if not video_filename:
            raise ValueError("비디오 파일명이 없습니다")
        
        video_path = get_file_path(video_filename, 'video')
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"비디오 파일을 찾을 수 없습니다: {video_path}")
        
        # 2. 썸네일 파일 경로 확인 (선택)
        thumbnail_filename = video_data.get(config.COLUMN_THUMBNAIL_FILE, "").strip()
        thumbnail_path = None
        if thumbnail_filename:
            thumbnail_path = get_file_path(thumbnail_filename, 'thumbnail')
            if not os.path.exists(thumbnail_path):
                print(f"⚠️  썸네일 파일을 찾을 수 없습니다: {thumbnail_path}")
                thumbnail_path = None
        
        # 3. 메타데이터 준비
        title = video_data.get(config.COLUMN_TITLE, "제목 없음")
        description = video_data.get(config.COLUMN_DESCRIPTION, "")
        tags = parse_tags(video_data.get(config.COLUMN_TAGS, ""))
        category = str(video_data.get(config.COLUMN_CATEGORY, config.DEFAULT_CATEGORY))
        privacy = video_data.get(config.COLUMN_PRIVACY, config.DEFAULT_PRIVACY).lower()
        
        # privacy 값 검증
        if privacy not in ['public', 'unlisted', 'private']:
            print(f"⚠️  잘못된 공개 범위: {privacy}, 기본값({config.DEFAULT_PRIVACY}) 사용")
            privacy = config.DEFAULT_PRIVACY
        
        # 4. 상태를 "Uploading"으로 업데이트
        print(f"\n{'='*60}")
        print(f"📤 업로드 시작 (행 {row_number})")
        print(f"{'='*60}")
        sheets.update_status(row_number, config.STATUS_UPLOADING)
        
        # 5. YouTube 업로드
        result = uploader.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            category=category,
            privacy=privacy,
            thumbnail_path=thumbnail_path
        )
        
        # 6. 상태를 "Complete"로 업데이트
        video_url = result['video_url']
        sheets.update_status(row_number, config.STATUS_COMPLETE, video_url=video_url)
        
        print(f"{'='*60}")
        print(f"✅ 업로드 완료 (행 {row_number})")
        print(f"   URL: {video_url}")
        print(f"{'='*60}\n")
        
        return True
    
    except Exception as e:
        # 오류 발생 시 상태를 "Error"로 업데이트
        error_message = str(e)
        print(f"\n❌ 업로드 실패 (행 {row_number}): {error_message}\n")
        sheets.update_status(row_number, config.STATUS_ERROR, error_message=error_message)
        return False


def main():
    """메인 함수"""
    print("=" * 60)
    print("YouTube Auto Upload - Google Sheets 연동")
    print("=" * 60)
    
    # 1. Google Sheets ID 확인
    if not config.GOOGLE_SHEETS_ID:
        print("\n❌ config.py에서 GOOGLE_SHEETS_ID를 설정해주세요!")
        print("   Google Sheets URL에서 ID를 복사하세요:")
        print("   https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
        print("\n   예시:")
        print("   GOOGLE_SHEETS_ID = '1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t'")
        return
    
    try:
        # 2. Google Sheets 연결
        print("\n🔗 Google Sheets 연결 중...")
        sheets = SheetsHandler()
        
        # 3. YouTube API 인증
        print("\n🔗 YouTube API 인증 중...")
        uploader = YouTubeUploader()
        
        # 4. 업로드 대기 중인 비디오 가져오기
        print("\n📋 업로드 대기 중인 비디오 확인 중...")
        pending_videos = sheets.get_pending_videos()
        
        if not pending_videos:
            print("⚠️  업로드 대기 중인 비디오가 없습니다.")
            print("   Google Sheets에서 Status를 'Pending'으로 설정하세요.")
            return
        
        print(f"\n✅ {len(pending_videos)}개의 비디오를 찾았습니다.")
        
        # 5. 각 비디오 업로드
        success_count = 0
        fail_count = 0
        
        for idx, video in enumerate(pending_videos, 1):
            print(f"\n[{idx}/{len(pending_videos)}] 처리 중...")
            title = video.get(config.COLUMN_TITLE, '제목 없음')
            print(f"제목: {title}")

            # 썸네일이 없으면 자동 생성
            video = ensure_thumbnail(sheets, video)

            if upload_single_video(sheets, uploader, video):
                success_count += 1
            else:
                fail_count += 1
            
            # 다음 비디오 전에 잠시 대기 (API 제한 방지)
            if idx < len(pending_videos):
                wait_time = 3
                print(f"⏳ 다음 비디오까지 {wait_time}초 대기...")
                time.sleep(wait_time)
        
        # 6. 결과 요약
        print("\n" + "=" * 60)
        print("📊 업로드 완료!")
        print("=" * 60)
        print(f"✅ 성공: {success_count}개")
        print(f"❌ 실패: {fail_count}개")
        print(f"📝 전체: {len(pending_videos)}개")
        print("=" * 60)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
