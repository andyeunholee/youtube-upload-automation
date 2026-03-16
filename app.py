"""
YouTube Upload Wizard - Streamlit 대화형 UI
============================================
7단계 마법사 방식으로 YouTube Private 업로드를 진행합니다.
Google Sheets 불필요 - 모든 정보를 UI에서 직접 입력합니다.

실행: streamlit run app.py
"""

import glob
import os

import streamlit as st
from PIL import Image

import config
from thumbnail_generator import generate_campus_image, generate_thumbnail
from youtube_uploader import YouTubeUploader

# ── 페이지 설정 ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="YouTube Upload Wizard",
    page_icon="🎬",
    layout="wide",
)

# ── 상수 ───────────────────────────────────────────────────────────────────────
STEPS = ["영상 선택", "캠퍼스 이미지", "썸네일 완성", "제목", "설명", "태그", "업로드"]
TMP_CAMPUS_FILE = os.path.join(config.THUMBNAILS_DIR, "_campus_preview_tmp.jpg")


# ── 헬퍼 ───────────────────────────────────────────────────────────────────────
def cleanup_temp_videos():
    """Cloud 세션에서 남겨진 임시 비디오 파일 정리"""
    if not os.path.isdir(config.VIDEOS_DIR):
        return
    for f in glob.glob(os.path.join(config.VIDEOS_DIR, "tmp*")):
        try:
            os.remove(f)
        except Exception:
            pass



def reset_wizard():
    keys = [
        "step", "video_file", "university_name",
        "campus_image_path", "thumbnail_filename",
        "title", "description", "tags", "is_shorts",
        "upload_done",
    ]
    for k in keys:
        st.session_state.pop(k, None)


def get_available_channels() -> list:
    base_dir = os.path.dirname(config.TOKEN_FILE)
    channels = []
    if not os.path.isdir(base_dir):
        return ["default"]
    for fname in os.listdir(base_dir):
        if fname.startswith("token_youtube_") and fname.endswith(".pickle"):
            channels.append(fname.replace("token_youtube_", "").replace(".pickle", ""))
        elif fname == "token_youtube.pickle":
            if "default" not in channels:
                channels.append("default")
    return sorted(channels) if channels else ["default"]


# ── 세션 초기화 ───────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 1
    cleanup_temp_videos()  # 이전 세션 임시 파일 정리

# ── 사이드바 ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ 채널 설정")
    selected_channel = config.DEFAULT_CHANNEL
    st.session_state["selected_channel"] = selected_channel
    st.info(f"📺 업로드 채널: **{selected_channel}**")

    token_file = (
        config.TOKEN_FILE.replace(".pickle", "_youtube.pickle")
        if selected_channel == "default"
        else os.path.join(
            os.path.dirname(config.TOKEN_FILE),
            f"token_youtube_{selected_channel}.pickle",
        )
    )
    # 인증 여부 확인 (파일 또는 Secrets)
    is_authenticated = os.path.exists(token_file)
    if not is_authenticated:
        try:
            tokens = st.secrets.get("tokens", {})
            if tokens.get(selected_channel):
                is_authenticated = True
        except Exception:
            pass

    if is_authenticated:
        st.success(f"✅ 인증 완료 ({selected_channel})")
    else:
        st.warning("⚠️ 인증 필요\n로컬에서 인증 후 Secrets를 업데이트하세요.")

    st.markdown("---")
    if st.button("🔄 처음부터 다시 시작"):
        reset_wizard()
        st.rerun()

    st.markdown("---")
    st.caption(f"Videos: `{config.VIDEOS_DIR}`")
    st.caption(f"Thumbnails: `{config.THUMBNAILS_DIR}`")

# ── 타이틀 & 진행률 ────────────────────────────────────────────────────────────
st.title("🎬 YouTube Upload Wizard")

