# Descrio Detalhada da Aplicao EFTX Antenna Pattern Designer

Este documento apresenta uma viso abrangente do funcionamento da aplicao, descrevendo em detalhe o propsito de cada diretrio, arquivo e componente relevante no repositrio **EFTX_ANTENNA_PATTERN**. O objetivo  facilitar a compreenso da arquitetura, dos fluxos de dados e das responsabilidades distribudas pelo cdigo.

---

## 1. Viso Geral

A aplicao  uma soluo web completa para composio, anlise e exportao de diagramas de radiao de antenas (HRP/VRP), voltada para projetos de telecomunicaes. Ela suporta:

- Cadastro e autenticao de usurios (com confirmao de e-mail) e perfis `user`/`admin`;
- Gesto de antenas, importao de padres (HRP/VRP) via arquivos CSV/TXT, persistidos ponto a ponto em banco PostgreSQL;
- Criao de projetos que reaproveitam padres elementares para construir arrays verticais e horizontais, calculando mtricas (HPBW, diretividade, F/B, ripple, SLL, ganho estimado) e exportando relatrios (`.PAT`, `.PRN`, PDF);
- Auxlio inteligente via integrao com o modelo Gemini (persona AntennaExpert), persistindo histrico de conversas por usurio.
- Base de conhecimento vetorial alimentada pelos datasheets em `docs/`, usada pelo assistente para fornecer respostas contextuais.

A stack principal inclui **Flask 3**, **SQLAlchemy/Alembic**, **Jinja2**, **NumPy**, **Matplotlib**, **ReportLab**, **pypdf** e **Google Generative AI**.

---

## 2. Estrutura de Diretrios e Arquivos

### 2.1. Raiz do Repositrio

- `autoapp.py` / `run.py` / `wsgi.py`: pontos de entrada para execuo local (Flask CLI/`flask run`), scripts intermedirios e deploy WSGI. Todos instanciam a aplicao via `app.create_app`.
- `pyproject.toml` / `requirements.txt`: definem dependncias de execuo/desenvolvimento e metadados do projeto.
- `alembic.ini` + `migrations/`: configurao e histrico de migraes Alembic para esquema de banco.
- `docs/`: documentao auxiliar (auditoria, plano, setup).
- `proc.md`: Prompt operacional (SOP) descrevendo arquitetura, backlog, polticas e expectativas de engenharia; atualizado sempre que processos mudam.
- `descricao.md`: **ESTE** arquivo  documentao detalhada do funcionamento do app com nfase em cada componente.
- `.env.example`: arquivo exemplo com variveis necessrias (`DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY`, etc.).
- `.gitignore`: polticas de excluso de arquivos transitrios (`.env`, caches, builds, etc.).

### 2.2. Diretrio `app/`

#### 2.2.1. Ncleo da Aplicao

- `app/__init__.py`: fbrica da aplicao (`create_app`). Faz `load_dotenv`, seleciona configurao (desenvolvimento/produo/teste), registra extenses Flask, blueprints, globais de template e comandos CLI.
- `app/config.py`: classes de configurao (`BaseConfig`, `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`). Define parmetros como conexes de banco, limites de sesso, JWT, rotas de exportao, prompts do assistente, modelo Gemini (`gemini-2.5-flash`) e saudao padro.
- `app/extensions.py`: inicializa extenses globais (SQLAlchemy, Alembic/Migrate, Flask-Login, CSRF, Mailman, Limiter, JWTManager).
- `app/cli.py`: comandos customizados CLI vinculados ao Flask (ex.: seeds, manuteno).
- `app/utils/`: utilidades comuns
  - `calculations.py`: frmulas auxiliares (ex.: `vertical_beta_deg`, `total_feeder_loss`), auxiliares de RF.
  - `security.py`: hashing/verificao de senha, tokens de confirmao, rehash.
  - `templating.py`: registra helpers/filtros para Jinja (branding, formatao, datas).

#### 2.2.2. Persistncia

