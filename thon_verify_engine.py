#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# THON SAFE JSON V58.19 - atomic json protection
try:
    import thon_safe_json
    thon_safe_json.activate()
except Exception as _thon_safe_json_err:
    print("[SAFE_JSON] falha ao ativar:", _thon_safe_json_err)

"""THON Toolkit V58.17 - Engine externa de VERIFICAÇÃO.
Recebe candidatos de busca DLP ou descoberta API e verifica por yt-dlp.
Mostra progresso ao vivo: candidato atual, score, aprovados/reprovados.
"""
import os, json, argparse, concurrent.futures
from datetime import datetime
from collections import Counter
from thon_engine_common import *

VERIFY_RESULT_FILE = os.path.join(APP_DIR, "thon_verify_result.json")


def get_first_video_id(cid, variant):
    variants = [variant] + [v for v in FALLBACK_ORDER if v != variant]
    last_err = ""
    for v in variants:
        r = run_ytdlp([
            "--flat-playlist", "--print", "%(id)s", "--playlist-end", "1",
            f"https://youtube.com/channel/{cid}"
        ], variant=v, timeout=55)
        if r.get("code") == 0 and r.get("out"):
            vid = (r.get("out") or "").splitlines()[0].strip()
            if vid and vid != "NA":
                return vid, v, ""
        last_err = (r.get("err") or "")[:300]
    return "", variant, last_err or "sem primeiro video"


def get_subs(cid, variant):
    vid, used_variant, err = get_first_video_id(cid, variant)
    if not vid:
        return 0, used_variant, err
    variants = [used_variant] + [v for v in FALLBACK_ORDER if v != used_variant]
    last_err = ""
    for v in variants:
        r = run_ytdlp(["--dump-json", f"https://youtube.com/watch?v={vid}"], variant=v, timeout=70)
        if r.get("code") == 0 and r.get("out"):
            try:
                data = json.loads(r.get("out"))
                subs = int(data.get("channel_follower_count") or 0)
                return subs, v, ""
            except Exception as e:
                last_err = str(e)
        else:
            last_err = (r.get("err") or "")[:300]
    return 0, used_variant, last_err or "sem inscritos"


# V58.34: filtro de gringo mais rigido (roda no verify antes de qualificar)
GRINGO_NOMES_FORTES = [
    "the ", "podcast", "show", "tv", "news", "channel", "official", "world",
    "daily", "weekly", "live", "talks", "academy", "school", "media", "production",
    "studios", "films", "entertainment", "network", "hub", "central", "zone",
    "english", "business", "money", "wealth", "success", "mindset", "growth",
    "marketing tips", "marketing school", "podcast en", "en español",
]
GRINGO_NOMES_BLOQUEIO_DIRETO = [
    "bloomberg", "euronews", "drumeo", "brad lea", "pat flynn", "dhar mann",
    "young and profiting", "ben amos", "engage video", "logan derosa",
    "she md", "bmv global", "brava film", "jogadim",
]

def is_gringo_name(nome):
    """V58.34: detecta canal gringo pelo nome (antes de qualificar)."""
    if not nome:
        return False, ""
    n = str(nome).lower().strip()
    # bloqueio direto por nome conhecido
    for g in GRINGO_NOMES_BLOQUEIO_DIRETO:
        if g in n:
            return True, f"nome_gringo_conhecido ({g})"
    # se tem 3+ sinais gringos no nome
    hits = sum(1 for g in GRINGO_NOMES_FORTES if g in n)
    if hits >= 3:
        return True, f"nome_gringo ({hits} sinais)"
    # nome com 2+ sinais EN, sem acentos e sem sinais PT
    pt_sinais = ["brasil", "brasileiro", "brasileira", "podcast", "canal", "empreendedor",
                 "negocio", "negócio", "financa", "finança", "vendas", "sucesso",
                 "cast", "portugues", "português", "pod"]
    pt_hits = sum(1 for p in pt_sinais if p in n)
    if hits >= 2 and pt_hits == 0 and not any(c in n for c in "áàâãéêíóôõúç"):
        return True, f"nome_possivel_gringo ({hits} sinais EN, 0 PT)"
    return False, ""


