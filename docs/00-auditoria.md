# Auditoria Inicial - EFTX Antenna Pattern

## Resumo do repositorio
- `app/`: aplicacao Flask com blueprints (`auth`, `admin`, `projects`, `api`, `public`), formularios WTForms, servicos numericos e utilitarios.
- `app/services/`: implementa parser de diagramas, composicao ERP, metricas, gestao de exportacoes (PDF/PAT/PRN) e previews com Matplotlib.
- `migrations/`: setup Alembic com 3 revisoes (`20250930_000001`, `46986b249afd`, `3e83237a9467`).
- `exports/`: raiz configurada para guardar arquivos gerados por projeto.
- `docs/`: apenas `SETUP.md`; nao ha guia funcional nem changelog.
- `.venv/`: ambiente local Python 3.13 (dependencias instaladas).
- `prompt.txt`: instrucoes mestre recebidas (mantido no repo).

## Ambiente e dependencias
- Python local 3.12.4 (global) e virtualenv `.venv` com Python 3.13.5 (`.venv/Scripts/python`).
- `pip-freeze.txt` capturou dependencias atuais (Flask 3.1.2, SQLAlchemy 2.0.43, Flask-Limiter 3.13, Matplotlib 3.10.6, ReportLab 4.4.4 etc.).
- `pytest` nao esta instalado: `python -m pytest -q` falha com "No module named pytest".
- `flask db current` (rodando com `.venv`) retorna revisao `3e83237a9467` e loga alerta de Flask-Limiter usando storage em memoria.
- `.env` contem credenciais reais (senha de app Gmail)  forte indicio de segredo versionado.

## Backend atual
- `app/__init__.py` cria app, carrega config por nome e registra extensoes (`SQLAlchemy`, `Migrate`, `LoginManager`, `JWTManager`, `Limiter`, `Mail`, `CSRF`). Nao ha logger estruturado nem handlers de erro globais.
- Blueprints registrados: `public` (landing + brand), `auth` (registro/login + JWT), `projects` (CRUD web + downloads), `admin` (painel, importacao de diagramas, gestor de dados), `api` (endpoints REST). Nao existe blueprint `export` nem `health` como pedido.
- Rate limiting via `Flask-Limiter` aplicado nas rotas de autenticacao e API.
- `auth` mistura fluxo web (Flask-Login) com emissao de JWT (`/auth/token`, `/auth/token/refresh`). Validacao de CPF/CNPJ apenas via regex; nao ha confirmacao de email assincrona, mas tokens `itsdangerous` sao gerados.
- Falta RBAC nas rotas de API alem do checador `_require_admin` manual; nao ha decorator reutilizavel.
- Nao existem esquemas Marshmallow/Pydantic; pasta `app/schemas` vazia. Validacoes de API sao feitas com helpers que abortam manualmente.
- Nao ha servico de seguranca central para senhas (usa bcrypt + rehash Argon2 apenas para legado). Nao existe politica de refresh token alem do endpoint basico.

## Modelos e migracoes
- `User` inclui campos de endereco, cpf/cnpj, flags `email_confirmed`, `cnpj_verified`, `role`. Sem campos de verificacao por token ou auditoria de login.
- `Antenna` e `AntennaPattern` guardam series de angulos/amplitudes em JSONB (1 registro por tipo HRP/VRP). Nao ha suporte para multiplos conjuntos por antena ou versionamento.
- `Project` referencia uma unica antena (`antenna_id`), guarda parametros verticais/horizontais, perdas e metadados genericos. Requisito do prompt pedia combinacao de multiplas antenas e torre/cabo por elemento  nao atendido.
- `ProjectExport` guarda caminhos relativos de PAT/PRN/PDF e metadados ERP. Nao ha estados de processamento nem filas de export.
- Ausentes: tabelas `project_antennas`, `diagrams` detalhados, historico de autenticacao, auditoria de acessos.

## Servicos numericos e exportacao
- `pattern_parser.py` importa CSV/TXT, detecta colunas de angulo/amplitude, normaliza e amostra.
- `pattern_composer.py` reamostra HRP/VRP, calcula array factor horizontal/vertical, soma perdas, gera ERP (angles, ERP em W/dBW) e escreve PAT/PRN simples. Exportador PAT ainda usa cabecalho `# EFTX PAT export`, diferente do formato especificado (na parte "composto" o script moderno `exporters.py` gera PAT expandido, mas a funcao `export_pat` antiga continuou no arquivo).
- `metrics.py` implementa HPBW, ripple, SLL, front/back, diretividade 2D, ganho estimado.
- `exporters.py` gera pasta por export, cria PAT composto (header `'desc', gain, num_elems` + faixas 0..359 e tail vertical 0..-90), PRN com atenuacao positiva, PDF com ReportLab + Matplotlib (tabelas paginadas) e junta via PyPDF. Usa `ProjectExport` para persistir caminhos.
- `visuals.py` gera imagens PNG para previews (antena e projeto) em `static/generated/...` e calcula metricas resumidas.

