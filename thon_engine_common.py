#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THON Toolkit V58.17 - Engine comum
- JSON atomico
- progresso visivel
- blacklist
- yt-dlp variants
"""
import os, sys, json, time, subprocess, traceback
from datetime import datetime
from collections import Counter

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STATUS_FILE = os.path.join(APP_DIR, "thon_engine_status.json")
LOG_FILE = os.path.join(APP_DIR, "thon_engine_live.log")
LAST_RESULT_FILE = os.path.join(APP_DIR, "thon_engine_last_result.json")

FALLBACK_ORDER = ["default_minus_websafari", "android", "no_cache", "base", "tv_simply"]
VARIANTES = {
    "default_minus_websafari": ["--extractor-args", "youtube:player_client=default,-web_safari"],
    "android": ["--extractor-args", "youtube:player_client=android"],
    "no_cache": ["--no-cache-dir"],
    "base": [],
    "tv_simply": ["--extractor-args", "youtube:player_client=tv_simply"],
}

NEGATIVOS = [
    "cortes", "corte ", "melhores momentos", "highlights", "resumo",
    "kids", "infantil", "gameplay", "twitch", "react", "shorts",
    "notícias", "noticias", "rádio", "radio", "tv brasil", "band jornal",
]

DEFAULT_QUERIES = [
    "empreendedorismo podcast", "podcast empreendedorismo brasil", "empreendedorismo podcast brasileiro",
    "entrevista empreendedorismo", "empreendedorismo entrevista podcast", "bate papo empreendedorismo",
    "cast empreendedorismo", "canal empreendedorismo podcast",
    "marketing digital podcast", "podcast marketing digital brasil", "marketing digital podcast brasileiro",
    "entrevista marketing digital", "marketing digital entrevista podcast", "bate papo marketing digital",
    "cast marketing digital", "canal marketing digital podcast",
    "negocios podcast", "podcast negocios brasil", "negocios podcast brasileiro", "entrevista negocios",
    "negocios entrevista podcast", "bate papo negocios", "cast negocios", "canal negocios podcast",
    "tecnologia podcast", "podcast tecnologia brasil", "tecnologia podcast brasileiro", "entrevista tecnologia",
    "tecnologia entrevista podcast", "bate papo tecnologia", "cast tecnologia", "canal tecnologia podcast",
    "financas podcast", "podcast financas brasil", "financas podcast brasileiro", "entrevista financas",
    "financas entrevista podcast", "bate papo financas", "cast financas", "canal financas podcast",
    "criador empreendedorismo brasil", "youtube empreendedorismo brasil", "especialista marketing digital youtube",
    "consultor negocios youtube", "podcast pequeno empreendedorismo", "canal pequeno empreendedorismo",
    "podcast independente tecnologia", "bate papo tecnologia brasil", "entrevista sobre tecnologia brasil",
    "canal negocios brasil", "profissional liberal podcast", "medico podcast brasil", "advogado podcast brasil",
    "contador podcast brasil", "nutricionista podcast brasil", "psicologo podcast brasil", "fisioterapeuta podcast brasil",
    "dentista podcast brasil", "consultor podcast brasil", "mentor podcast brasil",
    "dr podcast", "dra podcast", "advogado canal", "contador canal", "nutricionista youtube",
    "psicologo youtube", "fisioterapeuta canal", "dentista youtube", "professor podcast", "engenheiro podcast",
    "arquiteto podcast", "consultor youtube", "mentor youtube", "coach podcast", "medico canal",
]


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_read_json(path, default=None):
    if default is None:
        default = {}
    try:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # backup do arquivo corrompido, sem derrubar engine
        try:
            bkp = path + ".corrompido_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            os.replace(path, bkp)
            log(f"[json] arquivo corrompido movido: {os.path.basename(bkp)}")
        except Exception:
            pass
        return default


def safe_write_json(path, data):
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def log(msg):
    line = str(msg)
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def reset_log():
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"THON ENGINE LOG RESET {now()}\n")
    except Exception:
        pass


def update_status(**kwargs):
    data = safe_read_json(STATUS_FILE, default={})
    data.update(kwargs)
    data["updated_at"] = now()
    safe_write_json(STATUS_FILE, data)
    return data


def fmt(n):
    try:
        n = int(n)
        if n >= 1_000_000:
            return f"{n/1_000_000:.1f}M"
        if n >= 1000:
            return f"{n/1000:.0f}K"
        return str(n)
    except Exception:
        return "N/A"


def norm_id(x):
    if not x:
        return ""
    s = str(x).strip()
    if "/channel/" in s:
        s = s.split("/channel/", 1)[1].split("?",1)[0].split("/",1)[0]
    return s.strip()


def candidate_id(c):
    if not isinstance(c, dict):
        return ""
    for k in ["channel_id", "id", "canal_id", "youtube_channel_id", "cid"]:
        v = norm_id(c.get(k))
        if v and len(v) >= 8 and v != "NA":
            return v
    url = c.get("url") or c.get("channel_url") or c.get("canal_url") or ""
    return norm_id(url)


def candidate_name(c):
    if not isinstance(c, dict):
        return ""
    for k in ["nome", "title", "channel", "canal", "uploader", "name"]:
        v = str(c.get(k) or "").strip()
        if v:
            return v
    return candidate_id(c)


def clean_candidate(c):
    cid = candidate_id(c)
    nome = candidate_name(c)
    url = c.get("url") or c.get("channel_url") or (f"https://youtube.com/channel/{cid}" if cid else "")
    out = dict(c)
    out.update({
        "id": cid,
        "channel_id": cid,
        "nome": nome,
        "title": nome,
        "url": url,
    })
    return out


def load_candidates_from_file(path):
    data = safe_read_json(path, default=[])
    if isinstance(data, list):
        raw = data
    elif isinstance(data, dict):
        raw = []
        for key in ["candidates", "candidatos", "candidatos_novos", "candidatos_brutos", "novos", "qualificados", "lote", "fila", "canais", "aprovados", "reprovados", "vistos"]:
            if isinstance(data.get(key), list):
                raw = data.get(key)
                break
    else:
        raw = []
    out = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        c = clean_candidate(item)
        cid = c.get("id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        out.append(c)
    return out


def ids_from_json_file(path):
    data = safe_read_json(path, default={})
    ids = set()
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = []
        for key in ["vistos", "reprovados", "aprovados", "canais", "lote", "fila", "qualificados"]:
            if isinstance(data.get(key), list):
                items += data.get(key)
    else:
        items = []
    for x in items:
        if isinstance(x, str):
            cid = norm_id(x)
        elif isinstance(x, dict):
            cid = candidate_id(x)
        else:
            cid = ""
        if cid:
            ids.add(cid)
    return ids


def load_blacklist(app_dir=APP_DIR):
    paths = [
        "winchester_vistos.json",
        "winchester_reprovados.json",
        "winchester_aprovados.json",
        "historico_reprovados.json",
        "historico_aprovados.json",
    ]
    ids = set()
    for p in paths:
        ids |= ids_from_json_file(os.path.join(app_dir, p))
    return ids


def should_drop_name(nome):
    n = (nome or "").lower()
    return any(x in n for x in NEGATIVOS)


def run_ytdlp(args, variant="base", timeout=70):
    cmd = [sys.executable, "-m", "yt_dlp", "--no-warnings", "--quiet"]
    cookie = os.environ.get("THON_YTDLP_COOKIE_BROWSER", os.environ.get("COOKIE", "")).strip().lower()
    if cookie and cookie not in {"none", "off", "0", "false"}:
        cmd += ["--cookies-from-browser", cookie]
    cmd += VARIANTES.get(variant, [])
    cmd += list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        return {
            "code": r.returncode,
            "out": out,
            "err": err,
            "is_403": ("403" in err or "Forbidden" in err or "HTTP Error 403" in err),
            "timeout": False,
            "cmd": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {"code": 124, "out": "", "err": "TIMEOUT", "is_403": False, "timeout": True, "cmd": " ".join(cmd)}
    except Exception as e:
        return {"code": 999, "out": "", "err": str(e), "is_403": False, "timeout": False, "cmd": " ".join(cmd)}


def parse_search_output(out, query, variant):
    candidatos = []
    for line in (out or "").splitlines():
        p = line.split("\t")
        if len(p) < 2:
            continue
        cid = norm_id(p[0])
        nome = (p[1] or "").strip()
        if not cid or cid == "NA" or len(cid) < 8 or not nome:
            continue
        if should_drop_name(nome):
            continue
        candidatos.append({
            "id": cid,
            "channel_id": cid,
            "nome": nome,
            "title": nome,
            "url": f"https://youtube.com/channel/{cid}",
            "query": query,
            "found_query": query,
            "search_variant": variant,
            "source": "thon_search_engine_v58_17",
        })
    return candidatos


def short_preview(items, n=20):
    out = []
    for c in list(items)[:n]:
        if not isinstance(c, dict):
            continue
        out.append({
            "id": candidate_id(c),
            "nome": candidate_name(c),
            "url": c.get("url") or c.get("channel_url") or "",
            "query": c.get("query") or c.get("found_query") or "",
            "status": c.get("status") or "",
            "score": c.get("score") or "",
            "subs_fmt": c.get("subs_fmt") or "",
        })
    return out
