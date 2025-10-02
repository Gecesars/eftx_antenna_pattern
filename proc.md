# PROC.md — Prompt Operacional Único para o Codex (EFTX Antenna Pattern Designer)

> **Este arquivo é a FONTE DE VERDADE** para o agente (gpt‑5‑codex high) trabalhar **no repositório existente**.  
> Ele consolida e harmoniza: objetivos, arquitetura, backlog por marcos, especificação de cálculo/exportação (PAT/PRN/PDF), UX, testes, CI/CD, observabilidade e deploy.  
> **Regra de ouro:** nunca começar do zero; sempre **auditar ➜ planejar ➜ aplicar patch mínimo ➜ registrar mudanças**.

---

## 0) Objetivo e Escopo

Construir e manter uma **aplicação web completa** para **cálculo, composição e exportação de diagramas de antenas** do portfólio **EFTX**.  
Tecnologias base: **Flask (Python), SQLAlchemy/Alembic (PostgreSQL), Jinja2**, **NumPy/Matplotlib/ReportLab/Pillow/pypdf**, com **exportação .PAT, .PRN e PDF**.  
Usuários: cadastro com verificação de e‑mail, perfis `user` e `admin`. `admin` gerencia catálogo de antenas e diagramas; usuários criam **projetos** que compõem ERP (HRP/VRP) e exportam relatórios.

Resultados esperados:
- **Precisão numérica** nas métricas (HPBW, Diretividade, F/B, Ripple, SLL, pico, ganho estimado);
- **Exportes normatizados** (.PAT/.PRN/PDF) prontos para integração externa e exigências (ex.: Anatel);
- **UX profissional** (tema dark azul EFTX), **segurança** (segredos fora do VCS), **testes** (≥70% em serviços),
- **Deploy** em VPS (Gunicorn+Nginx+systemd) com **observabilidade** (healthz, logs).

---

## 1) Protocolo de Execução (sempre que o Codex rodar)

### 1.1 Auditoria Inicial (não destrutiva)
- Ler todo o repositório (código, templates, estáticos, migrações, docs).
- Inventariar **lacunas** vs. este PROC.md.
- Produzir **plano incremental mínimo** e **diff unificado (git apply)** apenas do escopo do primeiro marco pendente.

**Prompt sugerido ao Codex:**
```
Audite o repositório atual e compare com o PROC.md. Liste gaps por área (dados, blueprints, serviços de export/cálculo, UI, testes, segurança, deploy). 
Proponha um patch mínimo e seguro para o próximo marco (M0→M1…). Gere diff texto-unificado aplicável com `git apply`.
```

### 1.2 Aplicação do Patch
- Aplicar o patch gerado; se falhar, reduzir o escopo e reemitir.
- Manter compatibilidade com chamadores legados (services/rotas/templates).

### 1.3 Registro Obrigatório de Mudanças
- Atualizar `CHANGELOG.md` com: ISO datetime, arquivos tocados, resumo técnico, riscos/breaking changes.
- `git add -A && git commit -m "feat: <resumo> [codex]"` após **cada** patch.
- Em caso de migração Alembic: **incluir arquivo de migration** no commit.

**Prompt padrão:**
```
Atualize CHANGELOG.md com data/hora ISO, resumo por arquivo e riscos. Em seguida faça git add -A e git commit com mensagem descritiva.
```

---

## 2) Arquitetura e Pastas (estado‑alvo)

Estrutura recomendada (adapte ao existente sem rupturas):
```
EFTX_APP/
├─ app.py / run.py
├─ wsgi.py
├─ config.py
├─ requirements.txt
├─ .env.example            # variáveis de ambiente (NÃO commitar .env)
├─ /models                 # SQLAlchemy (users, antennas, projects, project_antennas, diagrams, diagram_points, exports)
├─ /routes                 # blueprints: auth, projects, antennas (admin), export, api, public, health
├─ /services               # cálculos, exportadores, utilitários (pdf, pat, prn, interp, metrics)
├─ /templates              # Jinja2 (tema dark azul EFTX)
├─ /static                 # CSS/JS/imagens
├─ /migrations             # Alembic
└─ /docs                   # auditoria, plano, setup, decisões
```

**Configuração de engine/pool (exemplo):**
```python
SQLALCHEMY_ENGINE_OPTIONS = {
  "pool_size": 10, "max_overflow": 20, "pool_pre_ping": True
}
```

