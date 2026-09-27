# Providers: paid options, free alternatives, and when to pay

editbay runs free and local by default. This file records every paid service met while building it, what it
would buy, what it costs (as far as verified), and the free route on our two machines. Update it whenever a new
provider comes up. Labels: **measured** (timed on our hardware this project), **doc** (read in the provider's
docs on the date given; recheck before spending), **est.** (estimate or not yet benchmarked).

## Our hardware (2026-09-26)

- **Research**: Mac Studio, Apple M5 Max, 36 GB unified memory. Metal/MPS and MLX. Runs HyperFrames renders, the
  Qwen3-TTS CustomVoice route (stock voices), and every editbay tool.
- **Titan**: Windows 11, RTX 4090 24 GB, CUDA 12.8, i7-12700, 32 GB. Runs faster-whisper, the devin-v1 voice clone
  (Qwen3-TTS 1.7B Base), NVENC, and downloads that need browser cookies.

Two machines with a real GPU each means most "AI features" have a local route. The gap is mostly generative video
quality and, for some jobs, speed of setup.

## Which machine does what (measured 2026-09-27)

Same inputs on both machines. Until 2026-09-27 every job started on Titan over ssh ran in Windows' efficiency mode
(low clocks for "background" processes); the numbers below are with the fix unless marked "throttled".

| Job | Research (M5 Max) | Titan (4090, i7-12700) | Use |
|---|---|---|---|
| ASR, 19.4 min of speech | mlx-whisper large-v3 98 s, WER 4.37% (65 s, 3.89% with guards); turbo 23 s, 1.77% | faster-whisper beam 5: large-v3 76 s, WER 1.84%; turbo 7.4 s, 1.25% (throttled: 152 s, 17 s) | Titan |
| ASR, 90 s narration | with guards: large-v3 3.8 s, 0.46%; turbo 1.6 s, 0.91% (unguarded 2.74%, 7.31%) | large-v3 4.8 s, 0.46%; turbo 1.1 s, 0.91% | either; the Mac only with guards |
| devin-v1 voice clone | MPS 2.79 s per second of speech; 15/15 sentences pass voiceover_check | 2.34 s/s (throttled 4.46) | Titan; the Mac is a tested fallback |
| HyperFrames render, 70 s promo, 1080p60 | 2m11s | 20m35s throttled (Chrome's processes; not re-measured) | the Mac |
| Delivery encode, 68.7 s 1080p60 at ~11.6 Mbps | x264 slow 35 s, medium 21 s (VMAF 92.7 both); VideoToolbox 19 s (VMAF 90.6) | x264 slow 60 s (throttled 288 s); NVENC H.264 17 s (92.5), HEVC 28 s (93.0); moving the master there: 35 s | the Mac, x264 medium; VideoToolbox for drafts |

- Guards for mlx-whisper: `condition_on_previous_text=False`, `hallucination_silence_threshold=2`. Without them the
  Mac invents and loops text over pauses.
- VMAF at matched bitrate: x264 and NVENC tie (92.5-93.0); VideoToolbox is about 2 points lower.
- The throttle: Windows puts processes started over ssh in its efficiency mode. x264 ran at 12 fps at Normal priority
  and 53 fps at AboveNormal (the same 600 frames). transcribe_faster_whisper.py raises its own priority and
  tts_worker_runner.py raises the worker's tree (a venv's python.exe is a launcher; its real interpreter does not
  inherit AboveNormal). For anything else started on Titan, raise it: `$p = Start-Process ... -PassThru;
  $p.PriorityClass = 'AboveNormal'`, or set it from inside the process. Declare ctypes handle types, or the call
  fails silently.

## Summary