- `app/models.py`: modelos SQLAlchemy principais:
  - `User`: informaes pessoais, senha, flags (admin, confirmado), relao 1:N com `Project`, relao 1:1 com `AssistantConversation`.
  - `Antenna`: cadastro de antenas + relacionamentos com padres (`AntennaPattern`) e projetos (`ProjectAntenna`).
  - `AntennaPattern`: padres elementares (HRP/VRP) com `metadata_json` e filhos `AntennaPatternPoint` (pontos ngulo/amplitude). Mtodo `replace_points` recria a srie de pontos de forma deduplicada e ordenada.
  - `AntennaPatternPoint`: tabela ponto a ponto (ngulo, amplitude linear) com constraint nica `(pattern_id, angle_deg)`.
  - `Cable`: catlogo de cabos alimentadores com coeficiente de perda (`attenuation_db_per_100m`), bitola (`size_inch`), fabricante e notas. Projetos referenciam o cadastro via `cable_id`, mantendo `cable_type` apenas para compatibilidade retroativa.
  - `Project`: projeto de composio. Contm parmetros verticais/horizontais, metadados de sistema, relaes com antenas (`ProjectAntenna`) e exportaes (`ProjectExport`).
  - `ProjectAntenna`: ligaes N:N entre projetos e antenas (posio no array, espaamento, fase, amplitude).
  - `ProjectExport`: histrico de exportaes (caminho `PAT/PRN/PDF`, metadados ERP, timestamp).
  - `AssistantConversation` e `AssistantMessage`: persistem histrico individual do chat com o AntennaExpert.

#### 2.2.3. Formulrios (`app/forms/`)

- `auth.py`: formulrios de login, registro, reenviar confirmao (CSRF via Flask-WTF, validaes especficas de CPF/CNPJ, regras de senha).
- `project.py`: formulrio abrangente de criao/edio de projeto (validao de faixas, valores mnimos, coerncia entre parmetros verticais e horizontais).
- `admin.py`: formulrios administrativos para cadastro e edio de antenas, upload de padres (via `PatternUploadForm`).

#### 2.2.4. Blueprints e Rotas (`app/blueprints/`)

- `auth/views.py`: rotas de autenticao (`/register`, `/login`, `/logout`, `/confirm/<token>`, JWT issuance). Interage com `User`, tokens de e-mail, LoginManager e JWT.
- `public/views.py`: pginas pblicas (home, vitrine de antenas, branding).
- `projects/views.py`: dashboard protegido, criao/edio detalhada, clculo ERP (`compute_erp`), renderizao de mtricas, download dos arquivos exportados.
- `admin/views.py`: rotas protegidas por `admin_required` para gerenciamento de antenas, importao de HRP/VRP com parsing CSV, reamostragem e persistncia em `AntennaPatternPoint`, gerao de previews e exports diretos.
- `api/views.py`: REST JSON
  - CRUD de antenas/projetos/exportaes via JWT Bearer;
  - Clculo `compute_erp` e endpoints `/assistant/conversation` & `/assistant/message` que alimentam o front-end de chat.
- `__init__.py`: registra todos os blueprints no app.

#### 2.2.5. Servios (`app/services/`)

- `pattern_composer.py`: ncleo matemtico de composio dos arranjos.
  - `resample_pattern` / `resample_vertical`: reamostragem HRP (180180) e VRP (9090) preservando caractersticas do CSV.
  - `compose_horizontal_pattern`: calcula padro composto de painis horizontais somando contribuies complexas (posio em arco circular, espaamento mecnico, fase de excitao, ganho elementar).
  - `compose_vertical_pattern`: combina elementos verticais (pilha de antenas) usando tilt, espaamento e contagem.
  - `compute_erp`: integra padres compostos, aplica perdas e potncia para obter ERP (linear/dBw), mtricas auxiliares, valores exportveis (PAT/PRN). O helper `serialize_erp_payload` grava o resultado em `project.composition_meta`, mantendo dashboards e exports sincronizados com ajustes posteriores.
  - `export_pat` / `export_prn`: grava arquivos nos formatos especficos.
- `visuals.py`: gerao de previews (grficos Matplotlib) e mtricas para exibio no painel; salva imagens em `static/generated/previews/...` e harmoniza `project.composition_meta` com os clculos mais recentes.
- `exporters.py`: coordena exportaes (bundle PAT/PRN/PDF) e grava `ProjectExport`.
- `assistant.py`: integra com Google Generative AI (Gemini). Carga do `.env`, configurao do modelo `gemini-2.5-flash`, histrico `[system_prompt, greeting]+messages`, chamadas via `start_chat(...).send_message(...)`, persistindo entradas/sadas na base, consultando o ndice vetorial (`knowledge_base.py`) para fornecer contexto, registrando logs de depurao e interpretando marcaes `<action type="create_project">{...}</action>` para criar projetos automaticamente (incluindo estimativa de elementos quando o alvo de ganho  informado).
  - O mecanismo de aes permite que o AntennaExpert guie o usurio e execute tarefas (ex.: criao de projetos) emitindo `<action type="create_project">{...}</action>`; o backend interpreta o JSON, resolve a antena, estima `v_count`/`h_count` a partir do ganho desejado (`target_gain_dbi`) e salva o novo projeto, retornando o link direto ao usurio.
