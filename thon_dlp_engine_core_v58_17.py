#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# THON SAFE JSON V58.19 - atomic json protection
try:
    import thon_safe_json
    thon_safe_json.activate()
except Exception as _thon_safe_json_err:
    print("[SAFE_JSON] falha ao ativar:", _thon_safe_json_err)

"""THON Toolkit V58.17 - Orquestrador DLP externo visivel.
Mantem contrato antigo do backend: modo search_verify retorna JSON com qualificados/reprovados.
Internamente separa BUSCA e VERIFICACAO.
"""
import os, sys, json, argparse
from thon_engine_common import *
from thon_search_engine import run_search, SEARCH_RESULT_FILE
from thon_verify_engine import run_verify, VERIFY_RESULT_FILE

FINAL_RESULT_FILE = os.path.join(APP_DIR, "thon_dlp_external_result.json")


def merge_final(search_payload, verify_payload, output_path=None):
    payload = {
        "engine": "thon_dlp_engine_v58_17_visible_split_search_verify",
        "created_at": now(),
        "mode": "search_verify",
        "stats": {
            "brutos_encontrados": search_payload.get("brutos_encontrados", 0),
            "blacklist_removidos": search_payload.get("blacklist_removidos", 0),
            "novos_para_verificar": search_payload.get("novos_para_verificar", 0),
            "verificados": verify_payload.get("processados", 0),
            "qualificados": verify_payload.get("qualificados_total", 0),
            "reprovados": verify_payload.get("reprovados_total", 0),
        },
        "busca": search_payload,
        "verificacao": verify_payload,
        # nomes compatíveis com backend antigo
        "candidatos_brutos": search_payload.get("candidatos_brutos") or [],
        "candidatos_existentes_blacklist": search_payload.get("candidatos_existentes_blacklist") or [],
        "candidatos_novos": search_payload.get("candidatos_novos") or [],
        "candidates": search_payload.get("candidatos_novos") or [],
        "qualificados": verify_payload.get("qualificados") or [],
        "reprovados": verify_payload.get("reprovados") or [],
        "qualificados_total": verify_payload.get("qualificados_total", 0),
        "reprovados_total": verify_payload.get("reprovados_total", 0),
        "brutos_encontrados": search_payload.get("brutos_encontrados", 0),
        "blacklist_removidos": search_payload.get("blacklist_removidos", 0),
        "novos_para_verificar": search_payload.get("novos_para_verificar", 0),
        # V58.33: queries_used e queries_metrics (pra saturação V2 do backend funcionar)
        "queries_used": [r.get("query", "") for r in (search_payload.get("queries") or []) if r.get("query")],
        "queries_metrics": {
            r.get("query", ""): {
                "novos": int(r.get("count_novos", 0) or 0),
                "repetidos": int(r.get("count_repetidos", 0) or 0),
                "brutos": int(r.get("count", 0) or 0),
                "variant": r.get("variant", ""),
                "is_403": bool(r.get("is_403", False)),
            }
            for r in (search_payload.get("queries") or []) if r.get("query")
        },
    }
    out = output_path or FINAL_RESULT_FILE
    safe_write_json(out, payload)
    safe_write_json(FINAL_RESULT_FILE, payload)
    safe_write_json(LAST_RESULT_FILE, payload)
    update_status(
        etapa="finalizado",
        stage="done",
        state="done",
        final_result_file=os.path.basename(out),
        brutos_encontrados=payload["brutos_encontrados"],
        blacklist_removidos=payload["blacklist_removidos"],
        novos_para_verificar=payload["novos_para_verificar"],
        verify_qualificados=payload["qualificados_total"],
        verify_reprovados=payload["reprovados_total"],
        preview_qualificados=short_preview(payload.get("qualificados") or [], 50),
        mensagem=f"FINAL | brutos={payload['brutos_encontrados']} | blacklist={payload['blacklist_removidos']} | novos={payload['novos_para_verificar']} | qualificados={payload['qualificados_total']}",
    )
    log(f"[DLP ENGINE V58.17] FINAL | brutos={payload['brutos_encontrados']} | blacklist={payload['blacklist_removidos']} | novos={payload['novos_para_verificar']} | qualificados={payload['qualificados_total']} | reprovados={payload['reprovados_total']} | arquivo={os.path.basename(out)}")
    # imprime JSON final numa linha para backend conseguir parsear se usar stdout
    print("THON_ENGINE_JSON_RESULT_START", flush=True)
    print(json.dumps(payload, ensure_ascii=False), flush=True)
    print("THON_ENGINE_JSON_RESULT_END", flush=True)
    return payload


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", default="search_verify")
    p.add_argument("--queries", "--query-limit", dest="queries", type=int, default=600)
    p.add_argument("--per-query", dest="per_query", type=int, default=50)
    p.add_argument("--verify", "--verify-limit", "--verify-max", dest="verify", type=int, default=0)
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--output", "--out", dest="output", default="")
    p.add_argument("--input", "--in", dest="input", default="")
    p.add_argument("--source", default="dlp")
    p.add_argument("--min-subs", dest="min_subs", type=int, default=10000)
    p.add_argument("--max-subs", dest="max_subs", type=int, default=200000)
    p.add_argument("--score-min", dest="score_min", type=int, default=50)
    args, unknown = p.parse_known_args()

    # aceita env vindo do backend antigo
    args.queries = int(os.environ.get("THON_DLP_QUERIES", args.queries))
    args.per_query = int(os.environ.get("THON_DLP_PER_QUERY", args.per_query))
    args.workers = int(os.environ.get("THON_DLP_WORKERS", args.workers))
    if not args.verify:
        args.verify = int(os.environ.get("THON_DLP_VERIFY", "0") or 0)

    reset_log()
    update_status(engine="v58.17", state="starting", mode=args.mode, mensagem="Engine V58.17 iniciando")
    log("="*78)
    log(f"THON DLP ENGINE EXTERNA v58.17 | mode={args.mode} | queries={args.queries} | per_query={args.per_query} | verify={args.verify or 'todos'} | workers={args.workers}")
    log(f"yt-dlp={os.popen(sys.executable + ' -m yt_dlp --version').read().strip()}")
    log("="*78)

    mode = (args.mode or "search_verify").lower().strip()
    out = args.output or None

    if mode in {"search", "busca"}:
        payload = run_search(args.queries, args.per_query, args.workers, output_path=out)
        safe_write_json(LAST_RESULT_FILE, payload)
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return

    if mode in {"verify", "verificar", "verification"}:
        inp = args.input or SEARCH_RESULT_FILE
        if not os.path.isabs(inp):
            inp = os.path.join(APP_DIR, inp)
        cands = load_candidates_from_file(inp)
        payload = run_verify(cands, args.verify, args.workers, args.min_subs, args.max_subs, args.score_min, output_path=out, source=args.source)
        safe_write_json(LAST_RESULT_FILE, payload)
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return

    # search_verify completo
    blacklist_ids = load_blacklist(APP_DIR)
    update_status(blacklist_total=len(blacklist_ids))

    # V58.33: carrega queries do input JSON (backend injeta até 420)
    injected_queries = None
    if args.input:
        try:
            inp_path = args.input if os.path.isabs(args.input) else os.path.join(APP_DIR, args.input)
            with open(inp_path, "r", encoding="utf-8") as f:
                inp_data = json.load(f)
            iq = inp_data.get("queries") or []
            if isinstance(iq, list) and iq:
                # pode ser lista de dict [{"query": "...", "nicho": "..."}] ou lista de strings
                injected_queries = []
                for q in iq:
                    if isinstance(q, dict):
                        qs = q.get("query", "")
                        if qs:
                            injected_queries.append(qs)
                    elif isinstance(q, str) and q.strip():
                        injected_queries.append(q.strip())
                log(f"[DLP ENGINE V58.33] {len(injected_queries)} queries injetadas pelo backend (input JSON)")
        except Exception as _e_inp:
            log(f"[DLP ENGINE V58.33] aviso lendo input: {_e_inp}")

    # V58.33: se tem queries injetadas, usa elas; senão usa args.queries (default 60)
    if injected_queries:
        # passamos a LISTA de queries; o run_search respeita o limite via query_limit
        search_payload = run_search(args.queries, args.per_query, args.workers, blacklist_ids=blacklist_ids, output_path=SEARCH_RESULT_FILE, queries=injected_queries)
        log(f"[DLP ENGINE V58.33] busca usou {len(injected_queries)} queries do backend (limite={args.queries})")
    else:
        search_payload = run_search(args.queries, args.per_query, args.workers, blacklist_ids=blacklist_ids, output_path=SEARCH_RESULT_FILE)
        log(f"[DLP ENGINE V58.33] busca usou DEFAULT_QUERIES (sem input do backend)")

    candidates = search_payload.get("candidatos_novos") or []
    verify_limit = args.verify or len(candidates)
    verify_payload = run_verify(candidates, verify_limit, args.workers, args.min_subs, args.max_subs, args.score_min, output_path=VERIFY_RESULT_FILE, source="dlp_search")
    merge_final(search_payload, verify_payload, output_path=out)

if __name__ == "__main__":
    main()
