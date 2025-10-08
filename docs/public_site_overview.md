# Visão Geral do Site Institucional EFTX

Este documento consolida o conteúdo disponível no blueprint `public_site` para servir como fonte da *knowledge base* do assistente técnico. Inclui estrutura das páginas, mensagens institucionais, canais de contato e referências aos materiais utilizados no portal.

## Identidade e Mensagem Principal
- Marca apresentada como **EFTX Telecom** (ou nome definido via `COMPANY_NAME`).
- Slogan no herói da home: “Cobertura perfeita para quem transmite confiança”.
- Tagline complementar: “Engenharia, fabricação e serviços 360º”.
- Setores destacados na faixa inicial: Broadcast, Telecom, Energia, Defesa & Segurança, IoT & Smart Cities.
- Chamada à ação imediata: links “Explorar soluções” (`/produtos`) e “Planejar projeto” (`/contato`).

## Estrutura da Home (`/`)
1. **Hero institucional** — destaque para cobertura nacional, CTA duplo e visual animado com cartões sobre especialidades (redes FM, arrays UHF/VHF, microlinks licenciados).
2. **Introdução** — texto sobre 26 anos de atuação com integração engenharia ↔ manufatura ↔ campo.
3. **Indicadores** — métricas exibidas: 700+ sistemas instalados, 26 anos de atuação, presença técnica em 12 estados.
4. **Galeria institucional** — quando houver múltiplos *hero slides*, lista imagens de fábrica, campo de provas e integrações.
5. **Soluções integradas** — quatro pilares:
   - Planejamento e engenharia (estudos de cobertura, definição de arrays, memóriais técnicos).
   - Fabricação e supply (linha própria, rastreabilidade de lotes).
   - Integração em campo (montagem, VSWR, medições ERP, laudos).
   - Gestão e suporte (monitoramento, manutenção programada, estoque de contingência).
6. **Simulação & Aplicação** — bloco interativo com três cenários (Broadcast FM, TV Digital UHF, Telecom Carrier). Mostra métricas (ERP, HPBW, disponibilidade, margem de desvanecimento) e CTA para solicitar estudo dedicado.
7. **Produtos em destaque** — os seis primeiros PDFs em `docs/` geram cards com categoria, descrição, link de datasheet e CTA “Ver detalhes/solicitar proposta”.
8. **Processo de entrega** — etapas sequenciais: Diagnóstico → Projeto executivo → Integração & testes → Operação assistida.
9. **Downloads em evidência** — quatro documentos mais recentes, com link direto para PDF.
10. **Assistente técnico EFTX** — widget de chat (seção dedicada). Integração automática com o histórico do usuário autenticado via `/api/assistant/*`, com fallback institucional quando não autenticado.
11. **Call-to-action** — convite “Vamos desenhar o próximo sistema juntos?” com botões para contato e WhatsApp comercial.
12. **Bloco de contato** — lista telefone, e-mail, endereço, redes sociais e iframe de mapa (`COMPANY_MAP_EMBED`).
13. **Banner de cookies** — opções aceitar/rejeitar/personalizar; modal permite granularidade (analytics, funcionais, marketing). Consentimento salvo via `/cookies/consent`.

## Páginas Auxiliares
- **Catálogo (`/produtos`)** — grid completo de produtos extraídos dos PDFs em `docs/`. Busca textual (nome, categoria) e contagem dinâmica de resultados. Cada card oferece download do datasheet e link para contato.
- **Downloads (`/downloads`)** — tabela responsiva com nome do arquivo, tamanho, data de atualização e botão para baixa imediata.
- **Contato (`/contato`)** — formulário mailto (`contato@eftx.com.br`), canais diretos (WhatsApp institucional, suporte engenharia@eftx.com.br), horário comercial (segunda a sexta, 9h–18h BRT) e endereço físico.
- **Políticas (`/politica-de-cookies` e `/privacidade`)** — textos institucionais sobre LGPD e consentimento.

## Conteúdo Dinâmico e Fontes
- Produtos e downloads derivam dos PDFs presentes em `docs/`. Cada arquivo gera slug, categoria e descrição automática.
- Thumbnails e recursos multimídia são buscados em `SITE_CONTENT_ROOT` (`/eftx_site` ou `/extx_site` espelhado do WordPress). Fallback para diretório local `IMA/` quando disponível.
- Canais de contato, redes sociais e embed do mapa são configuráveis via variáveis de ambiente:
  - `COMPANY_PHONE`, `COMPANY_EMAIL`, `COMPANY_WHATSAPP`.
  - `COMPANY_INSTAGRAM`, `COMPANY_FACEBOOK`, `COMPANY_LINKEDIN`.
  - `COMPANY_ADDRESS`, `COMPANY_MAP_EMBED`.
- Analytics somente carregado mediante consentimento (`ANALYTICS_GTM_ID`).

## Assistente Técnico
- Widget da home consulta `/api/assistant/conversation` e `/api/assistant/message` para usuários autenticados, preservando histórico, criação de projetos e acesso à *knowledge base* (via embeddings em `docs/`).
- Visitantes anônimos recebem respostas através de `/assistente/ask`, que utiliza `answer_with_gemini` combinando produtos, downloads e FAQ institucional.
- Saudações e comportamento são regidos por `ASSISTANT_GREETING`, `ASSISTANT_SYSTEM_PROMPT`, `ASSISTANT_HISTORY_LIMIT` e chaves Gemini (`GEMINI_API_KEY`, `GEMINI_MODEL`).
- Para reindexar conteúdo no vetor de conhecimento: `flask rebuild-knowledge --source docs` (ou apontando explicitamente para este arquivo).

## Canais de Contato (valores padrão)
- Telefones: `(19) 98145-6085 / (19) 4117-0270`.
- E-mail comercial: `contato@eftx.com.br`.
- WhatsApp institucional: `https://wa.me/5519998537007`.
- Endereço: Rua Higyno Guilherme Costato, 298 – Jardim Pinheiros – Valinhos/SP (pode ser sobrescrito por variável de ambiente).
- Redes sociais oficiais: Instagram `@eftx_broadcast`, Facebook `facebook.com/eftxbroadcast`, LinkedIn `linkedin.com/company/eftx-broadcast-television-radio`.

## Próximos Passos para Atualização da Knowledge Base
1. Atualizar os PDFs e conteúdos referenciados em `docs/` e no diretório definido por `SITE_CONTENT_ROOT`.
2. Revisar este arquivo (`docs/public_site_overview.md`) sempre que houver mudanças no layout, seções ou mensagens-chave da home.
3. Rodar `flask rebuild-knowledge --source docs` para que o assistente técnico incorpore as novidades.
4. Validar o chat na home (usuário autenticado e visitante) garantindo que as respostas reflitam o conteúdo recém-indexado.
