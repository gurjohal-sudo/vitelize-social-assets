"""Audio for Vitelize Reels: offline text-to-speech (Piper) and an original synthesized music bed.

Both are generated locally, so there are no music licensing or voice licensing issues.
Voices (Piper, from huggingface.co/rhasspy/piper-voices) are downloaded on first use into tools/voices/.
"""
import io, wave, subprocess, pathlib, urllib.request
import numpy as np

SR = 44100
HERE = pathlib.Path(__file__).resolve().parent
VOICES = {
    "ryan": "en/en_US/ryan/high/en_US-ryan-high",
    "lessac": "en/en_US/lessac/high/en_US-lessac-high",
}
# Words the voice engine mispronounces, spelled the way they should sound.
PRONOUNCE = {"Vitelize": "Vitalize", "info@vitelizehealth.com": "info at vitalize health dot com", "U.S.": "U S", "FDA": "F D A", "GLP-1": "G L P one"}

def _voice_path(name):
    d = HERE / "voices"; d.mkdir(exist_ok=True)
    rel = VOICES[name]; base = d / pathlib.Path(rel).name
    for ext in (".onnx", ".onnx.json"):
        f = base.with_suffix(ext) if ext == ".onnx" else pathlib.Path(str(base) + ".onnx.json")
        if not f.exists():
            urllib.request.urlretrieve(f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{rel}{ext}", f)
    return base.with_suffix(".onnx")

def tts(text, voice="ryan", speed=1.0):
    """Return mono float32 audio at SR for the given text."""
    for k, v in PRONOUNCE.items():
        text = text.replace(k, v)
    model = _voice_path(voice)
    out = subprocess.run(["python3", "-m", "piper", "-m", str(model), "--length-scale", str(1 / speed), "-f", "-"],
                         input=text.encode(), capture_output=True, check=True).stdout
    with wave.open(io.BytesIO(out)) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if sr != SR:
        x = np.interp(np.linspace(0, len(x), int(len(x) * SR / sr), endpoint=False), np.arange(len(x)), x).astype(np.float32)
    return x

def _note(f, n, kind="pad"):
    t = np.arange(n) / SR
    if kind == "pad":
        w = sum(np.sin(2 * np.pi * f * m * t + m) / (m * m) for m in (1, 2, 3)) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t)
    else:
        w = np.sin(2 * np.pi * f * t)
    return w.astype(np.float32)

def music(duration, bpm=96, seed=7):
    """Original, calm, modern bed: warm pad chords, soft pulse, light kick. Royalty-free (generated)."""
    n = int(duration * SR); out = np.zeros(n, np.float32)
    beat = 60 / bpm; bar = 4 * beat
    prog = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    b = 0
    while b * bar < duration:
        s = int(b * bar * SR); L = min(int(bar * SR), n - s)
        if L <= 0: break
        env = np.minimum(1, np.minimum(np.arange(L) / (0.4 * SR), (L - np.arange(L)) / (0.4 * SR))).astype(np.float32)
        chord = prog[b % 4]
        for m in chord:
            out[s:s + L] += 0.06 * _note(hz(m), L) * env
        out[s:s + L] += 0.05 * _note(hz(chord[0] - 12), L, "sine") * env
        for k in range(8):  # eighth-note pluck on chord tones
            ps = s + int(k * beat / 2 * SR); pl = min(int(0.35 * SR), n - ps)
            if pl <= 0: continue
            out[ps:ps + pl] += 0.035 * _note(hz(chord[k % 3] + 12), pl, "sine") * np.exp(-np.arange(pl) / (0.08 * SR))
        for k in range(4):  # soft kick
            ks = s + int(k * beat * SR); kl = min(int(0.25 * SR), n - ks)
            if kl <= 0: continue
            tt = np.arange(kl) / SR
            out[ks:ks + kl] += 0.18 * np.sin(2 * np.pi * (50 + 60 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 14)
        b += 1
    fade = int(1.5 * SR); out[-fade:] *= np.linspace(1, 0, fade); out[:int(0.5 * SR)] *= np.linspace(0, 1, int(0.5 * SR))
    return out / max(1e-6, np.abs(out).max()) * 0.9

def mix(duration, vo_clips, with_music=True, music_db=-20, duck_db=-8):
    """vo_clips: list of (start_seconds, audio). Returns stereo int16 wav bytes."""
    n = int(duration * SR); vo = np.zeros(n, np.float32)
    for st, clip in vo_clips:
        s = int(st * SR); e = min(n, s + len(clip)); vo[s:e] += clip[:e - s]
    bed = music(duration) * 10 ** (music_db / 20) if with_music else np.zeros(n, np.float32)
    if with_music and vo_clips:  # duck music under speech
        active = np.convolve((np.abs(vo) > 0.01).astype(np.float32), np.ones(int(0.25 * SR)) / int(0.25 * SR), "same")
        bed *= 10 ** (duck_db * np.clip(active * 3, 0, 1) / 20)
    y = vo / max(1e-6, np.abs(vo).max()) * 0.85 + bed if vo_clips else bed
    y = np.clip(y, -1, 1)
    st = (np.stack([y, y], 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
    return buf.getvalue()
