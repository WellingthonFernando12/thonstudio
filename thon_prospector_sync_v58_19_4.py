# -*- coding: utf-8 -*-
"""
THON PROSPECTOR SYNC V58.19.4
Backend-only helper.

Responsabilidade:
- Ler thon_verify_result.json / outputs equivalentes.
- Extrair qualificados do DLP.
- Inserir esses qualificados no lote de caca/fila de aprovacao.
- Evitar duplicatas.
- Escrita atomica.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

APP = Path(__file__).resolve().parent
CHANNEL_RE = re.compile(r"^UC[A-Za-z0-9_-]{20,30}$")

LOTE_FILES = [
    "fila_pendente_api.json",
]

QUALIFIED_FILES = [
    "winchester_qualificados.json",
]

BRUTO_FILES = [
    "canais_brutos_api.json",
]

VERIFY_RESULT_FILES = [
    "thon_verify_result.json",
    "thon_dlp_engine_last_output.json",
    "thon_dlp_external_result.json",
    "thon_engine_last_result.json",
]

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def load_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.is_absolute():
        p = APP / p
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        # fallback .bak quando existir
        bak = Path(str(p) + ".bak")
        if bak.exists():
            try:
                return json.loads(bak.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                pass
        return default

def atomic_write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    if not p.is_absolute():
        p = APP / p
    p.parent.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    tmp = p.with_name(f".{p.name}.tmp.{ts}")
    raw = json.dumps(data, ensure_ascii=False, indent=2)
    tmp.write_text(raw, encoding="utf-8")
    # valida antes de substituir
    json.loads(tmp.read_text(encoding="utf-8"))
    if p.exists():
        try:
            shutil.copy2(p, Path(str(p) + ".bak"))
        except Exception:
            pass
    os.replace(tmp, p)

def walk(x: Any) -> Iterable[Any]:
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from walk(v)
    elif isinstance(x, list):
        for v in x:
            yield from walk(v)

def get_channel_id(o: Any) -> str:
    if not isinstance(o, dict):
        return ""
    for k in ("channel_id", "id", "channelId", "canal_id", "youtube_channel_id"):
        v = o.get(k)
        if isinstance(v, str) and CHANNEL_RE.match(v):
            return v
    # URLs as vezes guardam /channel/UC...
    for k in ("url", "channel_url", "webpage_url", "link"):
        v = o.get(k)
        if isinstance(v, str):
            m = re.search(r"UC[A-Za-z0-9_-]{20,30}", v)
            if m:
                return m.group(0)
    return ""

def get_name(o: Dict[str, Any], cid: str) -> str:
    for k in ("nome", "title", "name", "channelTitle", "canal", "channel", "channel_name"):
        v = o.get(k)
        if isinstance(v, str) and v.strip():
            return " ".join(v.split())[:180]
    return cid

def get_url(o: Dict[str, Any], cid: str) -> str:
    for k in ("url", "channel_url", "webpage_url", "link"):
        v = o.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return f"https://youtube.com/channel/{cid}"

def normalize_candidate(o: Dict[str, Any], source: str = "sync") -> Dict[str, Any] | None:
    cid = get_channel_id(o)
    if not cid:
        return None
    name = get_name(o, cid)
    out = dict(o)
    out.update({
        "id": cid,
        "channel_id": cid,
        "nome": name,
        "title": name,
        "url": get_url(o, cid),
        "source": o.get("source") or source,
        "qualificado": True,
        "status": o.get("status") or "qualificado",
        "lote_status": o.get("lote_status") or "pendente_aprovacao",
        "synced_to_lote_at": _now(),
        "sync_version": "v58.19.4",
    })
    return out

def _looks_qualified(o: Dict[str, Any], parent_key: str = "") -> bool:
    pk = (parent_key or "").lower()
    if any(x in pk for x in ("qualificado", "qualified", "aprovado", "approved")):
        if not any(x in pk for x in ("reprov", "reject", "fail", "erro")):
            return True

    for k in ("status", "resultado", "result", "classificacao", "classification", "decision"):
        v = o.get(k)
        if isinstance(v, str):
            vv = v.lower()
            if any(x in vv for x in ("qualificado", "qualified", "aprovado", "approved")) and not any(x in vv for x in ("reprov", "reject", "fail")):
                return True

    for k in ("qualificado", "qualified", "is_qualified", "aprovado", "approved"):
        if o.get(k) is True:
            return True

    # fallback por score: so usa se a propria estrutura indicar verify/lead e nao for reprovado
    score = o.get("score")
    if isinstance(score, (int, float)) and score >= 50:
        txt = json.dumps(o, ensure_ascii=False).lower()
        if not any(x in txt for x in ("reprovado", "rejected", "sem inscritos", "fora do range")):
            if get_channel_id(o):
                return True

    return False

def extract_qualified_from_data(data: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()

    def visit(x: Any, parent_key: str = "") -> None:
        if isinstance(x, dict):
            # listas principais: qualificados / approved / etc
            for k, v in x.items():
                kl = str(k).lower()
                if isinstance(v, list) and any(word in kl for word in ("qualificado", "qualified", "aprovado", "approved")) and not any(word in kl for word in ("reprov", "reject")):
                    for item in v:
                        if isinstance(item, dict):
                            n = normalize_candidate(item, f"verify_result:{k}")
                            if n and n["channel_id"] not in seen:
                                seen.add(n["channel_id"])
                                out.append(n)
                elif isinstance(v, (dict, list)):
                    visit(v, kl)

            # item isolado marcado como qualificado
            if _looks_qualified(x, parent_key):
                n = normalize_candidate(x, f"verify_result:{parent_key or 'item'}")
                if n and n["channel_id"] not in seen:
                    seen.add(n["channel_id"])
                    out.append(n)

        elif isinstance(x, list):
            for item in x:
                visit(item, parent_key)

    visit(data)
    return out

def extract_qualified_from_files(files: List[str] | None = None) -> List[Dict[str, Any]]:
    files = files or VERIFY_RESULT_FILES
    all_items: List[Dict[str, Any]] = []
    seen = set()
    for fname in files:
        data = load_json(fname, None)
        if data is None:
            continue
        for item in extract_qualified_from_data(data):
            cid = item["channel_id"]
            if cid in seen:
                continue
            seen.add(cid)
            item["sync_source_file"] = fname
            all_items.append(item)
    return all_items

def _load_list_file(fname: str) -> List[Dict[str, Any]]:
    data = load_json(fname, [])
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        # formatos comuns com lista dentro
        for key in ("items", "candidatos", "novos", "fila", "leads", "data", "qualificados"):
            v = data.get(key)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
        # dict por id
        vals = [v for v in data.values() if isinstance(v, dict)]
        if vals:
            return vals
    return []

def _merge_into_list_file(fname: str, candidates: List[Dict[str, Any]]) -> Tuple[int, int]:
    existing = _load_list_file(fname)
    seen = set()
    cleaned = []
    for item in existing:
        cid = get_channel_id(item)
        if cid and cid in seen:
            continue
        if cid:
            seen.add(cid)
        cleaned.append(item)

    added = 0
    for cand in candidates:
        cid = get_channel_id(cand)
        if not cid or cid in seen:
            continue
        cleaned.append(cand)
        seen.add(cid)
        added += 1

    atomic_write_json(fname, cleaned)
    return added, len(cleaned)

def sync_qualificados_to_lote(files: List[str] | None = None, verbose: bool = True) -> Dict[str, Any]:
    qualificados = extract_qualified_from_files(files)
    report: Dict[str, Any] = {
        "version": "v58.19.4",
        "ran_at": _now(),
        "qualified_found": len(qualificados),
        "files": {},
        "qualified_ids": [q.get("channel_id") for q in qualificados],
    }

    if not qualificados:
        if verbose:
            print("[LOTE SYNC V58.19.4] nenhum qualificado novo encontrado nos outputs")
        atomic_write_json("thon_lote_sync_report.json", report)
        return report

    for fname in LOTE_FILES + QUALIFIED_FILES + BRUTO_FILES:
        try:
            added, total = _merge_into_list_file(fname, qualificados)
            report["files"][fname] = {"added": added, "total": total}
            if verbose:
                print(f"[LOTE SYNC V58.19.4] {fname}: +{added} | total={total}")
        except Exception as e:
            report["files"][fname] = {"error": str(e)}
            if verbose:
                print(f"[LOTE SYNC V58.19.4] ERRO {fname}: {e}")

    atomic_write_json("thon_lote_sync_report.json", report)
    return report

def install_backend_hooks() -> None:
    # Hook leve: no startup do backend, sincroniza qualquer verify_result que ficou sem entrar no lote.
    try:
        sync_qualificados_to_lote(verbose=True)
    except Exception as e:
        print("[LOTE SYNC V58.19.4] falha no hook backend:", e)
