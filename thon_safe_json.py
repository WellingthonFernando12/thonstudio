# THON SAFE JSON V58.19
# Atomic write + lock + .bak fallback for JSON files.
# Keeps API/engine logic untouched.

import os
import json
import time
import shutil
import builtins
import threading
from pathlib import Path

try:
    import fcntl
except Exception:
    fcntl = None

_ORIGINAL_OPEN = builtins.open
_ORIGINAL_PATH_WRITE_TEXT = Path.write_text
_ORIGINAL_JSON_LOAD = json.load

_ACTIVE = False
_LOCKS = {}
_LOCKS_GUARD = threading.RLock()

SAFE_JSON_NAMES = {
    "canais_brutos_api.json",
    "fila_pendente_api.json",
    "dlp_verification_queue.json",
    "youtube_api_quota_state.json",
    "youtube_api_key_rotation_state.json",
    "thon_engine_status.json",
    "thon_dlp_engine_last_input.json",
    "thon_dlp_engine_last_output.json",
    "thon_dlp_external_result.json",
    "thon_engine_last_result.json",
    "thon_search_result.json",
    "thon_verify_result.json",
    "winchester_aprovados.json",
    "winchester_reprovados.json",
    "winchester_vistos.json",
    "winchester_qualificados.json",
    "historico_aprovados.json",
    "historico_reprovados.json",
    "query_stats.json",
}

def _is_safe_json_path(path):
    try:
        p = Path(path)
        return p.name in SAFE_JSON_NAMES or (p.suffix == ".json" and p.name.startswith("thon_"))
    except Exception:
        return False

def _lock_path(path):
    p = Path(path)
    return p.with_name(p.name + ".lock")

def _tmp_path(path):
    p = Path(path)
    return p.with_name(f".{p.name}.tmp.{os.getpid()}.{threading.get_ident()}")

def _bak_path(path):
    p = Path(path)
    return p.with_name(p.name + ".bak")

class _FileLock:
    def __init__(self, path):
        self.path = Path(path)
        self.fp = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fp = _ORIGINAL_OPEN(str(_lock_path(self.path)), "a+", encoding="utf-8")
        if fcntl:
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if fcntl and self.fp:
                fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
        finally:
            if self.fp:
                self.fp.close()

class _AtomicWriteWrapper:
    def __init__(self, final_path, mode="w", *args, **kwargs):
        self.final_path = Path(final_path)
        self.tmp_path = _tmp_path(self.final_path)
        self.mode = mode
        self.args = args
        self.kwargs = kwargs
        self.lock = _FileLock(self.final_path)
        self.file = None
        self.closed = False

    def __enter__(self):
        self.lock.__enter__()
        self.final_path.parent.mkdir(parents=True, exist_ok=True)
        self.file = _ORIGINAL_OPEN(str(self.tmp_path), self.mode, *self.args, **self.kwargs)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close(commit=(exc_type is None))
        return False

    def __getattr__(self, name):
        return getattr(self.file, name)

    def write(self, *args, **kwargs):
        return self.file.write(*args, **kwargs)

    def writelines(self, *args, **kwargs):
        return self.file.writelines(*args, **kwargs)

    def flush(self):
        return self.file.flush()

    def close(self, commit=True):
        if self.closed:
            return
        self.closed = True

        try:
            if self.file:
                try:
                    self.file.flush()
                    os.fsync(self.file.fileno())
                except Exception:
                    pass
                self.file.close()

            if not commit:
                try:
                    self.tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                return

            # validate JSON before replacing final file
            try:
                raw = self.tmp_path.read_text(encoding=self.kwargs.get("encoding") or "utf-8", errors="replace")
                json.loads(raw)
            except Exception as e:
                bad = self.tmp_path.with_suffix(self.tmp_path.suffix + ".bad")
                try:
                    os.replace(str(self.tmp_path), str(bad))
                except Exception:
                    pass
                print(f"[SAFE_JSON] BLOQUEOU escrita invalida em {self.final_path.name}: {e}")
                print(f"[SAFE_JSON] tmp ruim salvo em: {bad.name}")
                return

            # keep .bak if current file is valid
            if self.final_path.exists():
                try:
                    old_raw = self.final_path.read_text(encoding="utf-8", errors="replace")
                    json.loads(old_raw)
                    shutil.copy2(self.final_path, _bak_path(self.final_path))
                except Exception:
                    # current file is already broken; do not overwrite .bak with broken file
                    pass

            os.replace(str(self.tmp_path), str(self.final_path))

        finally:
            try:
                self.lock.__exit__(None, None, None)
            except Exception:
                pass

def safe_open(file, mode="r", *args, **kwargs):
    # Atomic write only for target JSON files.
    # Read behavior is kept mostly normal, except json.load fallback handles .bak.
    if isinstance(file, (str, os.PathLike)):
        path = Path(file)
        writing = any(x in mode for x in ("w", "x")) and "b" not in mode and "a" not in mode
        if writing and _is_safe_json_path(path):
            if "encoding" not in kwargs:
                kwargs["encoding"] = "utf-8"
            return _AtomicWriteWrapper(path, mode, *args, **kwargs).__enter__()
    return _ORIGINAL_OPEN(file, mode, *args, **kwargs)

def safe_path_write_text(self, data, *args, **kwargs):
    if _is_safe_json_path(self):
        encoding = kwargs.get("encoding") or "utf-8"
        with _FileLock(self):
            tmp = _tmp_path(self)
            tmp.write_text(data, *args, **kwargs)
            try:
                json.loads(tmp.read_text(encoding=encoding, errors="replace"))
            except Exception as e:
                bad = tmp.with_suffix(tmp.suffix + ".bad")
                try:
                    os.replace(str(tmp), str(bad))
                except Exception:
                    pass
                print(f"[SAFE_JSON] BLOQUEOU write_text invalido em {Path(self).name}: {e}")
                return 0

            if Path(self).exists():
                try:
                    json.loads(Path(self).read_text(encoding=encoding, errors="replace"))
                    shutil.copy2(self, _bak_path(self))
                except Exception:
                    pass

            os.replace(str(tmp), str(self))
            return len(data)
    return _ORIGINAL_PATH_WRITE_TEXT(self, data, *args, **kwargs)

def safe_json_load(fp, *args, **kwargs):
    try:
        return _ORIGINAL_JSON_LOAD(fp, *args, **kwargs)
    except Exception as e:
        name = getattr(fp, "name", None)
        if name and _is_safe_json_path(name):
            bak = _bak_path(name)
            if bak.exists():
                try:
                    time.sleep(0.05)
                    with _ORIGINAL_OPEN(bak, "r", encoding="utf-8") as bf:
                        print(f"[SAFE_JSON] usando backup valido: {bak.name}")
                        return _ORIGINAL_JSON_LOAD(bf, *args, **kwargs)
                except Exception:
                    pass
        raise e

def activate():
    global _ACTIVE
    if _ACTIVE:
        return
    builtins.open = safe_open
    Path.write_text = safe_path_write_text
    json.load = safe_json_load
    _ACTIVE = True
    print("[SAFE_JSON] V58.19 ativo: atomic write + lock + bak fallback")