- `knowledge_base.py`: constri/consulta um ndice vetorial dos documentos (`docs/`) usando SentenceTransformers, armazenando embeddings em `vector_store/` e servindo trechos relevantes para enriquecer as respostas do assistente.
- `email.py`: envio de e-mails transacionais (confirmao, alertas admin).
- `pattern_parser.py`: leitura robusta de arquivos CSV/TXT (colunas Theta/E/Emax), fallback genrico.
- `metrics.py`: utilidades matemticas (HPBW, diretividade, ripple, SLL, converses dBlinear), reutilizadas por relatrios e composies.

#### 2.2.6. Templates (`app/templates/`)

- `base.html`: shell principal  inclui assets (`static/css/main.css`, `static/js/designer.js`, `forms.js`, `assistant.js`), menu lateral, topbar, footer.
- Diretrios `auth/`, `projects/`, `admin/`, `public/`, `emails/` contm os templates especficos:
  - `auth/*.html`: pginas de login/cadastro/reenviar.
  - `projects/dashboard.html`: lista projetos do usurio com aes.
  - `projects/detail.html`: exibe mtricas ERP, grficos e links de export.
  - `admin/*`: tabelas de antenas, formulrios de importao, data manager genrico.
  - `emails/*`: templates textuais HTML para confirmao e alertas.
  - `public/home.html` / `public/brand.html`: landing pages pblicas.

#### 2.2.7. Static (`app/static/`)

- `css/main.css`: tema escuro azul, layout responsivo, estilos para dashboards, formulrios, chat do assistente e grficos.
- `js/designer.js`: interaes do compositor ERP (AJAX para `/api/projects/<id>/patterns`, atualizao de grficos via canvas/DOM).
- `js/forms.js`: utilidades UI (ex.: toggle de senha, dilogos).
- `js/assistant.js`: lgica do painel Ajuda inteligente (fetch histrico/mensagens, estado de carregamento, exibio incremental, status de erro).
- `img/`: ativos grficos (logotipo EFTX).
- `generated/`: diretrio criado em runtime para previews de projetos/antenas.

---

## 3. Fluxos Principais

### 3.1. Importao de Padres
1. Admin faz upload (CSV/TXT) via `/admin/antennas/<id>/patterns`.
2. `pattern_parser.py` interpreta os dados, reamostra (1) e, antes de regravar, remove pontos antigos (`DELETE` at `AntennaPatternPoint`).
3. `replace_points` recria o conjunto de amostras, mantendo `metadata_json` com snapshot do arquivo e data de importao.

### 3.2. Composio e Exportao de Projetos
1. Usurio seleciona antena elementar, define parmetros verticais/horizontais.
2. `compute_erp` aplica `compose_vertical_pattern` + `compose_horizontal_pattern`, calcula ERP com perdas, gera mtricas.
3. `generate_project_previews` salva grficos e exibe estatsticas.
4. `generate_project_export` chama `export_pat`, `export_prn`, `ReportLab` (PDF) e registra `ProjectExport`.

### 3.3. Assistente Inteligente
1. Ao acessar Ajuda Inteligente, front chama `/api/assistant/conversation`  se no houver histrico, `get_or_create_conversation` grava a saudao inicial.
2. Mensagens subsequentes vo para `/api/assistant/message`, que monta o histrico com `system_prompt` e chama `GenerativeModel.start_chat(...).send_message()`.
3. Resposta e mensagem do usurio so persistidas; front exibe histrico completo.

### 3.4. Autenticao e Segurana
- Senhas com Argon2/Bcrypt; `password_needs_rehash` garante upgrade automtico.
- CSRF habilitado (Flask-WTF) e rate limits via Flask-Limiter.
- JWT opcional para APIs; tokens curtos com `Bearer` header.
- Confirmacao de e-mail com tokens temporrios (`itsdangerous`).

---

## 4. Migraes Alembic