## Frontend atual
- Layout `app/templates/base.html` monta shell autenticado com sidebar fixa. Estilo fornece tema escuro custom em `app/static/css/main.css` (sem Tailwind/Bootstrap). Nao ha componentes responsivos prontos; media queries limitados.
- Templates abrangem `admin`, `auth`, `projects`, `public`. Formularios WTForms renderizados manualmente; mascaras de CPF/CNPJ/telefone inexistentes (apenas placeholders).
- `designer.js` fornece painel interativo (canvas 2D) para visualizar HRP/VRP e ERP em tabelas. Atualiza previa via fetch `/api/projects/<id>/patterns` com sliders.
- Falta menu "Configuracoes" e tratamento de acessibilidade (sem aria/labels explicitos). PDF/PAT/PRN downloads presentes em dashboard/detalhe de projeto.

## Rotas e APIs
- Web: `/`, `/brand`, `/auth/*`, `/projects/*`, `/admin/*` incluindo gestor de dados generico (`/admin/data/<model>`). Nao ha rota `/health`.
- API JWT: `/api/antennas` (CRUD completo, mas sem paginacao/filtros), `/api/projects` (CRUD, export, calculo ERP inline). Nao existe `/export/pdf|pat|prn` dedicado; export acontece via `/projects/<id>/export`.
- Falta separacao clara entre rotas de admin e usuario na API (depende do `current_user.role`). Nao ha validacao de entrada estruturada nem codigos de erro padronizados.

## Conformidade vs prompt mestre
- Blueprints esperados `export` e `health` ausentes; `services/` ja consolida calculos, porem falta modularizacao por dominio (`antennas`, `projects`, `export`).
- Autenticacao: fluxo basico presente, mas faltam verificacao de email via token no API, reset de senha, expressoes de perfil `master`. Nao ha JWT refresh guardado ou revogacao.
- Modelagem nao cobre relacionamento N:N de projetos com antenas/elementos. Metrics exigidas (HPBW, diretividade, ripple, F/B, SLL) existem mas nao expostas na UI de forma completa.
- Exportacoes: implementacao atual gera PAT/PRN/PDF mas nao garante todos requisitos (PAT Aba 1, cabecalhos customizados, bundle). Precisamos validar formatos e alinhar com especificacoes do prompt.
- Frontend: tema custom fora dos frameworks Tailwind/Bootstrap solicitados; tabelas nao possuem paginacao real; responsividade limitada; falta mascaras e validacoes client-side.
- Observabilidade: sem configuracao de logger estruturado, sem Sentry/healthcheck, sem scripts de backup.
- Testes: inexistentes; nenhuma cobertura para parsers, metricas ou rotas.
- Configuracao: `.env` versionado com segredos; `config.py` nao separa logging, nem toggles de modo producao. Nao ha `.env.example` atualizado com novos campos (JWT secret, e-mail confirm tokens, admin recipients etc.).

## Riscos e pontos de atencao
- Segredos sensiveis commited (`MAIL_PASSWORD`). Necessario revogar.
- Ausencia de validacao robusta nas APIs pode gerar erros silenciosos (`abort` com mensagens genericas em portugues).
- Exportacoes gravam em `exports/<project>/<timestamp>` local; falta limpeza/retencao, e downloads confiam em `Path.resolve` sem scanning adicional.
- Falta de testes dificulta evolucao dos calculos numericos (risco de regressao).
- Sem mecanismos de monitoramento/healthcheck para deploy.
- Dependencias com versoes recentes (Flask 3.1) exigem revisao da compatibilidade com extensoes.

## Quick wins identificados
- Remover credenciais reais de `.env` e reforcar `.env.example`.
- Configurar logger basico + handler padrao de erros JSON.
- Adicionar blueprint `/health` simples usando `db.session.execute('SELECT 1')`.
- Implementar schemas Marshmallow para entradas principais e habilitar validacao/paginacao em `/api/*`.
- Integrar Tailwind ou Bootstrap rapidamente no layout base e ajustar tabelas responsivas.
- Adicionar `pytest`, escrever suites minimas para `pattern_parser`, `metrics`, `exporters` e endpoints API.
- Configurar storage persistente para rate limiting (Redis) via configuracao.

## Perguntas em aberto
1. Como sera feito o upload de diagramas: apenas CSV/TXT ou tambem formatos proprietarios? Ha exemplos de PAT/PRN oficiais para validacao?
2. Precisamos armazenar multiplas antenas em um mesmo projeto (stack) ou apenas uma base + parametros? Prompt indica composicao automatica multi-elementos.
3. Qual estrategia para envio de e-mails em producao (SMTP externo/SendGrid)? Ha limites de volume?
4. Existe requisito de auditoria/logs de acesso dos administradores e usuarios?
5. Devemos suportar internacionalizacao (UI PT-BR vs EN)?

## Plano incremental inicial (proposta)
- **M1 - Fundacao & dados**: normalizar configs (`.env.example`, secrets), revisar modelos (criar tabelas faltantes `project_antennas`, `diagrams_raw`), ajustar migrations e seeds admin/antenas demo.
- **M2 - Calculos & servicos**: consolidar `services/` em modulos por dominio, reforcar parsers, array factor, metricas; expor resultados em endpoints estruturados.
- **M3 - Exportacoes**: alinhar geracao PAT/PRN/PDF aos formatos do prompt, implementar fila/registro `ExportJob`, validar downloads e limpeza.
- **M4 - UX e seguranca**: migrar frontend para Tailwind/Bootstrap, aplicar mascaras e validacao client-side, RBAC completo, blueprint `/export` e `/health`, logs estruturados, melhoria JWT.
- **M5 - Testes e observabilidade**: adicionar testes unitarios/integracao (pytest + coverage), CI basica, healthchecks, documentacao README/CHANGELOG atualizados.

