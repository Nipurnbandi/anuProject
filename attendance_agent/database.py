import json, sqlite3
from pathlib import Path

DB = Path('data/attendance.db')

def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB); c.execute('PRAGMA foreign_keys=ON'); return c

def initialize():
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY, created_at TEXT DEFAULT CURRENT_TIMESTAMP, filename TEXT, duration REAL, summary TEXT);
        CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE, participant_id TEXT, first_detected REAL, last_detected REAL, duration REAL, status TEXT, quality REAL);
        CREATE TABLE IF NOT EXISTS interval_metrics(id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE, start REAL, end REAL, engagement REAL, people REAL, motion REAL, audio REAL);
        CREATE TABLE IF NOT EXISTS recommendations(id INTEGER PRIMARY KEY, session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE, kind TEXT, observation TEXT, reason TEXT, suggestion TEXT);''')

def save(filename, video, attendance, intervals, suggestions, summary):
    with connect() as c:
        sid=c.execute('INSERT INTO sessions(filename,duration,summary) VALUES(?,?,?)',(filename,video['duration_seconds'],json.dumps(summary))).lastrowid
        c.executemany('INSERT INTO attendance(session_id,participant_id,first_detected,last_detected,duration,status,quality) VALUES(?,?,?,?,?,?,?)',[(sid,a['participant_id'],a['first_detected'],a['last_detected'],a['duration_seconds'],a['status'],a['quality']) for a in attendance])
        c.executemany('INSERT INTO interval_metrics(session_id,start,end,engagement,people,motion,audio) VALUES(?,?,?,?,?,?,?)',[(sid,x['start_seconds'],x['end_seconds'],x['engagement'],x['people_avg'],x['motion'],x['audio_activity']) for x in intervals])
        c.executemany('INSERT INTO recommendations(session_id,kind,observation,reason,suggestion) VALUES(?,?,?,?,?)',[(sid,x['type'],x['observation'],x['reason'],x['suggestion']) for x in suggestions])
        return sid

def sessions():
    with connect() as c: return c.execute('SELECT id,created_at,filename,duration FROM sessions ORDER BY id DESC').fetchall()

def delete(sid):
    with connect() as c: c.execute('DELETE FROM sessions WHERE id=?',(sid,))
