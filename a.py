"""
사진 촬영 및 이미지 분석 웹사이트 (Streamlit)
웹캠으로 사진을 촬영하거나 파일을 업로드하여 분석 결과를 확인할 수 있습니다.
"""

import os
import io
from PIL import Image
from collections import Counter
from datetime import datetime
import streamlit as st

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="사진 촬영 & 이미지 분석",
    page_icon="📸",
    layout="wide",
)

st.title("📸 사진 촬영 & 이미지 분석")
st.caption("웹캠으로 사진을 찍거나 이미지를 업로드하면 분석해드립니다")


def analyze_image(image_data):
    """이미지를 분석하여 다양한 정보를 추출합니다."""
    img = Image.open(io.BytesIO(image_data))

    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')

    width, height = img.size
    total_pixels = width * height

    img_small = img.copy()
    img_small.thumbnail((100, 100))
    pixels = list(img_small.getdata())

    def quantize(rgb, step=32):
        return tuple((c // step) * step for c in rgb)

    if img_small.mode == 'RGBA':
        pixels = [quantize(p[:3]) for p in pixels if p[3] > 128]
    else:
        pixels = [quantize(p) for p in pixels]

    color_counts = Counter(pixels)
    top_colors = color_counts.most_common(5)

    gray_img = img.convert('L')
    gray_pixels = list(gray_img.getdata())
    avg_brightness = sum(gray_pixels) / len(gray_pixels)

    dark = sum(1 for p in gray_pixels if p < 85) / len(gray_pixels) * 100
    mid = sum(1 for p in gray_pixels if 85 <= p <= 170) / len(gray_pixels) * 100
    bright = sum(1 for p in gray_pixels if p > 170) / len(gray_pixels) * 100

    return {
        'size': {'width': width, 'height': height},
        'aspect_ratio': f"{width}:{height}" if width > 0 else "N/A",
        'total_pixels': f"{total_pixels:,}",
        'format': img.format or 'Unknown',
        'mode': img.mode,
        'brightness': {
            'average': round(avg_brightness, 1),
            'dark': round(dark, 1),
            'mid': round(mid, 1),
            'bright': round(bright, 1),
        },
        'dominant_colors': [
            {'rgb': (r, g, b), 'hex': f"#{r:02x}{g:02x}{b:02x}"}
            for (r, g, b), _ in top_colors
        ],
        'img': img,
    }


# 입력 방식 선택
input_method = st.radio(
    "이미지 입력 방식",
    ["📷 웹캠 촬영", "📁 파일 업로드"],
    horizontal=True,
)

image_data = None

if input_method == "📷 웹캠 촬영":
    photo = st.camera_input("사진을 촬영하세요")
    if photo:
        image_data = photo.read()
        st.image(image_data, caption="촬영된 사진", use_container_width=True)

else:
    uploaded_file = st.file_uploader("이미지 파일을 선택하세요", type=["jpg", "jpeg", "png", "gif", "webp"])
    if uploaded_file:
        image_data = uploaded_file.read()
        st.image(image_data, caption="업로드된 이미지", use_container_width=True)

# 분석 실행
if image_data:
    if st.button("🔍 이미지 분석", type="primary"):
        with st.spinner("이미지 분석 중..."):
            try:
                result = analyze_image(image_data)

                # 저장
                filename = datetime.now().strftime('%Y%m%d_%H%M%S') + '.jpg'
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                img = result['img']
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                img.save(filepath, 'JPEG', quality=85)

                st.success(f"✅ 분석 완료! (저장: {filename})")

                # 분석 결과 표시
                st.subheader("📊 분석 결과")

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("해상도", f"{result['size']['width']} × {result['size']['height']}")
                with col2:
                    st.metric("화면 비율", result['aspect_ratio'])
                with col3:
                    st.metric("총 픽셀", result['total_pixels'])
                with col4:
                    st.metric("형식", result['format'])
                with col5:
                    st.metric("평균 밝기", f"{result['brightness']['average']}/255")

                st.write("**밝기 분포**")
                b = result['brightness']
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("저조 (0~84)", f"{b['dark']}%")
                    st.progress(b['dark'] / 100)
                with c2:
                    st.metric("중조 (85~170)", f"{b['mid']}%")
                    st.progress(b['mid'] / 100)
                with c3:
                    st.metric("고조 (171~255)", f"{b['bright']}%")
                    st.progress(b['bright'] / 100)

                st.write("**지배색 Top 5**")
                color_boxes = "".join(
                    f'<span style="display: inline-block; width: 50px; height: 50px; background: {c["hex"]}; '
                    f'border-radius: 8px; margin: 4px; border: 2px solid #333;" title="{c["hex"]}"></span>'
                    for c in result['dominant_colors']
                )
                st.markdown(f'<div style="margin: 10px 0;">{color_boxes}</div>', unsafe_allow_html=True)
                st.caption(" ".join(c['hex'] for c in result['dominant_colors']))

            except Exception as e:
                st.error(f"분석 중 오류가 발생했습니다: {str(e)}")
