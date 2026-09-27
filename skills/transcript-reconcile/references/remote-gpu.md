# Running transcription on the GPU host

`tools/asr_remote.py` does this whole round trip; the manual steps below are for debugging it.

The config names the host: `gpu_host.ssh` (an ssh alias), `shell` (bash or pwsh), `work_root`, and `python` (a
Python with CUDA torch and faster-whisper; load torch before faster_whisper so ctranslate2 finds cuBLAS/cuDNN).

```bash
ssh HOST 'New-Item -ItemType Directory -Force -Path WORK/job | Out-Null; [Environment]::Exit(0)'   # pwsh
scp $EB/tools/transcribe_faster_whisper.py audio.wav vocab.txt "HOST:WORK/job/"
ssh HOST 'Set-Location WORK/job; & PYTHON transcribe_faster_whisper.py audio.wav --model large-v3 --prompt-file vocab.txt --out t.v3; & PYTHON transcribe_faster_whisper.py audio.wav --model large-v3-turbo --batched --out t.turbo; [Environment]::Exit(0)'
scp "HOST:WORK/job/t.*.json" transcript/
```

PowerShell over ssh:
- End every remote command with `; [Environment]::Exit(0)` or the session can hang on exit.
- Batch commands into one call; each call pays shell startup.
- For anything with `$variables`, copy a `.ps1` and run `pwsh -NoProfile -File script.ps1`.
- Other agents may share the host: check what a process is before stopping it.

Speed on an RTX 4090 (19 min of speech): large-v3 sequential with beam 5 about 170 s; turbo batched about 11 s.
The first run of a model downloads it (about 3 GB for large-v3); a zero-byte `model.bin` in the Hugging Face cache
means a broken earlier download: delete that snapshot and rerun.
