# 🎯 PROMPT MASTER — Análise de Leads THON Toolkit

## Como usar este prompt

1. Exporte o lote pelo THON (botão "📤 Exportar lote .xlsx")
2. Abra a planilha no Excel/Google Sheets
3. Selecione TODAS as linhas (Ctrl+A) ou copie as colunas: `nome, url, subs, score, nicho, descricao, longos, shorts, views, last_video_days, score_tags, sinais_monetizacao, ja_tem_editor`
4. Cole no chat com a IA
5. Envie o prompt abaixo (personalize os trechos entre `[COLCHETES]`)

---

## 📋 PROMPT PARA COPIAR E COLAR

```
Você é um analista de leads sênior para uma agência de edição de vídeos/podcasts no Brasil. Seu trabalho é qualificar canais do YouTube como potenciais clientes.

## CONTEXTO DO NEGÓCIO

- Serviço: edição de vídeos longos (podcasts, entrevistas, tutoriais) + cortes para shorts
- Ticket médio: R$ 2.000-8.000/mês por cliente
- Cliente ideal: criadores de conteúdo brasileiros com canal em crescimento, que precisam de ajuda profissional de edição
- NÃO queremos: canais de grandes empresas (já têm editor interno), canais gringos, canais parados, canais com audiência comprada

## CRITÉRIOS DE QUALIFICAÇÃO

### ✅ Lead EXCELENTE (aprovar) — deve ter a MAIORIA destes:
- Score >= 70
- 10K <= inscritos <= 200K (sweet spot: têm orçamento mas não são grandes demais)
- Pelo menos 3 vídeos longos (20min+) nos últimos vídeos
- Avg views >= 5% dos inscritos (audiência engajada, não comprada)
- Last video em até 60 dias (canal ativo)
- Tem email ou Instagram visíveis (contato encontrado)
- Sinais de monetização (patrocinadores, loja, afiliados)
- Descrição do canal fala sobre o nicho dele (não é canal genérico)

### ⚠️ Lead para REVISAR (revisar) — tem potencial mas algo preocupa:
- Score 55-69
- Inscritos no range mas views baixos (ratio 1-3%)
- Canal ativo mas sem sinais claros de monetização
- Sem contato visível mas descrição profissional
- Nicho bom mas só 1-2 vídeos longos recentes
- Último vídeo entre 60-120 dias (pode ter pausado)

### ❌ Lead RUIM (reprovar) — tem QUALQUER UM destes:
- Score < 55
- ja_tem_editor = SIM (já tem editor, não precisa de nós)
- views/subs < 1% (audiência comprada, inscritos falsos)
- last_video_days > 180 (canal parado)
- shorts >> longos (canal de shorts não precisa de edição de longos)
- Descrição em inglês ou espanhol (gringo)
- Descrição vazia ou genérica ("canal de entretenimento")
- Nome do canal contém: "cortes", "clips", "highlights", "vlog", "react", "gameplay", "tutorial", "diy"
- Mais de 4 shorts e menos de 2 longos (formato errado pro nosso serviço)

## INSTRUÇÕES DE ANÁLISE

Para cada canal que eu enviar, responda no formato:

### [NOME DO CANAL]
- **URL**: [url]
- **Inscritos**: [subs] · **Score**: [score]
- **Decisão**: [APROVAR / REPROVAR / REVISAR]
- **Motivo**: [justificativa em 1-2 linhas baseada nos critérios acima]
- **Score IA**: [0-100, sua própria avaliação considerando público, engajamento, fit com serviço]
- **Público-alvo estimado**: [perfil da audiência em 1 linha — ex: "empreendedores 25-40 anos", "mulheres 30-50 interessadas em finanças"]
- **Potencial de fechamento**: [ALTO/MÉDIO/BAIXO] — probabilidade de virar cliente pagante
- **Estratégia de abordagem**: [1 sugestão de como abordar esse lead — ex: "Mencionar episódio X sobre Y", "Oferecer cortes dos últimos 3 episódios"]

## DADOS DOS LEADS

[COLE AQUI OS DADOS DA PLANILHA — pode ser as linhas copiadas do Excel, CSV, ou uma tabela markdown]

## SAÍDA ESPERADA

Analise TODOS os leads que enviei. No final, me dê:

1. **Resumo executivo**: X aprovados, Y reprovados, Z para revisar
2. **Top 3 leads** (maior potencial de fechamento) com justificativa
3. **Bottom 3 leads** (pior fit) com motivo de descarte
4. **Planilha preenchida** no formato CSV para eu colar de volta no Excel:

```
id,nome,decisao,motivo_reprovacao,score_ia,potencial
UCxxxxx,Nome Canal,aprovar,,85,ALTO
UCyyyyy,Outro Canal,reprovar,audiencia comprada,20,BAIXO
```

Use a coluna `decisao` com: aprovar / reprovar / revisar
Use a coluna `motivo_reprovacao` SOMENTE quando decisao = reprovar
Use a coluna `score_ia` com sua nota de 0-100
Use a coluna `potencial` com: ALTO / MÉDIO / BAIXO

Seja criterioso. Cada lead aprovado custa tempo de abordagem. É melhor reprovar um lead duvidoso do que aprovar um que não vai converter.
```

---

## 🎯 VARIAÇÕES DO PROMPT

### Versão RÁPIDA (poucos leads, resposta curta)

```
Analise estes leads do YouTube como potencial cliente de edição de vídeos. Para cada um: dê nota 0-100, decisão (aprovar/reprovar/revisar) e 1 motivo. Critério: score>=70, 10K-200K subs, 3+ longos, views>=5% subs, ativo nos últimos 60 dias, sem editor interno.

[COLE OS LEADS]
```