- `20250930_000001_create_core_tables.py`: cria tabelas centrais (`users`, `antennas`, padres simples).
- `46986b249afd_.py` e `3e83237a9467_.py`: ajustes (ex.: `v_tilt_deg`, aumento de tamanho de `password_hash`).
- `730014782f4e_.py`: introduz tabelas `antenna_pattern_points`, `project_antennas`, normalizao de padres e limpeza de colunas antigas.
- `8b4e91acba2d_add_assistant_conversations.py`: adiciona suporte ao histrico do assistente (conversas/mensagens).

Cada migrao  encadeada; `flask db upgrade` aplica toda a sequncia.

---

## 5. Dependncias Externas e Convenes

- **Flask-Limiter**: proteo contra abuso de endpoints (limites configurveis via `RATE_LIMIT_*`).
- **ReportLab/pypdf**: gerao e mescla de PDFs com modelo institucional (`modelo.pdf`).
- **NumPy/Matplotlib**: clculos numricos, grficos polares/planos.
- **Google Generative AI**: integrao via `google-generativeai` com modelo `gemini-2.5-flash` e prompt personalizado.
- **python-dotenv**: carrega variveis sensveis a partir de `.env` local (obrigatrio para chaves e URLs).

---

## 6. Boas Prticas e Expanses Futuras

- **Testes**: meta de 70% cobertura nos servios crticos. Priorizar testes de reamostragem (361 pontos HRP), mtricas e exportaes.
- **Observabilidade**: adicionar logs estruturados (JSON) e monitoramento `/healthz` (latncia de SELECT, uptime, verso).
- **CI/CD**: pipelines para lint/testes; empacotar deploy Gunicorn + Nginx com arquivo `systemd` apontando para `.env` seguro.
- **IA Assistente**: evoluir com contexto adicional (dados do projeto/antenna) e ajustes dinmicos de prompt.

---

## 7. Concluso
f1
Este projeto combina uma arquitetura Flask modular com clculos especializados para RF, gerao de relatrios e suporte inteligente por IA. A organizao detalhada em modelos, servios e camadas de apresentao facilita manuteno e expanso. Este documento, aliado ao `proc.md`, deve ser mantido atualizado a cada alterao estrutural significativa para garantir rastreabilidade e alinhamento entre cdigo e operao.
- Use o comando `flask rebuild-knowledge --source docs` para indexar/atualizar os datasheets. Caso o modelo de embeddings exija autenticao, defina `HUGGINGFACEHUB_API_TOKEN` (ou equivalente) antes de rodar o comando.

\n---\n\n## 8. Atualizacoes Recentes\n\n- Painel admin/data modernizado: helpers _titleize, _truncate e _format_cell_value melhoram formatacao, adicionam contadores e evitam conflitos de nomes com metodos nativos do dict.\n- Exportadores PAT/PRN/PDF recebem parametro highlight para marcar o ponto de horizonte no VRP e usam _safe_float para persistir metricas sem NaN no PostgreSQL.\n- Ambiente virtual ajustado apos migracao: pyvenv.cfg aponta para C:\\Users\\iltom\\AppData\\Local\\Programs\\Python\\Python313 e foi criado wrapper local pip.cmd para delegar python -m pip dentro da venv, prevenindo uso acidental do pip global.\n- Cadastro de cabos adicionado: tabela `cabos`, formulario administrativo dedicado e selecao guiada no projeto (drop-down) alimentam os calculos de perdas sem depender de valores digitados manualmente.\n


## 9. Atualizacoes: Cabos, Antenas, Composicao Visual e Relatorios

- Cabos (atenuacao por curva):
  - Removido campo fixo `attenuation_db_per_100m`. Agora a perda do cabo usa a curva `attenuation_db_per_100m_curve` (JSON) com interpolacao linear por frequencia. Fallback mantem aproximacao anterior somente quando a curva nao existir.
  - Importador por datasheet (admin) com IA Gemini: extrai metadados do datasheet e pre-preenche o formulario. O JSON de curva pode ser revisado manualmente antes de salvar.