def get_videos_metrics(cid, variant):
    variants = [variant] + [v for v in FALLBACK_ORDER if v != variant]
    last_err = ""
    for v in variants:
        r = run_ytdlp([
            "--flat-playlist",
            "--print", "%(duration)s\t%(view_count)s\t%(upload_date)s",
            "--playlist-end", "25",
            f"https://youtube.com/channel/{cid}"
        ], variant=v, timeout=75)
        if r.get("code") != 0 or not r.get("out"):
            last_err = (r.get("err") or "")[:300]
            continue
        longos = shorts = total_views = total_longos = 0
        datas = []
        for line in (r.get("out") or "").splitlines():
            p = line.split("\t")
            try:
                dur = int(float(p[0])) if len(p) > 0 and p[0] else 0
                views = int(float(p[1])) if len(p) > 1 and p[1] else 0
                data = p[2] if len(p) > 2 else ""
                if dur > 600:
                    longos += 1
                    total_longos += 1
                    total_views += max(0, views)
                elif 0 < dur <= 90:
                    shorts += 1
                if data and len(data) >= 8:
                    datas.append(data[:8])
            except Exception:
                pass
        avg = total_views // total_longos if total_longos else 0
        dias = 999
        if datas:
            datas.sort(reverse=True)
            try:
                dt = datetime.strptime(datas[0], "%Y%m%d")
                dias = (datetime.now() - dt).days
            except Exception:
                pass
        return {"longos": longos, "shorts": shorts, "avg_views": avg, "ultimo_dias": dias, "used_variant": v}, ""
    return None, last_err or "sem videos"


def score_channel(subs, metrics, min_subs=10000, max_subs=200000, score_min=50):
    if subs < min_subs:
        return 0, f"subs abaixo {fmt(subs)}"
    if subs > max_subs:
        return 0, f"subs acima {fmt(subs)}"
    longos = int(metrics.get("longos") or 0)
    shorts = int(metrics.get("shorts") or 0)
    avg = int(metrics.get("avg_views") or 0)
    dias = int(metrics.get("ultimo_dias") or 999)
    score = 45
    if longos >= 3:
        score += 25
    elif longos >= 1:
        score += 12
    else:
        score -= 30
    if dias <= 45:
        score += 12
    elif dias <= 120:
        score += 6
    elif dias > 365:
        score -= 12
    if avg >= 1000:
        score += 12
    elif avg >= 300:
        score += 6
    if shorts >= 5:
        score -= 8
    score = max(0, min(100, int(score)))
    motivo = "" if (score >= score_min and longos >= 1) else f"score {score}, longos {longos}"
    return score, motivo


def verify_one(c, min_subs=10000, max_subs=200000, score_min=50):
    c = clean_candidate(c)
    cid = candidate_id(c)
    nome = candidate_name(c)
    variant = c.get("search_variant") or c.get("verify_variant") or "default_minus_websafari"
    if not cid:
        return {**c, "status": "reprovado", "score": 0, "motivo": "sem channel_id"}

    # V58.34: filtro de gringo PELO NOME antes de chamar yt-dlp (nao gasta quota)
    gringo, gringo_motivo = is_gringo_name(nome)
    if gringo:
        return {**c, "status": "reprovado", "score": 0, "subs": 0, "subs_fmt": "N/A",
                "motivo": f"gringo_nome: {gringo_motivo}", "verify_variant": variant,
                "longos": 0, "shorts": 0, "avg_views": 0, "ultimo_dias": 999}

    subs, subs_variant, err = get_subs(cid, variant)
    if subs <= 0:
        return {**c, "status": "reprovado", "score": 0, "subs": 0, "subs_fmt": "N/A", "motivo": "sem inscritos/erro", "verify_variant": subs_variant, "erro": err}
    if subs < min_subs or subs > max_subs:
        return {**c, "status": "reprovado", "score": 0, "subs": subs, "subs_fmt": fmt(subs), "motivo": f"subs fora {fmt(subs)}", "verify_variant": subs_variant}

    metrics, err_videos = get_videos_metrics(cid, subs_variant)
    if not metrics:
        return {**c, "status": "reprovado", "score": 0, "subs": subs, "subs_fmt": fmt(subs), "motivo": "sem videos/erro", "verify_variant": subs_variant, "erro": err_videos}

    score, motivo = score_channel(subs, metrics, min_subs, max_subs, score_min)
    status = "qualificado" if score >= score_min and int(metrics.get("longos") or 0) >= 1 else "reprovado"
    return {
        **c,
        "status": status,
        "score": score,
        "subs": subs,
        "subs_fmt": fmt(subs),
        "longos": int(metrics.get("longos") or 0),
        "shorts": int(metrics.get("shorts") or 0),
        "avg_views": int(metrics.get("avg_views") or 0),
        "ultimo_dias": int(metrics.get("ultimo_dias") or 999),
        "motivo": motivo,
        "verify_variant": metrics.get("used_variant") or subs_variant,
    }


def persist_partial(verificados, total, output_path=None, source="dlp"):
    qual = [x for x in verificados if x.get("status") == "qualificado"]
    rep = [x for x in verificados if x.get("status") != "qualificado"]
    payload = {
        "engine": "thon_verify_engine_v58_17",
        "source": source,
        "created_at": now(),
        "total": total,
        "processados": len(verificados),
        "qualificados_total": len(qual),
        "reprovados_total": len(rep),
        "qualificados": qual,
        "reprovados": rep,
        "verificados": verificados,
    }
    out = output_path or VERIFY_RESULT_FILE
    safe_write_json(out, payload)
    safe_write_json(VERIFY_RESULT_FILE, payload)
    return payload


