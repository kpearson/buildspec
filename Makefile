.PHONY: install uninstall reinstall test help

# Default target
help:
	@echo "Buildspec Toolkit - Makefile Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make install      Install buildspec CLI and Claude Code files"
	@echo "  make uninstall    Remove buildspec CLI and Claude Code files"
	@echo "  make reinstall    Uninstall and reinstall buildspec"
	@echo "  make test         Test the CLI installation"
	@echo "  make help         Show this help message"
	@echo ""

install:
	@echo "Installing Buildspec Toolkit..."
	@echo ""
	@./scripts/install.sh

uninstall:
	@echo "Uninstalling Buildspec Toolkit..."
	@echo ""
	@./scripts/uninstall.sh

reinstall: uninstall install
	@echo ""
	@echo "✅ Buildspec reinstalled successfully"

test:
	@echo "Testing buildspec installation..."
	@echo ""
	@if command -v buildspec >/dev/null 2>&1; then \
		echo "✅ buildspec command found at: $$(which buildspec)"; \
		echo ""; \
		buildspec --help; \
	else \
		echo "❌ buildspec command not found"; \
		echo "Run 'make install' first"; \
		exit 1; \
	fi
