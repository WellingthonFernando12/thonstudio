"""TH Query Factory V2 — rotação inteligente de queries com saturação rápida."""
from .query_factory import (
    get_next_queries,
    generate_more,
    registrar_resultado_query,
    query_em_cooldown,
    query_prioridade,
    get_status,
    reset_saturacao,
    ensure_files,
    load_options,
    MAX_FALHAS_SEGUIDAS,
    COOLDOWN_PROGRESSIVO,
)
