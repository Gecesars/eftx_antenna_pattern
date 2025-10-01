
# PROSS.md — Plano Operacional do EFTX Antenna App (Auditar ➜ Corrigir ➜ Evoluir)

> Este arquivo **é a fonte de verdade** para o agente (Codex CLI).  
> **Nunca comece do zero.** Sempre:
> 1) **Faça auditoria do repositório existente** (estrutura, modelos, blueprints, serviços, templates, estáticos, migrações).  
> 2) Compare o resultado com este **PROSS.md**.  
> 3) Gere um **plano incremental** e um **diff** mínimo e seguro.  
> 4) **Aplique as mudanças** e **registre tudo automaticamente** (CHANGELOG.md + commits).

---

## A. Escopo do Produto (estado atual + alvo)

**Estado atual (resumo):**
- Flask 3 + SQLAlchemy 2, WSGI via `wsgi.py`, configs separadas em `app/config.py`.
- Autenticação dupla: sessão (Flask-Login) e JWT (Flask-JWT-Extended).
- Serviços de composição ERP com NumPy/Matplotlib; export PDF/PRN/PAT com ReportLab/pypdf.
- Blueprints: `auth`, `projects`, `admin`, `api`, `public` (falta `export` dedicado e `health`).
- Modelos: `User`, `Antenna`, `AntennaPattern`, `Project` (referência a uma antena), `ProjectExport`.
- Armazenamento de padrões em JSONB, geração de previews e histórico de exportações.
- Limitações: **sem relação N:N projeto↔antenas**, **sem testes**, **exportadores legados** ainda com inconsistências, **segredos em .env versionado**.

**Alvo:**
- App robusto, seguro, responsivo, com **composição de arranjos multi-antenas** e **exportações corretas (PDF/PAT/PRN)**, **testes**, **observabilidade** e **pronto para VPS**.

> Fontes do estado atual e limitações devem ser revalidadas a cada execução auditando o repositório (ver Seção F).

---

## B. Definition of Done (DoD)

1. **Segurança**: nenhum segredo no repositório; `.env.example` presente; leitura via `python-dotenv`/variáveis.  
2. **Dados**: esquema com `project_antennas` para N:N (posição, fase, espaçamento, amplitude), `diagrams`/`diagram_points` indexados.  
3. **API/Blueprints**: `auth`, `projects`, `antennas (admin)`, `export`, `health`, `api` — todos registrados.  
4. **Export**: `.PAT` e `.PRN` em formatos exigidos (PRN com **atenuação positiva**); **PDF** com gráficos e tabelas paginadas.  
5. **UX**: tema escuro + azul EFTX, páginas responsivas e profissionais; formulários validados.  
6. **Testes**: `pytest` cobrindo serviços de cálculo/export (≥70% cobertura nos serviços).  
7. **Qualidade**: `black`, `isort`, `flake8`, `mypy` limpos; CI executando testes.  
8. **Operação**: `/healthz` com ping ao DB; logs estruturados; Dockerfile + compose local; guia de deploy (gunicorn/nginx/systemd).  
9. **Performance**: índices adequados, paginação, pool do SQLAlchemy configurado.  
10. **Documentação**: `docs/` com auditoria, plano, decisões e guias.

---

## C. Roadmap por Marcos (M0→M8)

### M0 — Saneamento e Fundações
- Remover `.env` do histórico e ignorá-lo; criar `.env.example` (SECRET_KEY/JWT, DATABASE_URL, MAIL_*, EXPORT_ROOT etc.).
- Adicionar `.gitignore` amplo, pin mínimo em `requirements.txt`, ativar virtualenv.
- Criar `docs/00-auditoria.md` (inventário + achados) e `docs/01-plano.md` (milestones).

### M1 — Modelo de Dados e Migrações
- Criar `project_antennas (project_id, antenna_id, position, phase_deg, spacing_m, amplitude)` com FKs e índices;  
  ajustar `Project` para não depender de `antenna_id` único.
- Normalizar `AntennaPattern` e pontos: `diagram_points (diagram_id, angle_deg, value_linear)` com índice composto.
- Migrar dados existentes; jobs de seed e import de CSVs HFSS para novas tabelas.

