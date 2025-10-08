# EFTX Antenna Pattern – Documentação Completa

## 1. Panorama Geral

EFTX Antenna Pattern é uma plataforma web escrita em Flask 3 que combina composição de diagramas de antenas, gestão de projetos de broadcast/telecom, exportação de relatórios técnicos e um portal institucional para prospecção. O repositório inclui o core aplicativo (`app/`), migrações Alembic, ativos estáticos, templates Jinja2 e integrações com IA (Gemini) e WhatsApp (webhooks n8n).

**HEAD atual do repositório:** `4952f76c37fea2f95dd660c3074a52a66567acc0`

## 2. Estrutura de diretórios

```
.
├── app/                      # Pacote Flask principal
│   ├── blueprints/           # Módulos de rotas (auth, admin, projects, api, public, public_site, integrations_whatsapp)
│   ├── core/                 # Utilitários de conteúdo/site (PDFs, imagens, IA institucional)
│   ├── static/               # CSS, JS, imagens e libs (Font Awesome copiada do WordPress)
│   ├── templates/            # Jinja2 (base, áreas autenticadas e site público)
│   ├── utils/                # Helpers (cookies, templating, security, calculations)
│   ├── config.py             # Classes de configuração e variáveis de ambiente
│   ├── extensions.py         # Instancia extensões (db, migrate, login, limiter, csrf, mail, jwt)
│   ├── models.py             # Modelos SQLAlchemy (users, antennas, patterns, projects, etc.)
│   └── services/             # Lógica de negócios (exporters, assistant IA, pattern composer)
├── docs/                     # PDFs institucionais usados na vitrine pública
├── migrations/               # Scripts Alembic (histórico do schema)
├── alembic.ini               # Config Alembic
├── autoapp.py/run.py/wsgi.py # Entrypoints
├── deploy.sh                 # Script helper de deploy systemd/gunicorn
├── pip-freeze.txt            # Dependências
├── proc.md / descricao.md    # Documentos de processo e arquitetura
└── eftx_app.md               # (Este documento)
```

### Conteúdo espelhado do site institucional

O diretório `/eftx_site/` (fora do repositório) armazena o dump do WordPress original:

- `content/pages/` – HTML das páginas e notícias (`index.html?page_id=...`, `index.html?noticia=...`).
- `content/docs/` – PDFs (datasheets, catálogos) replicados e também copiados para `docs/` dentro do app.
- `content/images/` – Imagens (`wp-content/uploads/...`) usadas como thumbnails no portal público.
- `content/video/` – Vídeos MP4 referenciáveis.
- `content/other/` – Assets (CSS, JS, fontes, slider) do tema WordPress.
- `dados_baixados.json` – JSON com o mapa completo da captura.

A fábrica `discover_site_root()` aponta para esse diretório para consumir imagens/ativos.

## 3. Inicialização do aplicativo

1. `autoapp.py`/`run.py`/`wsgi.py` chamam `app.create_app()` com o ambiente desejado (`development`, `production`, etc.).
2. `create_app` carrega variáveis via `.env`, aplica a configuração (`config.py`), registra extensões (`extensions.py`), blueprints (`blueprints/__init__.py`), context processors (`utils/templating.py`) e CLI customizada (`cli.py`).
3. Em produção, o systemd service (vide `deploy.sh`) roda Gunicorn (`run:app`) com 3 workers, aplica migrações (`flask db upgrade`) e monta diretórios temporários / caches (`/opt/tmp`, `/opt/hf-cache`).

## 4. Blueprints e responsabilidades

| Blueprint | Prefixo | Responsabilidades | Dependências |
|-----------|---------|------------------|--------------|
| `auth`    | `/auth` | Registro, login, confirmação de e-mail, JWT (`/token`, `/token/refresh`) | Flask-Login, Flask-JWT-Extended, Flask-Limiter, envio de e-mail |
| `admin`   | `/admin`| Dashboard admin, CRUD de antenas/cabos, parsers de datasheet, uploads | Login/role check, CSRF, SQLAlchemy |
| `projects`| `/projects` | Gestão de projetos, composição HRP/VRP, exportação PAT/PRN/PDF, downloads de arquivos e bundles | Login obrigatório, services `pattern_composer`, `exporters`, `visuals` |
| `api`     | `/api`  | Endpoints JSON (antenas, projetos, assistente IA) | JWT, limiter, services de IA/padrões |
| `public`  | `/catalogo` | Catálogo legado de antenas para usuários autenticados | SQLAlchemy |
| `public_site` | `/` | Site institucional completo (home, produtos, downloads, contato, políticas) | Conteúdo de `/eftx_site` + `docs/`, utilitários `core/site_content` |
| `integrations_whatsapp` | `/webhooks/whatsapp/...` | Webhooks inbound/status n8n + fallback/Gemini | CSRF-exempt, limiter, `core/assistant_institutional` |

