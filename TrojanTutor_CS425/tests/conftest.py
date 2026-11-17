import os
# Tests must never touch the developer's real session database or call a real LLM.
os.environ['TROJANTUTOR_SESSION_DB'] = ':memory:'
os.environ['TROJANTUTOR_LLM'] = 'off'
os.environ.setdefault('TROJANTUTOR_STREAM_DELAY', '0')