- Antenas (metadados + ganho por frequencia):
  - Novos campos em `Antenna`: `manufacturer` (padrao "EFTX Broadcast & Telecom"), `datasheet_path`, `gain_table` (JSON de ganho em dBd por MHz), `category` (TV, FM, Microondas, Telecom) e `thumbnail_path`.
  - Importador por datasheet (admin) com IA Gemini: extrai metadados gerais (nao le tabelas de diagrama). Tenta capturar a primeira imagem do PDF como thumbnail, salvando em `exports/uploads/antennas/thumbs/` e preenchendo `thumbnail_path`.
  - Portfolio publico reorganizado por categoria e exibindo thumbnail.

- Composicao visual (UX do projeto):
  - Modal "Configurar composicao (visual)" com ilustracoes SVG responsivas:
    - Vertical: retangulos vermelho claro empilhados, cota centro-a-centro com "v = X m" e seta de tilt partindo do centro do sistema.
    - Horizontal: anel do arranjo com rotulo de raio fisico `R = sN/(2)` e angulo em frente de cada elemento conforme a posicao `i*(360/N)+i*step`.
  - Os valores do modal refletem exatamente os inputs; ao aplicar, os campos do formulario recebem os valores.

- Exportacao e relatorio PDF:
  - As imagens de "Composicao Vertical" e "Composicao Horizontal" sao salvas por export em `exports/<project_id>/<timestamp>/` e inseridas no PDF.
  - Nome do PDF usa o nome do projeto (slug), em vez de um nome fixo.
  - Layout do PDF ajustado: titulos acima dos graficos (padroes HRP polar e VRP plano, e ilustracoes de composicao) e dimensoes ampliadas para melhor leitura.
  - Ganho estimado calibrado por frequencia: se a antena tiver `gain_table` (dBd por MHz), o ganho do arranjo e ajustado por `(dBi)` relativo ao ganho nominal, refletindo "Ganho calibrado" no relatorio e na tela de detalhes do projeto.

- Rotas e UI complementares:
  - `POST /admin/cables/parse-datasheet`: extrai dados do cabo e curva de atenuacao.
  - `POST /admin/antennas/parse-datasheet`: extrai metadados da antena e opcionalmente um thumbnail.
  - `GET /projects/<id>/asset/<export_id>/<name>`: serve imagens de composicao inline ou para download (`?download=1`).
  - Pagina publica `/` agora agrupa antenas por categoria e exibe thumbnails via `public.antenna_thumb` (servidor seguro de imagens do EXPORT_ROOT).

Notas:
- As integracoes com IA usam `GEMINI_API_KEY` e respeitam limites de conteudo. Caso nao haja texto extraivel no PDF, a extracao pode ser parcial.
- As figuras e PDFs sao criados sob `EXPORT_ROOT` e o servico garante permissoes de escrita adequadas para `www-data`.

## 10. Atualizacoes: Site institucional, integraes e consentimento

- Blueprint `public_site`: novas rotas `/`, `/produtos`, `/downloads`, `/contato`, `/politica-de-cookies` e `/privacidade`, servindo o site institucional com templates dedicados (`templates/public_site/*`) e assets remotos do tema WordPress espelhado. `url_for('public_site.*')` passa a ser o destino padro no cabealho.
- Descoberta de contedo: utilitrio `core/site_content.py` localiza automaticamente `/extx_site` ou `/eftx_site`, monta cards de produtos e agrupa PDFs de `DOCS_ROOT` (`/docs` por padro) para exibio e download. Sitemap (`/sitemap.xml`) e robots (`/robots.txt`) refletem as novas rotas pblicas.
- Consentimento de cookies: banner/modal em `home.html` usa `utils/cookies.py` (cookie assinado, SameSite=Lax, HttpOnly) e injeta o estado via `templating.py`; scripts analticos s carregam com consentimento (env `ANALYTICS_GTM_ID`).
- Segurana e SEO: `create_app` registra cabealhos CSP, X-Content-Type-Options, Referrer-Policy e Permissions-Policy; templates incluem metatags OpenGraph/Twitter e JSON-LD (Organization/Product).
- Integrao WhatsApp: blueprint `integrations_whatsapp` expe `/webhooks/whatsapp/inbound` e `/webhooks/whatsapp/status` com autenticao `X-Webhook-Token`, fallback institucional e chamada opcional ao Gemini 2.5 via `core/assistant_institutional.py` (feature flag `USE_GEMINI`).
- Configurao ampliada em `config.py`/`.env.example`: novas env vars (`SITE_CONTENT_ROOT`, `DOCS_ROOT`, `USE_GEMINI`, `GEMINI_INSTITUTIONAL_MODEL`, `INSTITUTIONAL_PERSONA`, `N8N_WEBHOOK_TOKEN`, `ANALYTICS_GTM_ID`, rate limits de WhatsApp, `CONTENT_SECURITY_POLICY`, `PREFER_SECURE_COOKIES`).

