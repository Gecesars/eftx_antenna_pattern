# Changelog

## 2025-10-01T19:45:38Z
- removed tracked .env to protect secrets
- refreshed .env.example with jwt/mail defaults and admin alert recipients
- aligned dependency manifests (requirements.txt, pyproject.toml) with testing and quality stack
- updated app/config.py SQLAlchemy engine options for pool sizing
- added docs/01-plano.md detailing milestone roadmap

## 2025-10-08T04:15:36Z
- reworked base layout to inject WordPress-style header/footer for blueprint public_site
- mirrored eftx.com.br homepage markup, menus e scripts em public_site/home.html
- adicionou entrada "Área do Cliente" que direciona autenticados ao dashboard e visitantes ao login
- reforçou contraste em topo/rodapé com ícones brancos e removeu créditos WordPress no footer
- carregou CSS/JS originais do tema personalizado e novo logo estático em static/img/logo.png
- documentou o formato visual no descricao.md para referência futura