## 5. Extensões e utilitários

- **Banco**: SQLAlchemy + Alembic (PostgreSQL). Migrações em `migrations/`.
- **Autenticação**: Flask-Login, JWT (`flask_jwt_extended`), modelo `User` com roles e confirmações.
- **Segurança**: CSRF global, rate limiting (`Flask-Limiter`), cabeçalhos CSP/X-Content-Type/Permissions Policy via `register_security_headers`.
- **Cookies LGPD**: `utils/cookies.py` (cookie assinado com consentimento por categoria, storage em HttpOnly + SameSite Lax).
- **Templates**: `utils/templating.register_template_globals` expõe branding, consentimento e dados corporativos (phone/email/endereço/mapa/redes) definidos em `.env`.
- **Conteúdo institucional** (`core/site_content.py`):
  - `load_products_from_site` lê `docs/*.pdf`, gera cards com slug, título amigável, categoria, descrição e URL de datasheet.
  - `_match_thumbnail` procura imagens correlatas em `/eftx_site/content/images/...` (matching slug/substrings).
  - `list_pdfs_from_docs` compõe tabela de downloads com tamanho/mtime.

## 6. Portal institucional (Blueprint `public_site`)

### Layout

- **Cabeçalho** (em `base.html` quando blueprint = `public_site`):
  - Faixa superior com telefone, e-mail, WhatsApp e ícones Font Awesome para redes (`COMPANY_*`).
  - Menu principal com âncoras “Empresa”, “Serviços”, “Produtos”, “Downloads”, “Notícias”, “Contato” e CTA “Área restrita”.
- **Home (`templates/public_site/home.html`)**: markup espelhado do WordPress original, incluindo slider (`wowslider`), boxes de produtos/serviços/contato e cards institucionais. Usa diretamente os assets hospedados em `eftx.com.br` e publica títulos/tags configurados em `public_site.views` (padrão “EFTX Broadcast & Telecom”).
- **Produtos (`public_site/products`)**: grid com thumbnails/datasheet linkado, busca client-side baseada em JS inline (ou fallback simples caso ausente).
- **Downloads**: tabela com nome, tamanho, data e botão.
- **Contato**: formulário mailto, cartões com canais e endereço.
- **Políticas**: páginas estáticas (cookies e privacidade) alinhadas à LGPD.
- **Banner de cookies**: formulário de preferências com armazenamento assinado (`set_consent`).

### Assets incorporados

- `app/static/img/eftx-logo.png` – logo oficial (copiado de `/eftx_site`).
- `app/static/vendor/fontawesome/` – CSS e webfonts importados do tema WP.
- Assets remotos do tema institucional (CSS/JS) são carregados via `base.html` quando o blueprint `public_site` está ativo; os arquivos locais em `app/static/css/main.css` seguem responsáveis pelo shell autenticado.

## 7. Funcionalidades do core

- **Projetos de antena**: CRUD com cálculos (pattern composer), visualização HRP/VRP, exportação PAT/PRN/PDF, métricas calibradas e preview de composição.
- **Integração IA**:
  - Assistente interno (`/api/assistant/...`) com histórico e prompts customizados.
  - Webhook WhatsApp (`/webhooks/whatsapp/inbound`) que agrega FAQ, produtos e downloads para responder via Gemini 2.5 Pro (flag `USE_GEMINI`).
- **Autenticação**: fluxo de registro, confirmação por e-mail, reenvio, login, JWT tokens e refresh.
- **Administração**: catálogos de antenas/cabos, upload de datasheets, extração com IA (parser), preview de thumbnails.

## 8. Configuração (.env)

Variáveis importantes (ver `.env.example` e `.env`):

- Banco: `DATABASE_URL`
- Paths: `SITE_CONTENT_ROOT`, `DOCS_ROOT`, `EXPORT_ROOT`
- IA: `USE_GEMINI`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_INSTITUTIONAL_MODEL`, `INSTITUTIONAL_PERSONA`
- WhatsApp: `N8N_WEBHOOK_TOKEN`, `RATE_LIMIT_WHATSAPP`, `RATE_LIMIT_WHATSAPP_STATUS`
- Analytics: `ANALYTICS_GTM_ID`
- Cookies: `PREFER_SECURE_COOKIES`
- Conteúdo institucional: `COMPANY_NAME`, `COMPANY_PHONE`, `COMPANY_EMAIL`, `COMPANY_ADDRESS`, `COMPANY_WHATSAPP`, `COMPANY_INSTAGRAM`, `COMPANY_FACEBOOK`, `COMPANY_LINKEDIN`, `COMPANY_MAP_EMBED`

## 9. Deploy (VPS)

- Instalar dependências (Python 3.13, Redis opcional para limiter, PostgreSQL).
- Aplicar script `deploy.sh` ou criar unit systemd (ver template no script):
  - Usa `/opt/py313` como venv.
  - `EnvironmentFile=/eftx_app/eftx_antenna_pattern/.env`.
  - `ExecStartPre=flask db upgrade` e `ExecStart=gunicorn run:app --workers 3 --timeout 180`.
  - `TMPDIR=/opt/tmp`, `MPLCONFIGDIR=/opt/tmp/mpl`.
- Após atualizações: `sudo systemctl restart eftx`, verificar `journalctl -u eftx -f`.
- Servido em `http://<host>:PORT` (default 8000).