| Capability | Default (free) | Paid options met | Pay when |
|---|---|---|---|
| Transcription | faster-whisper large-v3 + turbo on Titan, reconciled | ElevenLabs Scribe v2; OpenAI / Groq Whisper APIs | many speakers need diarization beyond our voiceprint tools, or Titan is down |
| Voice | devin-v1 on Titan (clone, with consent); Qwen3 "aiden"; Kokoro; `say` drafts | ElevenLabs, HeyGen, Gemini TTS, Fish Audio | a language or style the local models cannot do |
| Music | beat_bed.py (original, exact grid); Devin's own beats; CC0 / CC BY | Suno V6 via kie.ai; ElevenLabs Music; Lyria / HeyGen via HyperFrames | the music is featured, not a bed |
| Sound effects | sfx_synth.py; HyperFrames' bundled library (check credits) | ElevenLabs sound generation | a specific real-world sound we cannot synthesise or record |
| Stills / plates | own captures; local FLUX/SDXL (to set up) | Seedream 5 Pro, Nano Banana, Imagen 4, GPT Image via kie.ai; Gemini API | a hero image where local quality falls short after two tries |
| Generated video | HyperFrames motion on stills (parallax, camera moves); local Wan 2.2 / LTX-Video (to set up) | Kling v3 turbo, Veo 3.1, Seedance, Hailuo, Sora 2 via kie.ai | a photoreal moving shot that must look filmed |
| Background removal, upscale, interpolation | HyperFrames remove-background; rembg/BiRefNet, Real-ESRGAN, RIFE on the 4090 | Recraft remove-bg, Topaz upscale via kie.ai | rarely |
| Rendering | local: M5 Max renders a 60 s 1080p60 explainer in about 57 s | HyperFrames cloud (HeyGen), AWS Lambda, Cloud Run | long pieces on a deadline |
| Generic stock images | local models on the GPU host | Antigravity CLI `agy` with `gemini-3.8-flash-high` | when the local route is not ready and the plan covers the provider |
| X posting | manual posting | X API v2 | approved automated posting needs a measured per-post estimate |
| Frame descriptions | the agent reads batched contact sheets | Gemini via `hyperframes snapshot --describe` | never by default (sends frames out; descriptions were wrong in testing) |

## Details

### Transcription
- **Local (in use, measured):** 19.4 min of speech on the 4090: large-v3 sequential, beam 5, word timestamps in
  170 s; turbo batched in 11 s. Two passes plus a third source and `reconcile.py` fixed 82 errors a single pass
  left in (names, invented words, a dropped sentence).
- **ElevenLabs Scribe v2 (doc, 2026-09-26):** word or character timestamps, diarization up to 32 speakers,
  `keyterms` (up to 1000; +20% cost), `no_verbatim` (keep off for cutting), files up to 10 h, a forced-alignment
  endpoint for known scripts. `scribe_v1` is deprecated. Price per hour: not captured; check the pricing page.
- **OpenAI / Groq Whisper APIs (doc):** `verbose_json` with word timestamps imports into `hyperframes transcribe`.
  Price not verified here.
- **Benefit of paying:** diarization quality and zero setup. **Cost of not paying:** none so far; the local path
  is faster than a round trip for our lengths.
- **Free options not yet used:** WhisperX or stable-ts forced alignment (sharper word edges than Whisper's
  cross-attention timestamps); mlx-whisper or Parakeet MLX on the M5 Max when Titan is busy (est.).

### Voice
- **devin-v1 (in use, measured):** Qwen3-TTS 1.7B Base, in-context clone from REF-A2, on the 4090 through the
  explainers pipeline's clone worker. 14 sentences in a single ~190 s job (model load included); a one-sentence
  redo in ~40 s. Sentence-by-sentence with one seed per beat reads ~158 wpm with no stretching. Needs Devin's
  per-project yes and the disclosure line.
- **Qwen3 CustomVoice "aiden" (measured):** runs on the Mac (MPS); 8 sentences in ~85 s including load. Garbled one
  sentence in our test and mangled takes in earlier benchmarks: always run `voiceover_check.py`.
- **Paid (doc):** ElevenLabs TTS (also via kie.ai), HeyGen TTS (HyperFrames' first choice), Gemini TTS (needs a paid
  Google project; earlier lab notes), Fish Audio (key present; the explainers pipeline rejected paid narration for
  billing risk). Benefit: more languages and styles, no GPU. Cost: per-character billing (not verified here) and a
  third party holding voice data.
- **Free alternatives:** Chatterbox (Titan fallback), Kokoro-82M (`npx hyperframes tts`, local), `say` for drafts.

### Music
- **beat_bed.py (in use, measured):** original, deterministic, exact grid. A 22-bar bed renders in seconds; its grid
  lets render-verify prove cuts land on beats (detector check: 124 BPM generated, 123 BPM detected, 34 ms lag).
  Honest limit: it is a bed, not a song.
- **Suno V6 via kie.ai (doc):** instrumental, 10-360 s in custom mode, stems and MIDI available. Suno has no public
  self-serve API. kie.ai credits cost $0.005 each; per-song credits are not readable from the docs (est. check
  kie.ai/pricing). Results must be downloaded promptly (retention stated as 24 h to 14 days).
