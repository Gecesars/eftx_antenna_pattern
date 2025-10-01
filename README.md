# EFTX Antenna Pattern Designer

Aplicação web completa para cadastro de antenas EFTX, composição de projetos e exportação de padrões ERP (.PAT, .PRN, PDF).

## Tecnologias
- Python 3.12, Flask (blueprints, Jinja2)
- SQLAlchemy 2 + Alembic (PostgreSQL via psycopg2)
- Flask-Login, Flask-WTF (CSRF), Flask-Limiter, Flask-Mailman, Argon2
- Numpy, Matplotlib (Agg), ReportLab, pypdf, Pillow
- Front-end HTML5, CSS3, JavaScript puro

## Funcionalidades
- Cadastro de usuários com validação de e-mail (itsdangerous) e autenticação com Argon2
- Perfis `user` e `admin`; admin gerencia portfólio de antenas e importa HRP/VRP (CSV/TSV)
- Projetos com parâmetros de composição vertical/horizontal e cálculo de ERP 0°-359°
- Designer interativo com pré-visualização HRP/VRP e atualizações via API
- Exportação automática de arquivos .PAT, .PRN e relatório PDF com gráficos

## Quick start
1. `python -m venv .venv && .venv\Scripts\activate` (Windows) ou `source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. Copie `.env.example` para `.env` e ajuste URL do banco (PostgreSQL) e SMTP. Para Gmail, gere uma **senha de app** e configure:
   ```
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=465
   MAIL_USE_TLS=false
   MAIL_USE_SSL=true
   MAIL_USERNAME=seu.email@gmail.com
   MAIL_PASSWORD=sua-senha-app-16-digitos
   ```
4. `flask --app run.py db upgrade`
5. `flask --app run.py users create-admin --email admin@eftx.com`
6. `flask --app run.py run --host=0.0.0.0 --port=8000`

Documentação adicional em `docs/SETUP.md`.
