from attendance_agent.engagement import score_intervals
from attendance_agent.agent import recommend
from attendance_agent.database import initialize, save, sessions, delete

def test_engagement_scoring_without_audio():
    out=score_intervals([{'time':0,'people':2,'motion':.4},{'time':1,'people':1,'motion':.2}],None,60)
    assert len(out)==1 and 0 <= out[0]['engagement'] <= 100

def test_audio_windows_are_allocated_to_their_own_timeline_interval():
    frames = [{'time': 0, 'people': 1, 'motion': .2},
              {'time': 60, 'people': 1, 'motion': .2}]
    audio = {'windows': [
        {'start': 0, 'end': 60, 'active': True},
        {'start': 60, 'end': 120, 'active': False},
    ]}
    out = score_intervals(frames, audio, 60)
    assert out[0]['audio_activity'] == 1
    assert out[1]['audio_activity'] == 0

def test_empty_video_has_no_intervals():
    assert score_intervals([], None) == []

def test_agent_explains_low_activity():
    items=[{'start_seconds':0,'end_seconds':60,'engagement':20,'people_avg':0,'motion':0,'audio_activity':0}]
    result=recommend([],items,None)
    assert result and result[0]['reason'] and result[0]['suggestion']

def test_database_lifecycle(tmp_path, monkeypatch):
    import attendance_agent.database as db
    monkeypatch.setattr(db,'DB',tmp_path/'test.db'); initialize()
    sid=save('demo.mp4',{'duration_seconds':5,'attendance':[]},[],[],[] ,{'present':0})
    assert sessions()[0][0]==sid
    delete(sid); assert sessions()==[]