def run_verify(candidates, verify_limit=0, workers=2, min_subs=10000, max_subs=200000, score_min=50, output_path=None, source="dlp"):
    cleaned = []
    seen = set()
    for c in candidates:
        if not isinstance(c, dict):
            continue
        cc = clean_candidate(c)
        cid = candidate_id(cc)
        if not cid or cid in seen:
            continue
        seen.add(cid)
        cleaned.append(cc)
    if verify_limit and int(verify_limit) > 0:
        cleaned = cleaned[:int(verify_limit)]
    total = len(cleaned)
    workers = max(1, int(workers or 1))

    update_status(
        etapa="verificacao",
        stage="verify",
        state="running",
        verify_total=total,
        verify_processados=0,
        verify_qualificados=0,
        verify_reprovados=0,
        preview_verificacao=short_preview(cleaned, 50),
        mensagem=f"Iniciando verificacao externa: {total} candidatos",
    )
    log(f"[VERIFY ENGINE] VERIFY SMART | source={source} | candidatos={total} | verify={total} | workers={workers}")

    verificados = []

    def on_result(r):
        verificados.append(r)
        qual = sum(1 for x in verificados if x.get("status") == "qualificado")
        rep = len(verificados) - qual
        update_status(
            etapa="verificacao",
            stage="verify",
            verify_processados=len(verificados),
            verify_total=total,
            verify_qualificados=qual,
            verify_reprovados=rep,
            candidato_atual={"nome": r.get("nome"), "id": r.get("id"), "status": r.get("status"), "score": r.get("score"), "subs_fmt": r.get("subs_fmt"), "motivo": r.get("motivo")},
            latest_verified=short_preview([r], 1),
            preview_qualificados=short_preview([x for x in verificados if x.get("status") == "qualificado"], 30),
            mensagem=f"Verificacao: {len(verificados)}/{total} | qualificados={qual} | reprovados={rep} | atual={r.get('nome')}",
        )
        log(f"[VERIFY ENGINE] {len(verificados):03d}/{total:03d} | {r.get('status','').upper():11} | score={int(r.get('score') or 0):3d} | subs={r.get('subs_fmt','N/A'):>6} | longos={str(r.get('longos','-')):>2} | avg={fmt(r.get('avg_views',0)):>5} | {r.get('nome','')[:60]}")
        if len(verificados) % 5 == 0 or r.get("status") == "qualificado":
            persist_partial(verificados, total, output_path, source)

    if workers == 1:
        for c in cleaned:
            on_result(verify_one(c, min_subs, max_subs, score_min))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(verify_one, c, min_subs, max_subs, score_min) for c in cleaned]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    on_result(fut.result())
                except Exception as e:
                    log(f"[VERIFY ENGINE ERRO] {e}")

    payload = persist_partial(verificados, total, output_path, source)
    update_status(
        etapa="verificacao_concluida",
        stage="verify_done",
        state="done",
        verify_processados=len(verificados),
        verify_total=total,
        verify_qualificados=payload["qualificados_total"],
        verify_reprovados=payload["reprovados_total"],
        preview_qualificados=short_preview(payload.get("qualificados") or [], 50),
        verify_result_file=os.path.basename(output_path or VERIFY_RESULT_FILE),
        mensagem=f"Verificacao concluida: qualificados={payload['qualificados_total']} | reprovados={payload['reprovados_total']}",
    )
    log(f"[VERIFY ENGINE] FINAL | qualificados={payload['qualificados_total']} | reprovados={payload['reprovados_total']} | arquivo={os.path.basename(output_path or VERIFY_RESULT_FILE)}")
    return payload


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", "--in", dest="input", default="thon_search_result.json")
    p.add_argument("--output", "--out", dest="output", default="")
    p.add_argument("--verify", "--verify-limit", dest="verify", type=int, default=0)
    p.add_argument("--workers", type=int, default=12)
    p.add_argument("--source", default="dlp")
    p.add_argument("--min-subs", dest="min_subs", type=int, default=10000)
    p.add_argument("--max-subs", dest="max_subs", type=int, default=200000)
    p.add_argument("--score-min", dest="score_min", type=int, default=50)
    args, _ = p.parse_known_args()
    path = args.input
    if not os.path.isabs(path):
        path = os.path.join(APP_DIR, path)
    candidates = load_candidates_from_file(path)
    run_verify(candidates, args.verify, args.workers, args.min_subs, args.max_subs, args.score_min, output_path=(args.output or None), source=args.source)

if __name__ == "__main__":
    main()
