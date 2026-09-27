#!/usr/bin/env python3
"""Run a JSON-lines TTS worker on the machine that has the GPU, under that machine's GPU lock (stdlib only).

The worker protocol (Qwen3-TTS CustomVoice worker.py and clone_worker.py share it): the first stdout line announces
readiness; then one JSON request per stdin line ({"text", "output_path", "seed", "settings", optional "voice_id"})
and one JSON response per stdout line ({"ok", "sample_rate", "samples", "wall_s", ...}).

Usage (on the GPU host):  python tts_worker_runner.py job.json
job.json:
  {"worker": {"python": "...python.exe", "script": ".../clone_worker.py",
              "args": ["--ckpt-dir", "...", "--profile", ".../profile.json"],
              "env": {"HF_HOME": "...", "HF_HUB_OFFLINE": "1", "PYTHONIOENCODING": "utf-8"}},
   "lock": ".../runs/.gpu.lock",
   "out_dir": ".../tts/<job>",
   "items": [{"id": "s001", "text": "...", "seed": 123, "settings": {"language": "English"}}]}
Writes out_dir/<id>.wav (native float WAV from the worker) and out_dir/results.json. Items whose WAV exists with the
same text hash are skipped, so an interrupted job resumes. Exit 1 if any item failed.
"""
import atexit, hashlib, json, os, subprocess, sys, time


def alive(pid):
    if os.name == "nt":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong(); ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return code.value == 259
    try:
        os.kill(pid, 0); return True
    except OSError:
        return False


def take_lock(path):
    """One GPU job at a time on this machine: the same pid lock the narration pipelines use."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode()); os.close(fd)
            atexit.register(lambda: os.path.exists(path) and os.remove(path))
            return
        except FileExistsError:
            owner = open(path, encoding="utf-8").read().strip()
            if owner.isdigit() and not alive(int(owner)):
                os.remove(path); continue
            raise SystemExit(f"GPU busy: pid {owner} holds {path}. Wait for it; do not delete a live lock.")


def read_msg(proc):
    while True:
        line = proc.stdout.readline()
        if not line:
            return None
        try:
            msg = json.loads(line)
            if isinstance(msg, dict):
                return msg
        except json.JSONDecodeError:
            continue


def main():
    job = json.load(open(sys.argv[1], encoding="utf-8"))
    out = job["out_dir"]; os.makedirs(out, exist_ok=True)
    rpath = os.path.join(out, "results.json")
    results = json.load(open(rpath, encoding="utf-8")) if os.path.exists(rpath) else {}
    sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()
    todo = [it for it in job["items"] if not (os.path.exists(os.path.join(out, it["id"] + ".wav"))
                                              and results.get(it["id"], {}).get("text_sha256") == sha(it["text"])
                                              and results[it["id"]].get("seed") == it.get("seed"))]
    print(f"{len(todo)}/{len(job['items'])} items to generate", flush=True)
    if not todo:
        return 0
    take_lock(job["lock"])
    w = job["worker"]
    env = {**os.environ, **w.get("env", {})}
    err = open(os.path.join(out, "worker.log"), "a", encoding="utf-8")
    proc = subprocess.Popen([w["python"], w["script"], *w.get("args", [])], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=err, text=True, encoding="utf-8", env=env)
    atexit.register(proc.terminate)
    ready = read_msg(proc)
    if not ready or not ready.get("ready"):
        raise SystemExit(f"worker did not become ready; see {os.path.join(out, 'worker.log')}")
    print(f"worker ready on {ready.get('device')} ({ready.get('dtype')})", flush=True)
    failed = 0
    for it in todo:
        wav = os.path.join(out, it["id"] + ".wav")
        req = {"text": it["text"], "output_path": wav, "seed": it.get("seed"), "settings": it.get("settings") or {"language": "English"}}
        if it.get("voice_id"):
            req["voice_id"] = it["voice_id"]
        t0 = time.time()
        proc.stdin.write(json.dumps(req) + "\n"); proc.stdin.flush()
        r = read_msg(proc)
        if r is None:
            raise SystemExit("worker exited mid-job; see worker.log")
        ok = bool(r.get("ok"))
        failed += not ok
        results[it["id"]] = {"ok": ok, "text_sha256": sha(it["text"]), "seed": it.get("seed"),
                             "sample_rate": r.get("sample_rate"), "samples": r.get("samples"), "wall_s": r.get("wall_s"),
                             "error": r.get("error")}
        json.dump(results, open(rpath, "w", encoding="utf-8"), indent=1)
        print(f"[{'ok' if ok else 'FAILED'}] {it['id']} {round(time.time() - t0, 1)}s  {it['text'][:70]}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