# 단계 표시 바
step_cols = st.columns(len(STEPS))
for i, (col, label) in enumerate(zip(step_cols, STEPS), 1):
    if i < st.session_state.step:
        col.markdown(f"<div style='text-align:center;color:#22c55e'>✅<br><small>{label}</small></div>", unsafe_allow_html=True)
    elif i == st.session_state.step:
        col.markdown(f"<div style='text-align:center;color:#3b82f6;font-weight:bold'>▶️<br><small>{label}</small></div>", unsafe_allow_html=True)
    else:
        col.markdown(f"<div style='text-align:center;color:#94a3b8'>⬜<br><small>{label}</small></div>", unsafe_allow_html=True)

st.progress((st.session_state.step - 1) / (len(STEPS) - 1))
st.markdown("---")


# ════════════════════════════════════════════════════════════════════════════════
# STEP 1: 영상 파일 선택
# ════════════════════════════════════════════════════════════════════════════════
if st.session_state.step == 1:
    st.subheader("Step 1 · 업로드할 영상 파일 선택")

    _is_cloud = os.path.exists('/mount/src')  # Streamlit Community Cloud 전용 경로

    # 로컬 / Cloud 모두 파일 업로더 방식으로 통일
    uploaded_video = st.file_uploader(
        "영상 파일을 업로드하세요",
        type=["mp4", "mov", "avi", "mkv", "webm", "m4v", "mpeg4"],
        key="video_upload",
    )
    if not uploaded_video:
        st.info("📂 영상 파일을 선택하세요.")
        st.stop()
    size_mb = len(uploaded_video.getbuffer()) / (1024 * 1024)
    st.caption(f"파일 크기: {size_mb:.1f} MB")

    st.markdown("---")
    video_type = st.radio(
        "영상 유형",
        ["📺 일반 영상 (가로)", "📱 Shorts (세로 / 60초 이하)"],
        horizontal=True,
        index=1 if st.session_state.get("is_shorts", False) else 0,
    )

    if st.button("다음 →", type="primary"):
        import tempfile
        _ext = os.path.splitext(uploaded_video.name)[1] or ".mp4"
        os.makedirs(config.VIDEOS_DIR, exist_ok=True)
        _tmp_video = tempfile.NamedTemporaryFile(
            delete=False, suffix=_ext, dir=config.VIDEOS_DIR
        )
        _tmp_video.write(uploaded_video.getbuffer())
        _tmp_video.close()
        st.session_state.video_file = os.path.basename(_tmp_video.name)
        st.session_state._cloud_tmp_video = _tmp_video.name
        st.session_state.is_shorts = video_type.startswith("📱")
        st.session_state.step = 2
        st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# STEP 2: 대학교 이름 입력 → 캠퍼스 이미지 생성
# ════════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 2:
    st.subheader("Step 2 · 대학교 캠퍼스 이미지 생성")
    st.caption(f"선택된 영상: `{st.session_state.video_file}`")

    if st.session_state.get("is_shorts"):
        st.info("📱 **Shorts 모드** · 썸네일은 선택 사항입니다.")
        if st.button("⏭️ 썸네일 없이 바로 제목 입력 →", type="secondary"):
            st.session_state.pop("thumbnail_filename", None)
            if "title" not in st.session_state:
                st.session_state.title = ""
            st.session_state.step = 4
            st.rerun()
        st.markdown("또는 아래에서 썸네일을 생성하세요:")
        st.markdown("---")

    uni_name = st.text_input(
        "대학교 이름 (영문)",
        placeholder="예: Rice University, Harvard University, MIT",
        value=st.session_state.get("university_name", ""),
    )

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← 이전"):
            st.session_state.step = 1
            st.rerun()

    with col_next:
        if st.button(
            "🖼️ 캠퍼스 이미지 생성",
            type="primary",
            disabled=not uni_name.strip(),
        ):
            with st.spinner(f"'{uni_name}' 캠퍼스 이미지 생성 중... (10~20초 소요)"):
                img, err = generate_campus_image(uni_name.strip())

            if img is None:
                st.error("❌ 이미지 생성 실패")
                st.code(err, language="")
            else:
                os.makedirs(config.THUMBNAILS_DIR, exist_ok=True)
                img.save(TMP_CAMPUS_FILE, "JPEG", quality=95)
                st.session_state.university_name = uni_name.strip()
                st.session_state.campus_image_path = TMP_CAMPUS_FILE
                st.session_state.step = 3
                st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# STEP 3: 색상 입력 → 최종 썸네일 생성
