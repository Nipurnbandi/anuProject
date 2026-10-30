"""Sparse-frame video analysis with short-lived anonymous person tracks."""

import cv2
import numpy as np


def analyze_video(path, sample_fps=1.0, min_present_seconds=3.0, progress=None):
    """Analyze a recording and return temporary tracks plus time-stamped signals.

    HOG detects upright pedestrians; it is intentionally used without face
    recognition. A centroid matcher connects nearby detections between samples.
    """
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("Could not open this video. Try MP4, AVI, or MOV.")

    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if not fps or not np.isfinite(fps) or fps <= 0:
        capture.release()
        raise ValueError("The video does not report a valid frame rate.")
    duration = frame_count / fps if frame_count else 0.0
    sample_fps = max(.1, min(float(sample_fps), fps))
    stride = max(1, int(round(fps / sample_fps)))
    sample_period = stride / fps

    detector = cv2.HOGDescriptor()
    detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    tracks = {}
    frame_signals = []
    previous_gray = None
    frame_index = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % stride == 0:
                timestamp = frame_index / fps
                height, width = frame.shape[:2]
                # Resize only large frames; HOG's standard pedestrian window
                # needs enough pixels to retain a useful body silhouette.
                scale = min(1.0, 720 / max(height, width))
                view = cv2.resize(frame, (int(width * scale), int(height * scale))) if scale < 1 else frame
                gray = cv2.cvtColor(cv2.resize(view, (320, 180)), cv2.COLOR_BGR2GRAY)
                motion = 0.0
                if previous_gray is not None:
                    change = cv2.absdiff(gray, previous_gray)
                    motion = min(1.0, float(np.mean(change > 18)) * 5)
                previous_gray = gray

                rectangles, strengths = detector.detectMultiScale(
                    view, winStride=(8, 8), padding=(8, 8), scale=1.05
                )
                detections = []
                for (x, y, box_width, box_height), strength in zip(rectangles, strengths):
                    if box_height >= 80:
                        detections.append((x + box_width / 2, y + box_height / 2, float(strength)))

                # Greedy nearest-neighbour association. Each old track can
                # receive at most one detection in this sample.
                matched = set()
                for x, y, strength in detections:
                    candidate, distance = None, float("inf")
                    for track_id, track in tracks.items():
                        if track_id in matched or timestamp - track["last"] > 3 * sample_period + 1:
                            continue
                        delta = float(np.hypot(x - track["x"], y - track["y"]))
                        if delta < distance and delta < max(view.shape[:2]) * .16:
                            candidate, distance = track_id, delta
                    if candidate is None:
                        candidate = f"T{len(tracks) + 1:03d}"
                        tracks[candidate] = {
                            "first": timestamp, "last": timestamp, "hits": 0,
                            "x": x, "y": y, "confidence": [], "observed": 0.0,
                        }
                    track = tracks[candidate]
                    # Attendance time is sampled observation time, rather than
                    # the full first-to-last span that can include missed gaps.
                    track["observed"] += sample_period
                    track.update(last=timestamp, x=x, y=y, hits=track["hits"] + 1)
                    track["confidence"].append(float(np.clip(strength / 2, 0, 1)))
                    matched.add(candidate)

                frame_signals.append({
                    "time": timestamp,
                    "people": len(detections),
                    "motion": motion,
                    "track_ids": sorted(matched),
                })

            frame_index += 1
            if progress and frame_index % max(1, stride * 12) == 0 and frame_count:
                progress(min(.95, frame_index / frame_count))
    finally:
        capture.release()

    attendance = []
    for track_id, track in tracks.items():
        is_present = track["hits"] >= 2 and track["observed"] >= min_present_seconds
        attendance.append({
            "participant_id": track_id,
            "first_detected": round(track["first"], 2),
            "last_detected": round(track["last"], 2),
            "duration_seconds": round(track["observed"], 2),
            "status": "Present" if is_present else "Review",
            "quality": round(float(np.mean(track["confidence"])), 3),
            "detections": track["hits"],
        })

    return {
        "duration_seconds": duration or frame_index / fps,
        "sample_fps": round(fps / stride, 3),
        "attendance": attendance,
        "frames": frame_signals,
    }
