import json
import os
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st

from attendance_agent.agent import recommend
from attendance_agent.audio import analyze_audio
from attendance_agent.database import delete, initialize, save, sessions
from attendance_agent.engagement import score_intervals
from attendance_agent.video import analyze_video

st.set_page_config(page_title="Classroom Signal", page_icon="◉", layout="wide")
initialize()

st.markdown("""
<style>
:root { --ink:#182d35; --muted:#63777b; --teal:#167d78; --pale:#eaf4f1; --line:#e1eae7; }
.stApp { background: #f6f8f6; color:var(--ink); font-family:'Segoe UI',sans-serif; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:#edf3f0; border-right:1px solid var(--line); }
h1,h2,h3 { font-family:'Segoe UI',sans-serif; color:var(--ink); letter-spacing:-.035em; }
h1 { font-size:2.65rem !important; }
.eyebrow { color:var(--teal); text-transform:uppercase; font-size:.72rem; font-weight:700; letter-spacing:.14em; }
.lede { color:var(--muted); font-size:1.03rem; margin-top:-.6rem; }
.panel { background:#fff; border:1px solid var(--line); border-radius:16px; padding:1.2rem 1.35rem; }
.tiny { color:var(--muted); font-size:.83rem; }
div[data-testid="stMetric"] { background:#fff; border:1px solid var(--line); padding:1rem 1.1rem; border-radius:14px; }
div[data-testid="stMetricLabel"] { color:var(--muted); }
div.stButton > button[kind="primary"] { background:var(--teal); border-color:var(--teal); border-radius:9px; }
div.stDownloadButton > button { border-radius:9px; }
hr { border-color:var(--line); }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("<div class='eyebrow'>Classroom Signal</div>", unsafe_allow_html=True)
    st.markdown("### Session workspace")
    st.caption("Review aggregate class activity from a local recording.")
    uploaded = st.file_uploader("Choose a recording", type=["mp4", "mov", "avi", "mkv"], help="The selected file is processed locally and removed after analysis.")
    interval_minutes = st.select_slider("Timeline interval", options=[1, 2, 5, 10], value=5, format_func=lambda x: f"{x} min")
    sample_fps = st.slider("Frame sampling", 0.2, 2.0, 1.0, 0.2, help="More samples can improve continuity but take longer.")
    run_analysis = st.button("Analyze recording", type="primary", use_container_width=True, disabled=uploaded is None)
    st.divider()
    with st.expander("Local data & privacy"):
        st.write("Video is analyzed on this device and is not kept by the app. Derived session metrics are stored in a local SQLite database. Participants receive temporary anonymous IDs; there is no face recognition or speech transcription.")

st.markdown("<div class='eyebrow'>Instructor analytics · local processing</div>", unsafe_allow_html=True)
st.title("A clearer view of the session.")
st.markdown("<p class='lede'>Presence and classroom activity signals, brought together for instructor review.</p>", unsafe_allow_html=True)

if run_analysis and uploaded:
    suffix = os.path.splitext(uploaded.name)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp:
        temp.write(uploaded.getbuffer())
        media_path = temp.name
    progress = st.progress(0, text="Preparing local analysis…")
    try:
        video = analyze_video(media_path, sample_fps=sample_fps,
                              progress=lambda value: progress.progress(int(value * 75), text="Scanning sampled frames and associating anonymous tracks…"))
        audio = analyze_audio(media_path)
        timeline = score_intervals(video["frames"], audio, interval_minutes * 60)
        suggestions = recommend(video["attendance"], timeline, audio)
        sustained = sum(item["status"] == "Present" for item in video["attendance"])
        summary = {
            "participants_detected": len(video["attendance"]),
            "present": sustained,
            "attendance_percent": round(100 * sustained / max(1, len(video["attendance"])), 1),
            "average_engagement": round(sum(item["engagement"] for item in timeline) / max(1, len(timeline)), 1),
            "audio_activity_percent": round(100 * audio["activity_fraction"], 1) if audio else None,
        }
        session_id = save(uploaded.name, video, video["attendance"], timeline, suggestions, summary)
        st.session_state["analysis"] = (session_id, uploaded.name, video, audio, timeline, suggestions, summary)
        progress.progress(100, text="Session summary ready")
    except Exception as error:
        st.error(f"Could not analyze this recording: {error}")
    finally:
        try:
            os.unlink(media_path)
        except OSError:
            pass

analysis = st.session_state.get("analysis")
if analysis:
    session_id, filename, video, audio, timeline, suggestions, summary = analysis
    mins = video["duration_seconds"] / 60
    st.markdown(f"<div class='tiny'>CURRENT REVIEW &nbsp; / &nbsp; {filename} &nbsp; · &nbsp; {mins:.1f} min &nbsp; · &nbsp; Session {session_id}</div>", unsafe_allow_html=True)
    st.write("")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Tracks detected", summary["participants_detected"])
    metric_cols[1].metric("Sustained presence", summary["present"], help="Anonymous tracks passing the minimum-duration rule.")
    metric_cols[2].metric("Activity indicator", f"{summary['average_engagement']:.0f} / 100")
    metric_cols[3].metric("Audio activity", f"{summary['audio_activity_percent']}%" if audio else "Unavailable")
    st.caption("Indicators are approximate signals affected by camera position, movement in the scene, and recording conditions. Review attendance manually.")

    overview_tab, attendance_tab, coach_tab, export_tab = st.tabs(["Session overview", "Presence review", "Teaching notes", "Export & history"])
    with overview_tab:
        left, right = st.columns([1.55, 1])
        with left:
            st.subheader("Activity through the session")
            if timeline:
                frame = pd.DataFrame(timeline)
                frame["minute"] = frame["start_seconds"] / 60
                chart = px.area(frame, x="minute", y="engagement", markers=True,
                                labels={"minute": "Minutes into recording", "engagement": "Estimated indicator"},
                                range_y=[0, 100])
                chart.update_traces(line_color="#167d78", fillcolor="rgba(22,125,120,.16)", marker=dict(size=7))
                chart.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#63777b")
                chart.update_xaxes(showgrid=False, zeroline=False)
                chart.update_yaxes(gridcolor="#e6eeeb", title=None)
                st.plotly_chart(chart, use_container_width=True)
            else:
                st.info("No timeline intervals were available for this recording.")
        with right:
            st.subheader("Signal mix")
            if timeline:
                signals = pd.DataFrame({"Interval": [f"{int(x['start_seconds']//60)} min" for x in timeline],
                                        "People detected": [x["people_avg"] for x in timeline],
                                        "Scene movement": [x["motion"] for x in timeline],
                                        "Audio energy": [x["audio_activity"] for x in timeline]})
                melted = signals.melt(id_vars="Interval", var_name="Signal", value_name="Level")
                bars = px.bar(melted, x="Interval", y="Level", color="Signal", barmode="group",
                              color_discrete_sequence=["#315e69", "#48a39a", "#d4a763"])
                bars.update_layout(height=330, margin=dict(l=5, r=5, t=20, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend_title=None, font_color="#63777b")
                bars.update_yaxes(gridcolor="#e6eeeb", title=None)
                bars.update_xaxes(title=None, showgrid=False)
                st.plotly_chart(bars, use_container_width=True)
            st.markdown("<div class='tiny'>Movement is scene-level and can include instructor or camera motion.</div>", unsafe_allow_html=True)
    with attendance_tab:
        st.subheader("Anonymous presence tracks")
        st.write("Tracks are temporary labels within this recording. They do not identify individual students.")
        attendance_df = pd.DataFrame(video["attendance"])
        if not attendance_df.empty:
            attendance_df = attendance_df.rename(columns={"participant_id": "Track", "first_detected": "First seen (s)", "last_detected": "Last seen (s)", "duration_seconds": "Observed span (s)", "status": "Review status", "quality": "Detector signal"})
            st.dataframe(attendance_df, use_container_width=True, hide_index=True, column_config={"Detector signal": st.column_config.ProgressColumn("Detector signal", min_value=0, max_value=1, format="%.2f")})
        else:
            st.info("No people were detected in the sampled frames. A fixed, well lit view with visible people can improve detection.")
        st.info("‘Observed span’ is the time between first and last detections. Gaps between detections may occur, so it is not continuous verified attendance.")
    with coach_tab:
        st.subheader("Ideas for instructor review")
        st.write("Suggestions are generated from aggregate indicators. Use your knowledge of the lesson to decide whether they apply.")
        for note in suggestions:
            with st.container(border=True):
                st.markdown(f"**{note['type']}** · {note['observation']}")
                st.markdown(f"**Signal behind this note:** {note['reason']}")
                st.markdown(f"**Possible next step:** {note['suggestion']}")
        st.caption("This tool provides decision support only. Estimated engagement is not a validated attention or learning measure.")
    with export_tab:
        st.subheader("Take the session summary with you")
        report = {"session_id": session_id, "source_file": filename, "summary": summary, "attendance": video["attendance"], "timeline": timeline, "audio_metrics": audio, "recommendations": suggestions}
        d1, d2 = st.columns(2)
        d1.download_button("Download session report · JSON", json.dumps(report, indent=2), file_name=f"classroom-session-{session_id}.json", mime="application/json", use_container_width=True)
        d2.download_button("Download presence table · CSV", pd.DataFrame(video["attendance"]).to_csv(index=False), file_name=f"presence-tracks-{session_id}.csv", mime="text/csv", use_container_width=True)
        st.divider()
        st.subheader("Saved local sessions")
        saved = sessions()
        if not saved:
            st.caption("No saved sessions yet.")
        for row in saved:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**Session {row[0]}** · {row[2]}  \n<span class='tiny'>{row[1]} · {row[3]/60:.1f} min</span>", unsafe_allow_html=True)
            if c2.button("Delete", key=f"delete-{row[0]}", use_container_width=True):
                delete(row[0])
                if st.session_state.get("analysis", (None,))[0] == row[0]:
                    del st.session_state["analysis"]
                st.rerun()
else:
    st.write("")
    a, b = st.columns([1.3, 1], gap="large")
    with a:
        st.markdown("### Start with a recording")
        st.markdown("<div class='panel'><div class='eyebrow'>Session workflow</div><br><b>01 · Add a video</b><br><span class='tiny'>Choose a classroom recording in the left panel.</span><br><br><b>02 · Review signals</b><br><span class='tiny'>See anonymous presence tracks and activity changes over time.</span><br><br><b>03 · Reflect and export</b><br><span class='tiny'>Read the reasons behind suggestions and save a session report.</span></div>", unsafe_allow_html=True)
    with b:
        st.markdown("### What this view can tell you")
        st.markdown("<div class='panel'><b>Presence</b><br><span class='tiny'>Repeated person detections, grouped into temporary anonymous tracks.</span><br><br><b>Class activity</b><br><span class='tiny'>Aggregate scene movement and optional audio energy by interval.</span><br><br><b>Instructor prompts</b><br><span class='tiny'>Simple, explainable cues to support your own session review.</span></div>", unsafe_allow_html=True)
    st.caption("All analysis runs locally. The application does not identify students or interpret private speech.")
