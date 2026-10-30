import os, shutil, subprocess, tempfile, wave
import numpy as np


def analyze_audio(video_path, window_seconds=1.0):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        return None
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.close()
    try:
        result = subprocess.run([ffmpeg, '-v', 'error', '-y', '-i', str(video_path), '-vn', '-ac', '1', '-ar', '16000', tmp.name], capture_output=True, timeout=180)
        if result.returncode:
            return None
        with wave.open(tmp.name, 'rb') as wf:
            rate, n = wf.getframerate(), wf.getnframes()
            raw = wf.readframes(n)
        data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
        if not len(data): return None
        size = max(1, int(rate*window_seconds))
        rms = np.array([np.sqrt(np.mean(data[i:i+size]**2)) for i in range(0, len(data), size)])
        floor = max(.008, float(np.percentile(rms, 25))*2.0)
        active = rms > floor
        segments, inside = [], False
        for i, on in enumerate(active):
            if on and not inside: start = i*window_seconds; inside = True
            if inside and (not on or i == len(active)-1):
                end = (i if not on else i+1)*window_seconds
                if end-start >= 1: segments.append({'start': start, 'end': end})
                inside = False
        return {
            'duration_seconds': len(data) / rate,
            'activity_fraction': float(np.mean(active)),
            'activity_seconds': float(np.sum(active) * window_seconds),
            'silence_seconds': float(max(0, len(data) / rate - np.sum(active) * window_seconds)),
            'segments': segments,
            'windows': [
                {'start': i * window_seconds,
                 'end': min((i + 1) * window_seconds, len(data) / rate),
                 'active': bool(value)}
                for i, value in enumerate(active)
            ],
        }
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    finally:
        try: os.unlink(tmp.name)
        except OSError: pass
