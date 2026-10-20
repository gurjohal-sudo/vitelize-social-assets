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

def music_drive(duration, bpm=128, seed=11):
    """High-energy house bed (default for Reels): punchy four-on-the-floor kick with sidechain pumping,
    rolling off-beat bass, detuned chord stabs, 16th-note arpeggio, open hats, claps, snare-roll risers
    and crashes, over a bright I-V-vi-IV progression in D major. Original and royalty-free (generated)."""
    rng = np.random.default_rng(seed)
    n = int(duration * SR); beat = 60 / bpm; bar = 4 * beat; s16 = beat / 4
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    prog = [(62, 66, 69), (57, 61, 64), (59, 62, 66), (55, 59, 62)]  # D A Bm G
    drums = np.zeros(n, np.float32); synth = np.zeros(n, np.float32)
    def add(buf, start, sig):
        s0 = int(start * SR)
        if s0 >= n or s0 < 0: return
        e = min(n, s0 + len(sig)); buf[s0:e] += sig[:e - s0]
    env = lambda L, d: np.exp(-np.arange(L) / (d * SR)).astype(np.float32)
    def saw(f, L, det=(0, 7, -7)):
        t = np.arange(L) / SR
        return sum(2 * ((t * f * 2 ** (c / 1200)) % 1) - 1 for c in det).astype(np.float32) / len(det)
    def lp(x, a):  # one-pole low-pass
        y = np.empty_like(x); acc = 0.0
        for k in range(len(x)): acc += a * (x[k] - acc); y[k] = acc
        return y
    kL = int(0.25 * SR); tk = np.arange(kL) / SR
    kick = (np.sin(2 * np.pi * (50 * tk + 160 * (1 - np.exp(-tk * 40)) / 40)) * np.exp(-tk * 9)).astype(np.float32)
    kick += (rng.standard_normal(kL) * env(kL, 0.004) * 0.3).astype(np.float32)
    hL = int(0.04 * SR); hat = np.diff(rng.standard_normal(hL).astype(np.float32) * env(hL, 0.008), prepend=0)
    oL = int(0.16 * SR); ohat = np.diff(rng.standard_normal(oL).astype(np.float32) * env(oL, 0.06), prepend=0)
    cL = int(0.2 * SR); clap = sum(np.roll(rng.standard_normal(cL).astype(np.float32) * env(cL, 0.05), int(d * SR)) for d in (0, .01, .021))
    snL = int(0.12 * SR); snare = (rng.standard_normal(snL) * env(snL, 0.04) + np.sin(2 * np.pi * 190 * np.arange(snL) / SR) * env(snL, 0.05)).astype(np.float32)
    crL = int(1.6 * SR); crash = np.diff(rng.standard_normal(crL).astype(np.float32) * env(crL, 0.5), prepend=0)
    bars = int(np.ceil(duration / bar)) + 1
    for b in range(bars):
        t0 = b * bar; ch = prog[b % 4]; intro = b == 0
        if b % 4 == 0: add(drums, t0, 0.08 * crash)
        for k in range(4):
            add(drums, t0 + k * beat, 0.9 * kick)
            add(drums, t0 + k * beat + beat / 2, 0.06 * ohat)
            if k in (1, 3): add(drums, t0 + k * beat, 0.16 * clap)
        for k in range(16):
            add(drums, t0 + k * s16, (0.03 if k % 2 else 0.015) * hat)
        if b % 4 == 3:  # snare roll riser into the next phrase
            for k in range(8):
                add(drums, t0 + 2 * beat + k * s16, (0.03 + 0.015 * k) * snare)
        if not intro:
            for k in range(4):  # rolling off-beat bass with a 16th pickup
                for off in (beat / 2, 3 * s16):
                    L = int(s16 * SR * 0.95); f = hz(ch[0] - 24)
                    add(synth, t0 + k * beat + off, 0.42 * np.tanh(3 * lp(saw(f, L, (0, 5)), 0.08)) * env(L, 0.09))
        for k in (0, 0.75, 1.5, 2.5, 3.0, 3.5):  # detuned chord stabs
            L = int(0.18 * SR)
            sig = sum(saw(hz(m + 12), L) for m in ch) / 3
            add(synth, t0 + k * beat, (0.16 if not intro else 0.10) * lp(sig, 0.25) * env(L, 0.07))
        arp = [ch[0] + 24, ch[1] + 24, ch[2] + 24, ch[1] + 24]
        for k in range(16):  # bright 16th arpeggio
            L = int(s16 * SR * 0.8); f = hz(arp[k % 4] + (12 if k in (6, 14) else 0))
            t = np.arange(L) / SR
            sq = np.sign(np.sin(2 * np.pi * f * t)).astype(np.float32) * 0.5 + np.sin(2 * np.pi * f * 2 * t).astype(np.float32) * 0.3
            add(synth, t0 + k * s16, 0.07 * lp(sq, 0.3) * env(L, 0.05))
        L = int(bar * SR); t = np.arange(L) / SR  # pad
        pad = sum(saw(hz(m), L, (0, 9, -9)) for m in ch) / 3
        add(synth, t0, 0.09 * lp(pad, 0.05) * np.minimum(1, np.minimum(t / 0.05, (bar - t) / 0.05)).astype(np.float32))
    # sidechain pump: duck synths on every kick
    tt = (np.arange(n) / SR) % beat
    pump = (0.25 + 0.75 * np.minimum(1, tt / (beat * 0.55)) ** 1.6).astype(np.float32)
    out = drums + synth * pump
    out = np.tanh(1.6 * out / max(1e-6, np.abs(out).max())).astype(np.float32)
    fade = int(1.0 * SR); out[-fade:] *= np.linspace(1, 0, fade); out[:int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))
    return out / max(1e-6, np.abs(out).max()) * 0.95

def mix(duration, vo_clips, with_music=True, music_db=-7, duck_db=-12, style="drive"):
    """vo_clips: list of (start_seconds, audio). Returns stereo int16 wav bytes."""
    n = int(duration * SR); vo = np.zeros(n, np.float32)
    for st, clip in vo_clips:
        s = int(st * SR); e = min(n, s + len(clip)); vo[s:e] += clip[:e - s]
    if with_music and not vo_clips:
        music_db = -1.0  # music-only Reels play the bed at full level
    gen = music_drive if style == "drive" else music
    bed = gen(duration) * 10 ** (music_db / 20) if with_music else np.zeros(n, np.float32)
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
