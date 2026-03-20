"""
Thumbnail Generator v2
======================
1. Google Gemini Imagen 3 로 대학교 캠퍼스 이미지 생성
2. Thumbnail-Balnk-Frame.jpg 를 기본 프레임으로 로드
3. 프레임의 흰색 영역에 캠퍼스 이미지를 합성
4. 대학교 이름 텍스트를 중앙에 렌더링 (사용자 지정 색상 + 외곽선)
5. YouTube 규격(1280×720 JPEG) 파일로 저장
"""

import io
import os
import re
import traceback
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import config


# ── 유틸리티 ──────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """'#RRGGBB' 또는 'RRGGBB' 문자열을 (R, G, B) 튜플로 변환."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _find_font() -> Optional[str]:
    """우선순위 목록에서 실제로 존재하는 첫 번째 폰트 경로를 반환."""
    for path in config.THUMBNAIL_FONT_PATHS:
        if os.path.exists(path):
            return path
    return None


def _split_name_into_lines(name: str) -> List[str]:
    """
    대학교 이름을 2줄로 분할합니다.
    - 1단어  → 1줄 그대로
    - 2단어  → 각각 1줄씩
    - 3단어+ → 전체 글자 수가 균등해지도록 분할점 탐색
    """
    words = name.split()
    if len(words) <= 1:
        return [name]
    if len(words) == 2:
        return words

    best_split = 1
    best_diff = float("inf")
    for i in range(1, len(words)):
        line1 = " ".join(words[:i])
        line2 = " ".join(words[i:])
        diff = abs(len(line1) - len(line2))
        if diff < best_diff:
            best_diff = diff
            best_split = i

    return [" ".join(words[:best_split]), " ".join(words[best_split:])]


def _detect_white_area(frame: Image.Image) -> Tuple[int, int, int, int]:
    """
    프레임 이미지에서 흰색 콘텐츠 영역을 탐지합니다.
    Returns: (x, y, width, height)
    JPEG 압축으로 인한 노이즈를 고려해 임계값을 230으로 설정.
    """
    arr = np.array(frame.convert("RGB"))
    white_mask = (arr[:, :, 0] > 230) & (arr[:, :, 1] > 230) & (arr[:, :, 2] > 230)

    rows = np.where(white_mask.any(axis=1))[0]
    cols = np.where(white_mask.any(axis=0))[0]

    if len(rows) == 0 or len(cols) == 0:
        # 폴백: 전체에서 좌우 28px, 상단 75px, 하단 20px 제외
        return 28, 75, frame.width - 56, frame.height - 95

    x = int(cols[0])
    y = int(rows[0])
    w = int(cols[-1]) - x + 1
    h = int(rows[-1]) - y + 1
    return x, y, w, h


# ── 캠퍼스 이미지 생성 ──────────────────────────────────────────────────────────

