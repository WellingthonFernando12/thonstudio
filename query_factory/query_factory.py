"""
TH Query Factory V2 — Rotação inteligente com saturação rápida
================================================================

Problemas da V1 corrigidos:
1. Queries gigantes e inúteis ("podcast estratégia de podcast financas br")
2. Sem controle de saturação (query rodava infinitas vezes mesmo falhando)
3. Ignorava config do frontend (usava todas as 100 opções)
4. Combinações absurdas (gameplay x corretor de imóveis)

Solução V2:
1. Queries curtas (máx 4 palavras) e focadas
2. Contador de falhas: 5 tentativas frustradas = pula pra próxima
3. Cooldown progressivo: 1ª falha 1h, 2ª 6h, 3ª 1d, 4ª 7d, 5ª 30d
4. Respeita config do frontend (nichos/perfis/regioes marcados)
5. Variação automática de sufixos (brasil, brasileiro, 2024, etc)
6. Score de produtividade: queries que trouxeram qualificados ganham prioridade
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
OPTIONS_FILE = BASE_DIR / "options.json"
CURSOR_FILE = BASE_DIR / "cursor.json"
SEEN_FILE = BASE_DIR / "seen.json"
QUEUE_FILE = BASE_DIR / "queue.json"
STATS_FILE = BASE_DIR / "stats.json"
PERF_FILE = BASE_DIR / "performance.json"  # novo: score por query

# ============================================================
# CONFIGURAÇÃO DE SATURAÇÃO (V2 — threshold por candidatos)
# ============================================================
# V58.30: se uma query trouxer <= THRESHOLD_CANDIDATOS novos, vai pro cooldown IMEDIATAMENTE
# (nao espera 5 falhas — isso tira leite de pedra)
THRESHOLD_CANDIDATOS = 5           # <=5 novos = saturada na hora
MAX_FALHAS_SEGUIDAS = 3            # apos 3 falhas com 0 novos, tambem satura (criterio duplo)
COOLDOWN_PROGRESSIVO = [3600, 21600, 86400, 604800, 2592000]  # 1h, 6h, 1d, 7d, 30d
TAXA_NOVOS_MINIMA = 0.10           # abaixo de 10% de novos = falha
TAXA_QUALIFICACAO_BOA = 0.05       # acima de 5% de qualificados = prioridade alta
MAX_PALAVRAS_QUERY = 5             # V58.31: 5 palavras (era 4) pra mais combinacoes
QUEUE_MIN_SIZE = 50                # quando fila cai abaixo disso, gera mais
QUEUE_GENERATE_BATCH = 500         # V58.31: gera 500 de cada vez (era 300)
SEEN_TTL_DIAS = 7                  # V58.31: queries vistas expiram em 7 dias (nao bloqueiam pra sempre)

# Sufixos brasileiros pra variação automática (V58.31: expandido pra mais variedade)
SUFIXOS_BR = [
    "", "brasil", "brasileiro", "brasileira", "português", "portugues", "pt-br", "ptbr",
    "2024", "2025", "2023", "melhor", "top", "canal", "youtube",
    "entrevista", "podcast", "completo", "ao vivo", "novo", "recente",
]
# Sufixos pra perfis profissionais
SUFIXOS_PERFIL = ["", "youtube", "canal", "podcast"]

DEFAULT_OPTIONS = {
    "objetivos": ["Cliente com dinheiro"],
    "nichos": ["Empreendedorismo", "Marketing digital", "Negócios", "Finanças"],
    "perfis": ["Empresário", "Consultor", "Podcaster", "Criador de conteúdo"],
    "formatos": ["Podcast", "Entrevista", "Talk show", "Bate-papo"],
    "regioes": ["Brasil"],
    "intencoes": ["case de sucesso", "como crescer", "como vender mais"],
    "blacklist": {"global": [], "b2b": [], "games": []},
}

DEFAULT_CURSOR = {
    "nivel": 1,
    "formato_i": 0,
    "perfil_i": 0,
    "nicho_i": 0,
    "regiao_i": 0,
    "intencao_i": 0,
    "sufixo_i": 0,
    "tentativas_nesta_combinacao": 0,  # V2: contador de falhas
    "total_geradas": 0,
    "total_entregues": 0,
}

DEFAULT_STATS = {
    "generated_batches": 0,
    "delivered_batches": 0,
    "last_generated_at": None,
    "last_delivered_at": None,
    "queries_saturo": 0,  # V2: quantas queries foram pro cooldown
}

DEFAULT_PERF = {
    "queries": {}  # {query_str: {falhas: N, ultimos_resultados: [bool], qualificados: N, cooldown_ate: timestamp}}
}


# ============================================================
# I/O helpers
# ============================================================
def _load(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if data is not None else default
    except Exception:
        pass
    return default.copy() if isinstance(default, dict) else default


def _save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _clean(value: Any) -> str:
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def _norm_key(value: Any) -> str:
    return _clean(value).lower()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [x.strip() for x in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        parts = [value]
    return [_clean(x) for x in parts if _clean(x)]


# ============================================================
# FILTRO DE OPÇÕES — respeita config do frontend (V2)
# ============================================================
# Mapeamento de alias do config do frontend -> chave em options.json
ALIASES = {
    "objetivos": ["objetivos", "objetivo", "goals"],
    "nichos": ["nichos", "nicho", "mercados", "mercado"],
    "perfis": ["perfis", "perfil", "personas", "persona", "profiles"],
    "formatos": ["formatos", "formato", "formatos_video", "huntType", "modo"],
    "regioes": ["regioes", "regiao", "região", "localizacoes", "localizacao", "localizações"],
}

# Palavras que invalidam uma combinação (V2: filtro anti-lixo)
BLACKLIST_COMBOS = {
    # games + profissão séria = lixo
    ("gameplay", "advogado"), ("gameplay", "médico"), ("gameplay", "contador"),
    ("gameplay", "corretor"), ("gameplay", "dentista"), ("gameplay", "psicólogo"),
    ("gameplay", "engenheiro"), ("gameplay", "arquiteto"), ("gameplay", "consultor"),
    ("gameplay", "mentor"), ("gameplay", "coach"), ("gameplay", "professor"),
    # react + nicho sério = lixo
    ("react", "advogado"), ("react", "médico"), ("react", "contador"),
    ("react", "corretor"), ("react", "dentista"), ("react", "psicólogo"),
    # vlog + B2B = lixo
    ("vlog", "advogado"), ("vlog", "contador"), ("vlog", "consultor"),
    # tutorial + podcast = redundante
    ("tutorial", "podcaster"), ("tutorial", "apresentador"),
}


def _pick_options(options: dict[str, Any], config: dict[str, Any] | None, key: str) -> list[str]:
    """Pega opções do config do frontend; se vazio, usa default de options.json."""
    config = config or {}
    selected: list[str] = []
    for alias in ALIASES.get(key, [key]):
        selected.extend(_as_list(config.get(alias)))

    # Mapeamento de formatos do frontend pra options.json
    if key == "formatos":
        mapped = []
        for item in selected:
            low = _norm_key(item)
            if low in {"longform", "long form"}:
                mapped.extend(["Podcast", "Entrevista", "Talk show", "Bate-papo"])
            elif low in {"shortform", "short form"}:
                mapped.extend(["Shorts", "Reels", "TikTok"])
            elif low in {"ambos", "full", "full content"}:
                mapped.extend(["Podcast", "Entrevista", "Talk show", "Bate-papo"])
            else:
                mapped.append(item)
        selected = mapped

    # V2: se config tem opções, usa SÓ elas. Se não, pega default.
    if selected:
        source = [_clean(x) for x in selected]
    else:
        source = [_clean(x) for x in options.get(key, [])][:10]  # limita a 10 pra não explodir

    seen = set()
    out = []
    for item in source:
        k = _norm_key(item)
        if item and k not in seen:
            seen.add(k)
            out.append(item)
    return out


def _combo_valido(formato: str, perfil: str, nicho: str) -> bool:
    """V2: valida se a combinação faz sentido (não é lixo)."""
    f = _norm_key(formato)
    p = _norm_key(perfil)
    n = _norm_key(nicho)
    # bloqueia combos conhecidos como lixo
    if (f, p) in BLACKLIST_COMBOS:
        return False
    if (f, n) in BLACKLIST_COMBOS:
        return False
    # gameplay/react só faz sentido com nicho games/esports
    if f in {"gameplay", "react"} and not any(g in n for g in ["game", "esport", "twitch", "stream"]):
        return False
    return True


# ============================================================
# GERAÇÃO DE QUERIES — V2 com sufixos e validação
# ============================================================
def _combo_fast(cursor: dict[str, int], pools: dict[str, list[str]]) -> tuple[str, str, dict[str, Any]]:
    formatos = pools["formatos"]
    perfis = pools["perfis"]
    nichos = pools["nichos"]
    regioes = pools["regioes"]
    intencoes = pools["intencoes"]

    nivel = int(cursor.get("nivel") or 1)
    formato = formatos[int(cursor.get("formato_i") or 0) % max(1, len(formatos))]
    perfil = perfis[int(cursor.get("perfil_i") or 0) % max(1, len(perfis))]
    nicho = nichos[int(cursor.get("nicho_i") or 0) % max(1, len(nichos))]
    regiao = regioes[int(cursor.get("regiao_i") or 0) % max(1, len(regioes))]
    intencao = intencoes[int(cursor.get("intencao_i") or 0) % max(1, len(intencoes))]
    sufixo_idx = int(cursor.get("sufixo_i") or 0) % len(SUFIXOS_BR)
    sufixo = SUFIXOS_BR[sufixo_idx]

    # V2: queries mais curtas e focadas por nível
    # V58.31: níveis 6-8 adicionados pra MUITO mais variedade
    if nivel == 1:
        # Nível 1: formato + nicho + sufixo (mais simples, mais resultados)
        parts = [formato, nicho]
        if sufixo:
            parts.append(sufixo)
    elif nivel == 2:
        # Nível 2: formato + perfil (ex: "podcast empreendedor")
        parts = [formato, perfil]
        if sufixo and sufixo not in ("", "brasil", "brasileiro"):
            parts.append(sufixo)
    elif nivel == 3:
        # Nível 3: formato + perfil + nicho (ex: "podcast advogado juridico")
        parts = [formato, perfil, nicho]
    elif nivel == 4:
        # Nível 4: formato + intencao + nicho (ex: "podcast case de sucesso empreendedorismo")
        parts = [formato, intencao, nicho]
    elif nivel == 5:
        # Nível 5: perfil + nicho + regiao (ex: "podcaster financas sao paulo")
        parts = [perfil, nicho, regiao]
    elif nivel == 6:
        # V58.31 Nível 6: nicho + intencao + sufixo (ex: "empreendedorismo case de sucesso 2024")
        parts = [nicho, intencao]
        if sufixo:
            parts.append(sufixo)
    elif nivel == 7:
        # V58.31 Nível 7: perfil + intencao + nicho (ex: "podcaster dicas de empreendedorismo")
        parts = [perfil, intencao, nicho]
    else:
        # V58.31 Nível 8: formato + nicho + regiao + sufixo (ex: "podcast empreendedorismo sao paulo 2024")
        parts = [formato, nicho, regiao]
        if sufixo:
            parts.append(sufixo)

    # Limpa e junta
    query = _clean(" ".join(parts)).lower()

    # V2: valida se a query não é lixo
    if not _combo_valido(formato, perfil, nicho):
        query = ""  # será filtrada depois

    # V58.31: limita a 5 palavras (era 4)
    palavras = query.split()
    if len(palavras) > MAX_PALAVRAS_QUERY:
        query = " ".join(palavras[:MAX_PALAVRAS_QUERY])

    meta = {
        "nivel": nivel,
        "formato": formato,
        "perfil": perfil,
        "nicho": nicho,
        "regiao": regiao,
        "intencao": intencao,
        "sufixo": sufixo,
    }
    return query, nicho, meta


def _advance_fast(cursor: dict[str, int], pools: dict[str, list[str]]) -> dict[str, int]:
    """V2: avança cursor priorizando variação de sufixo (mais barato) antes de trocar combinação."""
    # Primeiro rotaciona sufixo (mesma combinação, mas variação)
    cursor["sufixo_i"] = int(cursor.get("sufixo_i", 0)) + 1
    if cursor["sufixo_i"] < len(SUFIXOS_BR):
        return cursor
    # Esgotou sufixos, volta e avança nicho
    cursor["sufixo_i"] = 0

    cursor["nicho_i"] = int(cursor.get("nicho_i", 0)) + 1
    if cursor["nicho_i"] < max(1, len(pools["nichos"])):
        return cursor
    cursor["nicho_i"] = 0

    cursor["perfil_i"] = int(cursor.get("perfil_i", 0)) + 1
    if cursor["perfil_i"] < max(1, len(pools["perfis"])):
        return cursor
    cursor["perfil_i"] = 0

    cursor["regiao_i"] = int(cursor.get("regiao_i", 0)) + 1
    if cursor["regiao_i"] < max(1, len(pools["regioes"])):
        return cursor
    cursor["regiao_i"] = 0

    cursor["formato_i"] = int(cursor.get("formato_i", 0)) + 1
    if cursor["formato_i"] < max(1, len(pools["formatos"])):
        return cursor
    cursor["formato_i"] = 0

    cursor["intencao_i"] = int(cursor.get("intencao_i", 0)) + 1
    if cursor["intencao_i"] < max(1, len(pools["intencoes"])):
        return cursor
    cursor["intencao_i"] = 0

    # Esgotou tudo neste nível, sobe o nível
    cursor["nivel"] = int(cursor.get("nivel", 1)) + 1
    if int(cursor.get("nivel", 1)) > 8:  # V58.31: 8 níveis (era 5)
        cursor["nivel"] = 1

    cursor["total_geradas"] = int(cursor.get("total_geradas", 0)) + 1
    return cursor


def _prepare_pools(options: dict[str, Any], config: dict[str, Any] | None) -> dict[str, list[str]]:
    return {
        "formatos": _pick_options(options, config, "formatos"),
        "perfis": _pick_options(options, config, "perfis"),
        "nichos": _pick_options(options, config, "nichos"),
        "regioes": _pick_options(options, config, "regioes"),
        "intencoes": [_clean(x) for x in options.get("intencoes", []) if _clean(x)][:10] or DEFAULT_OPTIONS["intencoes"],
    }


# ============================================================
# PERFORMANCE / SATURAÇÃO (V2 — sistema novo)
# ============================================================
def load_performance() -> dict[str, Any]:
    data = _load(PERF_FILE, DEFAULT_PERF)
    if not isinstance(data, dict):
        return DEFAULT_PERF.copy()
    return data


def save_performance(perf: dict[str, Any]) -> None:
    _save(PERF_FILE, perf if isinstance(perf, dict) else DEFAULT_PERF)


def registrar_resultado_query(query: str, novos: int, repetidos: int, qualificados: int) -> dict | None:
    """V58.30: registra resultado e SATURA IMEDIATAMENTE se <= THRESHOLD_CANDIDATOS novos.

    Regra nova (mais agressiva, pra nao tirar leite de pedra):
    - Se trouxer <= 5 candidatos novos → COOLDOWN IMEDIATO de 1h (nao espera falhas)
    - Se cooldown ja existia, escala: 1h → 6h → 1d → 7d → 30d
    - Se trouxer > 5 novos → reset falhas, considera sucesso

    Returns: dict com info de saturação se query foi pro cooldown, None caso contrário.
    """
    if not query:
        return None
    perf = load_performance()
    queries_perf = perf.setdefault("queries", {})
    q = queries_perf.setdefault(_norm_key(query), {
        "falhas": 0,
        "sucessos": 0,
        "qualificados_total": 0,
        "ultimos_resultados": [],
        "cooldown_ate": None,
        "cooldown_nivel": 0,  # V58.30: nivel do cooldown progressivo (0=nenhum, 1=1h, 2=6h, ...)
        "ultima_rodada": None,
        "novos_ultima_rodada": 0,
    })

    # Se tá em cooldown, ignora (nao devia ter rodado)
    cd = q.get("cooldown_ate")
    if cd and cd > time.time():
        return None

    novos_int = int(novos or 0)
    repetidos_int = int(repetidos or 0)
    quals_int = int(qualificados or 0)

    # Atualiza históricos
    q["ultimos_resultados"] = (q.get("ultimos_resultados") or [])[-4:] + [novos_int > 0]
    q["qualificados_total"] = int(q.get("qualificados_total", 0)) + quals_int
    q["ultima_rodada"] = int(time.time())
    q["novos_ultima_rodada"] = novos_int

    # V58.30: THRESHOLD IMEDIATO — se trouxe <=5 novos, satura na hora
    saturada_threshold = novos_int <= THRESHOLD_CANDIDATOS

    if not saturada_threshold and novos_int > 0:
        # Teve mais de 5 novos = sucesso, reseta falhas e nivel de cooldown
        q["falhas"] = 0
        q["sucessos"] = int(q.get("sucessos", 0)) + 1
        q["cooldown_nivel"] = 0
        save_performance(perf)
        return None

    # SATURADA — aplica cooldown progressivo
    falhas = int(q.get("falhas", 0)) + 1
    q["falhas"] = falhas

    # Nivel do cooldown: escala conforme quantas vezes saturou
    nivel_atual = int(q.get("cooldown_nivel", 0))
    novo_nivel = min(nivel_atual + 1, len(COOLDOWN_PROGRESSIVO))
    q["cooldown_nivel"] = novo_nivel
    cooldown_seg = COOLDOWN_PROGRESSIVO[novo_nivel - 1]
    q["cooldown_ate"] = int(time.time()) + cooldown_seg

    # Motivo amigavel
    if saturada_threshold and novos_int == 0:
        motivo = f"0 candidatos (saturada nivel {novo_nivel})"
    elif saturada_threshold:
        motivo = f"{novos_int} candidatos (<= {THRESHOLD_CANDIDATOS}, saturada nivel {novo_nivel})"
    else:
        motivo = f"{falhas} falhas seguidas (saturada nivel {novo_nivel})"

    save_performance(perf)
    return {
        "query": query,
        "falhas": falhas,
        "novos": novos_int,
        "cooldown_seg": cooldown_seg,
        "cooldown_nivel": novo_nivel,
        "motivo": motivo,
    }


def query_em_cooldown(query: str) -> bool:
    """V2: verifica se query tá em cooldown."""
    if not query:
        return False
    perf = load_performance()
    q = (perf.get("queries") or {}).get(_norm_key(query))
    if not q:
        return False
    cd = q.get("cooldown_ate")
    return bool(cd and cd > time.time())


def query_prioridade(query: str) -> float:
    """V2: score de prioridade da query (0-1). Mais qualificados = mais prioridade."""
    if not query:
        return 0
    perf = load_performance()
    q = (perf.get("queries") or {}).get(_norm_key(query))
    if not q:
        return 0.5  # nova query = prioridade média
    if q.get("cooldown_ate") and q["cooldown_ate"] > time.time():
        return 0  # em cooldown
    qual = int(q.get("qualificados_total", 0))
    succ = int(q.get("sucessos", 0))
    fail = int(q.get("falhas", 0))
    total = succ + fail
    if total == 0:
        return 0.5
    return min(1.0, (succ / total) * 0.6 + min(qual * 0.1, 0.4))


# ============================================================
# GERAÇÃO DE BATCH
# ============================================================
def _seen_purge_old(seen_data: dict) -> tuple[set, int]:
    """V58.31: remove queries vistas com mais de SEEN_TTL_DIAS dias.

    Suporta 2 formatos:
    - Novo: {"queries": {"query_str": timestamp, ...}}
    - Antigo: {"queries": ["query1", "query2", ...]}

    Returns: (set de queries ainda válidas, quantas foram removidas)
    """
    if not isinstance(seen_data, dict):
        return set(), 0
    raw = seen_data.get("queries")
    now = int(time.time())
    ttl_seg = SEEN_TTL_DIAS * 86400

    # Formato novo: dict com timestamps
    if isinstance(raw, dict):
        validas = set()
        removidas = 0
        for q, ts in raw.items():
            try:
                ts_int = int(ts or 0)
                if ts_int > 0 and (now - ts_int) < ttl_seg:
                    validas.add(q)
                else:
                    removidas += 1
            except (TypeError, ValueError):
                # timestamp invalido, mantem (conservador)
                validas.add(q)
        return validas, removidas

    # Formato antigo: lista simples — converte pra dict com timestamp = agora
    if isinstance(raw, list):
        # Todas sao consideradas "vistas agora" (nao temos timestamp)
        # Vai ser migrado pra novo formato no save
        return set(raw), 0

    return set(), 0


def _seen_save(seen_data: dict, validas: set) -> None:
    """V58.31: salva seen.json no novo formato (dict com timestamps)."""
    now = int(time.time())
    novo_formato = {}
    # Preserva timestamps existentes
    raw = seen_data.get("queries") if isinstance(seen_data, dict) else None
    if isinstance(raw, dict):
        for q in validas:
            if q in raw:
                novo_formato[q] = raw[q]
            else:
                novo_formato[q] = now
    else:
        # Migração de lista -> dict
        for q in validas:
            novo_formato[q] = now
    seen_data["queries"] = novo_formato


def generate_more(config: dict[str, Any] | None = None, amount: int = QUEUE_GENERATE_BATCH) -> int:
    ensure_files()
    options = load_options()
    cursor = _load(CURSOR_FILE, DEFAULT_CURSOR)
    queue = _load(QUEUE_FILE, {"queries": []})
    seen_data = _load(SEEN_FILE, {"queries": []})
    stats = _load(STATS_FILE, DEFAULT_STATS)
    pools = _prepare_pools(options, config)
    queued = queue.setdefault("queries", [])
    # V58.31: seen com TTL (queries com mais de 7 dias expiram)
    seen, seen_removidas_ttl = _seen_purge_old(seen_data)
    if seen_removidas_ttl > 0:
        print(f"[QUERY FACTORY V2] TTL: removidas {seen_removidas_ttl} queries vistas com mais de {SEEN_TTL_DIAS} dias")
    perf = load_performance()

    generated = 0
    attempts = 0
    max_attempts = max(amount * 50, 5000)
    puladas_cooldown = 0
    puladas_lixo = 0
    puladas_seen = 0

    while generated < amount and attempts < max_attempts:
        attempts += 1
        query, nicho, meta = _combo_fast(cursor, pools)
        cursor = _advance_fast(cursor, pools)

        key = _norm_key(query)
        if not key:
            puladas_lixo += 1
            continue
        if key in seen:
            puladas_seen += 1
            continue
        # V2: pula queries em cooldown
        if query_em_cooldown(query):
            puladas_cooldown += 1
            seen.add(key)  # marca como vista pra não checar de novo
            continue

        seen.add(key)
        queued.append({
            "query": query,
            "nicho": _clean(nicho).lower(),
            "meta": meta,
            "prioridade": query_prioridade(query),
            "created_at": int(time.time()),
        })
        generated += 1

    # V58.31: se gerou muito pouco mesmo com muitas tentativas, força reset parcial do seen
    # Mantem só as queries vistas nas ultimas 24h, apaga as mais antigas
    if generated < amount * 0.1 and attempts >= max_attempts * 0.5:
        print(f"[QUERY FACTORY V2] RÉDIA: generated={generated}/{amount} | tentativas={attempts} | Forçando reset parcial do seen...")
        now = int(time.time())
        seen_recente = set()
        raw = seen_data.get("queries") if isinstance(seen_data, dict) else {}
        if isinstance(raw, dict):
            for q, ts in raw.items():
                try:
                    if (now - int(ts or 0)) < 86400:  # mantem só ultimas 24h
                        seen_recente.add(q)
                except (TypeError, ValueError):
                    pass
        seen = seen_recente
        seen_data["queries"] = {q: now for q in seen_recente}  # migra pra dict
        # Tenta de novo com seen reduzido
        attempts2 = 0
        max_attempts2 = max(amount * 50, 5000)
        while generated < amount and attempts2 < max_attempts2:
            attempts2 += 1
            query, nicho, meta = _combo_fast(cursor, pools)
            cursor = _advance_fast(cursor, pools)
            key = _norm_key(query)
            if not key:
                continue
            if key in seen:
                continue
            if query_em_cooldown(query):
                continue
            seen.add(key)
            queued.append({
                "query": query,
                "nicho": _clean(nicho).lower(),
                "meta": meta,
                "prioridade": query_prioridade(query),
                "created_at": int(time.time()),
            })
            generated += 1
        print(f"[QUERY FACTORY V2] Após reset parcial: generated={generated}/{amount}")

    # V2: ordena fila por prioridade (maior primeiro)
    queued.sort(key=lambda x: x.get("prioridade", 0.5), reverse=True)

    # V58.31: salva seen no novo formato (com timestamps)
    _seen_save(seen_data, seen)
    stats["generated_batches"] = int(stats.get("generated_batches", 0) or 0) + 1
    stats["last_generated_at"] = int(time.time())
    _save(CURSOR_FILE, cursor)
    _save(QUEUE_FILE, queue)
    _save(SEEN_FILE, seen_data)
    _save(STATS_FILE, stats)
    print(f"[QUERY FACTORY V2] geradas={generated} | puladas_cooldown={puladas_cooldown} | puladas_lixo={puladas_lixo} | puladas_seen={puladas_seen} | tentativas={attempts}")
    return generated


def get_next_queries(config: dict[str, Any] | None = None, limit: int = 100, as_tuples: bool = False) -> list[Any]:
    """V2: pega próximas queries da fila, ordenadas por prioridade."""
    ensure_files()
    limit = max(1, int(limit or 100))
    queue = _load(QUEUE_FILE, {"queries": []})
    queue_queries = queue.get("queries") or []

    # V2: se fila pequena, gera mais
    if len(queue_queries) < QUEUE_MIN_SIZE:
        generate_more(config=config, amount=QUEUE_GENERATE_BATCH)
        queue = _load(QUEUE_FILE, {"queries": []})
        queue_queries = queue.get("queries") or []

    # V2: filtra queries em cooldown (caso tenham saturado após serem enfileiradas)
    filtradas = []
    for item in queue_queries:
        q = item.get("query", "")
        if not query_em_cooldown(q):
            filtradas.append(item)
    # Se filtrou muita coisa, reordena
    if len(filtradas) < len(queue_queries):
        print(f"[QUERY FACTORY V2] filtrou {len(queue_queries) - len(filtradas)} queries em cooldown")

    selected = filtradas[:limit]
    queue["queries"] = filtradas[limit:]

    stats = _load(STATS_FILE, DEFAULT_STATS)
    cursor = _load(CURSOR_FILE, DEFAULT_CURSOR)
    cursor["total_entregues"] = int(cursor.get("total_entregues", 0) or 0) + len(selected)
    stats["delivered_batches"] = int(stats.get("delivered_batches", 0) or 0) + 1
    stats["last_delivered_at"] = int(time.time())
    _save(QUEUE_FILE, queue)
    _save(CURSOR_FILE, cursor)
    _save(STATS_FILE, stats)

    if as_tuples:
        return [(x.get("query", ""), x.get("nicho") or (x.get("meta") or {}).get("nicho") or "factory") for x in selected]
    return [x.get("query", "") for x in selected]


# ============================================================
# INIT
# ============================================================
def ensure_files() -> None:
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    if not OPTIONS_FILE.exists():
        _save(OPTIONS_FILE, DEFAULT_OPTIONS)
    if not CURSOR_FILE.exists():
        _save(CURSOR_FILE, DEFAULT_CURSOR)
    if not SEEN_FILE.exists():
        _save(SEEN_FILE, {"queries": []})
    if not QUEUE_FILE.exists():
        _save(QUEUE_FILE, {"queries": []})
    if not STATS_FILE.exists():
        _save(STATS_FILE, DEFAULT_STATS)
    if not PERF_FILE.exists():
        _save(PERF_FILE, DEFAULT_PERF)


def load_options() -> dict[str, Any]:
    ensure_files()
    data = _load(OPTIONS_FILE, DEFAULT_OPTIONS)
    if not isinstance(data, dict):
        return DEFAULT_OPTIONS.copy()
    merged = DEFAULT_OPTIONS.copy()
    merged.update(data)
    return merged


# ============================================================
# STATS / DEBUG
# ============================================================
def get_status() -> dict[str, Any]:
    """Retorna status do query factory pra debug."""
    perf = load_performance()
    queries_perf = perf.get("queries") or {}
    em_cooldown = sum(1 for q in queries_perf.values() if q.get("cooldown_ate") and q["cooldown_ate"] > time.time())
    saturadas_total = sum(1 for q in queries_perf.values() if q.get("cooldown_ate"))
    return {
        "cursor": _load(CURSOR_FILE, DEFAULT_CURSOR),
        "stats": _load(STATS_FILE, DEFAULT_STATS),
        "queue_size": len((_load(QUEUE_FILE, {"queries": []})).get("queries", [])),
        "seen_size": len((_load(SEEN_FILE, {"queries": []})).get("queries", [])),
        "perf_queries_total": len(queries_perf),
        "perf_em_cooldown": em_cooldown,
        "perf_saturadas_total": saturadas_total,
    }


def reset_saturacao():
    """V2: limpa cooldown de todas as queries (força retry)."""
    perf = load_performance()
    for q in (perf.get("queries") or {}).values():
        q["cooldown_ate"] = None
        q["falhas"] = 0
    save_performance(perf)
    print(f"[QUERY FACTORY V2] saturação resetada para {len(perf.get('queries', {}))} queries")


if __name__ == "__main__":
    ensure_files()
    print("=== STATUS ===")
    print(json.dumps(get_status(), indent=2, ensure_ascii=False))
    print("\n=== PRÓXIMAS 10 QUERIES ===")
    for q in get_next_queries(limit=10, as_tuples=True):
        print(f"  {q}")
