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

KOKORO = "https://huggingface.co/onnx-community/Kokoro-82M-v1.0-ONNX/resolve/main"
_kokoro = None

def _kokoro_engine(voice):
    """Natural neural voices (Kokoro 82M, Apache-2.0). British female: bf_emma (default), bf_isabella, bf_alice, bf_lily."""
    global _kokoro
    d = HERE / "voices" / "kokoro"; d.mkdir(parents=True, exist_ok=True)
    if not (d / "model.onnx").exists():
        urllib.request.urlretrieve(f"{KOKORO}/onnx/model.onnx", d / "model.onnx")
    if not (d / f"{voice}.bin").exists():
        urllib.request.urlretrieve(f"{KOKORO}/voices/{voice}.bin", d / f"{voice}.bin")
    bins = {f.stem: np.fromfile(f, dtype=np.float32).reshape(-1, 1, 256) for f in d.glob("*.bin")}
    np.savez(d / "voices.npz", **bins)
    from kokoro_onnx import Kokoro
    _kokoro = Kokoro(str(d / "model.onnx"), str(d / "voices.npz"))
    return _kokoro

def tts(text, voice="bf_emma", speed=0.95):
    """Return mono float32 audio at SR. Kokoro voices (bf_*, bm_*, af_*, am_*) are the default; "ryan"/"lessac" use Piper."""
    if voice not in VOICES:
        for k, v in PRONOUNCE.items():
            text = text.replace(k, v)
        eng = _kokoro if _kokoro is not None else _kokoro_engine(voice)
        lang = "en-gb" if voice.startswith("b") else "en-us"
        parts = []
        for sent in [x.strip() for x in __import__("re").split(r"(?<=[.!?])\s+", text) if x.strip()]:
            a, sr = eng.create(sent, voice=voice, speed=speed, lang=lang)
            parts += [a.astype(np.float32), np.zeros(int(0.22 * sr), np.float32)]
        x = np.concatenate(parts[:-1]) if parts else np.zeros(1, np.float32)
        return np.interp(np.linspace(0, len(x), int(len(x) * SR / sr), endpoint=False), np.arange(len(x)), x).astype(np.float32)
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

def music(duration, bpm=122, seed=7):
    """Original upbeat, modern bed: driving four-on-the-floor kick, offbeat hats, claps on 2 and 4,
    eighth-note bass, bright stabs over a I-V-vi-IV progression. Royalty-free (generated)."""
    rng = np.random.default_rng(seed)
    n = int(duration * SR); out = np.zeros(n, np.float32)
    beat = 60 / bpm; bar = 4 * beat
    prog = [(60, 64, 67), (55, 59, 62), (57, 60, 64), (53, 57, 60)]  # C G Am F
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    def add(start, sig):
        s = int(start * SR)
        if s >= n: return
        e = min(n, s + len(sig)); out[s:e] += sig[:e - s]
    def env(L, dec):
        return np.exp(-np.arange(L) / (dec * SR)).astype(np.float32)
    kickL = int(0.22 * SR); tk = np.arange(kickL) / SR
    kick = (np.sin(2 * np.pi * (48 + 90 * np.exp(-tk * 35)) * tk) * np.exp(-tk * 12)).astype(np.float32)
    hatL = int(0.05 * SR); hat = (rng.standard_normal(hatL) * env(hatL, 0.012)).astype(np.float32)
    hat = np.diff(hat, prepend=0)  # crude high-pass for a crisp hat
    clapL = int(0.18 * SR); clap = (rng.standard_normal(clapL) * env(clapL, 0.045)).astype(np.float32)
    bars = int(np.ceil(duration / bar))
    for b in range(bars):
        t0 = b * bar; chord = prog[b % 4]
        for k in range(4):
            add(t0 + k * beat, 0.55 * kick)
            add(t0 + k * beat + beat / 2, 0.10 * hat)
            if k in (1, 3): add(t0 + k * beat, 0.16 * clap)
        for k in range(16):  # sixteenth hats, light
            if k % 2: add(t0 + k * beat / 4, 0.04 * hat)
        for k in range(8):  # eighth-note bass, octave bounce
            L = int(beat / 2 * SR * 0.9); t = np.arange(L) / SR
            f = hz(chord[0] - 24 + (12 if k % 2 else 0))
            sig = (np.tanh(2.2 * np.sin(2 * np.pi * f * t)) * env(L, 0.16)).astype(np.float32)
            add(t0 + k * beat / 2, 0.16 * sig)
        for k in (0, 1.5, 2.5, 3.5):  # syncopated bright stabs
            L = int(0.22 * SR); t = np.arange(L) / SR
            sig = sum(np.sign(np.sin(2 * np.pi * hz(m) * t)) * 0.5 + np.sin(2 * np.pi * hz(m + 12) * t) for m in chord)
            add(t0 + k * beat, 0.035 * (sig * env(L, 0.07)).astype(np.float32))
        L = int(bar * SR); t = np.arange(L) / SR  # soft pad underneath for warmth
        pad = sum(np.sin(2 * np.pi * hz(m) * t) for m in chord).astype(np.float32)
        add(t0, 0.025 * pad * np.minimum(1, np.minimum(t / 0.2, (bar - t) / 0.2)).astype(np.float32))
    fade = int(1.2 * SR); out[-fade:] *= np.linspace(1, 0, fade); out[:int(0.15 * SR)] *= np.linspace(0, 1, int(0.15 * SR))
    return out / max(1e-6, np.abs(out).max()) * 0.9

def mix(duration, vo_clips, with_music=True, music_db=-7, duck_db=-12):
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