def generate_campus_image(university_name: str) -> tuple:
    """
    Google Gemini 로 대학교 캠퍼스 이미지를 생성합니다.

    Imagen 3 (imagen-3.0-generate-001) 를 먼저 시도하고,
    실패 시 Gemini 2.0 Flash 이미지 생성으로 폴백합니다.

    Args:
        university_name: 대학교 이름 (영문)

    Returns:
        (PIL Image | None, error_message | None)
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    prompt = (
        f"Professional wide-angle aerial photograph of {university_name} campus. "
        f"Beautiful university buildings and classic architecture, lush green lawns, "
        f"tall trees with full foliage, clear blue sky with fluffy white clouds, "
        f"daytime, vibrant natural colors, photorealistic, no text, no watermarks, "
        f"no people in foreground, high resolution. "
        f"No aircraft, no drones, no blimps, no airships, no birds, nothing in the sky except clouds."
    )

    error1 = None

    # 1차 시도: Imagen 4 (고화질)
    try:
        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="16:9",
            ),
        )
        image_bytes = response.generated_images[0].image.image_bytes
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return img, None   # print 전에 반환 (Windows 콘솔 인코딩 오류 방지)

    except Exception as e:
        error1 = str(e)

    # 2차 시도: Imagen 4 Fast (빠른 버전)
    try:
        response = client.models.generate_images(
            model="imagen-4.0-fast-generate-001",
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/jpeg",
                aspect_ratio="16:9",
            ),
        )
        image_bytes = response.generated_images[0].image.image_bytes
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return img, None

    except Exception as e:
        error2 = str(e)
        error_msg = f"Imagen 4 error: {error1}\nImagen 4 Fast error: {error2}"
        return None, error_msg


# ── 텍스트 렌더링 ──────────────────────────────────────────────────────────────

def _draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
    outline_width: int,
) -> None:
    """외곽선(모든 방향 오프셋)을 그린 뒤 본문 텍스트를 렌더링합니다."""
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


# ── 썸네일 생성 (최종) ──────────────────────────────────────────────────────────

def generate_thumbnail(
    university_name: str,
    text_color_hex: str,
    outline_color_hex: str,
    campus_image: Image.Image,
    output_dir: str,
) -> Optional[str]:
    """
    최종 썸네일을 합성하여 저장합니다.

    처리 순서:
      1. Thumbnail-Balnk-Frame.jpg 로드
      2. 흰색 콘텐츠 영역 탐지
      3. 캠퍼스 이미지를 해당 영역 크기로 리사이즈
      4. 캠퍼스 이미지를 캔버스에 배치
      5. 프레임의 어두운 부분(테두리/배너)을 위에 오버레이
      6. 대학교 이름 텍스트를 중앙에 렌더링
      7. JPEG 저장

    Args:
        university_name:  대학교 이름 (텍스트 오버레이에 사용)
        text_color_hex:   텍스트 색상 Hex (예: '#FFFFFF')
        outline_color_hex: 외곽선 색상 Hex (예: '#003087')
        campus_image:     generate_campus_image() 가 반환한 PIL Image
        output_dir:       저장 폴더 경로

    Returns:
        성공 시 저장된 파일명(basename), 실패 시 None
    """
    try:
        # 1. 프레임 로드
        if not os.path.exists(config.THUMBNAIL_FRAME_FILE):
            raise FileNotFoundError(
                f"프레임 파일 없음: {config.THUMBNAIL_FRAME_FILE}"
            )
        frame = Image.open(config.THUMBNAIL_FRAME_FILE).convert("RGB")
        fw, fh = frame.size

        # 2. 흰색 콘텐츠 영역 탐지
        cx, cy, cw, ch = _detect_white_area(frame)
        print(f"  콘텐츠 영역: x={cx}, y={cy}, w={cw}, h={ch}")

        # 3. 캠퍼스 이미지를 콘텐츠 영역 크기로 리사이즈 (커버 방식)
        campus_aspect = campus_image.width / campus_image.height
        area_aspect   = cw / ch
        if campus_aspect > area_aspect:
            # 좌우가 더 넓음 → 높이 기준으로 맞추고 좌우 크롭
            scale_h  = ch
            scale_w  = int(campus_image.width * ch / campus_image.height)
            resized  = campus_image.resize((scale_w, scale_h), Image.LANCZOS)
            x_offset = (scale_w - cw) // 2
            campus_cropped = resized.crop((x_offset, 0, x_offset + cw, ch))
        else:
            # 상하가 더 높음 → 너비 기준으로 맞추고 상하 크롭
            scale_w  = cw
            scale_h  = int(campus_image.height * cw / campus_image.width)
            resized  = campus_image.resize((scale_w, scale_h), Image.LANCZOS)
            y_offset = (scale_h - ch) // 2
            campus_cropped = resized.crop((0, y_offset, cw, y_offset + ch))

        # 4. 캔버스에 캠퍼스 이미지 배치 (프레임과 같은 크기의 캔버스)
        canvas = frame.copy()
        canvas.paste(campus_cropped, (cx, cy))

        # 5. 프레임의 어두운 영역(배너, 테두리)을 위에 오버레이
        #    → 프레임에서 흰색 픽셀을 투명으로 처리 후 합성
        frame_arr  = np.array(frame)
        frame_rgba = np.zeros((fh, fw, 4), dtype=np.uint8)
        frame_rgba[:, :, :3] = frame_arr
        white_mask = (
            (frame_arr[:, :, 0] > 230)
            & (frame_arr[:, :, 1] > 230)
            & (frame_arr[:, :, 2] > 230)
        )
        frame_rgba[:, :, 3] = np.where(white_mask, 0, 255)

        frame_overlay = Image.fromarray(frame_rgba, "RGBA")
        canvas_rgba   = canvas.convert("RGBA")
        canvas_rgba.paste(frame_overlay, (0, 0), frame_overlay)
        result = canvas_rgba.convert("RGB")

        # 5.5: 상단 ELITEPREP.COM 배지 텍스트 → 흰색, 배경 → 진한 남색
        result_arr = np.array(result)
        badge_area = result_arr[:70, :].copy()
        bright_mask = (
            (badge_area[:, :, 0] > 210) &
            (badge_area[:, :, 1] > 210) &
            (badge_area[:, :, 2] > 210)
        )
        if bright_mask.any():
            rows = np.where(bright_mask.any(axis=1))[0]
            cols = np.where(bright_mask.any(axis=0))[0]
            py1, py2 = int(rows[0]), int(rows[-1]) + 1
            px1, px2 = int(cols[0]), int(cols[-1]) + 1
            pill = badge_area[py1:py2, px1:px2].copy()
            # 어두운 텍스트 픽셀 → 흰색
            dark = (pill[:, :, 0] < 100) & (pill[:, :, 1] < 100) & (pill[:, :, 2] < 100)
            pill[dark] = [255, 255, 255]
            # 밝은 배경 픽셀 → 진한 남색
            bright_bg = (pill[:, :, 0] > 200) & (pill[:, :, 1] > 200) & (pill[:, :, 2] > 200)
            pill[bright_bg] = [30, 45, 100]
            badge_area[py1:py2, px1:px2] = pill
            result_arr[:70, :] = badge_area
            result = Image.fromarray(result_arr)

        # 6. 텍스트 렌더링
        text_color    = _hex_to_rgb(text_color_hex)
        outline_color = _hex_to_rgb(outline_color_hex)
        lines         = _split_name_into_lines(university_name)
        font_path     = _find_font()
        draw          = ImageDraw.Draw(result)
        ow            = config.THUMBNAIL_OUTLINE_WIDTH

        # 폰트 크기 자동 조정: 콘텐츠 영역의 최대 93% 너비 / 88% 높이에 맞을 때까지 축소
        font_size = 300
        font = None
        while font_size >= 40:
            try:
                font = (
                    ImageFont.truetype(font_path, font_size)
                    if font_path
                    else ImageFont.load_default()
                )
            except Exception:
                font = ImageFont.load_default()

            bboxes    = [draw.textbbox((0, 0), line, font=font) for line in lines]
            max_lw    = max(bb[2] - bb[0] for bb in bboxes)
            spacing   = int(font_size * 0.05)
            total_lh  = sum(bb[3] - bb[1] for bb in bboxes) + spacing * (len(lines) - 1)

            if max_lw <= cw * 0.93 and total_lh <= ch * 0.88:
                break
            font_size -= 6

        # 텍스트 블록 전체를 콘텐츠 영역 중앙에 배치
        bboxes    = [draw.textbbox((0, 0), line, font=font) for line in lines]
        lwidths   = [bb[2] - bb[0] for bb in bboxes]
        lheights  = [bb[3] - bb[1] for bb in bboxes]
        spacing   = int(font_size * 0.05)
        total_lh  = sum(lheights) + spacing * (len(lines) - 1)

        start_y = cy + (ch - total_lh) // 2
        cur_y   = start_y

        for i, line in enumerate(lines):
            lx = cx + (cw - lwidths[i]) // 2
            _draw_outlined_text(draw, lx, cur_y, line, font, text_color, outline_color, ow)
            cur_y += lheights[i] + spacing

        # 7. JPEG 저장
        os.makedirs(output_dir, exist_ok=True)
        safe_name  = re.sub(r"[^\w\-]", "_", university_name)[:40]
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename   = f"thumb_{safe_name}_{timestamp}.jpg"
        output_path = os.path.join(output_dir, filename)
        result.save(output_path, "JPEG", quality=config.THUMBNAIL_QUALITY)

        print(f"  썸네일 저장 완료: {filename}")
        return filename

    except Exception as e:
        print(f"  썸네일 생성 실패: {e}")
        traceback.print_exc()
        return None
