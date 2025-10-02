# Descrição Detalhada da Aplicação EFTX Antenna Pattern Designer

Este documento apresenta uma visão abrangente do funcionamento da aplicação, descrevendo em detalhe o propósito de cada diretório, arquivo e componente relevante no repositório **EFTX_ANTENNA_PATTERN**. O objetivo é facilitar a compreensão da arquitetura, dos fluxos de dados e das responsabilidades distribuídas pelo código.

---

## 1. Visão Geral

A aplicação é uma solução web completa para composição, análise e exportação de diagramas de radiação de antenas (HRP/VRP), voltada para projetos de telecomunicações. Ela suporta:

- Cadastro e autenticação de usuários (com confirmação de e-mail) e perfis `user`/`admin`;
- Gestão de antenas, importação de padrões (HRP/VRP) via arquivos CSV/TXT, persistidos ponto a ponto em banco PostgreSQL;
- Criação de projetos que reaproveitam padrões elementares para construir arrays verticais e horizontais, calculando métricas (HPBW, diretividade, F/B, ripple, SLL, ganho estimado) e exportando relatórios (`.PAT`, `.PRN`, PDF);
- Auxílio inteligente via integração com o modelo Gemini (persona “AntennaExpert”), persistindo histórico de conversas por usuário.

A stack principal inclui **Flask 3**, **SQLAlchemy/Alembic**, **Jinja2**, **NumPy**, **Matplotlib**, **ReportLab**, **pypdf** e **Google Generative AI**.

---

## 2. Estrutura de Diretórios e Arquivos

### 2.1. Raiz do Repositório

