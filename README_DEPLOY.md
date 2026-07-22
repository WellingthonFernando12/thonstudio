# 🚀 THON Toolkit - Guia de Deploy (Render.com)

Este guia explica como colocar o THON online no Render.com (plano grátis ou pago).

## ⚠️ IMPORTANTE: Limpeza de Dados

Este ZIP vem **100% limpo**. Sem chaves de API, sem dados de clientes, sem histórico.
Você precisa configurar suas próprias chaves e senhas no painel do Render.

---

## 📋 Passo a Passo (10 minutos)

### Passo 1: Criar conta no GitHub
1. Acesse https://github.com
2. Clique em "Sign up"
3. Crie sua conta (email + senha + usuário)

### Passo 2: Criar repositório
1. No GitHub, clique no botão verde "New"
2. Nome do repositório: `thon-toolkit`
3. Marque como **Private** (só você vê)
4. Clique em "Create repository"

### Passo 3: Subir o código
1. No repositório criado, clique em "uploading an existing file"
2. Arraste **TODOS os arquivos** deste ZIP para dentro
3. Clique em "Commit changes"

### Passo 4: Criar conta no Render
1. Acesse https://render.com
2. Clique em "Sign Up" → "GitHub" (loga com sua conta do GitHub)
3. Autorize o Render a acessar seus repositórios

### Passo 5: Criar o Web Service
1. No painel do Render, clique em "New +" → "Web Service"
2. Selecione o repositório `thon-toolkit`
3. Configurações:
   - **Name:** `thon-toolkit`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn backend:app --workers 1 --threads 8 --timeout 120`
   - **Plan:** Free (depois pode mudar pra Starter)
4. Clique em "Advanced"
5. Adicione as **Environment Variables** (variáveis de ambiente):

| Key | Value |
|-----|-------|
| `THON_AUTH_PASSWORD` | `sua_senha_aqui` (ex: thon123) |
| `YOUTUBE_API_KEY` | `sua_chave_do_youtube_aqui` |
| `THON_RUNTIME_LOG` | `thon_backend_runtime.log` |

6. Clique em "Create Web Service"

### Passo 6: Aguardar o deploy
- O Render vai instalar as dependências e iniciar o servidor
- Leva uns 5-10 minutos na primeira vez
- Quando ficar verde "Live", tá pronto!

### Passo 7: Acessar!
- Seu link será: `https://thon-toolkit.onrender.com`
- Abra no navegador
- Digite a senha que você definiu em `THON_AUTH_PASSWORD`
- Pronto! Sistema online.

---

## 🔧 Configurações Importantes

### Variáveis de Ambiente (Environment Variables)

No painel do Render, em "Environment", você pode adicionar:

| Variável | Obrigatório | Descrição |
|----------|-------------|-----------|
| `THON_AUTH_PASSWORD` | **SIM** | Senha de acesso ao painel. Sem isso, qualquer um acessa. |
| `YOUTUBE_API_KEY` | Sim* | Sua chave da YouTube Data API v3 |
| `THON_RUNTIME_LOG` | Não | Nome do arquivo de log (default: thon_backend_runtime.log) |

\* Se não definir `YOUTUBE_API_KEY`, o sistema funciona mas não busca canais via API.

### Plano Free vs Pago

| Recurso | Free | Starter ($7/mês) |
|---------|------|------------------|
| RAM | 512MB | 512MB |
| Auto Hunt | ❌ Dorme em 15min | ✅ 24/7 |
| yt-dlp | ✅ Funciona | ✅ Funciona |
| Disco persistente | ❌ | ✅ (precisa pagar extra) |
| Tempo de build | 15 min | 15 min |

**Recomendação:** Teste no Free. Se for usar em produção, mude para Starter.

---

## 🆘 Problemas Comuns

### "Application failed to bind to $PORT"
- **Causa:** Render não conseguiu iniciar o servidor
- **Solução:** Verifique se o Start Command está correto:
  ```
  gunicorn backend:app --workers 1 --threads 8 --timeout 120
  ```

### "ModuleNotFoundError: No module named 'flask'"
- **Causa:** Dependências não instaladas
- **Solução:** Verifique se o `requirements.txt` está no repositório

### "401 Unauthorized"
- **Causa:** Você não definiu `THON_AUTH_PASSWORD` ou a senha está errada
- **Solução:** Adicione a variável no painel do Render → Environment

### yt-dlp não funciona (403)
- **Causa:** Render pode bloquear subprocessos no plano Free
- **Solução:** Mude para plano Starter ou use modo API

### Dados somem ao reiniciar
- **Causa:** Plano Free não tem disco persistente
- **Solução:** Faça export dos dados (XLSX/CSV) regularmente, ou mude para plano com disco

---

## 📞 Suporte

Se tiver problemas:
1. Verifique os logs no painel do Render (aba "Logs")
2. Confira se todas as variáveis de ambiente estão definidas
3. Verifique se o `requirements.txt` tem todas as dependências

---

## 📁 Estrutura do Projeto

```
thon-toolkit/
├── backend.py                    # Backend Flask principal
├── prospector.html               # Frontend (Prospector)
├── thon_auth.py                  # Sistema de login
├── thon_gringo_filter.py         # Filtro anti-gringo
├── thon_dlp_engine.py            # Wrapper da engine DLP
├── thon_dlp_engine_core_v58_17.py # Core da engine DLP
├── thon_search_engine.py         # Engine de busca
├── thon_verify_engine.py         # Engine de verificação
├── requirements.txt              # Dependências Python
├── render.yaml                   # Configuração do Render
├── README_DEPLOY.md              # Este arquivo
└── query_factory/                # Fábrica de queries
    ├── __init__.py
    ├── query_factory.py
    └── options.json
```
