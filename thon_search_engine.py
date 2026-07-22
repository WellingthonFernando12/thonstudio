#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# THON SAFE JSON V58.19 - atomic json protection
try:
    import thon_safe_json
    thon_safe_json.activate()
except Exception as _thon_safe_json_err:
    print("[SAFE_JSON] falha ao ativar:", _thon_safe_json_err)

"""THON Toolkit V58.17 - Engine externa de BUSCA.
Busca com yt-dlp, mostra brutos/blacklist/novos e grava progresso ao vivo.
"""
import os, json, time, argparse, concurrent.futures
from collections import Counter
from thon_engine_common import *

SEARCH_RESULT_FILE = os.path.join(APP_DIR, "thon_search_result.json")


def search_one_query(query, per_query=50):
    attempts = []
    best = None
    for variant in FALLBACK_ORDER:
        r = run_ytdlp([
            "--flat-playlist",
            "--print", "%(channel_id)s\t%(uploader)s",
            f"ytsearch{int(per_query)}:{query}",
        ], variant=variant, timeout=75)
        candidatos = parse_search_output(r.get("out"), query, variant)
        row = {
            "query": query,
            "variant": variant,
            "count": len(candidatos),
            "code": r.get("code"),
            "is_403": bool(r.get("is_403")),
            "timeout": bool(r.get("timeout")),
            "err": (r.get("err") or "")[:350],
        }
        attempts.append(row)
        # melhor parcial
        if best is None or len(candidatos) > len(best.get("candidatos", [])):
            best = dict(row)
            best["candidatos"] = candidatos
        # sucesso limpo: usa e para
        if candidatos and not r.get("is_403") and r.get("code") == 0:
            row["candidatos"] = candidatos
            return row, attempts
        # se veio parcial mas com 403, continua tentando fallback, mas guarda best
    if best is None:
        best = {"query": query, "variant": "base", "count": 0, "code": 999, "is_403": False, "timeout": False, "err": "sem resultado", "candidatos": []}
    return best, attempts


