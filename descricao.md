# DescriÃ§Ã£o Detalhada da AplicaÃ§Ã£o EFTX Antenna Pattern Designer

Este documento apresenta uma visÃ£o abrangente do funcionamento da aplicaÃ§Ã£o, descrevendo em detalhe o propÃ³sito de cada diretÃ³rio, arquivo e componente relevante no repositÃ³rio **EFTX_ANTENNA_PATTERN**. O objetivo Ã© facilitar a compreensÃ£o da arquitetura, dos fluxos de dados e das responsabilidades distribuÃ­das pelo cÃ³digo.

---

## 1. VisÃ£o Geral

A aplicaÃ§Ã£o Ã© uma soluÃ§Ã£o web completa para composiÃ§Ã£o, anÃ¡lise e exportaÃ§Ã£o de diagramas de radiaÃ§Ã£o de antenas (HRP/VRP), voltada para projetos de telecomunicaÃ§Ãµes. Ela suporta:

- Cadastro e autenticaÃ§Ã£o de usuÃ¡rios (com confirmaÃ§Ã£o de e-mail) e perfis `user`/`admin`;
- GestÃ£o de antenas, importaÃ§Ã£o de padrÃµes (HRP/VRP) via arquivos CSV/TXT, persistidos ponto a ponto em banco PostgreSQL;
- CriaÃ§Ã£o de projetos que reaproveitam padrÃµes elementares para construir arrays verticais e horizontais, calculando mÃ©tricas (HPBW, diretividade, F/B, ripple, SLL, ganho estimado) e exportando relatÃ³rios (`.PAT`, `.PRN`, PDF);
- AuxÃ­lio inteligente via integraÃ§Ã£o com o modelo Gemini (persona â€œAntennaExpertâ€), persistindo histÃ³rico de conversas por usuÃ¡rio.
- Base de conhecimento vetorial alimentada pelos datasheets em `docs/`, usada pelo assistente para fornecer respostas contextuais.

A stack principal inclui **Flask 3**, **SQLAlchemy/Alembic**, **Jinja2**, **NumPy**, **Matplotlib**, **ReportLab**, **pypdf** e **Google Generative AI**.

---

## 2. Estrutura de DiretÃ³rios e Arquivos

### 2.1. Raiz do RepositÃ³rio

