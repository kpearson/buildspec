.PHONY: install uninstall reinstall test build install-binary clean help

# Default target
help:
	@echo "Buildspec Toolkit - Makefile Commands"
	@echo ""
	@echo "Usage:"
	@echo "  make build           Build standalone binary with PyInstaller"
	@echo "  make install-binary  Install standalone binary to ~/.local/bin"
	@echo "  make install         Install buildspec CLI and Claude Code files (pip)"
	@echo "  make uninstall       Remove buildspec CLI and Claude Code files"
	@echo "  make reinstall       Uninstall and reinstall buildspec"
	@echo "  make clean           Remove build artifacts"
	@echo "  make test            Test the CLI installation"
	@echo "  make help            Show this help message"
	@echo ""
	@echo "Recommended: Use 'make build && make install-binary' for standalone installation"
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

build:
	@echo "Building standalone binary with PyInstaller..."
	@echo ""
	@echo "Installing buildspec dependencies..."
	@uv pip install -e . --quiet
	@if ! command -v pyinstaller >/dev/null 2>&1; then \
		echo "Installing PyInstaller..."; \
		uv tool install pyinstaller --quiet; \
	fi
	@echo "Running PyInstaller..."
	@cd $(PWD) && pyinstaller buildspec.spec --clean --noconfirm
	@echo ""
	@echo "✅ Binary built successfully: dist/buildspec"
	@echo ""

install-binary: build
	@echo "Installing standalone binary..."
	@echo ""
	@mkdir -p ~/.local/bin
	@cp dist/buildspec ~/.local/bin/buildspec
	@chmod +x ~/.local/bin/buildspec
	@echo "✅ Binary installed to ~/.local/bin/buildspec"
	@echo ""
	@./scripts/install.sh
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "The buildspec binary is now independent of any Python version."
	@echo "It will work in projects using Python 2.7, 3.x, Node.js, Go, etc."
	@echo ""

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build dist __pycache__
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Build artifacts removed"

test:
	@echo "Testing buildspec installation..."
	@echo ""
	@if command -v buildspec >/dev/null 2>&1; then \
		echo "✅ buildspec command found at: $$(which buildspec)"; \
		echo ""; \
		buildspec --help; \
	else \
		echo "❌ buildspec command not found"; \
		echo "Run 'make install' or 'make install-binary' first"; \
		exit 1; \
	fi