### M2 — Blueprints, Segurança e Health
- Registrar `export` e `health` no `app/blueprints/__init__.py`.
- `GET /healthz`: OK + `SELECT 1` no DB + versão do app.
- Autorização por role (`admin_required`) nas rotas administrativas.

### M3 — Serviços de Cálculo & Export (revisão final)
- Reamostragem VRP (-90..+90) passo 1° (0.1° quando necessário) e HRP (-180..+180) passo 1°; HRP 0..359 via embrulho.
- Métricas: HPBW, Directivity (Simpson), F/B (janela 180±30°), Ripple mainlobe (≥−6 dB), SLL, Pico e Ganho estimado.
- `.PAT` composto com cabeçalho `'By EFTX', <gain>, <num_elems>`, HRP 0..359 e VRP com tail 0..−90.
- `.PRN` com **atenuação dB positiva** em 360 amostras por plano; metadados (NAME, MAKE, FREQUENCY, H/V_WIDTH, F/B, GAIN dBi).
- **PDF** com ReportLab + pypdf, gráficos Matplotlib, tabelas multi-coluna paginadas e opção de `modelo.pdf`.

### M4 — Frontend Responsivo e Profissional
- Jinja2 + Tailwind (CDN) / Bootstrap; layout dark azul EFTX.
- Páginas: login/cadastro, dashboard, projetos, antenas (admin), export/relatórios; tabelas com paginação/busca.

### M5 — Testes e Qualidade
- `pytest` para serviços de cálculo/export/rotas básicas; `pytest-cov`.
- `black`, `isort`, `flake8`, `mypy`, `bandit` + pre-commit.
- GitHub Actions com lint + testes.

### M6 — Observabilidade
- Logging JSON (timestamp, level, request_id). Integração Sentry (opcional).

### M7 — Deploy em VPS
- Gunicorn + Nginx + systemd; migrations no deploy; backups `pg_dump`; `.env` via systemd EnvironmentFile.

### M8 — Migração/Seed e Documentação de Uso
- Importar padrões existentes; criar admin; popular antenas básicas; guias `docs/`.

---

## D. Especificação Técnica de Export/Cálculo (normativa)

- **Normalização**: `none|max|rms`; clamp numérico: `val = max(val, 1e-12)` para calcular dB.  
- **Simpson**: integração para diretividade (2D cut).  
- **HPBW**: limiar `sqrt(0.5)` sobre E/Emax.  
- **F/B**: pico do lobo traseiro em [150°, 210°] (ajustável).  
- **Ripple**: diferença pico-a-pico no feixe principal (≥ −6 dB).  
- **SLL**: máximo fora do feixe principal (≥ −6 dB).  
- **PAT-HRP**: 0..359 (1°), interpolação circular; cabeçalho composto e blocos finais 356..359 + tail VRP quando aplicável.  
- **PAT-VRP**: −90..+90 (0.1° no elemento; 1° no composto) + tail 0..−90.  
- **PRN**: escrever **atenuação** `max(0, -20*log10(E/Emax))`.  
- **PDF**: figuras 200 dpi; tabelas multi-coluna paginadas (fonte 6–7pt).

---

## E. UX & Acessibilidade (resumo)

- Tema: fundo `#0f172a`, primário `#2563eb`, texto `#e5e7eb`; foco visível; contraste AA.  
- Grid responsivo (1–2–3 colunas); formulários com validação e mensagens claras.  
- Tabelas com paginação, ordenação e busca (JS leve).

---

## F. Protocolo de Execução para o Codex CLI

> **Sempre rodar a partir da raiz do projeto existente.**

### 1) Auditoria inicial (não destrutiva)
**Prompt:**
```
Leia todo o repositório atual (código, templates, estáticos, migrações, docs). Compare com o PROSS.md. 
Liste gaps por área (dados, blueprints, serviços de export/cálculo, UI, testes, segurança). 
Proponha um plano incremental mínimo (M0→M1 primeiro) e gere um diff texto-unificado (git apply) não destrutivo.
```
**Comando sugerido (Windows PowerShell):**
```powershell
codex -m "gpt-5-codex" -c model_reasoning_effort="high" --sandbox workspace-write -a on-failure -C . "
Audite o repositório e gere o patch mínimo para M0 e M1 conforme PROSS.md, com explicações por arquivo."
```

