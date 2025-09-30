# Setup Guide

1. Create a Python 3.12 virtualenv and install dependencies: `pip install -e .`
2. Copy `.env.example` to `.env` and adjust settings.
3. Initialize the database:
   - `flask db upgrade`
4. Create an admin user:
   - `flask users create-admin --email you@example.com`
5. Run the server: `flask run --host=0.0.0.0 --port=8000`