- `autoapp.py` / `run.py` / `wsgi.py`: pontos de entrada para execução local (Flask CLI/`flask run`), scripts intermediários e deploy WSGI. Todos instanciam a aplicação via `app.create_app`.
- `pyproject.toml` / `requirements.txt`: definem dependências de execução/desenvolvimento e metadados do projeto.
- `alembic.ini` + `migrations/`: configuração e histórico de migrações Alembic para esquema de banco.
- `docs/`: documentação auxiliar (auditoria, plano, setup).
- `proc.md`: Prompt operacional (SOP) descrevendo arquitetura, backlog, políticas e expectativas de engenharia; atualizado sempre que processos mudam.
- `descricao.md`: **ESTE** arquivo – documentação detalhada do funcionamento do app com ênfase em cada componente.
- `.env.example`: arquivo exemplo com variáveis necessárias (`DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, etc.).
- `.gitignore`: políticas de exclusão de arquivos transitórios (`.env`, caches, builds, etc.).

### 2.2. Diretório `app/`

#### 2.2.1. Núcleo da Aplicação

- `app/__init__.py`: fábrica da aplicação (`create_app`). Faz `load_dotenv`, seleciona configuração (desenvolvimento/produção/teste), registra extensões Flask, blueprints, globais de template e comandos CLI.
- `app/config.py`: classes de configuração (`BaseConfig`, `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`). Define parâmetros como conexões de banco, limites de sessão, JWT, rotas de exportação, prompts do assistente, modelo Gemini (`gemini-2.5-flash`) e saudação padrão.
- `app/extensions.py`: inicializa extensões globais (SQLAlchemy, Alembic/Migrate, Flask-Login, CSRF, Mailman, Limiter, JWTManager).
- `app/cli.py`: comandos customizados CLI vinculados ao Flask (ex.: seeds, manutenção).
- `app/utils/`: utilidades comuns
  - `calculations.py`: fórmulas auxiliares (ex.: `vertical_beta_deg`, `total_feeder_loss`), auxiliares de RF.
  - `security.py`: hashing/verificação de senha, tokens de confirmação, rehash.
  - `templating.py`: registra helpers/filtros para Jinja (branding, formatação, datas).

#### 2.2.2. Persistência

- `app/models.py`: modelos SQLAlchemy principais:
  - `User`: informações pessoais, senha, flags (admin, confirmado), relação 1:N com `Project`, relação 1:1 com `AssistantConversation`.
  - `Antenna`: cadastro de antenas + relacionamentos com padrões (`AntennaPattern`) e projetos (`ProjectAntenna`).
  - `AntennaPattern`: padrões elementares (HRP/VRP) com `metadata_json` e filhos `AntennaPatternPoint` (pontos ângulo/amplitude). Método `replace_points` recria a série de pontos de forma deduplicada e ordenada.
  - `AntennaPatternPoint`: tabela ponto a ponto (ângulo, amplitude linear) com constraint única `(pattern_id, angle_deg)`.
  - `Project`: projeto de composição. Contém parâmetros verticais/horizontais, metadados de sistema, relações com antenas (`ProjectAntenna`) e exportações (`ProjectExport`).
  - `ProjectAntenna`: ligações N:N entre projetos e antenas (posição no array, espaçamento, fase, amplitude).
  - `ProjectExport`: histórico de exportações (caminho `PAT/PRN/PDF`, metadados ERP, timestamp).
  - `AssistantConversation` e `AssistantMessage`: persistem histórico individual do chat com o AntennaExpert.

#### 2.2.3. Formulários (`app/forms/`)

- `auth.py`: formulários de login, registro, reenviar confirmação (CSRF via Flask-WTF, validações específicas de CPF/CNPJ, regras de senha).
- `project.py`: formulário abrangente de criação/edição de projeto (validação de faixas, valores mínimos, coerência entre parâmetros verticais e horizontais).
- `admin.py`: formulários administrativos para cadastro e edição de antenas, upload de padrões (via `PatternUploadForm`).

#### 2.2.4. Blueprints e Rotas (`app/blueprints/`)

- `auth/views.py`: rotas de autenticação (`/register`, `/login`, `/logout`, `/confirm/<token>`, JWT issuance). Interage com `User`, tokens de e-mail, LoginManager e JWT.
- `public/views.py`: páginas públicas (home, vitrine de antenas, branding).
- `projects/views.py`: dashboard protegido, criação/edição detalhada, cálculo ERP (`compute_erp`), renderização de métricas, download dos arquivos exportados.
- `admin/views.py`: rotas protegidas por `admin_required` para gerenciamento de antenas, importação de HRP/VRP com parsing CSV, reamostragem e persistência em `AntennaPatternPoint`, geração de previews e exports diretos.
- `api/views.py`: REST JSON
  - CRUD de antenas/projetos/exportações via JWT Bearer;
  - Cálculo `compute_erp` e endpoints `/assistant/conversation` & `/assistant/message` que alimentam o front-end de chat.
- `__init__.py`: registra todos os blueprints no app.

#### 2.2.5. Serviços (`app/services/`)

- `pattern_composer.py`: núcleo matemático de composição dos arranjos.
  - `resample_pattern` / `resample_vertical`: reamostragem HRP (−180…180°) e VRP (−90…90°) preservando características do CSV.
  - `compose_horizontal_pattern`: calcula padrão composto de painéis horizontais somando contribuições complexas (posição em arco circular, espaçamento mecânico, fase de excitação, ganho elementar).
  - `compose_vertical_pattern`: combina elementos verticais (pilha de antenas) usando tilt, espaçamento e contagem.
  - `compute_erp`: integra padrões compostos, aplica perdas e potência para obter ERP (linear/dBw), métricas auxiliares, valores exportáveis (PAT/PRN).
  - `export_pat` / `export_prn`: grava arquivos nos formatos específicos.
- `visuals.py`: geração de previews (gráficos Matplotlib) e métricas para exibição no painel; salva imagens em `static/generated/previews/...`.
- `exporters.py`: coordena exportações (bundle PAT/PRN/PDF) e grava `ProjectExport`.
- `assistant.py`: integra com Google Generative AI (Gemini). Carga do `.env`, configuração do modelo `gemini-2.5-flash`, histórico `[system_prompt, greeting]+messages`, chamadas via `start_chat(...).send_message(...)`, persistindo entradas/saídas na base e registrando logs de debug.
- `email.py`: envio de e-mails transacionais (confirmação, alertas admin).
- `pattern_parser.py`: leitura robusta de arquivos CSV/TXT (colunas Theta/E/Emax), fallback genérico.
- `metrics.py`: utilidades matemáticas (HPBW, diretividade, ripple, SLL, conversões dB↔linear), reutilizadas por relatórios e composições.

#### 2.2.6. Templates (`app/templates/`)

- `base.html`: shell principal – inclui assets (`static/css/main.css`, `static/js/designer.js`, `forms.js`, `assistant.js`), menu lateral, topbar, footer.
- Diretórios `auth/`, `projects/`, `admin/`, `public/`, `emails/` contêm os templates específicos:
  - `auth/*.html`: páginas de login/cadastro/reenviar.
  - `projects/dashboard.html`: lista projetos do usuário com ações.
  - `projects/detail.html`: exibe métricas ERP, gráficos e links de export.
  - `admin/*`: tabelas de antenas, formulários de importação, data manager genérico.
  - `emails/*`: templates textuais HTML para confirmação e alertas.
  - `public/home.html` / `public/brand.html`: landing pages públicas.

#### 2.2.7. Static (`app/static/`)

- `css/main.css`: tema escuro azul, layout responsivo, estilos para dashboards, formulários, chat do assistente e gráficos.
- `js/designer.js`: interações do compositor ERP (AJAX para `/api/projects/<id>/patterns`, atualização de gráficos via canvas/DOM).
- `js/forms.js`: utilidades UI (ex.: toggle de senha, diálogos).
- `js/assistant.js`: lógica do painel “Ajuda inteligente” (fetch histórico/mensagens, estado de carregamento, exibição incremental, status de erro).
- `img/`: ativos gráficos (logotipo EFTX).
- `generated/`: diretório criado em runtime para previews de projetos/antenas.

---

## 3. Fluxos Principais

### 3.1. Importação de Padrões
1. Admin faz upload (CSV/TXT) via `/admin/antennas/<id>/patterns`.
2. `pattern_parser.py` interpreta os dados, reamostra (1°) e, antes de regravar, remove pontos antigos (`DELETE` até `AntennaPatternPoint`).
3. `replace_points` recria o conjunto de amostras, mantendo `metadata_json` com snapshot do arquivo e data de importação.

### 3.2. Composição e Exportação de Projetos
1. Usuário seleciona antena elementar, define parâmetros verticais/horizontais.
2. `compute_erp` aplica `compose_vertical_pattern` + `compose_horizontal_pattern`, calcula ERP com perdas, gera métricas.
3. `generate_project_previews` salva gráficos e exibe estatísticas.
4. `generate_project_export` chama `export_pat`, `export_prn`, `ReportLab` (PDF) e registra `ProjectExport`.

### 3.3. Assistente Inteligente
1. Ao acessar “Ajuda Inteligente”, front chama `/api/assistant/conversation` – se não houver histórico, `get_or_create_conversation` grava a saudação inicial.
2. Mensagens subsequentes vão para `/api/assistant/message`, que monta o histórico com `system_prompt` e chama `GenerativeModel.start_chat(...).send_message()`.
3. Resposta e mensagem do usuário são persistidas; front exibe histórico completo.

### 3.4. Autenticação e Segurança
- Senhas com Argon2/Bcrypt; `password_needs_rehash` garante upgrade automático.
- CSRF habilitado (Flask-WTF) e rate limits via Flask-Limiter.
- JWT opcional para APIs; tokens curtos com `Bearer` header.
- Confirmação de e-mail com tokens temporários (`itsdangerous`).

---

## 4. Migrações Alembic

- `20250930_000001_create_core_tables.py`: cria tabelas centrais (`users`, `antennas`, padrões simples).
- `46986b249afd_.py` e `3e83237a9467_.py`: ajustes (ex.: `v_tilt_deg`, aumento de tamanho de `password_hash`).
- `730014782f4e_.py`: introduz tabelas `antenna_pattern_points`, `project_antennas`, normalização de padrões e limpeza de colunas antigas.
- `8b4e91acba2d_add_assistant_conversations.py`: adiciona suporte ao histórico do assistente (conversas/mensagens).

Cada migração é encadeada; `flask db upgrade` aplica toda a sequência.

---

## 5. Dependências Externas e Convenções

- **Flask-Limiter**: proteção contra abuso de endpoints (limites configuráveis via `RATE_LIMIT_*`).
- **ReportLab/pypdf**: geração e mescla de PDFs com modelo institucional (`modelo.pdf`).
- **NumPy/Matplotlib**: cálculos numéricos, gráficos polares/planos.
- **Google Generative AI**: integração via `google-generativeai` com modelo `gemini-2.5-flash` e prompt personalizado.
- **python-dotenv**: carrega variáveis sensíveis a partir de `.env` local (obrigatório para chaves e URLs).

---

## 6. Boas Práticas e Expansões Futuras

- **Testes**: meta de ≥70% cobertura nos serviços críticos. Priorizar testes de reamostragem (361 pontos HRP), métricas e exportações.
- **Observabilidade**: adicionar logs estruturados (JSON) e monitoramento `/healthz` (latência de SELECT, uptime, versão).
- **CI/CD**: pipelines para lint/testes; empacotar deploy Gunicorn + Nginx com arquivo `systemd` apontando para `.env` seguro.
- **IA Assistente**: evoluir com contexto adicional (dados do projeto/antenna) e ajustes dinâmicos de prompt.

---

## 7. Conclusão

Este projeto combina uma arquitetura Flask modular com cálculos especializados para RF, geração de relatórios e suporte inteligente por IA. A organização detalhada em modelos, serviços e camadas de apresentação facilita manutenção e expansão. Este documento, aliado ao `proc.md`, deve ser mantido atualizado a cada alteração estrutural significativa para garantir rastreabilidade e alinhamento entre código e operação.
