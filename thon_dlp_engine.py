#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# THON DLP WRAPPER V58.20 BACKEND-ONLY
# Em modo verify_only, NAO verifica via DLP. API direta joga no lote.
# Modo DLP/search normal continua chamando a engine original preservada.

from __future__ import annotations
import json, os, re, runpy, sys
from pathlib import Path
from datetime import datetime

APP = Path(__file__).resolve().parent
os.chdir(APP)
CORE = APP / "thon_dlp_engine_core_v58_17.py"
CHANNEL_RE = re.compile(r"UC[A-Za-z0-9_-]{20,30}")

try:
    import thon_safe_json
    thon_safe_json.activate()
except Exception as e:
    print("[SAFE_JSON] falha ao ativar:", e)

try:
    import thon_lote_repair_v58_20 as lote_sync
except Exception as e:
    lote_sync = None
    print("[LOTE SYNC V58.20] falha ao importar:", e)

def load_json(fname, default=None):
    try: return json.loads((APP / fname).read_text(encoding="utf-8", errors="replace"))
    except Exception: return default

def walk(x):
    if isinstance(x, dict):
        yield x
        for v in x.values(): yield from walk(v)
    elif isinstance(x, list):
        for v in x: yield from walk(v)

def get_id(o):
    if isinstance(o, dict):
        for k in ("id","channel_id","channelId","canal_id","youtube_channel_id"):
            v=o.get(k)
            if isinstance(v,str):
                m=CHANNEL_RE.search(v)
                if m: return m.group(0)
        for k in ("url","channel_url","webpage_url","link"):
            v=o.get(k)
            if isinstance(v,str):
                m=CHANNEL_RE.search(v)
                if m: return m.group(0)
    return ""

def normalize(o, source):
    cid=get_id(o)
    if not cid: return None
    name = o.get("nome") or o.get("title") or o.get("name") or o.get("channelTitle") or cid
    url = o.get("url") or o.get("channel_url") or f"https://youtube.com/channel/{cid}"
    out=dict(o)
    out.update({"id":cid,"channel_id":cid,"nome":name,"title":out.get("title") or name,"url":url,"source":out.get("source") or source,"status_fila":"pendente","qualificado":True,"engine_mode":"api_direct_no_dlp"})
    return out

def collect(fname, label):
    data=load_json(fname, None)
    arr=[]; seen=set()
    if data is None:
        print(f"[API DIRECT V58.20] {fname}: nao lido/nao existe")
        return arr
    for o in walk(data):
        if not isinstance(o, dict): continue
        n=normalize(o,label)
        if not n: continue
        cid=n["id"]
        if cid in seen: continue
        seen.add(cid); arr.append(n)
    print(f"[API DIRECT V58.20] {fname}: {len(arr)} candidatos")
    return arr

def arg_value(names, default=None):
    for i,a in enumerate(sys.argv):
        if a in names and i+1 < len(sys.argv): return sys.argv[i+1]
        for n in names:
            if a.startswith(n+"="): return a.split("=",1)[1]
    return default

def is_verify_only():
    txt=" ".join(sys.argv).lower()
    mode=(arg_value(["--mode","-mode"],"") or "").lower()
    if mode == "verify_only" or "verify_only" in txt:
        print("[DLP WRAPPER V58.20] verify_only detectado por argv")
        return True
    # backend antigo pode chamar sem argv, mas deixar status/input
    for fname in ["thon_dlp_engine_last_input.json","thon_engine_mode.json","thon_engine_status.json"]:
        data=load_json(fname,None)
        if data is None: continue
        raw=json.dumps(data, ensure_ascii=False).lower()
        if "verify_only" in raw or '"api_discovery_only": true' in raw:
            print(f"[DLP WRAPPER V58.20] verify_only detectado por {fname}")
            return True
    return False

def run_api_direct_no_dlp():
    print("="*78)
    print("THON DLP WRAPPER V58.20 | API DIRECT | DLP/VERIFY DESLIGADO")
    print("Nao chama SEARCH ENGINE e nao chama VERIFY ENGINE.")
    print("Queue/input viram lote de caca direto.")
    print("="*78)
    candidates=[]; seen=set()
    for fname,label in [("dlp_verification_queue.json","api_direct_queue"),("thon_dlp_engine_last_input.json","api_direct_input")]:
        for x in collect(fname,label):
            cid=x["id"]
            if cid in seen: continue
            seen.add(cid); candidates.append(x)
    if lote_sync:
        report=lote_sync.sync_api_direct_candidates(candidates, verbose=True)
        total=report.get("after") if isinstance(report,dict) else "?"
    else:
        total="?"
    out={"engine":"thon_dlp_wrapper_v58_20_api_direct","created_at":datetime.now().isoformat(timespec="seconds"),"mode":"api_direct_no_dlp","search_desligado":True,"verify_desligado":True,"qualificados":candidates,"lote":candidates,"stats":{"qualificados":len(candidates),"reprovados":0,"total_lote":total}}
    for f in ["thon_verify_result.json","thon_dlp_engine_last_output.json","thon_dlp_external_result.json","thon_engine_last_result.json"]:
        (APP/f).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"[API DIRECT V58.20] enviados ao lote: {len(candidates)} | total_lote={total}")

if is_verify_only():
    run_api_direct_no_dlp()
    raise SystemExit(0)

if not CORE.exists():
    print("ERRO: core original nao encontrado:", CORE)
    raise SystemExit(1)
print("[DLP WRAPPER V58.20] modo DLP/search normal: chamando engine original preservada")
runpy.run_path(str(CORE), run_name="__main__")
