"""Assemble the skincare pilot reel: LongCat presenter clips + product scenes + subtitles.

720x1280 9:16 output, draft_only. Presenter clips are upscaled from 468x832 (~1.54x);
product scenes use the approved packshot on a white canvas with a slow zoom.
"""
import hashlib
import json
import subprocess
import wave
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'skincare_pilot_render_v3'
FONT = "'C\\:/Windows/Fonts/arialbd.ttf'"

PACKSHOT = 'output/product_1729964288705272356_single_pack_candidate_v2.png'
VIEW_BOTTLE = 'output/product_1729964288705272356_view_bottle.png'
VIEW_BOX = 'output/product_1729964288705272356_view_box.png'
VIEW_BRUSHHEAD = 'output/product_1729964288705272356_view_brushhead.png'

SCENES = [
    {'id': 'hook', 'video': 'output/longcat_hook/normalized.mp4'},
    {'id': 'product', 'images': [PACKSHOT, VIEW_BOTTLE],
     'audio': 'output/luisa_segments/product.wav'},
    {'id': 'usage', 'images': [VIEW_BRUSHHEAD, VIEW_BOTTLE],
     'audio': 'output/luisa_segments/usage.wav'},
    {'id': 'selection', 'images': [VIEW_BOX, PACKSHOT],
     'audio': 'output/luisa_segments/selection.wav'},
    {'id': 'cta', 'video': 'output/longcat_cta/normalized.mp4'},
]


def wav_seconds(path):
    with wave.open(str(path), 'rb') as audio:
        return audio.getnframes() / audio.getframerate()


def wrap(text, width=32):
    words, lines, line = text.split(), [], ''
    for word in words:
        candidate = (line + ' ' + word).strip()
        if len(candidate) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return '\n'.join(lines)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = json.loads((ROOT / 'output/skincare_pilot_spec.json').read_text(encoding='utf-8'))
    texts = {s['scene_id']: s['text'] for s in spec['scenes']}

    segments = []
    start = 0.0
    for index, scene in enumerate(SCENES):
        if 'video' in scene:
            manifest = json.loads((ROOT / scene['video']).parent.joinpath('manifest.json').read_text(encoding='utf-8'))
            duration = manifest['media_validation']['video_duration_seconds']
        else:
            duration = wav_seconds(ROOT / scene['audio'])
        segments.append({**scene, 'index': index, 'duration': duration, 'start': start})
        start += duration
    total = start
    print('total', round(total, 2), 's')

    seg_dir = OUT / 'segments'
    seg_dir.mkdir(exist_ok=True)
    part_files = []
    for seg in segments:
        target = seg_dir / f"part{seg['index']}.mp4"
        part_files.append(target)
        if target.exists() and target.stat().st_size > 0:
            continue
        lines_all = wrap(texts[seg['id']]).split('\n')
        chunks = ['\n'.join(lines_all[i:i + 2]) for i in range(0, len(lines_all), 2)]
        per = seg['duration'] / len(chunks)
        filters = []
        for part, chunk in enumerate(chunks):
            text_file = seg_dir / f"sub{seg['index']}_{part}.txt"
            text_file.write_text(chunk, encoding='utf-8')
            lines = chunk.count('\n') + 1
            filters.append(
                f"drawtext=fontfile={FONT}:textfile='{text_file.as_posix().replace(':', '\\:')}'"
                ":fontsize=38:fontcolor=white:borderw=3:bordercolor=black:line_spacing=-6:"
                f"text_align=C:x=(w-text_w)/2:y=h-150-{lines}*40:"
                f"enable='gte(t\\,{part * per:.3f})*lt(t\\,{(part + 1) * per:.3f})'")
        subtitle = ','.join(filters)
        if 'video' in seg:
            subprocess.run([FFMPEG, '-y', '-i', str(ROOT / seg['video']),
                            '-vf', f'scale=720:1280,{subtitle}',
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                            '-c:a', 'aac', '-b:a', '128k',
                            str(target)], check=True, capture_output=True)
        else:
            images = seg['images']
            per_image = seg['duration'] / len(images)
            cmd = [FFMPEG, '-y']
            branches = []
            for image_index, image in enumerate(images):
                frames_i = int(round(per_image * 25))
                cmd += ['-loop', '1', '-t', f'{per_image:.3f}', '-i', str(ROOT / image)]
                branches.append(
                    f"[{image_index}:v]scale=700:1280:force_original_aspect_ratio=decrease,"
                    f"pad=720:1280:(ow-iw)/2:(oh-ih)/2:white,"
                    f"zoompan=z='min(1+0.06*on/{frames_i},1.06)':d=1:"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=720x1280:fps=25[v{image_index}]")
            cmd += ['-i', str(ROOT / seg['audio'])]
            concat_inputs = ''.join(f'[v{i}]' for i in range(len(images)))
            graph = ';'.join(branches) + \
                f";{concat_inputs}concat=n={len(images)}:v=1:a=0[vcat];[vcat]{subtitle}[vout]"
            subprocess.run(cmd + ['-filter_complex', graph,
                            '-map', '[vout]', '-map', f'{len(images)}:a',
                            '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                            '-c:a', 'aac', '-b:a', '128k', '-t', str(seg['duration']), '-shortest',
                            str(target)], check=True, capture_output=True)

    concat = OUT / 'concat.txt'
    concat.write_text(''.join(f"file '{p.as_posix()}'\n" for p in part_files))
    final = OUT / 'skincare_pilot_v3.mp4'
    subprocess.run([FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', str(concat),
                    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k',
                    str(final)], check=True, capture_output=True)

    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    manifest = {'reel_id': spec['reel_id'], 'total_duration_sec': total,
                'resolution': '720x1280', 'scenes': segments,
                'sources': {s['id']: s.get('video') or {'images': s['images'], 'audio': s['audio']}
                            for s in segments},
                'output_sha256': sha(final), 'draft_only': True,
                'production_approved': False,
                'quality_status': 'pending_visual_and_auditory_review',
                'commercial_dependency_review': 'pending'}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print('rendered', final, round(total, 2), 's')


if __name__ == '__main__':
    main()