**Segurança e segredos**
- Nunca comitar segredos; usar `.env` local e `EnvironmentFile` no systemd.
- Fornecer `.env.example` com chaves e explicações.

---

## 3) Modelo de Dados (mínimo viável + índices)

- `users (id, email unique, password_hash, role, verified_at, ...)`
- `antennas (id, name, model, maker, gain_db, weight, dims, ...)`
- `diagrams (id, antenna_id FK, kind {HRP,VRP}, norm {none,max,rms}, meta jsonb)`
- `diagram_points (id, diagram_id FK, angle_deg numeric, value_linear numeric)`  
  Índices: `(diagram_id, angle_deg)`, `btree`/`hash` conforme SGBD.
- `projects (id, user_id FK, name, tower_h, cable_type, cable_len_m, ...)`
- `project_antennas (id, project_id FK, antenna_id FK, position, phase_deg, spacing_m, amplitude)`  
  Índices: `(project_id)`, `(antenna_id)`, `(project_id, position)`
- `exports (id, project_id, kind {PAT,PRN,PDF}, path, created_at, meta jsonb)`

**Migrações**
- Alembic para criação/alteração de esquema.
- Jobs de **seed/import**: CSV/TSV (HFSS) → `diagrams` + `diagram_points`.

---

## 4) Blueprints e Rotas

- `auth`: `/auth/register`, `/auth/login`, `/auth/verify`, `/auth/logout`
- `antennas` (admin): CRUD + importação HRP/VRP
- `projects`: CRUD + composição multi‑antena (N:N) + preview
- `export`: `/export/pat`, `/export/prn`, `/export/pdf` (por projeto)
- `api`: endpoints JSON para previews/métricas
- `public`: páginas públicas essenciais
- `health`: `/healthz` (200 + ping DB + versão do app + uptime)

**Autorização**
- `admin_required` para `antennas` e tarefas administrativas.
- Usuário comum só acessa seus próprios projetos/exports.

---

## 5) Especificação Numérica (cálculo/intervalos)

### 5.1 Reamostragem e Domínios
- **HRP**: manter amostras originais em −180…+180° (passo 1°). Reamostragem circular sem modular para 0…360°; ajustes para visualização/export usam `angle % 360` apenas na saída.
- **VRP**: −90…+90° (passo 1° no composto; 0,1° quando necessário nos elementos).  
  Tail opcional: 0…−90° para compatibilidade com alguns consumidores.
- Normalização: `none|max|rms`. Aplicar `val = max(val, 1e-12)` antes de converter para dB.

### 5.2 Métricas
- **HPBW**: limiar em amplitude `sqrt(0.5)` (‑3 dB) sobre E/Emax; interpolar cruzamentos.
- **Diretividade (2D cut)**: integração **Simpson** sobre potência relativa do corte.
- **F/B**: buscar pico do lobo traseiro numa janela configurável (padrão 150°–210°).
- **Ripple (mainlobe)**: pico‑a‑pico no feixe principal (região ≥‑6 dB do pico).
- **SLL**: maior lóbulo fora do feixe principal (≥‑6 dB).
- **Pico & Ganho estimado**: reportar ângulo de pico e ganho/dir estimada (dBi).

### 5.3 Arrays verticais/horizontais
- A composição vertical multiplica o padrão elementar reamostrado por um fator de array complexo calculado a partir de `v_count`, espaçamento `v_spacing_m`, fase `v_beta_deg` (inclui tilt) e nível/amplitude progressivo, normalizado segundo `v_norm_mode`.
- A composição horizontal aplica a mesma abordagem vetorial, porém distribui os painéis em arco circular com espaçamento mecânico (`h_spacing_m`) e deslocamento angular `h_step_deg`; cada elemento contribui com fase geométrica + excitação (`h_beta_deg`) e amplitude progressiva `h_level_amp`.
- O resultado composto (dados ERP) é serializado para `project.composition_meta`, garantindo que páginas e exportações reflitam qualquer alteração de parâmetros após salvar.

---

## 6) Especificação de Exportação

### 6.1 Arquivo .PAT (composição)
- Cabeçalho composto (exemplo):
  - Linha 1: `'By EFTX'`
  - Linha 2: `<GAIN_dBi>,<NUM_ELEMS>`
