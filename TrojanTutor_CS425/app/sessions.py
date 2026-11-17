"""Persistent tutoring sessions (SQLite, standard library only).

Why: Week 1 kept history in a Python dict, so a server restart or a unit switch lost the
conversation. Sessions now survive restarts, keep context across unit switches, and every turn
is an auditable action log (engine, intent, concept, grounding status) — the record the
research phase needs (roadmap: Dec 28 "action logging", Jan 18 "student history").

Config: TROJANTUTOR_SESSION_DB (default data/sessions.sqlite3; ':memory:' for tests).
No accounts and no personal data: a session is an opaque random id held by the browser.
"""
from pathlib import Path
from threading import RLock
from uuid import uuid4
import json, os, sqlite3, time

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_TURNS = 16          # turns passed to the tutor as conversational context

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY, unit TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS turns(
  n INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL, content TEXT NOT NULL, unit TEXT, concept TEXT, intent TEXT,
  engine TEXT, grounding TEXT, sources TEXT, exercise TEXT, created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS turns_by_session ON turns(session_id, n);
CREATE TABLE IF NOT EXISTS progress(
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, lesson_id TEXT NOT NULL,
  step INTEGER NOT NULL, completed INTEGER NOT NULL DEFAULT 0, correct INTEGER NOT NULL DEFAULT 0,
  answered INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL, PRIMARY KEY(session_id, lesson_id));
"""


class SessionStore:
    def __init__(self, path=None):
        path = path or os.getenv('TROJANTUTOR_SESSION_DB', str(ROOT / 'data' / 'sessions.sqlite3'))
        self.lock = RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys = ON')
        self.db.executescript(_SCHEMA)
        self.db.commit()

    # ---- sessions ----
    def create(self, unit):
        sid, now = uuid4().hex, time.time()
        with self.lock:
            self.db.execute('INSERT INTO sessions VALUES (?,?,?,?)', (sid, unit, now, now))
            self.db.commit()
        return sid

    def get(self, sid):
        with self.lock:
            row = self.db.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
        return dict(row) if row else None

    def set_unit(self, sid, unit):
        with self.lock:
            cur = self.db.execute('UPDATE sessions SET unit=?, updated=? WHERE id=?', (unit, time.time(), sid))
            self.db.commit()
        return cur.rowcount == 1

    def delete(self, sid):
        with self.lock:
            cur = self.db.execute('DELETE FROM sessions WHERE id=?', (sid,))
            self.db.commit()
        return cur.rowcount == 1

    def purge(self, older_than_days=30):
        cutoff = time.time() - older_than_days * 86400
        with self.lock:
            cur = self.db.execute('DELETE FROM sessions WHERE updated < ?', (cutoff,))
            self.db.commit()
        return cur.rowcount

    # ---- turns ----
    def history(self, sid, limit=CONTEXT_TURNS):
        """Most recent turns, oldest first, in the shape app.tutor expects."""
        with self.lock:
            rows = self.db.execute('SELECT * FROM turns WHERE session_id=? ORDER BY n DESC LIMIT ?',
                                   (sid, limit)).fetchall()
        return [{'role': r['role'], 'content': r['content'], 'concept': r['concept'], 'intent': r['intent'],
                 'unit': r['unit'], 'exercise': r['exercise']} for r in reversed(rows)]

    def append(self, sid, question, result, unit):
        now = time.time()
        g = (result.get('grounding') or {}).get('status')
        srcs = json.dumps([{'id': s.get('id'), 'pages': s.get('pages'), 'unit': s.get('unit')}
                           for s in result.get('sources', [])])
        with self.lock:
            self.db.execute('INSERT INTO turns(session_id,role,content,unit,created) VALUES (?,?,?,?,?)',
                            (sid, 'user', question, unit, now))
            self.db.execute('INSERT INTO turns(session_id,role,content,unit,concept,intent,engine,grounding,sources,exercise,created)'
                            ' VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                            (sid, 'assistant', result['answer'], unit, result.get('concept_id'), result.get('intent'),
                             result.get('engine'), g, srcs, result.get('exercise') or result.get('homework_match'), now))
            self.db.execute('UPDATE sessions SET updated=? WHERE id=?', (now, sid))
            self.db.commit()

    def set_progress(self, sid, lesson_id, step, completed=False):
        with self.lock:
            self.db.execute('INSERT INTO progress(session_id, lesson_id, step, completed, updated) VALUES (?,?,?,?,?) '
                            'ON CONFLICT(session_id, lesson_id) DO UPDATE SET step=max(step, excluded.step), '
                            'completed=max(completed, excluded.completed), updated=excluded.updated',
                            (sid, lesson_id, step, int(completed), time.time()))
            self.db.commit()

    def record_answer(self, sid, lesson_id, correct):
        with self.lock:
            self.db.execute('INSERT INTO progress(session_id, lesson_id, step, updated) VALUES (?,?,0,?) '
                            'ON CONFLICT(session_id, lesson_id) DO NOTHING', (sid, lesson_id, time.time()))
            self.db.execute('UPDATE progress SET answered=answered+1, correct=correct+? WHERE session_id=? AND lesson_id=?',
                            (int(correct), sid, lesson_id))
            self.db.commit()

    def progress(self, sid):
        with self.lock:
            rows = self.db.execute('SELECT * FROM progress WHERE session_id=?', (sid,)).fetchall()
        return {r['lesson_id']: {'step': r['step'], 'completed': bool(r['completed']), 'answered': r['answered'],
                                 'correct': r['correct']} for r in rows}

    def transcript(self, sid):
        with self.lock:
            rows = self.db.execute('SELECT * FROM turns WHERE session_id=? ORDER BY n', (sid,)).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d['sources'] = json.loads(d['sources']) if d['sources'] else []
            out.append(d)
        return out

    def summary(self, sid):
        s = self.get(sid)
        if not s:
            return None
        turns = self.transcript(sid)
        covered = []
        for t in turns:
            if t['role'] == 'assistant' and t['concept'] and t['concept'] not in covered:
                covered.append(t['concept'])
        grounding = {}
        for t in turns:
            if t['role'] == 'assistant' and t['grounding']:
                grounding[t['grounding']] = grounding.get(t['grounding'], 0) + 1
        return {**s, 'turns': len(turns), 'concepts_covered': covered,
                'last_concept': covered[-1] if covered else None, 'grounding_counts': grounding,
                'history': [{'role': t['role'], 'content': t['content'], 'concept': t['concept'],
                             'engine': t['engine'], 'grounding': t['grounding'], 'unit': t['unit']} for t in turns]}
