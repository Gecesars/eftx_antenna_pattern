# Plano Incremental EFTX Antenna Pattern

## M0 - Saneamento e Fundacoes
- Remover segredos versionados, reforcar `.env.example` e alinhar requisitos basicos (requirements/pyproject).
- Ajustar configuracoes do SQLAlchemy (pool, overflow) e garantir documentacao base.

## M1 - Modelo de Dados
- Introduzir tabela `project_antennas` (N para N) com campos de posicao, fase, espacamento e amplitude.
- Normalizar diagramas em tabelas dedicadas (`diagrams`, `diagram_points`) e migrar dados existentes.
- Atualizar seeds e formularios/admin para refletir o novo modelo.

## M2 - Blueprints e Seguranca
- Registrar blueprints `export` e `health`, criando `/healthz` com teste de banco e versao.
- Revisar autorizacao (admin_required/JWT claims) e aplicar validacao estruturada de entrada.
- Centralizar logs estruturados e configuracao de rate limit via ambiente.

## M3 - Servicos de Calculo e Export
- Consolidar servicos de parsing/composer para suportar multi-antena e reamostragem padrao.
- Padronizar export PAT/PRN/PDF conforme regras PROSS (cabecalhos, intervalos, atenuacao positiva, tabelas paginadas).
- Armazenar historico em `ExportJob` com metadados e validar downloads/bundles.

## M4 - Frontend Responsivo
- Adotar Tailwind ou Bootstrap via CDN, aplicando tema escuro com destaque azul EFTX.
- Modernizar formularios (mascaras, feedback inline) e tabelas (paginacao, filtros, cards em mobile).
- Atualizar paginas de dashboard, antenas, projetos e admin com previews e a11y basica.

## M5 - Testes e Qualidade
- Instalar e configurar pytest + pytest-cov; criar suites para parsers, metricas, export e rotas chave.
- Adicionar toolchain (`black`, `isort`, `flake8`, `mypy`, `bandit`) e opcional pre-commit.
- Configurar pipeline/CI local (scripts) e metas de cobertura para servicos numericos.

## M6 - Observabilidade e Deploy
- Implementar logging em JSON, tracing simples e integracao opcional com Sentry.
- Criar Dockerfile + docker-compose para dev/local, scripts de backup e guia de deploy (gunicorn + nginx).
- Monitorar tarefas longas de export com filas/futuros hooks.

## M7 - Documentacao e Mudancas Futuras
- Expandir docs em `docs/` (decisoes, guias API, playbooks de suporte).
- Manter CHANGELOG atualizado a cada iteracao, descrevendo impactos tecnicos e de produto.
- Definir backlog adicional (ex: importadores extras, notificacoes) conforme feedback dos usuarios.