## 10. Changelog (ativo até HEAD 4952f76)

### Institucional / Conteúdo
- Replicado o site institucional dentro do app: cabeçalho, menu, hero, galerias, seções de serviços/segmentos, bloco de notícias e painel de contato com mapa.
- Integração com `/eftx_site` para carregar imagens, vídeos e materiais WordPress; JSON `dados_baixados.json` mapeia os ativos.
- Produtos em destaque agora são montados a partir dos PDFs em `docs/`, com miniaturas correspondentes (matching por slug) e links de download direto (`/downloads/arquivo/<pdf>`).
- Font Awesome (CSS + webfonts) copiados do tema original; ícones incluídos no cabeçalho/contatos.

### Aplicativo
- `core/site_content.py` reescrito para gerar cards de produtos usando os PDFs locais e thumbnails do site espelhado.
- `public_site/views.py` injeta dados corporativos (`COMPANY_*`), links sociais, slides com imagens e metadados para SEO (OpenGraph/Twitter).
- `base.html` agora detecta o blueprint para alternar entre layout institucional e shell autenticada.
- Banner de cookies com preferências assinado (HttpOnly, SameSite=Lax); consentimento controla carregamento de scripts analíticos.
- Variáveis de ambiente novas (`COMPANY_*`, `DOCS_ROOT`, rate limits Whatsapp) adicionadas a `.env` e `.env.example`.

### Integrações
- Blueprint `integrations_whatsapp` cria webhooks `/webhooks/whatsapp/inbound` e `/webhooks/whatsapp/status`, validando `X-Webhook-Token` e respondendo com Gemini 2.5 Pro (fallback estático se indisponível).
- `core/assistant_institutional.py` monta prompt institucional e retorna sugestões de links.

### Segurança & SEO
- `register_security_headers` aplica CSP, X-Content-Type-Options, Referrer-Policy e Permissions-Policy globalmente.
- `robots.txt`/`sitemap.xml` servidos pelo blueprint público.
- Fonte principal alterada para `Source Sans Pro` (carregada via Google Fonts); design mobile-first e responsivo.

### Deploy / Ambientes
- Template de service systemd (no script) instala Redis opcional, configura `/opt/tmp`, aplica migrações e sobe Gunicorn.
- `.env` de produção inclui paths, chaves e credenciais; recomenda-se migrar `Flask-Limiter` para backend Redis (`RATELIMIT_STORAGE_URL`).

### Melhorias anteriores preservadas
- Painel admin com parsing de datasheets, exportação ERP/HRP/VRP, IA AntennaExpert integrada, logging, rate limiting.
- `docs/` mantém os datasheets atualizados (total de 29 PDF). Galeria de dados replicada em `/eftx_site/content/images`.

## 11. Instruções de Operação Rápida

1. **Configuração local**
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env  # ajustar variáveis (DB, SITE_CONTENT_ROOT, COMPANY_*)
   flask db upgrade
   flask run
   ```
2. **Atualizar conteúdo institucional**
   - Colocar novos PDFs em `docs/` (nomes amigáveis ajudam no slug).
   - Copiar imagens correspondentes para `/eftx_site/content/images/...` (o matcher procura por slug/underscore).
   - Reiniciar o serviço ou recarregar para refletir na home.
3. **Deploy**
   - `git pull` no servidor, `sudo systemctl restart eftx`.
   - Verificar `journalctl -u eftx -f` e `curl -I http://localhost:PORT`.
4. **Webhooks WhatsApp**
   - Configurar `N8N_WEBHOOK_TOKEN`, `USE_GEMINI`, `GEMINI_API_KEY`.
   - Endpoint: `POST https://<host>/webhooks/whatsapp/inbound` com header `X-Webhook-Token`.
5. **Consentimento de cookies**
   - Preferências ficam no cookie assinado `eftx_cookie_consent`. O banner aparece até que o usuário salve uma opção.

---

**Referências úteis**
- `descricao.md` – Documentação histórica (migrações, modelos, serviços).
- `proc.md` – Processos operacionais e SOP.
- `deploy.sh` – Script de provisionamento systemd/gunicorn usado na VPS oficial.
- `/eftx_site/dados_baixados.json` – Mapa completo do site WordPress, útil para localizar imagens específicas.
