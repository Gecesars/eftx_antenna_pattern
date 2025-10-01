# Setup Guide

1. Crie e ative a virtualenv (Python 3.12).
2. `pip install -r requirements.txt`
3. Copie `.env.example` para `.env` e ajuste:
   - `DATABASE_URL` para o seu PostgreSQL.
   - Configuração SMTP. Para Gmail use senha de app e SSL na porta 465.
4. `flask --app run.py db upgrade`
5. `flask --app run.py users create-admin --email você@exemplo.com`
6. `flask --app run.py run --host=0.0.0.0 --port=8000`