- `autoapp.py` / `run.py` / `wsgi.py`: pontos de entrada para execuÃ§Ã£o local (Flask CLI/`flask run`), scripts intermediÃ¡rios e deploy WSGI. Todos instanciam a aplicaÃ§Ã£o via `app.create_app`.
- `pyproject.toml` / `requirements.txt`: definem dependÃªncias de execuÃ§Ã£o/desenvolvimento e metadados do projeto.
- `alembic.ini` + `migrations/`: configuraÃ§Ã£o e histÃ³rico de migraÃ§Ãµes Alembic para esquema de banco.
- `docs/`: documentaÃ§Ã£o auxiliar (auditoria, plano, setup).
- `proc.md`: Prompt operacional (SOP) descrevendo arquitetura, backlog, polÃ­ticas e expectativas de engenharia; atualizado sempre que processos mudam.
- `descricao.md`: **ESTE** arquivo â€“ documentaÃ§Ã£o detalhada do funcionamento do app com Ãªnfase em cada componente.
- `.env.example`: arquivo exemplo com variÃ¡veis necessÃ¡rias (`DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, etc.).
- `.gitignore`: polÃ­ticas de exclusÃ£o de arquivos transitÃ³rios (`.env`, caches, builds, etc.).

### 2.2. DiretÃ³rio `app/`

#### 2.2.1. NÃºcleo da AplicaÃ§Ã£o

- `app/__init__.py`: fÃ¡brica da aplicaÃ§Ã£o (`create_app`). Faz `load_dotenv`, seleciona configuraÃ§Ã£o (desenvolvimento/produÃ§Ã£o/teste), registra extensÃµes Flask, blueprints, globais de template e comandos CLI.
- `app/config.py`: classes de configuraÃ§Ã£o (`BaseConfig`, `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`). Define parÃ¢metros como conexÃµes de banco, limites de sessÃ£o, JWT, rotas de exportaÃ§Ã£o, prompts do assistente, modelo Gemini (`gemini-2.5-flash`) e saudaÃ§Ã£o padrÃ£o.
- `app/extensions.py`: inicializa extensÃµes globais (SQLAlchemy, Alembic/Migrate, Flask-Login, CSRF, Mailman, Limiter, JWTManager).
- `app/cli.py`: comandos customizados CLI vinculados ao Flask (ex.: seeds, manutenÃ§Ã£o).
- `app/utils/`: utilidades comuns
  - `calculations.py`: fÃ³rmulas auxiliares (ex.: `vertical_beta_deg`, `total_feeder_loss`), auxiliares de RF.
  - `security.py`: hashing/verificaÃ§Ã£o de senha, tokens de confirmaÃ§Ã£o, rehash.
  - `templating.py`: registra helpers/filtros para Jinja (branding, formataÃ§Ã£o, datas).

#### 2.2.2. PersistÃªncia

- `app/models.py`: modelos SQLAlchemy principais:
  - `User`: informaÃ§Ãµes pessoais, senha, flags (admin, confirmado), relaÃ§Ã£o 1:N com `Project`, relaÃ§Ã£o 1:1 com `AssistantConversation`.
  - `Antenna`: cadastro de antenas + relacionamentos com padrÃµes (`AntennaPattern`) e projetos (`ProjectAntenna`).
  - `AntennaPattern`: padrÃµes elementares (HRP/VRP) com `metadata_json` e filhos `AntennaPatternPoint` (pontos Ã¢ngulo/amplitude). MÃ©todo `replace_points` recria a sÃ©rie de pontos de forma deduplicada e ordenada.
  - `AntennaPatternPoint`: tabela ponto a ponto (Ã¢ngulo, amplitude linear) com constraint Ãºnica `(pattern_id, angle_deg)`.
  - `Project`: projeto de composiÃ§Ã£o. ContÃ©m parÃ¢metros verticais/horizontais, metadados de sistema, relaÃ§Ãµes com antenas (`ProjectAntenna`) e exportaÃ§Ãµes (`ProjectExport`).
  - `ProjectAntenna`: ligaÃ§Ãµes N:N entre projetos e antenas (posiÃ§Ã£o no array, espaÃ§amento, fase, amplitude).
  - `ProjectExport`: histÃ³rico de exportaÃ§Ãµes (caminho `PAT/PRN/PDF`, metadados ERP, timestamp).
  - `AssistantConversation` e `AssistantMessage`: persistem histÃ³rico individual do chat com o AntennaExpert.

#### 2.2.3. FormulÃ¡rios (`app/forms/`)

- `auth.py`: formulÃ¡rios de login, registro, reenviar confirmaÃ§Ã£o (CSRF via Flask-WTF, validaÃ§Ãµes especÃ­ficas de CPF/CNPJ, regras de senha).
- `project.py`: formulÃ¡rio abrangente de criaÃ§Ã£o/ediÃ§Ã£o de projeto (validaÃ§Ã£o de faixas, valores mÃ­nimos, coerÃªncia entre parÃ¢metros verticais e horizontais).
- `admin.py`: formulÃ¡rios administrativos para cadastro e ediÃ§Ã£o de antenas, upload de padrÃµes (via `PatternUploadForm`).

#### 2.2.4. Blueprints e Rotas (`app/blueprints/`)

- `auth/views.py`: rotas de autenticaÃ§Ã£o (`/register`, `/login`, `/logout`, `/confirm/<token>`, JWT issuance). Interage com `User`, tokens de e-mail, LoginManager e JWT.
- `public/views.py`: pÃ¡ginas pÃºblicas (home, vitrine de antenas, branding).
- `projects/views.py`: dashboard protegido, criaÃ§Ã£o/ediÃ§Ã£o detalhada, cÃ¡lculo ERP (`compute_erp`), renderizaÃ§Ã£o de mÃ©tricas, download dos arquivos exportados.
- `admin/views.py`: rotas protegidas por `admin_required` para gerenciamento de antenas, importaÃ§Ã£o de HRP/VRP com parsing CSV, reamostragem e persistÃªncia em `AntennaPatternPoint`, geraÃ§Ã£o de previews e exports diretos.
- `api/views.py`: REST JSON
  - CRUD de antenas/projetos/exportaÃ§Ãµes via JWT Bearer;
  - CÃ¡lculo `compute_erp` e endpoints `/assistant/conversation` & `/assistant/message` que alimentam o front-end de chat.
- `__init__.py`: registra todos os blueprints no app.

#### 2.2.5. ServiÃ§os (`app/services/`)

- `pattern_composer.py`: nÃºcleo matemÃ¡tico de composiÃ§Ã£o dos arranjos.
  - `resample_pattern` / `resample_vertical`: reamostragem HRP (âˆ’180â€¦180Â°) e VRP (âˆ’90â€¦90Â°) preservando caracterÃ­sticas do CSV.
  - `compose_horizontal_pattern`: calcula padrÃ£o composto de painÃ©is horizontais somando contribuiÃ§Ãµes complexas (posiÃ§Ã£o em arco circular, espaÃ§amento mecÃ¢nico, fase de excitaÃ§Ã£o, ganho elementar).
  - `compose_vertical_pattern`: combina elementos verticais (pilha de antenas) usando tilt, espaÃ§amento e contagem.
  - `compute_erp`: integra padrÃµes compostos, aplica perdas e potÃªncia para obter ERP (linear/dBw), mÃ©tricas auxiliares, valores exportÃ¡veis (PAT/PRN). O helper `serialize_erp_payload` grava o resultado em `project.composition_meta`, mantendo dashboards e exports sincronizados com ajustes posteriores.
  - `export_pat` / `export_prn`: grava arquivos nos formatos especÃ­ficos.
- `visuals.py`: geraÃ§Ã£o de previews (grÃ¡ficos Matplotlib) e mÃ©tricas para exibiÃ§Ã£o no painel; salva imagens em `static/generated/previews/...` e harmoniza `project.composition_meta` com os cÃ¡lculos mais recentes.
- `exporters.py`: coordena exportaÃ§Ãµes (bundle PAT/PRN/PDF) e grava `ProjectExport`.
- `assistant.py`: integra com Google Generative AI (Gemini). Carga do `.env`, configuraÃ§Ã£o do modelo `gemini-2.5-flash`, histÃ³rico `[system_prompt, greeting]+messages`, chamadas via `start_chat(...).send_message(...)`, persistindo entradas/saÃ­das na base, consultando o Ã­ndice vetorial (`knowledge_base.py`) para fornecer contexto, registrando logs de depuraÃ§Ã£o e interpretando marcaÃ§Ãµes `<action type="create_project">{...}</action>` para criar projetos automaticamente (incluindo estimativa de elementos quando o alvo de ganho Ã© informado).
  - O mecanismo de aÃ§Ãµes permite que o AntennaExpert guie o usuÃ¡rio e execute tarefas (ex.: criaÃ§Ã£o de projetos) emitindo `<action type="create_project">{...}</action>`; o backend interpreta o JSON, resolve a antena, estima `v_count`/`h_count` a partir do ganho desejado (`target_gain_dbi`) e salva o novo projeto, retornando o link direto ao usuÃ¡rio.
- `knowledge_base.py`: constrÃ³i/consulta um Ã­ndice vetorial dos documentos (`docs/`) usando SentenceTransformers, armazenando embeddings em `vector_store/` e servindo trechos relevantes para enriquecer as respostas do assistente.
- `email.py`: envio de e-mails transacionais (confirmaÃ§Ã£o, alertas admin).
- `pattern_parser.py`: leitura robusta de arquivos CSV/TXT (colunas Theta/E/Emax), fallback genÃ©rico.
- `metrics.py`: utilidades matemÃ¡ticas (HPBW, diretividade, ripple, SLL, conversÃµes dBâ†”linear), reutilizadas por relatÃ³rios e composiÃ§Ãµes.

#### 2.2.6. Templates (`app/templates/`)

- `base.html`: shell principal â€“ inclui assets (`static/css/main.css`, `static/js/designer.js`, `forms.js`, `assistant.js`), menu lateral, topbar, footer.
- DiretÃ³rios `auth/`, `projects/`, `admin/`, `public/`, `emails/` contÃªm os templates especÃ­ficos:
  - `auth/*.html`: pÃ¡ginas de login/cadastro/reenviar.
  - `projects/dashboard.html`: lista projetos do usuÃ¡rio com aÃ§Ãµes.
  - `projects/detail.html`: exibe mÃ©tricas ERP, grÃ¡ficos e links de export.
  - `admin/*`: tabelas de antenas, formulÃ¡rios de importaÃ§Ã£o, data manager genÃ©rico.
  - `emails/*`: templates textuais HTML para confirmaÃ§Ã£o e alertas.
  - `public/home.html` / `public/brand.html`: landing pages pÃºblicas.

#### 2.2.7. Static (`app/static/`)

- `css/main.css`: tema escuro azul, layout responsivo, estilos para dashboards, formulÃ¡rios, chat do assistente e grÃ¡ficos.
- `js/designer.js`: interaÃ§Ãµes do compositor ERP (AJAX para `/api/projects/<id>/patterns`, atualizaÃ§Ã£o de grÃ¡ficos via canvas/DOM).
- `js/forms.js`: utilidades UI (ex.: toggle de senha, diÃ¡logos).
- `js/assistant.js`: lÃ³gica do painel â€œAjuda inteligenteâ€ (fetch histÃ³rico/mensagens, estado de carregamento, exibiÃ§Ã£o incremental, status de erro).
- `img/`: ativos grÃ¡ficos (logotipo EFTX).
- `generated/`: diretÃ³rio criado em runtime para previews de projetos/antenas.

---

## 3. Fluxos Principais

### 3.1. ImportaÃ§Ã£o de PadrÃµes
1. Admin faz upload (CSV/TXT) via `/admin/antennas/<id>/patterns`.
2. `pattern_parser.py` interpreta os dados, reamostra (1Â°) e, antes de regravar, remove pontos antigos (`DELETE` atÃ© `AntennaPatternPoint`).
3. `replace_points` recria o conjunto de amostras, mantendo `metadata_json` com snapshot do arquivo e data de importaÃ§Ã£o.

### 3.2. ComposiÃ§Ã£o e ExportaÃ§Ã£o de Projetos
1. UsuÃ¡rio seleciona antena elementar, define parÃ¢metros verticais/horizontais.
2. `compute_erp` aplica `compose_vertical_pattern` + `compose_horizontal_pattern`, calcula ERP com perdas, gera mÃ©tricas.
3. `generate_project_previews` salva grÃ¡ficos e exibe estatÃ­sticas.
4. `generate_project_export` chama `export_pat`, `export_prn`, `ReportLab` (PDF) e registra `ProjectExport`.

### 3.3. Assistente Inteligente
1. Ao acessar â€œAjuda Inteligenteâ€, front chama `/api/assistant/conversation` â€“ se nÃ£o houver histÃ³rico, `get_or_create_conversation` grava a saudaÃ§Ã£o inicial.
2. Mensagens subsequentes vÃ£o para `/api/assistant/message`, que monta o histÃ³rico com `system_prompt` e chama `GenerativeModel.start_chat(...).send_message()`.
3. Resposta e mensagem do usuÃ¡rio sÃ£o persistidas; front exibe histÃ³rico completo.

### 3.4. AutenticaÃ§Ã£o e SeguranÃ§a
- Senhas com Argon2/Bcrypt; `password_needs_rehash` garante upgrade automÃ¡tico.
- CSRF habilitado (Flask-WTF) e rate limits via Flask-Limiter.
- JWT opcional para APIs; tokens curtos com `Bearer` header.
- ConfirmacÌ§aÌƒo de e-mail com tokens temporÃ¡rios (`itsdangerous`).

---

## 4. MigraÃ§Ãµes Alembic

- `20250930_000001_create_core_tables.py`: cria tabelas centrais (`users`, `antennas`, padrÃµes simples).
- `46986b249afd_.py` e `3e83237a9467_.py`: ajustes (ex.: `v_tilt_deg`, aumento de tamanho de `password_hash`).
- `730014782f4e_.py`: introduz tabelas `antenna_pattern_points`, `project_antennas`, normalizaÃ§Ã£o de padrÃµes e limpeza de colunas antigas.
- `8b4e91acba2d_add_assistant_conversations.py`: adiciona suporte ao histÃ³rico do assistente (conversas/mensagens).

Cada migraÃ§Ã£o Ã© encadeada; `flask db upgrade` aplica toda a sequÃªncia.

---

## 5. DependÃªncias Externas e ConvenÃ§Ãµes

- **Flask-Limiter**: proteÃ§Ã£o contra abuso de endpoints (limites configurÃ¡veis via `RATE_LIMIT_*`).
- **ReportLab/pypdf**: geraÃ§Ã£o e mescla de PDFs com modelo institucional (`modelo.pdf`).
- **NumPy/Matplotlib**: cÃ¡lculos numÃ©ricos, grÃ¡ficos polares/planos.
- **Google Generative AI**: integraÃ§Ã£o via `google-generativeai` com modelo `gemini-2.5-flash` e prompt personalizado.
- **python-dotenv**: carrega variÃ¡veis sensÃ­veis a partir de `.env` local (obrigatÃ³rio para chaves e URLs).

---

## 6. Boas PrÃ¡ticas e ExpansÃµes Futuras

- **Testes**: meta de â‰¥70% cobertura nos serviÃ§os crÃ­ticos. Priorizar testes de reamostragem (361 pontos HRP), mÃ©tricas e exportaÃ§Ãµes.
- **Observabilidade**: adicionar logs estruturados (JSON) e monitoramento `/healthz` (latÃªncia de SELECT, uptime, versÃ£o).
- **CI/CD**: pipelines para lint/testes; empacotar deploy Gunicorn + Nginx com arquivo `systemd` apontando para `.env` seguro.
- **IA Assistente**: evoluir com contexto adicional (dados do projeto/antenna) e ajustes dinÃ¢micos de prompt.

---

## 7. ConclusÃ£o

Este projeto combina uma arquitetura Flask modular com cÃ¡lculos especializados para RF, geraÃ§Ã£o de relatÃ³rios e suporte inteligente por IA. A organizaÃ§Ã£o detalhada em modelos, serviÃ§os e camadas de apresentaÃ§Ã£o facilita manutenÃ§Ã£o e expansÃ£o. Este documento, aliado ao `proc.md`, deve ser mantido atualizado a cada alteraÃ§Ã£o estrutural significativa para garantir rastreabilidade e alinhamento entre cÃ³digo e operaÃ§Ã£o.
- Use o comando `flask rebuild-knowledge --source docs` para indexar/atualizar os datasheets. Caso o modelo de embeddings exija autenticaÃ§Ã£o, defina `HUGGINGFACEHUB_API_TOKEN` (ou equivalente) antes de rodar o comando.

\n---\n\n## 8. Atualizacoes Recentes\n\n- Painel admin/data modernizado: helpers _titleize, _truncate e _format_cell_value melhoram formatacao, adicionam contadores e evitam conflitos de nomes com metodos nativos do dict.\n- Exportadores PAT/PRN/PDF recebem parametro highlight para marcar o ponto de horizonte no VRP e usam _safe_float para persistir metricas sem NaN no PostgreSQL.\n- Ambiente virtual ajustado apos migracao: pyvenv.cfg aponta para C:\\Users\\iltom\\AppData\\Local\\Programs\\Python\\Python313 e foi criado wrapper local pip.cmd para delegar python -m pip dentro da venv, prevenindo uso acidental do pip global.\n
