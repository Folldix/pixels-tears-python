# ═══════════════════════════════════════════════════════════
# Makefile — локальний CI/CD Pipeline для Pixels and Tears
# Використання:  make          → повний pipeline
#                make test     → лише тести
#                make lint     → лише лінтінг
#                make clean    → очистити звіти
# ═══════════════════════════════════════════════════════════

PYTHON     := python
PYTEST     := $(PYTHON) -m pytest
FLAKE8     := $(PYTHON) -m flake8
REPORTS    := reports
GAME_SRC   := game

.PHONY: all install test lint clean pipeline

# ── Повний pipeline (як у GitHub Actions) ───────────────────
all: pipeline

pipeline: install lint test
	@echo ""
	@echo "✅  Pipeline завершено. Звіти у папці $(REPORTS)/"

# ── Встановлення залежностей ─────────────────────────────────
install:
	@echo "📦  Встановлення залежностей..."
	$(PYTHON) -m pip install --upgrade pip -q
	$(PYTHON) -m pip install -r requirements.txt -q
	@mkdir -p $(REPORTS)/flake8

# ── Лінтінг (Flake8) ─────────────────────────────────────────
lint:
	@echo ""
	@echo "🔍  Flake8 лінтінг..."
	-$(FLAKE8) $(GAME_SRC) --format=default | tee $(REPORTS)/flake8/flake8.txt
	-$(FLAKE8) $(GAME_SRC) --format=html --htmldir=$(REPORTS)/flake8
	@echo "    Звіт: $(REPORTS)/flake8/index.html"

# ── Тести (Pytest) ────────────────────────────────────────────
test:
	@echo ""
	@echo "🧪  Запуск тестів Pytest..."
	SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
	$(PYTEST) \
		--html=$(REPORTS)/test_report.html \
		--self-contained-html \
		--cov=$(GAME_SRC) \
		--cov-report=html:$(REPORTS)/coverage \
		--cov-report=term-missing \
		-v
	@echo "    Звіт: $(REPORTS)/test_report.html"

# ── Лише швидкі тести (без slow) ─────────────────────────────
test-fast:
	SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
	$(PYTEST) -m "not slow" -v

# ── Очистити звіти ────────────────────────────────────────────
clean:
	@echo "🗑️   Очищення звітів..."
	rm -rf $(REPORTS)
	rm -rf .pytest_cache .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "    Готово."
