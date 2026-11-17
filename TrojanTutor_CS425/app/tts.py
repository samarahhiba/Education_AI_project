"""Optional neural text-to-speech (server side). OFF by default: the browser voice is used.

Browser voices vary a lot by machine; for a natural voice, point this at any OpenAI-compatible
/audio/speech endpoint:

  export TROJANTUTOR_TTS=openai OPENAI_API_KEY=... TROJANTUTOR_TTS_MODEL=<tts model> [TROJANTUTOR_TTS_VOICE=<voice>]
  (TROJANTUTOR_TTS_BASE_URL=... for a compatible local or hosted server)

Audio is cached on disk by (model, voice, text) hash, so replaying a lesson costs nothing.
Lesson scripts are deterministic, so a whole course can be pre-generated once.
"""
from pathlib import Path
import hashlib, json, os, urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'data' / 'tts_cache'
MAX_CHARS = 1200


class TTSUnavailable(RuntimeError):
    pass


def config():
    if os.getenv('TROJANTUTOR_TTS', 'off').lower() != 'openai':
        return None
    model = os.getenv('TROJANTUTOR_TTS_MODEL')
    key = os.getenv('OPENAI_API_KEY', '')
    base = os.getenv('TROJANTUTOR_TTS_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    if not model or (not key and 'api.openai.com' in base):
        return None
    return {'url': base + '/audio/speech', 'key': key, 'model': model,
            'voice': os.getenv('TROJANTUTOR_TTS_VOICE', 'alloy')}


def synthesize(text, transport=None):
    """Return MP3 bytes for `text` (cached)."""
    cfg = config()
    if cfg is None and transport is None:
        raise TTSUnavailable('server TTS not configured')
    cfg = cfg or {'url': 'test://', 'key': '', 'model': 'test', 'voice': 'test'}
    text = text.strip()[:MAX_CHARS]
    if not text:
        raise ValueError('empty text')
    h = hashlib.sha256(json.dumps([cfg['model'], cfg['voice'], text]).encode()).hexdigest()[:32]
    path = CACHE / f'{h}.mp3'
    if path.exists():
        return path.read_bytes()
    body = {'model': cfg['model'], 'voice': cfg['voice'], 'input': text, 'response_format': 'mp3'}
    headers = {'content-type': 'application/json'}
    if cfg['key']:
        headers['authorization'] = f"Bearer {cfg['key']}"
    if transport:
        audio = transport(cfg['url'], headers, body)
    else:
        req = urllib.request.Request(cfg['url'], data=json.dumps(body).encode(), headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                audio = r.read()
        except Exception as e:
            raise TTSUnavailable(f'{type(e).__name__}: {e}') from e
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return audio