### 2) Aplicar patch
```powershell
codex apply
```

### 3) Iterações dirigidas
- Blueprints/health/export (M2):
```powershell
codex -C . "Registre blueprints export e health em app/blueprints/__init__.py; crie rotas mínimas e testes."
```
- Exporters (M3):
```powershell
codex -C . "Refatore services/pattern_* para exportar PAT/PRN conforme PROSS.md; manter compatibilidade dos callers."
```
- UI (M4):
```powershell
codex -C . "Atualize templates com Tailwind CDN e tema dark azul EFTX; padronize listas e formulários responsivos."
```

### 4) Registro **obrigatório** de alterações (automatizado)
- Criar/atualizar `CHANGELOG.md` **a cada execução** com:
  - Data/hora ISO.
  - Lista de arquivos modificados/criados/removidos.
  - Resumo técnico do porquê das mudanças.
- Executar `git add -A && git commit -m "feat: <resumo> [codex]"` após aplicar cada patch.
- Em caso de migrações: gerar arquivo Alembic e incluir no commit.

**Prompt padrão para registrar mudanças:**
```
Atualize CHANGELOG.md com data ISO e resumo. Em seguida, execute git add -A e git commit com mensagem descritiva.
```

---

## G. Ações Imediatas Recomendadas

1) **Higiene de segredos**: remover `.env` do histórico e criar `.env.example`.  
2) **Schema N:N**: introduzir `project_antennas` e migrar dados.  
3) **Blueprints**: adicionar `export` e `health`.  
4) **Exporters**: padronizar `.PAT/.PRN` e PDF conforme Seção D.  
5) **Testes**: instalar `pytest` e criar suíte mínima para métricas/export.  

---

## H. Requisitos de Ambiente

`requirements.txt` mínimo (fixar versões compatíveis):
```
flask
flask_sqlalchemy
flask_migrate
flask_login
flask_wtf
flask_limiter
flask_mailman
flask_jwt_extended
psycopg2-binary
bcrypt
argon2-cffi
email-validator
python-dotenv
numpy
matplotlib
reportlab
pypdf
pillow
pytest
pytest-cov
black
isort
flake8
mypy
bandit
```

Pool do SQLAlchemy:
```python
SQLALCHEMY_ENGINE_OPTIONS = {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True}
```

---

## I. Testes (exemplos)

```python
def test_hpbw_gauss():
    import numpy as np
    from app.services.metrics import hpbw_deg
    ang = np.arange(-90, 91, 1)
    e = np.exp(-0.5*(ang/10.0)**2)
    assert 19 <= hpbw_deg(ang, e) <= 25
```

```python
def test_prn_positive_attenuation(tmp_path):
    # gerar PRN e validar que todas as linhas têm atenuação >= 0
    ...
```

---

## J. Observabilidade e Health

- `/healthz`: status 200 + duração do ping ao DB + versão do app.  
- Logging em JSON (nivel, mensagem, request_id, rota, status).

---

## K. Deploy (resumo)

- Gunicorn (workers = 2×vCPU + 1), Nginx reverse proxy, TLS, gzip.  
- systemd service com EnvironmentFile `.env`.  
- `flask db upgrade` executado no deploy; backups `pg_dump` diários.

---

## L. Diretrizes de Código (estilo)

- `black`, `isort`, `flake8` (E,W,F), `mypy` (gradual).  
- Funções de serviços **puras** quando possível; IO isolada em camadas de export.  
- Docstrings breves, tipagem em serviços críticos.

---

## M. Política de Falhas

- Em erro de export: retornar JSON com `error`, `details`, `trace_id`; não abortar a sessão do usuário.  
- Em falha de email: logar e seguir, exibindo aviso.

---

## N. Confirmação

Ao completar cada marco, o agente deve atualizar este PROSS.md (Seções C e G) refletindo o novo estado e próximos passos.