## 11. Formato visual do site EFTX (2025-10)

- **Identidade**: pginas pblicas (`app/templates/public_site/`) usam tipografia `Source Sans Pro` via CDN, esquema dark azul (`#041833`  `#0A4E8B`) com botes laranja (`#FF6A3D`) e alto contraste sobre fundo radial `#050f1f`.
- **Hero institucional**: bloco `hero--institutional` combina gradiente + overlay, texto principal  esquerda e vitrine de especialidades (`hero-card`) sobre anis animados (`hero-rings`). Barra inferior (`hero-strip`) lista segmentos atendidos.
- **Sees internas**: cada `section` possui cards translcidos com sombras profundas, grids responsivos (`solutions-grid`, `metrics-grid`, `simulation-wrapper`) e botes `btn/btn-primary` ajustados ao tema escuro.
- **Produtos destacados**: cards (`product-card`) exibem miniaturas em 160px; thumbnails so obtidas de `IMA/` pelo helper `core.site_content.load_products_from_site`, priorizando arquivos com mesmo nome do PDF e aceitando extenses `.png/.jpg/.jpeg/.webp/.svg`. Fallback mantido para imagens padro quando nada  encontrado.
- **Navegao por cliente**: item "rea do Cliente" aparece no menu superior replicado do site original; direciona usurios autenticados ao dashboard (`/projects/dashboard`) e no autenticados ao login (`/auth/login`). Rodap institucional foi simplificado para remover crditos externos e reforar os canais EFTX com cones brancos contrastantes.
- **Galeria institucional**: `gallery-grid` mostra imagens vindas de `IMA/` filtradas por keywords (fbrica, montagem, infra). Quando no h correspondncias, a seo permanece oculta.
- **Downloads/CTA/Contato**: blocos `downloads-list`, `cta-contact` e `contact-panels` trazem cartes translcidos, aes diretas (WhatsApp/mailto) e mapa em `iframe`, seguindo o mesmo tratamento de cor.
- **CSS dedicado**: todos os estilos vivem em `app/static/css/main.css` (tema dark do app autenticado). O portal pblico utiliza os CSS/JS remotos do tema WordPress original, carregados via `base.html` quando o blueprint `public_site` est ativo.

## 12. Atualizacoes recentes (2025-10)

- Home pblica revertida  verso institucional original (layout WordPress espelhado), com includes remotos e contexto padro (`hero_slides`, downloads, company_info). Arquivos restabelecidos: `app/templates/public_site/home.html`, `app/templates/base.html` (ramificao para blueprint `public_site`) e `app/blueprints/public_site/views.py` (contexto clssico sem hero dinmico). O favicon (`/site-assets/IMA/favicon.png`)  carregado globalmente via `<link rel="icon">` e os ttulos das pginas pblicas agora usam EFTX Broadcast & Telecom.
- Removido o script local `app/static/js/public_site.js` e referncias s animaes de hero; pgina volta a depender dos assets hospedados em `eftx.com.br`.
- Ambiente padro: venv temporria `.venv` foi removida; utilize sempre `source /opt/py313/bin/activate` antes de instalar dependncias ou rodar comandos Python no projeto.
- Deploy/servio: `systemctl reload eftx` executado ao final para garantir que o Gunicorn sirva a verso revertida da home.


## Atualizações recentes (2025-10-11)

- Adicionada rota `/aplicativos-rf/catalogo` ao blueprint `aplicativos_rf`, exibindo catálogo filtrável de calculadoras com sidebar e grid Bootstrap.
- Criado `app/blueprints/aplicativos_rf/catalog_data.py` centralizando as categorias e itens listados na página para facilitar manutenção.
- Template `templates/aplicativos_rf/catalogo.html` implementa layout `col-md-3` + `col-md-9`, cards com `stretched-link`, botões “Get the App” e footer com quatro colunas de links técnicos.
- Script `static/aplicativos_rf/js/catalog.js` adiciona busca em tempo real, destaque do filtro ativo e scroll suave sem dependências externas adicionais.
- As calculadoras continuam locais: links permanecem em `#` aguardando implementação específica de cada ferramenta.
