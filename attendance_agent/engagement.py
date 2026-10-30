"""Transparent session-level activity indicator calculations."""


def score_intervals(frames, audio, bin_seconds=300):
    if not frames:
        return []
    bin_seconds = max(1, int(bin_seconds))
    duration = max((float(item["time"]) for item in frames), default=0) + 1
    people_scale = max(1, max(int(item.get("people", 0)) for item in frames))
    motion_scale = max((float(item.get("motion", 0)) for item in frames), default=0) or 1
    audio_windows = (audio or {}).get("windows", [])

    results = []
    start = 0
    while start < duration:
        end = min(start + bin_seconds, duration)
        samples = [item for item in frames if start <= item["time"] < end]
        if not samples:
            start += bin_seconds
            continue

        presence = sum(min(1, item.get("people", 0) / people_scale) for item in samples) / len(samples)
        movement = sum(min(1, item.get("motion", 0) / motion_scale) for item in samples) / len(samples)

        # Allocate audio signal windows by their overlap with this time bin.
        active_seconds = measured_seconds = 0.0
        for window in audio_windows:
            overlap = max(0.0, min(end, window["end"]) - max(start, window["start"]))
            measured_seconds += overlap
            if window["active"]:
                active_seconds += overlap
        audio_activity = active_seconds / measured_seconds if measured_seconds else 0.0

        if audio:
            estimate = 100 * (.50 * presence + .30 * movement + .20 * audio_activity)
        else:
            estimate = 100 * ((.50 * presence + .30 * movement) / .80)

        results.append({
            "start_seconds": start,
            "end_seconds": end,
            "people_avg": sum(item.get("people", 0) for item in samples) / len(samples),
            "active_participants": max(item.get("people", 0) for item in samples),
            "presence": presence,
            "motion": movement,
            "audio_activity": audio_activity,
            "engagement": round(estimate, 1),
            "sample_count": len(samples),
        })
        start += bin_seconds
    return results