# ════════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 3:
    st.subheader("Step 3 · 썸네일 색상 설정")
    st.caption(f"대학교: **{st.session_state.university_name}**")

    # 캠퍼스 이미지 미리보기
    if os.path.exists(st.session_state.campus_image_path):
        campus_img = Image.open(st.session_state.campus_image_path)
        st.image(campus_img, caption="생성된 캠퍼스 이미지", use_container_width=True)

    st.markdown("#### 텍스트 색상 설정")

    def _is_valid_hex(h: str) -> bool:
        h = h.strip().lstrip("#")
        return len(h) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in h)

    col1, col2 = st.columns(2)
    with col1:
        text_hex_input = st.text_input(
            "텍스트 색상 (Hex#)",
            value=st.session_state.get("text_color_hex", config.THUMBNAIL_DEFAULT_TEXT_COLOR),
            placeholder="#FFFFFF",
            max_chars=7,
            help="예: #FFFFFF (흰색), #FFD700 (금색), #000000 (검정)",
        )
        text_hex_input = text_hex_input.strip()
        if text_hex_input and not text_hex_input.startswith("#"):
            text_hex_input = "#" + text_hex_input
        if _is_valid_hex(text_hex_input):
            text_color = text_hex_input
            st.markdown(
                f"<div style='width:100%;height:28px;background:{text_color};"
                f"border-radius:4px;border:1px solid #888'></div>",
                unsafe_allow_html=True,
            )
            st.caption(f"색상: `{text_color}`")
        else:
            text_color = config.THUMBNAIL_DEFAULT_TEXT_COLOR
            if text_hex_input:
                st.warning("올바른 Hex 코드를 입력하세요 (예: #FFFFFF)")

    with col2:
        outline_hex_input = st.text_input(
            "외곽선 색상 (Hex#)",
            value=st.session_state.get("outline_color_hex", config.THUMBNAIL_DEFAULT_OUTLINE_COLOR),
            placeholder="#003087",
            max_chars=7,
            help="예: #003087 (남색), #000000 (검정), #FF0000 (빨강)",
        )
        outline_hex_input = outline_hex_input.strip()
        if outline_hex_input and not outline_hex_input.startswith("#"):
            outline_hex_input = "#" + outline_hex_input
        if _is_valid_hex(outline_hex_input):
            outline_color = outline_hex_input
            st.markdown(
                f"<div style='width:100%;height:28px;background:{outline_color};"
                f"border-radius:4px;border:1px solid #888'></div>",
                unsafe_allow_html=True,
            )
            st.caption(f"색상: `{outline_color}`")
        else:
            outline_color = config.THUMBNAIL_DEFAULT_OUTLINE_COLOR
            if outline_hex_input:
                st.warning("올바른 Hex 코드를 입력하세요 (예: #003087)")

    # 미리 생성된 썸네일 표시
    if "thumbnail_filename" in st.session_state:
        thumb_path = os.path.join(config.THUMBNAILS_DIR, st.session_state.thumbnail_filename)
        if os.path.exists(thumb_path):
            st.markdown("#### 현재 썸네일 미리보기")
            st.image(thumb_path, use_container_width=True)

    col_back, col_gen, col_next = st.columns(3)
    with col_back:
        if st.button("← 이전 (이미지 재생성)"):
            st.session_state.pop("thumbnail_filename", None)
            st.session_state.step = 2
            st.rerun()

    with col_gen:
        if st.button("🎨 썸네일 생성 / 재생성", type="secondary"):
            campus_img = Image.open(st.session_state.campus_image_path)
            with st.spinner("썸네일 합성 중..."):
                fname = generate_thumbnail(
                    university_name=st.session_state.university_name,
                    text_color_hex=text_color,
                    outline_color_hex=outline_color,
                    campus_image=campus_img,
                    output_dir=config.THUMBNAILS_DIR,
                )
            if fname is None:
                st.error("❌ 썸네일 생성 실패.")
            else:
                st.session_state.thumbnail_filename = fname
                st.session_state.text_color_hex = text_color
                st.session_state.outline_color_hex = outline_color
                st.rerun()

    with col_next:
        can_proceed = "thumbnail_filename" in st.session_state or st.session_state.get("is_shorts")
        if st.button("다음 →", type="primary", disabled=not can_proceed):
            if "title" not in st.session_state:
                st.session_state.title = st.session_state.get("university_name", "")
            st.session_state.step = 4
            st.rerun()

    if "thumbnail_filename" not in st.session_state:
        if st.session_state.get("is_shorts"):
            st.info("💡 색상을 선택 후 **썸네일 생성** 버튼을 누르거나, 썸네일 없이 **다음 →** 를 누르세요.")
        else:
            st.info("💡 색상을 선택한 후 **썸네일 생성** 버튼을 눌러주세요.")