### Versão FOCADA EM FECHAMENTO (qual tem mais chance de virar cliente)

```
Você é um vendedor de serviços de edição de vídeo. Analise estes leads e me diga QUAIS têm maior chance de FECHAR contrato (não só quais são bons canais). Considere: sinal de orçamento (monetização), dor evidente (muita edição pra fazer sozinho), acessibilidade (tem contato), momento (canal crescendo = precisa de ajuda). Rank do maior pro menor potencial de fechamento. Para cada um: decisão (aprovar/reprovar/revisar), potencial (ALTO/MÉDIO/BAIXO) e estratégia de abordagem em 1 linha.

[COLE OS LEADS]
```

### Versão COMPLETA COM PERFIL DE PÚBLICO (a mais detalhada)

```
Para cada lead abaixo, faça uma análise completa de qualificação:

1. **Decisão**: aprovar / reprovar / revisar
2. **Score IA** (0-100): sua avaliação considerando:
   - Fit com serviço de edição (peso 30%)
   - Saúde do canal: subs, views, atividade (peso 25%)
   - Qualidade do público: engajamento, nicho claro (peso 20%)
   - Acessibilidade: tem contato, é brasileiro (peso 15%)
   - Potencial de receita: monetização, ticket (peso 10%)
3. **Perfil do público-alvo**: quem assiste este canal? (idade, gênero, interesses)
4. **Tamanho do público estimado**: alcance real (views médias × potencial de crescimento)
5. **Dores prováveis do criador**: o que ele deve estar sofrendo agora? (ex: "sem tempo de editar", "cortes ruins", "thumbnail amadora")
6. **Potencial de fechamento**: ALTO/MÉDIO/BAIXO
7. **Estratégia de abordagem personalizada**: 1-2 linhas sobre como abordar
8. **Risco/bandeira vermelha**: algo que pode atrapalhar o fechamento

Critérios:
- Reprovar se: ja_tem_editor=SIM, views<1% subs, last_video>180d, gringo, descricao vazia
- Aprovar se: score>=70, 10K-200K subs, 3+ longos, contato visível, monetização
- Revisar nos demais casos

No final, gere CSV com: id,nome,decisao,motivo,score_ia,potencial,perfil_publico

[COLE OS LEADS]
```

---

## 💡 DICAS DE USO

### Como colar os dados da planilha

**Opção 1 — CSV direto (recomendado)**:
Salve a aba "Lote de Caca" como CSV no Excel e cole o conteúdo. Fica assim:
```
id,nome,url,subs,score,nicho,...
UCabc,Thiago Nigro,https://...,89000,92,financas,...
UCdef,Canal Morto,https://...,120000,28,marketing,...
```

**Opção 2 — Tabela Markdown**:
Cole direto do Excel — a IA costuma converter sozinha.

**Opção 3 — Seleção de colunas**:
Se a planilha tiver muitos dados, copie só as colunas essenciais:
`nome, url, subs, score, nicho, descricao, longos, shorts, views, last_video_days, score_tags, sinais_monetizacao, ja_tem_editor`

### Como enviar leads demais de uma vez

Se tiver mais de 30 leads, divida em lotes de 10-15. A IA analisa melhor em pedaços menores e você confere a qualidade da análise.

### Como usar a resposta

A IA vai te devolver:
1. Análise individual de cada lead (decisão + motivo + score + potencial + estratégia)
2. CSV pronto pra colar de volta no Excel

Você pega o CSV, cola numa nova aba da planilha exportada pelo THON, mapeia as colunas `decisao` e `motivo_reprovacao` (pode usar PROCV no Excel), salva, e importa de volta pelo botão "📥 Importar planilha analisada".

### Personalização

Antes de enviar, ajuste no prompt:
- `[TICKET MÉDIO]`: quanto você cobra por mês
- `[NICHOS QUE NÃO QUER]`: adicione na lista de reprovação
- `[NICHOS QUE PRIORIZA]`: adicione nos critérios de aprovação

---

## 📊 TEMPLATE DE RESPOSTA ESPERADA

A IA deve responder parecido com isso:

```
### Thiago Nigro
- URL: youtube.com/@thiago.nigro
- Inscritos: 89K · Score: 92
- **Decisão**: APROVAR
- **Motivo**: Score alto, 25 longos, ratio 9%, ativo (12 dias), monetizado, tem email
- **Score IA**: 88
- **Público-alvo**: empreendedores 25-40, classe B, interessados em investimento
- **Potencial de fechamento**: ALTO
- **Estratégia**: Mencionar episódio sobre "investimentos 2024", oferecer cortes dos 3 últimos episódios

### Canal Morto
- URL: youtube.com/@canalmorto
- Inscritos: 120K · Score: 28
- **Decisão**: REPROVAR
- **Motivo**: Audiência comprida (ratio 0.25%), 40 shorts vs 1 longo
- **Score IA**: 15
- **Público-alvo**: indefinido (descrição genérica)
- **Potencial de fechamento**: BAIXO
- **Estratégia**: N/A

---

## RESUMO EXECUTIVO
- 3 aprovados, 1 reprovado, 1 revisar
- Top 3: Thiago Nigro (88), Canal Bom (75), Lead Revisar (62)
- Bottom 1: Canal Morto (15)

## CSV PARA COLAR NO EXCEL
id,nome,decisao,motivo_reprovacao,score_ia,potencial
UCabcdef,Thiago Nigro,aprovar,,88,ALTO
UCxyz,Canal Morto,reprovar,audiencia comprida,15,BAIXO
...
```

Pronto. É só copiar, personalizar e usar.