- **HRP**: 360 amostras (0..359, 1°).  
- **VRP**: −90..+90 (1°; 0,1° em elementos se necessário) + tail 0..−90 quando aplicável.
- Valores: preferir **E/Emax (linear)** quando requerido; manter compatibilidade dos consumidores existentes.

### 6.2 Arquivo .PRN
- Escrever **atenuação em dB positiva**: `att = max(0, -20*log10(E/Emax))`.
- Sempre 360 amostras por plano.
- Metadados (opcionais no topo ou bloco): `NAME, MAKE, FREQUENCY, H/V_WIDTH, F/B, GAIN_dBi`.

### 6.3 Relatório PDF
- **ReportLab** + **pypdf** para mesclar em `modelo.pdf` quando fornecido.
- Gráficos Matplotlib (dpi ≥200), fontes 6–8pt em tabelas.
- Sumário técnico: métricas, parâmetros do projeto, antenas, cabos, composição e observações.

---

## 7) UX/Frontend

- Jinja2 com **Tailwind (CDN)** ou Bootstrap, tema **dark azul EFTX**.  
- Páginas: Login/Cadastro, Dashboard, Projetos, Antenas (admin), Export/Relatórios.
- Tabelas com **paginação, busca e ordenação** via JS leve.
- Acessibilidade: contraste AA, foco visível, mensagens claras de validação.

---

## 8) Testes, Qualidade e CI

- **pytest** (com **pytest‑cov**) para serviços de cálculo/export/rotas básicas (alvo: ≥70% cobertura nos serviços).
- Linters: **black, isort, flake8, mypy, bandit** (pre‑commit).
- GitHub Actions: jobs para lint + testes.
- Exemplos mínimos:
  - `hpbw_deg` em padrão gaussiano (expectativa 19–25° dependendo do sigma).  
  - PRN: todas as linhas com atenuação **≥ 0**.  
  - HRP reamostrado: exatamente 360 amostras.

---

## 9) Observabilidade e Health

- `/healthz`: `status=200`, duração `SELECT 1`, versão do app, uptime.  
- Logging **estruturado** (JSON: ts, level, route, status, request_id).  
- Integração Sentry opcional via env var.

---

## 10) Deploy (VPS)

- **Gunicorn** (`workers = 2×vCPU + 1`), **Nginx** reverse proxy (TLS, gzip).  
- `systemd` com `EnvironmentFile=/etc/eftx_app.env`.  
- Alembic migrations no deploy (`flask db upgrade`).  
- Backups `pg_dump` diários com retenção e verificação.

---

## 11) Dependências (mínimo recomendado)

Arquivo `requirements.txt` deve conter versões compatíveis (fixe/pinne quando estabilizar).  
Inclua: Flask 3, Flask‑Login/WTF/Limiter/Mailman/JWT‑Extended, SQLAlchemy 2, Alembic/Flask‑Migrate, psycopg2‑binary, Argon2/bcrypt, itsdangerous, python‑dotenv, NumPy, Matplotlib, ReportLab, pypdf, Pillow, email‑validator, pytest/pytest‑cov, black/isort/flake8/mypy/bandit.

---

## 12) Assistente IA (Gemini)

- Variáveis de ambiente: `GEMINI_API_KEY`, `GEMINI_MODEL` (padrão `gemini-2.5-flash`), `ASSISTANT_SYSTEM_PROMPT`, `ASSISTANT_HISTORY_LIMIT`, `ASSISTANT_GREETING`.
- Carregar `.env` na inicialização do Flask (`load_dotenv`) antes de criar o app.
- Serviço `app/services/assistant.py`: carrega a chave via `load_dotenv`, instancia `GenerativeModel('gemini-2.5-flash')` e chama `start_chat(history=[system_prompt como user, saudacao inicial como model] + mensagens persistidas)`, replicando o fluxo testado em CLI. Persistência garante continuação da conversa por cliente, e os logs (`assistant.prepare`/`assistant.response`/`assistant.error`) ajudam a diagnosticar falhas.
- O agente pode disparar ações operacionais envolvendo `<action type="create_project">{...}</action>` no texto de resposta; o backend interpreta essa marcação, cria o projeto com os parâmetros informados (estimando `v_count`/`h_count` quando houver `target_gain_dbi`) e devolve um resumo com link direto para o projeto recém-criado.
- Se nenhum espaçamento for informado e houver mais de um elemento, o sistema usa automaticamente espaçamento `λ/2` tanto vertical quanto horizontal, garantindo que o padrão composto reflita a interação entre os elementos.
- O assistente consulta o índice vetorial construído a partir dos arquivos em `docs/` (`flask rebuild-knowledge`) e inclui o contexto relevante antes de chamar o modelo.
- O comando `flask rebuild-knowledge --source docs` recompila o índice vetorial; se o modelo de embeddings exigir autenticação, defina `HUGGINGFACEHUB_API_TOKEN` (ou `HUGGINGFACE_TOKEN`).
- Front-end: botão flutuante “Ajuda inteligente” invoca endpoints `/api/assistant/conversation` e `/api/assistant/message`, exibindo saudação inicial e histórico.
- Prompt base: persona “AntennaExpert” com instruções técnicas/didáticas sobre uso do EFTX Antenna Pattern Designer; respostas devem citar recursos do app e orientar correções de projeto.
---

