import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import requests
from PIL import Image, ImageDraw

MODEL_PATH = 'models/face_detection_yunet/face_detection_yunet_2026may.onnx'


def alignment_geometry(box, eyes_y, nose_y, image_height):
    x, y, width, height = box
    if not all(math.isfinite(value) for value in (*box, eyes_y, nose_y, image_height)) or width <= 0 or height <= 0 or not y < eyes_y < nose_y < y + height:
        raise ValueError('Invalid face geometry')
    old_top = int(y) + int(height * 0.28)
    bottom = min(image_height, int(y + height) + int(height * 0.08) + 10)
    target = eyes_y + 0.75 * (nose_y - eyes_y)
    shift = round(2 * target - bottom - old_top)
    if not -160 <= shift <= 160 or old_top + shift < 0 or old_top + shift >= bottom:
        raise ValueError('Required face adjustment is outside the isolated test range')
    return {
        'proxy_crop_top': old_top, 'proxy_crop_bottom': bottom,
        'proxy_mask_midline': (old_top + bottom) / 2,
        'nose_bridge_target_approximation': target,
        'bbox_shift_candidate': shift,
        'adjusted_proxy_midline': (old_top + shift + bottom) / 2,
        'method_limit': 'YuNet box is a proxy, not the provider S3FD box. Nose-bridge target is an approximation, not an upstream 68-point landmark.',
    }


def download_model(path):
    if path.exists():
        raise ValueError('Model path already exists; retain and inspect rather than overwrite')
    session = requests.Session()
    session.trust_env = False
    pointer = session.get('https://raw.githubusercontent.com/opencv/opencv_zoo/main/' + MODEL_PATH, timeout=30)
    pointer.raise_for_status()
    if not pointer.content.startswith(b'version https://git-lfs.github.com/spec/v1'):
        raise ValueError('Expected the Git LFS pointer with a model checksum')
    checksum = next(line.split('sha256:')[1] for line in pointer.text.splitlines() if line.startswith('oid sha256:'))
    size = int(next(line.split(' ')[1] for line in pointer.text.splitlines() if line.startswith('size ')))
    if size > 2_000_000:
        raise ValueError('Unexpected detector size')
    response = session.get('https://media.githubusercontent.com/media/opencv/opencv_zoo/main/' + MODEL_PATH, timeout=60)
    response.raise_for_status()
    if len(response.content) != size or hashlib.sha256(response.content).hexdigest() != checksum:
        raise ValueError('Detector does not match the reviewed LFS pointer')
    with path.open('xb') as output:
        output.write(response.content)
    return checksum


def diagnose(directory):
    model = directory / 'yunet_2026may.onnx'
    checksum = download_model(model)
    frame = cv2.imread(str(directory / 'presenter_crop.png'))
    if frame is None:
        raise ValueError('Prepared portrait unavailable')
    height, width = frame.shape[:2]
    detector = cv2.FaceDetectorYN_create(str(model), '', (width, height), 0.9)
    _, faces = detector.detect(frame)
    if faces is None or len(faces) != 1:
        raise ValueError('Expected exactly one face')
    face = faces[0].tolist()
    eye_y = (face[5] + face[7]) / 2
    nose_y = face[9]
    geometry = alignment_geometry(face[:4], eye_y, nose_y, height)
    image = Image.open(directory / 'presenter_crop.png').convert('RGB')
    draw = ImageDraw.Draw(image)
    for y, color in ((geometry['proxy_mask_midline'], 'red'), (geometry['nose_bridge_target_approximation'], 'lime'), (nose_y, 'cyan')):
        draw.line((0, int(y), width, int(y)), fill=color, width=2)
    for i in range(4, 14, 2):
        x, y = face[i:i + 2]
        draw.ellipse((x-3, y-3, x+3, y+3), fill='yellow')
    draw.rectangle((0, 0, width, 68), fill='black')
    draw.text((6, 6), 'RED: estimated current mask split\nGREEN: approximate nose-bridge target\nCYAN: detected nose tip; YELLOW: landmarks', fill='white')
    image.save(directory / 'alignment_diagnostic.png')
    result = {'detector': 'OpenCV YuNet, CPU', 'model_sha256': checksum,
              'face_box_yunet': face[:4], 'eyes_y': eye_y, 'nose_y': nose_y,
              'mouth_y': (face[11] + face[13]) / 2, **geometry,
              'generation_submitted': False, 'production_approved': False}
    (directory / 'alignment.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, default=Path('output/presenter_lipsync_jonas_short'))
    args = parser.parse_args()
    print(json.dumps(diagnose(args.directory), indent=2))
