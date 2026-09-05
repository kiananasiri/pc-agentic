.PHONY: help setup dev run start migrate clean

VENV = .venv
PYTHON = $(VENV)/bin/python

help:
	@echo "Available commands:"
	@echo "  make setup   - Create .venv, install Python & npm dependencies, run migrations"
	@echo "  make dev     - Run backend (Django) and frontend (Astro) concurrently"
	@echo "  make migrate - Run Django database migrations"
	@echo "  make clean   - Remove .venv and build artifacts"

$(VENV)/bin/activate:
	@echo "Creating Python virtual environment in $(VENV)..."
	python3 -m venv --system-site-packages $(VENV)

setup: $(VENV)/bin/activate
	@echo "Installing Python dependencies..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r chatbot/requirements.txt
	@echo "Installing Node.js dependencies..."
	npm install
	cd frontend && npm install
	@echo "Running Django migrations..."
	$(PYTHON) chatbot/manage.py migrate
	@echo "✅ Setup complete! Run 'make dev' to start both servers."

migrate: $(VENV)/bin/activate
	$(PYTHON) chatbot/manage.py migrate

dev:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment missing. Running setup..."; \
		$(MAKE) setup; \
	fi
	@if [ ! -d "node_modules/concurrently" ]; then \
		echo "Installing npm dependencies..."; \
		npm install; \
	fi
	@if [ ! -d "frontend/node_modules" ]; then \
		echo "Installing frontend dependencies..."; \
		cd frontend && npm install; \
	fi
	@echo "🚀 Starting Django backend & Astro frontend..."
	npm run dev

run: dev
start: dev

clean:
	rm -rf $(VENV)
	rm -rf node_modules
	rm -rf frontend/node_modules
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete."