- **ElevenLabs Music (doc):** a composition plan with section durations, instrumental option. Price not verified.
- **Free alternatives:** Devin's own beats (preferred for Lil Gohan work), CC0/CC BY libraries with credit,
  MusicGen (HyperFrames' local fallback; runs on the 4090 or MPS; est.), Stable Audio Open on the 4090 (est.).
- **Pay when** the music carries the piece (a showreel or a promo) and a generated bed sounds generic.

### Sound effects
- **sfx_synth.py (in use):** 13 deterministic sounds, no licensing questions, required by brands that ban stock SFX.
- **ElevenLabs sound generation (doc):** 0.5-30 s per effect, `prompt_influence`, loops on v2. The capabilities page
  mentions 40 credits per second when a duration is set; verify against your plan before a batch.
- **Free alternatives:** HyperFrames media-use bundled SFX (read its CREDITS.md per file), Mixkit or Pixabay SFX
  (check each licence), recording real foley.

### Images
- **kie.ai (doc):** Seedream 5 Pro (1K/2K, up to 10 reference images), Nano Banana 2/Pro, Imagen 4, GPT Image,
  Flux-2, Ideogram, Recraft. kie.ai's own range: 10-50 credits per image, i.e. about $0.05-0.25 at $0.005 per
  credit (per-model prices not verified).
- **Gemini API (doc):** key present in the credentials file; Nano Banana image models. Paid usage terms apply.
- **Free alternatives:** own screenshots and site captures (`hyperframes capture --skip-vision`), official logos
  with their licence noted, FLUX.1 [schnell] or SDXL through ComfyUI on the 4090 (to set up; est. seconds per
  image), mflux (FLUX on MLX) on the M5 Max (est.).
- **Honesty rule:** generated images are illustrations and are labelled; never present them as captures.

- **Antigravity CLI `agy` with `gemini-3.8-flash-high` (measured, 2026-09-27):** generic stock-image tests took
  34 s and 29 s per image and returned 768x1376 PNGs natively. No per-call charge was seen under the Antigravity
  plan; treat that as plan-dependent, not a guarantee. **Free alternative:** local models on the GPU host.

### Generated video
- **kie.ai (doc):** Kling v3 turbo image-to-video (3-15 s, 720p/1080p; returns 24 fps: re-encode all-intra at 60 fps
  for seek-safe HyperFrames use), Veo 3.1 (16:9 or 9:16, 1080p/4K, audio), Seedance, Hailuo, Wan 3.0, Sora 2. kie.ai's
  own range: 100-500 credits per video, about $0.50-2.50 per clip (per-model prices not verified).
- **Free alternatives:** HyperFrames motion on stills (camera moves, parallax, depth, masks) covers most B-roll needs
  at zero cost; open models on the 4090: Wan 2.2 (5B text/image-to-video at 720p), LTX-Video (fast), HunyuanVideo
  (heavy) (all est.; not benchmarked here). Expect a visible quality gap to Kling or Veo on photoreal people.
- **Pay when** a shot must look filmed and cannot be captured. Label it as generated.

### Rendering and delivery
- **Local (measured):** HyperFrames renders the 60 s 1080p60 explainer in ~57 s on the M5 Max (high quality);
  4 s test at 1080p60 in 9.6 s including setup. Titan's NVENC matches x264 quality in half the time, but moving a
  master there costs about as long as encoding it here; renders and delivery encodes stay on the Mac (see Which machine
  does what).
- **Paid (doc):** HyperFrames cloud rendering through HeyGen, AWS Lambda, Google Cloud Run. Useful for long 4K
  pieces on a deadline; not needed at our current lengths.

### Posting

- **X API v2 (doc, 2026-09-27):** pay-per-use posting was listed at about $0.015 per post or $0.20 with a URL;
  recheck the [X API v2 pricing](https://docs.x.com/x-api/getting-started/pricing) before spending. **Free
  alternative:** manual posting.

## Estimating a paid run

Write the estimate in the project's `HUMAN_QUEUE.md` before the first call:

```
- [ ] SPEND: 6 x Kling v3 turbo 5 s 1080p via kie.ai for the B-roll in beats C12-C17.
      Estimate: 6 x 100-500 credits = 600-3000 credits = $3-15 (kie.ai range; per-model price read on <date>).
      Free alternative tried: HyperFrames parallax on captured stills (qa/strips_03.jpg); falls short because ...
      Approve / decline:
```

Cap retries at two per asset; a third attempt means the prompt or the plan is wrong.