## 12) Backlog por Marcos (M0→M8)

**M0 — Saneamento**
- Remover `.env` versionado; criar `.env.example`; `.gitignore` abrangente; ativar venv; docs de auditoria.

**M1 — Dados**
- Introduzir `project_antennas` (N:N) e `diagram_points`; migrar dados; índices; seeds/imports.

**M2 — Blueprints & Health**
- Registrar `export` e `health`; `/healthz` com ping ao DB; `admin_required`.

**M3 — Cálculo & Export**
- Reamostragem HRP/VRP; métricas; `.PAT`/`.PRN` padronizados; PDF com `modelo.pdf`.

**M4 — Frontend**
- Tema dark azul EFTX; templates com responsividade e UX consistente.

**M5 — Testes & Qualidade**
- Suite pytest; linters; CI.

**M6 — Observabilidade**
- Logs estruturados; Sentry opcional.

**M7 — Deploy**
- Gunicorn+Nginx+systemd; backups.

**M8 — Migração/Seed & Docs**
- Importar padrões, criar admin, popular antenas base; guias de uso.

---

## 13) Prompts Operacionais (Copiar/Colar no Codex)

### 13.1 Auditoria & Patch M0/M1
```
Leia todo o repositório e compare com o PROC.md.
Gere um patch mínimo para M0 e M1 (saneamento + schema N:N + diagram_points + seeds), sem quebrar chamadas existentes.
Inclua migrações Alembic e ajustes de models/serviços/rotas quando estritamente necessários.
Produza diff unificado pronto para `git apply` e um resumo das mudanças.
```

### 13.2 Registrar Mudanças
```
Atualize CHANGELOG.md com data/hora ISO, lista de arquivos e motivações técnicas.
Execute git add -A && git commit -m "feat: saneamento e schema N:N [codex]".
```

### 13.3 Exportadores
```
Refatore services de export para cumprir a especificação do PROC.md:
- PAT: HRP 0..359 (1°), VRP −90..+90 (1°) com tail opcional, cabeçalho 'By EFTX' + <GAIN>,<NUM_ELEMS>.
- PRN: atenuação positiva em dB; 360 amostras/Plano; metadados.
- PDF: ReportLab+pypdf; gráficos Matplotlib ≥200 dpi; tabelas paginadas.
Mantenha compatibilidade com funções chamadoras.
```

### 13.4 Health & Observabilidade
```
Crie blueprint 'health' com /healthz retornando 200, duração SELECT 1, versão do app e uptime.
Padronize logging para JSON.
```

### 13.5 Testes
```
Adicione pytest (com pytest-cov) para métricas (hpbw, diretividade) e export (PRN/PAT).
Garanta cobertura ≥70% nos serviços de cálculo/export.
```

### 13.6 Frontend
```
Atualize templates com Tailwind por CDN (tema dark azul EFTX), páginas de projetos/antenas/export com tabelas paginadas.
```

---

## 14) Políticas de Código

- Funções de cálculo **puras**; IO em camadas de serviço.  
- Tipagem (mypy) nos serviços críticos.  
- Lint automático (pre‑commit).  
- Tratamento de falhas de export: retornar JSON com `error`, `details`, `trace_id` sem derrubar sessão.

---

## 15) Confirmação e Manutenção do PROC.md

- Ao concluir um marco, **atualizar esta especificação** refletindo o novo estado e próximos passos.  
- Manter coerência entre README, requirements e docs de setup.  
- Este arquivo deve ser lido pelo agente **na primeira etapa de qualquer execução**.