# ════════════════════════════════════════════════════════════════════════════════
# STEP 4: 제목 입력
# ════════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 4:
    st.subheader("Step 4 · YouTube 제목 입력")

    # 썸네일 미리보기
    if "thumbnail_filename" in st.session_state:
        thumb_path = os.path.join(config.THUMBNAILS_DIR, st.session_state.thumbnail_filename)
        if os.path.exists(thumb_path):
            st.image(thumb_path, caption="완성된 썸네일", use_container_width=True)

    title = st.text_input(
        "제목 (Title)",
        value=st.session_state.get("title", st.session_state.get("university_name", "")),
        max_chars=100,
    )
    st.caption(f"글자 수: {len(title)} / 100")

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← 이전"):
            st.session_state.step = 3
            st.rerun()
    with col_next:
        if st.button("다음 →", type="primary", disabled=not title.strip()):
            st.session_state.title = title.strip()
            st.session_state.step = 5
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# STEP 5: 설명 입력
# ════════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 5:
    st.subheader("Step 5 · 영상 설명 입력")
    st.caption(f"제목: **{st.session_state.title}**")

    description = st.text_area(
        "설명 (Description)",
        value=st.session_state.get("description", ""),
        height=250,
        placeholder="영상 설명을 입력하세요. (선택 사항)",
    )
    st.caption(f"글자 수: {len(description)}")

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← 이전"):
            st.session_state.step = 4
            st.rerun()
    with col_next:
        if st.button("다음 →", type="primary"):
            st.session_state.description = description
            st.session_state.step = 6
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# STEP 6: 태그 입력
# ════════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 6:
    st.subheader("Step 6 · 태그 입력")
    st.caption(f"제목: **{st.session_state.title}**")

    tags = st.text_input(
        "태그 (쉼표로 구분)",
        value=st.session_state.get("tags", ""),
        placeholder="대학교, 입시, 캠퍼스투어, 유학, Rice University",
    )
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        st.caption(f"태그 {len(tag_list)}개: {' · '.join(tag_list)}")

    if st.session_state.get("is_shorts"):
        st.info("📱 Shorts 모드: 태그에 'Shorts'가 자동으로 추가됩니다.")

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← 이전"):
            st.session_state.step = 5
            st.rerun()
    with col_next:
        if st.button("업로드 준비 →", type="primary"):
            if st.session_state.get("is_shorts"):
                tag_list = [t.strip() for t in tags.split(",") if t.strip()]
                if "Shorts" not in tag_list:
                    tag_list = ["Shorts"] + tag_list
                st.session_state.tags = ", ".join(tag_list)
            else:
                st.session_state.tags = tags
            st.session_state.step = 7
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# STEP 7: 최종 확인 & YouTube 업로드
# ════════════════════════════════════════════════════════════════════════════════
elif st.session_state.step == 7:
    st.subheader("Step 7 · YouTube Private 업로드")

    # 요약 카드
    col_thumb, col_info = st.columns([1, 2])
    with col_thumb:
        thumb_path = None
        if "thumbnail_filename" in st.session_state:
            tp = os.path.join(config.THUMBNAILS_DIR, st.session_state.thumbnail_filename)
            if os.path.exists(tp):
                thumb_path = tp
                st.image(tp, use_container_width=True)
        if thumb_path is None and st.session_state.get("is_shorts"):
            st.caption("📱 Shorts · 썸네일 없음")

    with col_info:
        st.markdown(f"**영상 파일:** `{st.session_state.video_file}`")
        if st.session_state.get("is_shorts"):
            st.markdown("**유형:** 📱 Shorts")
        if st.session_state.get("university_name"):
            st.markdown(f"**대학교:** {st.session_state.university_name}")
        st.markdown(f"**제목:** {st.session_state.title}")
        desc_preview = st.session_state.get("description", "")
        if desc_preview:
            st.markdown(f"**설명:** {desc_preview[:120]}{'...' if len(desc_preview) > 120 else ''}")
        tags_str = st.session_state.get("tags", "")
        if tags_str:
            st.markdown(f"**태그:** {tags_str}")
        st.markdown("**공개 범위:** 🔒 Private")
        st.markdown(f"**채널:** {st.session_state.get('selected_channel', 'default')}")

    st.markdown("---")
    col_back, col_upload = st.columns(2)

    with col_back:
        if st.button("← 이전"):
            st.session_state.step = 6
            st.rerun()

    with col_upload:
        if st.button("🚀 YouTube에 업로드 시작", type="primary"):
            _video_path = os.path.join(config.VIDEOS_DIR, st.session_state.video_file)
            _thumb = None
            if "thumbnail_filename" in st.session_state:
                tp = os.path.join(config.THUMBNAILS_DIR, st.session_state.thumbnail_filename)
                if os.path.exists(tp):
                    _thumb = tp
            tags_list = [
                t.strip()
                for t in st.session_state.get("tags", "").split(",")
                if t.strip()
            ]
            _channel = st.session_state.get("selected_channel", "default")
            _progress = st.empty()
            _progress.info("📤 YouTube API 인증 중...")
            try:
                uploader = YouTubeUploader(channel_name=_channel)
                _progress.info("📤 영상 업로드 중... (파일 크기에 따라 수 분 소요)")
                result = uploader.upload_video(
                    video_path=_video_path,
                    title=st.session_state.title,
                    description=st.session_state.get("description", ""),
                    tags=tags_list,
                    category=config.DEFAULT_CATEGORY,
                    privacy="private",
                    thumbnail_path=_thumb,
                )
                _progress.empty()
                st.session_state.upload_done = {
                    "video_id": result["video_id"],
                    "is_shorts": st.session_state.get("is_shorts", False),
                    "thumb_path": _thumb,
                    "channel": _channel,
                }
                st.rerun()
            except Exception as e:
                _progress.empty()
                st.error(f"❌ 업로드 실패: {e}")
                st.info("YouTube API 인증이 필요하면 터미널에서 `python auth_youtube.py`를 실행하세요.")

    # ── 업로드 완료 결과 & Community Post ─────────────────────────────────────
    if "upload_done" in st.session_state:
        ud = st.session_state.upload_done
        video_id = ud["video_id"]

        st.balloons()
        st.success("✅ 업로드 완료!")
        if ud["is_shorts"]:
            st.markdown("### 🎉 YouTube Shorts URL")
            st.markdown(f"**https://www.youtube.com/shorts/{video_id}**")
        else:
            st.markdown("### 🎉 YouTube URL")
            st.markdown(f"**https://www.youtube.com/watch?v={video_id}**")

        st.markdown("---")
        if st.button("🔄 새 영상 업로드", key="btn_new_upload"):
            st.session_state.pop("upload_done", None)
            reset_wizard()
            st.rerun()
