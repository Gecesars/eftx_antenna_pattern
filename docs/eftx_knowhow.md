# Know-how e Diferenciais EFTX

Este material resume os pilares técnicos, operacionais e comerciais que diferenciam a EFTX Broadcast & Telecom, servindo como fonte de conhecimento para o assistente virtual e para treinamentos internos.

## Pilares de Know-how
- **Engenharia 360°**: atuação integrada em planejamento, simulação, memorial descritivo, implantação em campo e suporte pós-start-up.
- **Especialistas multidisciplinares**: radiofrequência, estrutura metálica, instalações elétricas críticas, redes IP, SNMP, telemetria e TI atuando em conjunto.
- **Laboratório próprio**: medições de VSWR, ensaios ambientais, ajustes de combinadores, validação de filtros e monitoramento contínuo.
- **Stack numérica proprietária**: parsers e compositores ERP com reamostragem 361 pontos, métricas HPBW/Directividade/SLL e exportação PAT/PRN/PDF certificadas.
- **Homologações e compliance**: aderência a cadernos Anatel, ITU-R, ISDB-Tb, FM, normas de segurança NR-10/NR-35 e políticas LGPD.
- **Base instalada relevante**: mais de 700 sistemas de antenas entregues e 26 anos de operação com equipes residentes em 12 estados.

## Diferenciais Operacionais
- **Simulação aplicada**: bibliotecas de cenários FM, TV digital e backhaul licenciados com perdas reais, tilt elétrico/mecânico e conformidade de máscara.
- **Tempo de resposta**: equipe comercial e engenharia comprometida com SLA de 1 dia útil para propostas e 24/7 para contratos críticos.
- **Gestão de ativos**: catálogo digital com dados técnicos, datasheets, curva de atenuação de cabos e histórico de exportações por projeto.
- **Automação do know-how**: assistente técnico IA (Gemini) conectado à base de conhecimento (`docs/`), sugerindo documentação e ações operacionais.
- **Infraestrutura de deploy**: scripts de provisionamento (Gunicorn + Nginx + systemd), backups agendados e monitoramento `/healthz`.
- **Integrações inteligentes**: IA institucional, webhooks WhatsApp, índice vetorial para contextualização e prompts alinhados à persona AntennaExpert.

## Serviços e Benefícios
- **Consultoria e viabilidade**: estudos de cobertura, medições em campo, relatórios comparativos de ERP e recomendações estruturais.
- **Fabricação sob medida**: painéis, combinadores, linhas rígidas/flexíveis com rastreabilidade de lote e logística para qualquer região do Brasil.
- **Integração turn-key**: instalação comissionada, ajustes finos, emissão de laudos certificados e treinamento da equipe local.
- **Operação assistida**: manutenção preventiva, estoque em consignação, telemetria proativa e suporte remoto.
- **Processos seguros**: gestão de consentimento LGPD, cookies, CSP, rate limiting e controle de acesso a dados sensíveis.
- **Entrega acelerada**: pipelines internos de exportação e relatórios automatizados reduzem tempo de aprovação regulatória e de marketing técnico.

## Recursos Complementares
- **Documentação digital**: `docs/` centraliza datasheets, guias, planos e relatórios atualizados.
- **Simulação & Aplicação**: widget na home resume cenários típicos com métricas (ERP, HPBW, disponibilidade, margem de desvanecimento).
- **FAQ institucional**: coletânea pronta para atendimento, integrando diferenciais e fluxos de contato.
- **Equipe de campo**: squads regionalizados para FM, TV e telecom corporativo garantindo SLA mesmo em topografias críticas.

> Manter este arquivo atualizado sempre que novos cases, certificações ou integrações forem lançados. Após alterações, executar `flask rebuild-knowledge --source docs` para sincronizar a base vetorial.
