# Multimodal Attendance & Engagement Agent

A local, privacy-conscious classroom session analysis demo. It processes uploaded video on this machine, assigns anonymous temporary track IDs, estimates attendance from sustained detections, measures scene motion and optional audio activity, and produces explainable instructor suggestions. It does not identify students or infer emotions, intent, or academic ability.

## Run

Python 3.10+ is recommended (tested code uses common OpenCV/NumPy/Streamlit APIs). In PowerShell from this folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open the local URL shown by Streamlit. Choose MP4, MOV, AVI, or MKV in the Session workspace sidebar, set the timeline interval and sampling rate, then select **Analyze recording**. Review the overview, presence tracks, teaching notes, and export tabs. Processing is local. Optional audio extraction uses `ffmpeg` if installed; without it, video and motion analysis still work. Reports can be downloaded as JSON/CSV. The uploaded video is processed from a temporary local file and removed after analysis; derived session data is saved in `data/attendance.db`. Use Delete in Export & history to remove a session and its records.

## What the estimates mean

OpenCV's HOG person detector scans sampled frames and a lightweight centroid matcher links nearby detections. Detection can miss people, especially in crowded, distant, occluded, or dim scenes; IDs are anonymous within a session and are not identities. The sustained-presence estimate requires multiple detections and accumulates sampled observation time; it does not treat the entire gap between the first and last sighting as attendance. Movement is a scene-level motion signal and can reflect the instructor, camera, or environment. Audio uses short-window RMS energy only and never transcribes or stores speech. Engagement is a heuristic indicator, not a validated measure of attention or learning.

Engagement per interval is `0.50 × normalized people presence + 0.30 × normalized scene motion + 0.20 × audio activity fraction` (audio term omitted and remaining weights renormalized when audio is unavailable). These values support instructor reflection only; no automated disciplinary or academic decisions should be made from them.

## Architecture

`app.py` is the Streamlit dashboard. `attendance_agent/` contains video detection/tracking, optional audio signal processing, transparent engagement scoring, rule-based recommendations, SQLite persistence, and report serialization. `data/` stores the local SQLite database. No cloud APIs are called.

## University submission notes

### Abstract and problem
Manual attendance and basic presence systems do not provide session-level activity context. This project demonstrates a local multimodal pipeline that extracts anonymous sustained-presence estimates, aggregate scene motion, and audio activity, then summarizes these signals for an instructor.

### Objectives and scope
Provide a practical recorded-video workflow, timestamped presence estimates, interval-level activity indicators, explainable recommendations, local persistence, and exportable reports. It does not perform face recognition, speech transcription, identity verification, or validated psychological assessment. Live webcam operation and student-level attention classification are outside current scope.

### Existing and proposed systems
Manual registers capture presence but not session dynamics. The proposed local application combines sparse-frame person detection, temporal centroid association, audio energy analysis when available, transparent weighted scoring, and deterministic recommendations.

### Methodology and algorithms
Frames are sampled at a configurable low rate. OpenCV HOG+SVM detects upright pedestrians. Greedy nearest-centroid association within a spatial threshold assigns anonymous IDs; tracks with detections over a minimum duration qualify as present. Scene motion is estimated from thresholded frame differences. Optional audio is extracted to a temporary WAV with FFmpeg and analyzed using frame RMS against an adaptive noise floor. Time bins aggregate presence, motion, and audio fraction. A rule engine maps low activity, prolonged quiet, and activity peaks to suggestions with reasons.

### Architecture and modules
Video processor (OpenCV), audio analyzer (FFmpeg + Python wave/NumPy), attendance and engagement analytics, rule-based recommendation agent, SQLite repository, and Streamlit dashboard.

### Requirements
Functional: upload and analyze video; view/export attendance and interval analytics; view recommendations; delete stored session data. Non-functional: local-first, explainable, modular, and usable without an API key. Hardware: ordinary laptop, 4 GB RAM recommended. Software: Python 3.10+, OpenCV, NumPy, pandas, Streamlit, Plotly; FFmpeg is optional.

### Database design
`sessions` stores source filename, creation time, duration and summary JSON; `attendance` stores anonymous participant ID, first/last timestamps, observed duration, status, and quality; `interval_metrics` stores interval bounds and aggregate signals; `recommendations` stores type, observation, reason and suggestion. Foreign keys cascade on session deletion.

### AI/ML and testing strategy
HOG+SVM is a pretrained classical computer-vision detector; no model training or identity recognition is performed. Scoring and recommendations are transparent deterministic rules. Unit tests cover scoring, recommendations, and database lifecycle. End-to-end behavior depends on video quality and optional FFmpeg availability.

### Results, limitations, and future scope
The application produces real measurements from uploaded media, not hardcoded dashboard values. Detection and tracking degrade with occlusion, camera movement, crowding, and large perspective changes. Audio is coarse energy activity, not speech/turn-taking recognition. Future work could add consent-based calibration, stronger anonymous tracking, camera-motion compensation, and validation against instructor observations. All estimates require human interpretation and can encode environmental bias.

### Privacy, ethics, conclusion
Video is processed locally and not retained by this application; only derived metrics are stored. Audio is not transcribed. Session records can be deleted. Obtain appropriate consent and institutional approval before using classroom recordings. The agent offers recommendations only. The project demonstrates an explainable, privacy-conscious analytics prototype while making its limitations explicit.

## Troubleshooting

- If `ffmpeg` is not found, install it and ensure it is on PATH; otherwise audio metrics are omitted.
- For weak person detection, use a fixed camera with visible full bodies and adequate lighting. Estimates are not attendance proof.
- If Streamlit is unavailable, verify the virtual environment is activated and rerun the install command.
- Database location is `data/attendance.db`; deleting it resets all saved analytics.
