# Notas sobre o espelho WordPress (`/eftx_site`)

## Contatos oficiais
- Telefones exibidos no topo/rodapé do site original: `(19) 98145-6085 / (19) 4117-0270`.
- E-mail institucional padrão: `contato@eftx.com.br`.
- WhatsApp comercial: `5519998537007` (link original: `https://api.whatsapp.com/send?phone=5519998537007`).
- Endereço físico: `Rua Higyno Guilherme Costato, 298 - Jardim Pinheiros - Valinhos/SP`.
- Mapa embutido: iframe Google Maps `pb=!1m18!1m12!1m3!1d918.4187471130787!2d-46.981851682980846!3d-22.962193779764863...` (guardado integralmente na configuração).

## Redes sociais
- Instagram: `https://www.instagram.com/iftx_broadcast/`
- Facebook: `https://www.facebook.com/iftxbroadcast`
- LinkedIn: `https://www.linkedin.com/company/iftx-broadcast-television-radio`

## Assets relevantes
- Slider principal (WOWSlider) listado em `/content/pages/eftx.com.br/index.html` com imagens `wp-content/uploads/2014/11/1.jpg` e `36456-e1709036794105.jpg`.
- Banco de imagens completo em `/content/images/eftx.com.br/wp-content/uploads/` com variações em 2014–2025 (produtos, fábrica, eventos).
- PDFs de produtos e datasheets em `/content/docs/eftx.com.br/wp-content/uploads/2024/` (mesmos arquivos replicados em `docs/`).
- Tema original guarda CSS/JS em `/content/other/eftx.com.br/wp-content/themes/personalizado/` (ex.: `pw-slider-engine`, `pw-css`).

## Links específicos
- Cartão BNDES: `https://www.cartaobndes.gov.br/cartaobndes/PaginasCartao/Catalogo.asp?CTRL=667652673&acao=DF&Cod=3063234`.
- Logo/Favicon: `wp-content/themes/personalizado/pw-images/logo-site.png` e `favicon.png`.

## Observações
- O backup mantém páginas completas (`/content/pages/eftx.com.br/index.html?page_id=...`) com formulários WPForms (IDs 331 e 332 para PF/PJ).
- Vídeos institucionais estão espelhados em `/content/video/eftx.com.br/wp-content/uploads/2021/01/` e `2024/10/`.
- Scripts de animação (WOWSlider, Swiper, ScrollReveal) residem no tema e podem ser servidos via `site_asset` se necessário.