def run_search(query_limit=60, per_query=50, workers=2, blacklist_ids=None, queries=None, output_path=None):
    if blacklist_ids is None:
        blacklist_ids = load_blacklist(APP_DIR)
    if not queries:
        queries = DEFAULT_QUERIES
    # V58.33: se queries veio do backend (lista grande), respeita o tamanho dela;
    # query_limit so corta se for maior que a lista (limite maximo).
    # Antes: queries = list(queries)[:int(query_limit)]  ← cortava 420 pra 60 sempre
    queries = list(queries)
    if len(queries) > int(query_limit):
        # so corta se a lista for maior que o limite (limite = teto maximo)
        queries = queries[:int(query_limit)]
    workers = max(1, int(workers or 1))
    per_query = int(per_query or 50)

    update_status(
        engine="v58.17",
        etapa="busca",
        stage="search",
        state="running",
        query_total=len(queries),
        query_processadas=0,
        brutos_encontrados=0,
        blacklist_removidos=0,
        novos_para_verificar=0,
        mensagem="Iniciando busca DLP externa",
    )
    log(f"[SEARCH ENGINE] SEARCH SMART | queries={len(queries)} | per_query={per_query} | workers={workers} | blacklist={len(blacklist_ids)}")

    results = []
    attempts_all = []
    raw_by_id = {}
    existing_by_id = {}
    new_by_id = {}

    def handle_result(idx, result_tuple):
        row, attempts = result_tuple
        results.append(row)
        attempts_all.extend(attempts)
        # V58.33: conta novos vs repetidos POR QUERY (pra queries_metrics funcionar)
        query_novos = 0
        query_repetidos = 0
        for c in row.get("candidatos") or []:
            cid = candidate_id(c)
            if not cid:
                continue
            if cid not in raw_by_id:
                raw_by_id[cid] = c
            if cid in blacklist_ids:
                existing_by_id[cid] = c
                query_repetidos += 1
            else:
                if cid not in new_by_id:
                    new_by_id[cid] = c
                    query_novos += 1
                else:
                    query_repetidos += 1
        # V58.33: adiciona count_novos e count_repetidos no row (pra queries_metrics)
        row["count_novos"] = query_novos
        row["count_repetidos"] = query_repetidos
        update_status(
            etapa="busca",
            stage="search",
            query_processadas=idx,
            query_atual=row.get("query"),
            variante_atual=row.get("variant"),
            brutos_encontrados=len(raw_by_id),
            blacklist_removidos=len(existing_by_id),
            novos_para_verificar=len(new_by_id),
            latest_found=short_preview([row], 1),
            preview_brutos=short_preview(raw_by_id.values(), 30),
            preview_existentes=short_preview(existing_by_id.values(), 20),
            preview_novos=short_preview(new_by_id.values(), 30),
            mensagem=f"Busca: {idx}/{len(queries)} | brutos={len(raw_by_id)} | blacklist={len(existing_by_id)} | novos={len(new_by_id)}",
        )
        log(f"[SEARCH ENGINE] {row.get('query','')[:46]:46} | {row.get('variant','')[:24]:24} | +{row.get('count',0):2d} | brutos={len(raw_by_id):4d} | blacklist={len(existing_by_id):4d} | novos={len(new_by_id):4d} | 403={row.get('is_403')} | code={row.get('code')}")

    if workers == 1:
        for idx, q in enumerate(queries, 1):
            handle_result(idx, search_one_query(q, per_query))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
            future_map = {ex.submit(search_one_query, q, per_query): i for i, q in enumerate(queries, 1)}
            done_count = 0
            for fut in concurrent.futures.as_completed(future_map):
                done_count += 1
                try:
                    handle_result(done_count, fut.result())
                except Exception as e:
                    log(f"[SEARCH ENGINE ERRO] {e}")

    raw = list(raw_by_id.values())
    existing = list(existing_by_id.values())
    novos = list(new_by_id.values())
    summary = {
        "engine": "thon_search_engine_v58_17",
        "created_at": now(),
        "query_limit": len(queries),
        "per_query": per_query,
        "workers": workers,
        "brutos_encontrados": len(raw),
        "blacklist_removidos": len(existing),
        "novos_para_verificar": len(novos),
        "variant_final_usada": dict(Counter([x.get("variant") for x in results])),
        "tentativas_403_por_variante": dict(Counter([x.get("variant") for x in attempts_all if x.get("is_403")])),
        "queries": results,
        "tentativas": attempts_all,
        "candidatos_brutos": raw,
        "candidatos_existentes_blacklist": existing,
        "candidatos_novos": novos,
        "candidates": novos,
    }
    out = output_path or SEARCH_RESULT_FILE
    safe_write_json(out, summary)
    safe_write_json(SEARCH_RESULT_FILE, summary)
    update_status(
        etapa="busca_concluida",
        stage="search_done",
        state="search_done",
        brutos_encontrados=len(raw),
        blacklist_removidos=len(existing),
        novos_para_verificar=len(novos),
        preview_brutos=short_preview(raw, 30),
        preview_existentes=short_preview(existing, 30),
        preview_novos=short_preview(novos, 50),
        search_result_file=os.path.basename(out),
        mensagem=f"Busca concluida: brutos={len(raw)} | blacklist={len(existing)} | novos={len(novos)}",
    )
    log(f"[SEARCH ENGINE] FINAL | brutos={len(raw)} | blacklist={len(existing)} | novos={len(novos)} | arquivo={os.path.basename(out)}")
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queries", "--query-limit", dest="queries", type=int, default=60)
    p.add_argument("--per-query", dest="per_query", type=int, default=50)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--output", "--out", dest="output", default="")
    args, _ = p.parse_known_args()
    reset_log()
    run_search(args.queries, args.per_query, args.workers, output_path=(args.output or None))

if __name__ == "__main__":
    main()
