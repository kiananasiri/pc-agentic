# Parsian Crypto Agentic Assistant

A full-stack crypto AI chatbot application with a Django backend and Astro frontend.

## Quick Start (Without Docker)

You can run both the Django backend and Astro frontend concurrently with a single command using the included `Makefile`.

### 1. Run Backend & Frontend (One Command)

```bash
make dev
```
*(If the virtual environment `.venv` or Node modules are missing, `make dev` will automatically run `make setup` first.)*

Alternatively, you can run:
```bash
./run.sh
# or
npm run dev
```

### 2. Available Commands

- `make setup` — Creates Python `.venv`, installs backend & frontend dependencies, and runs initial database migrations.
- `make dev` — Starts Django backend on `http://127.0.0.1:8000` and Astro frontend on `http://localhost:4321`.
- `make migrate` — Runs Django database migrations.
- `make clean` — Removes `.venv`, `node_modules`, and cached build files.

### 3. Environment Variables (Optional)

By default, the backend falls back to SQLite (`chatbot/db.sqlite3`) if no PostgreSQL environment variable is defined, enabling zero-config local runs.

To use PostgreSQL, configure environment variables in `chatbot/.env`:
```env
POSTGRES_DB=your_db_name
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```