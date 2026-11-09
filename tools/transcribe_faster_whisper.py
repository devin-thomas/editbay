"""Transcribe one audio file with faster-whisper on the GPU; write JSON (segments + word timestamps), SRT and TXT.

Usage: python transcribe_faster_whisper.py <audio.wav> --model large-v3 [--prompt-file vocab.txt] [--batched] --out <stem>
Needs a Python with CUDA torch + faster-whisper (the GPU host's venv); CPU works with --device cpu --compute int8.

Hallucination guards (on by default for the sequential decoder):
  --condition-previous off   reduces repetition loops
  --hallucination-silence 2  re-decodes segments whose words sit in >2 s of silence (needs word timestamps)
  VAD min silence 500 ms     so pauses inside speech are cut out before decoding
These do not stop every invention: large-v3 still adds "Wait," after long pauses in TTS audio (turbo did not, but
turbo drops fillers). Run both models and let reconcile.py vote; never trust one pass.
Use --prompt-file only for names and jargon (a comma list); it biases spelling, it is not an instruction.
"""
import argparse, json, os, time

# ctranslate2 needs cuBLAS/cuDNN; torch's wheel ships them, so load torch first and expose its DLL dir.
import torch  # noqa: F401
os.environ["PATH"] = os.path.join(os.path.dirname(torch.__file__), "lib") + os.pathsep + os.environ["PATH"]
from faster_whisper import WhisperModel, BatchedInferencePipeline


def ts(t, sep=","):
    h, rem = divmod(t, 3600); m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)) % 1000:03d}"


def unthrottle():
    """Windows treats a process started over ssh as background work and runs it at low clocks (EcoQoS). Measured on
    gpu-workstation (i7-12700): x264 at Normal priority 12 fps, at AboveNormal 53 fps. Raises this interpreter, which is the real
    one even when a venv launcher started it (the launcher's child does not inherit AboveNormal)."""
    if os.name == "nt":
        import ctypes
        k = ctypes.windll.kernel32
        k.GetCurrentProcess.restype = ctypes.c_void_p            # a 64-bit pseudo-handle; untyped ctypes truncates it
        k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        k.SetPriorityClass(k.GetCurrentProcess(), 0x8000)        # ABOVE_NORMAL_PRIORITY_CLASS


def main():
    unthrottle()
    ap = argparse.ArgumentParser()
    ap.add_argument("audio"); ap.add_argument("--model", default="large-v3")
    ap.add_argument("--prompt-file"); ap.add_argument("--batched", action="store_true")
    ap.add_argument("--hotwords", help="comma list of terms to favour (faster-whisper hotwords)")
    ap.add_argument("--condition-previous", action="store_true", help="condition on previous text (off by default)")
    ap.add_argument("--hallucination-silence", type=float, default=2.0)
    ap.add_argument("--vad-min-silence-ms", type=int, default=500)
    ap.add_argument("--device", default="cuda"); ap.add_argument("--compute", default="float16")
    ap.add_argument("--language", default="en")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    prompt = open(a.prompt_file, encoding="utf-8").read().strip() if a.prompt_file else None
    model = WhisperModel(a.model, device=a.device, compute_type=a.compute)
    t0 = time.time()
    kw = dict(language=a.language, word_timestamps=True, initial_prompt=prompt, beam_size=5, vad_filter=True,
              vad_parameters={"min_silence_duration_ms": a.vad_min_silence_ms}, hotwords=a.hotwords)
    if a.batched:
        segs, info = BatchedInferencePipeline(model=model).transcribe(a.audio, batch_size=16, **kw)
    else:
        segs, info = model.transcribe(a.audio, condition_on_previous_text=a.condition_previous,
                                      hallucination_silence_threshold=a.hallucination_silence, **kw)
    out = []
    for s in segs:
        out.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                    "avg_logprob": round(s.avg_logprob, 3), "no_speech_prob": round(s.no_speech_prob, 3),
                    "words": [[round(w.start, 2), round(w.end, 2), w.word, round(w.probability, 3)] for w in (s.words or [])]})
    el = time.time() - t0
    meta = {"audio": a.audio, "model": a.model, "batched": a.batched, "prompt": prompt, "hotwords": a.hotwords,
            "condition_previous": a.condition_previous, "duration": info.duration,
            "seconds": round(el, 1), "segments": out}
    json.dump(meta, open(a.out + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(a.out + ".srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(out, 1):
            f.write(f"{i}\n{ts(s['start'])} --> {ts(s['end'])}\n{s['text']}\n\n")
    with open(a.out + ".txt", "w", encoding="utf-8") as f:
        for s in out:
            m, sec = divmod(int(s["start"]), 60)
            f.write(f"[{m:02d}:{sec:02d}] {s['text']}\n")
    print(f"{a.model}{' batched' if a.batched else ''}: {len(out)} segments, {info.duration/60:.1f} min audio in {el:.0f} s "
          f"({info.duration/el:.0f}x)", flush=True)


if __name__ == "__main__":
    main()
