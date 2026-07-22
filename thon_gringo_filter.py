#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TH Gringo Filter V58.36 — Filtro RIGOROSO por perfil + anti-gringo
====================================================================
2 funcoes principais:

1. filtrar_por_perfil(nome, descricao, perfis_selecionados)
   - Se selecionou "podcast" → SO passa se canal tem sinais de podcast
   - Se selecionou "medico" → SO passa se canal tem sinais de medico
   - Se selecionou "advogado" → SO passa se canal tem sinais de advogado
   - Cada perfil tem lista de sinais especificos
   - Canal precisa ter pelo menos 1 sinal do perfil selecionado

2. filtrar_gringo(nome, descricao, country, territorios)
   - Filtro anti-gringo (pais + nome + descricao)
   - Score baseado em termos EN vs PT
"""
from __future__ import annotations
import re
from typing import Tuple, List

# ============================================================
# SINAIS POR PERFIL (rigoroso)
# ============================================================
PERFIL_SINAIS = {
    "podcast": [
        "podcast", "pod cast", "cast", "entrevista", "bate papo", "bate-papo",
        "conversa", "talk show", "talks", "episodio", "episódio", "convidado",
        "convidada", "papo", "programa", "bate", "prosa", "mesa redonda",
        "pauta", "debate", "discussao", "discussão",
    ],
    "medico": [
        "medico", "médico", "medica", "médica", "medicina", "doctor", "dra",
        "dr ", "clínica", "clinica", "saúde", "saude", "paciente", "consultório",
        "consultorio", "hospital", "cardiologista", "psiquiatra", "neurologista",
        "ortopedista", "pediatra", "ginecologista", "dermatologista", "cirurgiao",
        "cirurgião", "oftalmologista", "endocrinologista", "geriatra", "urologista",
    ],
    "advogado": [
        "advogado", "advogada", "advocacia", "direito", "jurídico", "juridico",
        "jurista", "tribunal", "processo", "constituição", "constituicao",
        "penal", "trabalhista", "tributário", "tributario", "contrato",
        "oab", "magistrado", "juiz", "desembargador", "ação", "acao judicial",
    ],
    "engenheiro": [
        "engenheiro", "engenheira", "engenharia", "elétrica", "eletrica",
        "mecânica", "mecanica", "software", "produção", "producao", "projeto",
        "obra", "construção", "construcao", "civil", "estrutura", "calculista",
        "crea", "arquitetura", "arquiteto", "arquiteta",
    ],
    "corretor": [
        "corretor", "corretora", "imóveis", "imoveis", "imobiliário",
        "imobiliario", "imobiliária", "imobiliaria", "apartamento", "casa",
        "venda", "aluguel", "locação", "locacao", "financiamento", "creci",
        "obra", "lançamento", "investimento imobiliário",
    ],
    "personal": [
        "personal", "trainer", "fitness", "treino", "treinamento", "musculação",
        "musculacao", "academia", "exercício", "exercicio", "físico", "fisico",
        "corpo", "saúde", "saude", "dieta", "emagrecimento", "hipertrofia",
    ],
    "consultor": [
        "consultor", "consultora", "consultoria", "consultores", "mentor",
        "mentoria", "mentorar", "advisor", "estratégia", "estrategia",
        "negócios", "negocios", "gestão", "gestao", "empresa", "growth",
    ],
    "psicologo": [
        "psicólogo", "psicologo", "psicóloga", "psicologa", "psicologia",
        "terapia", "terapeuta", "psicanalista", "analista", "comportamento",
        "mental", "ansiedade", "depressão", "depressao", "emocional", "crp",
    ],
    "nutricionista": [
        "nutricionista", "nutrição", "nutricao", "dieta", "alimentação",
        "alimentacao", "nutri", "nutricional", "calorias", "emagrecimento",
        "reeducação", "reeducacao", "crn", "macro", "micro",
    ],
    "dentista": [
        "dentista", "odontologia", "odontológico", "odontologico", "dente",
        "dental", "sorriso", "implante", "ortodontia", "cro", "clínica odontológica",
        "endodontia", "periodontia",
    ],
    "arquiteto": [
        "arquiteto", "arquiteta", "arquitetura", "projeto", "design",
        "interiores", "decoração", "decoracao", "urbanismo", "cau", "obra",
        "construção", "construcao", "planta", "maquete",
    ],
    "contador": [
        "contador", "contadora", "contabilidade", "contábil", "contabil",
        "tributário", "tributario", "imposto", "fiscal", "irpf", "irpj",
        "declaração", "declaracao", "crc", "lucro", "faturamento",
    ],
    "professor": [
        "professor", "professora", "prof ", "aula", "curso", "ensino",
        "didática", "didatica", "pedagogia", "educador", "educadora",
        "aprendizado", "ensinar", "escola", "faculdade", "universidade",
    ],
    "agencia": [
        "agência", "agencia", "agency", "marketing", "publicidade", "propaganda",
        "criação", "criacao", "design", "branding", "comunicação", "comunicacao",
        "digital", "social media", "trafego", "tráfego", "funil",
    ],
    "gamer": [
        "gamer", "games", "gameplay", "jogos", "let's play", "lets play",
        "stream", "streamer", "twitch", "xbox", "playstation", "nintendo",
        "pc gamer", "free fire", "minecraft", "fortnite", "lol", "valorant",
        "csgo", "dota", "speedrun", "walkthrough",
    ],
    "mentor": [
        "mentor", "mentora", "mentoria", "mentorar", "coach", "coaching",
        "liderança", "lideranca", "desenvolvimento", "pessoal", "high ticket",
        "escala", "crescimento", "transformação", "transformacao",
    ],
}

# ============================================================
# PAISES ACEITOS POR TERRITORIO
# ============================================================
PAISES_POR_TERRITORIO = {
    "BR":     {"BR"},
    "PT":     {"PT", "BR"},
    "US":     {"US", None, ""},
    "MX":     {"MX"},
    "AR":     {"AR"},
    "ES":     {"ES"},
    "CO":     {"CO"},
    "CL":     {"CL"},
    "LATAM":  {"MX", "AR", "CO", "CL", "ES", "BR"},
    "GLOBAL": None,
}

# ============================================================
# TERMOS GRINGOS
# ============================================================
GRINGO_NOMES_BLOQUEIO_DIRETO = [
    "bloomberg", "euronews", "drumeo", "brad lea", "pat flynn", "dhar mann",
    "young and profiting", "ben amos", "engage video", "logan derosa",
    "she md", "bmv global", "brava film", "jogadim", "huberman", "joe rogan",
    "tim ferriss", "garyvee", "lewis howes", "marie forleo", "rachel hollis",
    "tony robbins", "dean graziosi", "russell brunson", "grant cardone", "cardone",
]

GRINGO_TERMOS_NOME = [
    "the ", "podcast", "show", "channel", "official", "world", "news",
    "daily", "weekly", "live", "talks", "academy", "school", "media",
    "production", "studios", "films", "entertainment", "network", "hub",
    "central", "zone", "tv", "radio", "business", "money", "wealth",
    "success", "mindset", "growth", "marketing tips", "marketing school",
    "podcast en", "en español", "subscribe",
]

GRINGO_TERMOS_DESC = [
    "subscribe", "subscribers", "like and subscribe", "hit the bell",
    "comment down below", "in this video", "today we", "today i",
    "hey guys", "what's up", "whats up", "welcome back",
    "welcome to my channel", "lets talk", "let's talk", "let's dive",
    "join me", "follow me", "watch now", "check out", "amazing",
    "awesome", "incredible", "fantastic", "the best", "in the world",
]

PT_TERMOS = [
    "brasil", "brasileiro", "brasileira", "português", "portugues",
    "são paulo", "rio de janeiro", "minas gerais", "bahia", "curitiba",
    "empreendedorismo", "negócios", "negocios", "finanças", "financas",
    "marketing digital", "tráfego", "trafego", "vendas", "vender",
    "cliente", "sucesso", "dicas", "canal", "conteúdo", "conteudo",
    "inscreva", "vídeo", "video", "episódio", "episodio", "entrevista",
    "convidado", "papo", "conversa", "bate papo", "bate-papo",
]

PT_ACENTOS = "áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ"

NEGATIVOS_FORTES = [
    "cortes", "corte ", "clips", "clip ", "melhores momentos", "highlights",
    "resumo", "vlog", "rotina", "dia a dia", "mukbang", "estilo de vida",
    "lifestyle", "minha rotina", "rotina matinal", "react", "reaction",
    "reagindo", "reacao", "free fire gameplay", "minecraft gameplay",
    "fortnite gameplay", "gta gameplay", "lets play", "let's play",
    "jogando", "gameplay", "clip oficial", "clipe oficial", "videoclipe",
    "music video", "tutorial maquiagem", "diy", "como fazer ",
    "passo a passo maquiagem", "curso gratuito", "aula gratuita",
    "mentor gratuito", "mentoria gratuita", "notícias", "noticias",
    "news", "rádio", "radio", "ao vivo", "live",
]

GRINGO_THRESHOLD = 3


# ============================================================
# FILTRO POR PERFIL (rigoroso)
# ============================================================
def filtrar_por_perfil(nome: str = "", descricao: str = "", perfis_selecionados: List[str] = None) -> Tuple[bool, str]:
    """Filtra canal baseado nos perfis selecionados.

    Se selecionou "podcast" → SO passa se canal tem sinais de podcast.
    Se selecionou "medico" → SO passa se canal tem sinais de medico.
    Se nenhum perfil selecionado → passa (nao filtra).

    Returns: (reprovado: bool, motivo: str)
    """
    if not perfis_selecionados:
        return False, ""

    # Normaliza perfis
    perfis_norm = [p.strip().lower() for p in perfis_selecionados if p and p.strip()]
    if not perfis_norm:
        return False, ""

    nome_l = str(nome or "").lower()
    desc_l = str(descricao or "").lower()
    texto = nome_l + " " + desc_l

    # Canal precisa ter pelo menos 1 sinal de ALGUM perfil selecionado
    # Se selecionou "podcast" e "medico", canal pode ser podcast OU medico
    for perfil in perfis_norm:
        sinais = PERFIL_SINAIS.get(perfil, [])
        for sinal in sinais:
            if sinal in texto:
                return False, ""  # achou sinal do perfil → passa

    # Nao achou nenhum sinal dos perfis selecionados → reprova
    return True, f"perfil_incompativel (selecionou: {', '.join(perfis_norm)})"


# ============================================================
# FILTRO ANTI-GRINGO
# ============================================================
def filtrar_gringo(nome: str = "", descricao: str = "", country: str = "", territorios: List[str] = None) -> Tuple[bool, str]:
    """Filtra canal gringo com base em nome, descricao e pais."""
    if not territorios:
        territorios = ["BR"]

    if "GLOBAL" in territorios:
        return False, ""

    # 1. FILTRO DE PAIS
    if country:
        country_up = str(country).upper().strip()
        paises_aceitos = set()
        for terr in territorios:
            aceitos = PAISES_POR_TERRITORIO.get(terr)
            if aceitos is None:
                return False, ""
            paises_aceitos |= aceitos
        if country_up not in paises_aceitos:
            return True, f"pais_incompativel_{country_up}"

    nome_l = str(nome or "").lower()
    desc_l = str(descricao or "").lower()

    # 2. NEGATIVOS FORTES no NOME
    for neg in NEGATIVOS_FORTES:
        if neg in nome_l:
            return True, f"negativo_no_nome: {neg}"

    # 3. BLOQUEIO DIRETO POR NOME CONHECIDO
    for g in GRINGO_NOMES_BLOQUEIO_DIRETO:
        if g in nome_l:
            return True, f"gringo_conhecido: {g}"

    # 4. SCORE GRINGO vs PT
    score_gringo = 0
    score_pt = 0
    motivos = []

    for termo in GRINGO_TERMOS_NOME:
        if termo in nome_l:
            score_gringo += 1
            motivos.append(f"nome:{termo}")

    for termo in GRINGO_TERMOS_DESC:
        if termo in desc_l:
            score_gringo += 1
            motivos.append(f"desc:{termo}")

    for termo in PT_TERMOS:
        if termo in (nome_l + " " + desc_l):
            score_pt += 1

    acentos = sum(1 for c in (nome_l + desc_l) if c in PT_ACENTOS)
    if acentos >= 3:
        score_pt += 2

    score_final = score_gringo - (score_pt * 2)

    if score_final >= GRINGO_THRESHOLD:
        return True, f"gringo_score:{score_final} ({', '.join(motivos[:3])})"

    return False, ""


# ============================================================
# FILTRO COMPLETO (perfil + gringo)
# ============================================================
def filtrar_canal(nome: str = "", descricao: str = "", country: str = "",
                  territorios: List[str] = None, perfis: List[str] = None) -> Tuple[bool, str]:
    """Filtra canal por perfil E gringo. Retorna (reprovado, motivo)."""
    # Primeiro filtra por perfil (mais especifico)
    if perfis:
        rep, motivo = filtrar_por_perfil(nome, descricao, perfis)
        if rep:
            return True, motivo
    # Depois filtra gringo
    rep, motivo = filtrar_gringo(nome, descricao, country, territorios)
    return rep, motivo


def filtrar_lista_canais(canais: list, territorios: list = None, perfis: list = None) -> Tuple[list, list]:
    """Filtra lista de canais por perfil + gringo. Returns (aceitos, reprovados)."""
    aceitos = []
    reprovados = []
    for c in canais:
        if not isinstance(c, dict):
            continue
        nome = c.get("nome") or c.get("title") or ""
        desc = c.get("description") or c.get("descricao") or ""
        country = c.get("country") or ""
        rep, motivo = filtrar_canal(nome, desc, country, territorios, perfis)
        if rep:
            c["motivo"] = motivo
            c["score"] = 0
            reprovados.append(c)
        else:
            aceitos.append(c)
    return aceitos, reprovados


# ============================================================
# TESTE
# ============================================================
if __name__ == "__main__":
    print("="*70)
    print("TESTE TH FILTER V58.36 — Perfil + Gringo")
    print("="*70)

    # TESTE 1: Filtro por perfil
    print("\n--- TESTE 1: Filtro por perfil ---")
    testes_perfil = [
        # (nome, desc, perfis, esperado_reprovado, descricao)
        ("Podcast do Joao", "Entrevistas com empreendedores", ["podcast"], False, "Podcast com palavra podcast"),
        ("Thiago Nigro", "Canal de financas", ["podcast"], True, "Nao tem sinal de podcast"),
        ("Dra Maria Silva", "Canal sobre medicina e saude", ["medico"], False, "Medico com sinais medicos"),
        ("Podcast do Joao", "Entrevistas", ["medico"], True, "Podcast quando selecionou medico"),
        ("Advocacia Silva", "Escritorio de direito tributario", ["advogado"], False, "Advogado com sinais juridicos"),
        ("Canal do Gaming", "Gameplay de minecraft", ["podcast"], True, "Gamer quando selecionou podcast"),
        ("Nutricao em Foco", "Dicas de alimentacao saudavel", ["nutricionista"], False, "Nutricionista com sinais"),
        ("Joao Fernandes", "Canal de negocios", ["nutricionista"], True, "Sem sinais de nutricionista"),
        # Multi-perfil
        ("Podcast Medico", "Entrevistas com medicos sobre saude", ["podcast", "medico"], False, "Multi-perfil: eh os dois"),
        ("Canal Generic", "Noticias do dia", ["podcast", "medico"], True, "Multi-perfil: nao eh nenhum"),
    ]

    passou = 0
    for nome, desc, perfis, esperado, descr in testes_perfil:
        rep, motivo = filtrar_por_perfil(nome, desc, perfis)
        ok = rep == esperado
        if ok: passou += 1
        status = "✓" if ok else "✗"
        acao = "REPROVA" if rep else "passa"
        print(f"  {status} [{descr:45}] {nome:25} → {acao} {motivo}")
    print(f"  Perfil: {passou}/{len(testes_perfil)}")

    # TESTE 2: Filtro gringo
    print("\n--- TESTE 2: Filtro gringo ---")
    testes_gringo = [
        ("Thiago Nigro", "Canal brasileiro de financas", "BR", ["BR"], False),
        ("Young and Profiting", "We talk about investing", "US", ["BR"], True),
        ("Bloomberg News", "Latest news", "US", ["BR"], True),
        ("Podcast do Joao", "Podcast brasileiro", "", ["BR"], False),
        ("Tech Review Daily", "Daily tech reviews", "", ["BR"], True),
    ]
    passou2 = 0
    for nome, desc, country, terr, esperado in testes_gringo:
        rep, motivo = filtrar_gringo(nome, desc, country, terr)
        ok = rep == esperado
        if ok: passou2 += 1
        status = "✓" if ok else "✗"
        acao = "REPROVA" if rep else "passa"
        print(f"  {status} {nome:35} → {acao} {motivo}")
    print(f"  Gringo: {passou2}/{len(testes_gringo)}")

    # TESTE 3: Filtro completo (perfil + gringo)
    print("\n--- TESTE 3: Filtro completo ---")
    testes_completo = [
        ("Podcast do Joao", "Podcast brasileiro de empreendedorismo", "BR", ["BR"], ["podcast"], False, "Podcast BR selecionou podcast"),
        ("Dra Maria", "Canal sobre medicina e saude", "BR", ["BR"], ["medico"], False, "Medico BR selecionou medico"),
        ("Young and Profiting", "Business podcast in english", "US", ["BR"], ["podcast"], True, "Gringo mesmo sendo podcast"),
        ("Gameplay Channel", "Gaming and lets play", "BR", ["BR"], ["podcast"], True, "Gameplay quando selecionou podcast"),
        ("Pat Flynn", "Smart passive income podcast", "US", ["BR"], ["podcast"], True, "Gringo conhecido"),
    ]
    passou3 = 0
    for nome, desc, country, terr, perfis, esperado, descr in testes_completo:
        rep, motivo = filtrar_canal(nome, desc, country, terr, perfis)
        ok = rep == esperado
        if ok: passou3 += 1
        status = "✓" if ok else "✗"
        acao = "REPROVA" if rep else "passa"
        print(f"  {status} [{descr:45}] {nome:25} → {acao} {motivo}")
    print(f"  Completo: {passou3}/{len(testes_completo)}")

    total = passou + passou2 + passou3
    total_testes = len(testes_perfil) + len(testes_gringo) + len(testes_completo)
    print(f"\n{'='*70}")
    print(f"TOTAL: {total}/{total_testes} passaram")
    print(f"{'='*70}")
