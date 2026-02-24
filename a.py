"""
사진 촬영 및 이미지 분석 웹사이트
웹캠으로 사진을 촬영하고 분석 결과를 확인할 수 있습니다.
"""

import os
import io
import base64
from flask import Flask, render_template, request, jsonify
from PIL import Image
from collections import Counter
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 제한
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def analyze_image(image_data):
    """이미지를 분석하여 다양한 정보를 추출합니다."""
    img = Image.open(io.BytesIO(image_data))
    
    # RGB 변환 (RGBA, P 모드 등 처리)
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGB')
    
    width, height = img.size
    total_pixels = width * height
    
    # 메타데이터
    metadata = dict(img.info) if img.info else {}
    
    # 지배색 분석 (리사이즈하여 빠르게 처리)
    img_small = img.copy()
    img_small.thumbnail((100, 100))
    pixels = list(img_small.getdata())
    
    # 주요 색상 5개 (양자화)
    def quantize(rgb, step=32):
        return tuple((c // step) * step for c in rgb)
    
    if img_small.mode == 'RGBA':
        pixels = [quantize(p[:3]) for p in pixels if p[3] > 128]
    else:
        pixels = [quantize(p) for p in pixels]
    
    color_counts = Counter(pixels)
    top_colors = color_counts.most_common(5)
    
    # 밝기 분석
    gray_img = img.convert('L')
    gray_pixels = list(gray_img.getdata())
    avg_brightness = sum(gray_pixels) / len(gray_pixels)
    
    # 저조/중조/고조 비율
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
            {'rgb': f"rgb({r},{g},{b})", 'hex': f"#{r:02x}{g:02x}{b:02x}"}
            for (r, g, b), _ in top_colors
        ],
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Base64 데이터 또는 파일 업로드 처리
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
            image_data = file.read()
        elif request.is_json and 'image_data' in request.json:
            # data URL에서 base64 추출
            data_url = request.json['image_data']
            if ',' in data_url:
                image_data = base64.b64decode(data_url.split(',')[1])
            else:
                image_data = base64.b64decode(data_url)
        else:
            return jsonify({'error': '이미지 데이터가 없습니다.'}), 400
        
        result = analyze_image(image_data)
        
        # 분석된 이미지를 썸네일로 저장 (선택적)
        filename = datetime.now().strftime('%Y%m%d_%H%M%S') + '.jpg'
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        img = Image.open(io.BytesIO(image_data))
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(filepath, 'JPEG', quality=85)
        result['saved_file'] = filename
        
        return jsonify({'success': True, 'analysis': result})
    
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
