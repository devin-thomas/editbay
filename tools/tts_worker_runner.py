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


def release_lock(path):
    """Remove the lock only while it still names this process."""
    try:
        if open(path, encoding="utf-8").read().strip() == str(os.getpid()):
            os.remove(path)
    except OSError:
        pass


def take_lock(path, wait_s=2700, poll_s=5):
    """One GPU job at a time on this machine: the same pid lock the narration pipelines use.

    Queues instead of failing: while a live process holds the lock, poll every poll_s seconds for up to wait_s
    (default 45 min; job "lock_wait_s" overrides). A lock left by a dead pid is cleared. Concurrent producers used to
    exit on the first "GPU busy" and one fell back to a non-cloned voice (EditorialPipeline wave 1, 2026-09-27).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    deadline, announced = time.time() + wait_s, False
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode()); os.close(fd)
            atexit.register(release_lock, path)
            if announced:
                print("GPU lock acquired", file=sys.stderr, flush=True)
            return
        except FileExistsError:
            try:
                owner = open(path, encoding="utf-8").read().strip()
            except OSError:
                continue  # released between our open and read
            if owner.isdigit() and not alive(int(owner)):
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            if time.time() >= deadline:
                raise SystemExit(f"GPU busy: pid {owner} still holds {path} after {wait_s} s. Do not delete a live lock.")
            if not announced:
                print(f"GPU busy: pid {owner} holds {path}; waiting up to {wait_s} s", file=sys.stderr, flush=True)
                announced = True
            time.sleep(poll_s)


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


def raise_tree(pid):
    """Windows runs processes started over ssh at low clocks (EcoQoS); AboveNormal priority lifts that (x264 on gpu-workstation:
    12 fps at Normal, 53 fps at AboveNormal). A venv's python.exe is a launcher whose child is the real interpreter, and
    that child starts at Normal whatever the launcher got, so raise the whole tree once it exists."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes
    k = ctypes.windll.kernel32

    class PE(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]
    k.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    k.Process32First.argtypes = k.Process32Next.argtypes = [ctypes.c_void_p, ctypes.POINTER(PE)]
    k.OpenProcess.restype = ctypes.c_void_p
    k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    for _ in range(20):                                  # the launcher starts its child a moment later
        snap, e, kids = k.CreateToolhelp32Snapshot(2, 0), PE(), {}
        e.dwSize = ctypes.sizeof(PE)
        ok = k.Process32First(snap, ctypes.byref(e))
        while ok:
            kids.setdefault(e.th32ParentProcessID, []).append(e.th32ProcessID)
            ok = k.Process32Next(snap, ctypes.byref(e))
        k.CloseHandle(snap)
        tree, todo = [], [pid]
        while todo:
            p = todo.pop(); tree.append(p); todo += kids.get(p, [])
        if len(tree) > 1:
            break
        time.sleep(0.1)
    for p in tree:
        h = k.OpenProcess(0x0200, False, p)                 # PROCESS_SET_INFORMATION
        if h:
            k.SetPriorityClass(h, 0x8000); k.CloseHandle(h)  # ABOVE_NORMAL_PRIORITY_CLASS


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
    take_lock(job["lock"], wait_s=int(job.get("lock_wait_s", 2700)))
    w = job["worker"]
    env = {**os.environ, **w.get("env", {})}
    err = open(os.path.join(out, "worker.log"), "a", encoding="utf-8")
    proc = subprocess.Popen([w["python"], w["script"], *w.get("args", [])], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=err, text=True, encoding="utf-8", env=env)
    raise_tree(proc.pid)
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
