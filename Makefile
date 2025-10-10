.PHONY: install uninstall reinstall test build install-binary clean help archive-epic

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
	@echo "  make archive-epic EPIC=<name>    Move generated epic files to /tmp with timestamp"
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
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "❌ Error: Git working directory is not clean"; \
		echo "Please commit or stash your changes before building"; \
		exit 1; \
	fi
	@GIT_SHA=$$(git rev-parse --short HEAD); \
	if ls dist/*-$${GIT_SHA}-buildspec 2>/dev/null | grep -q .; then \
		EXISTING=$$(ls dist/*-$${GIT_SHA}-buildspec); \
		echo "❌ Error: Build already exists for commit $${GIT_SHA}"; \
		echo "Existing build: $${EXISTING}"; \
		echo "If you need to rebuild, delete the existing build first or commit new changes"; \
		exit 1; \
	fi
	@echo "Installing buildspec dependencies..."
	@uv sync --group build --quiet
	@echo "Running PyInstaller..."
	@cd $(PWD) && uv run pyinstaller buildspec.spec --clean --noconfirm
	@TIMESTAMP=$$(date +%s); \
	GIT_SHA=$$(git rev-parse --short HEAD); \
	BINARY_NAME="$${TIMESTAMP}-$${GIT_SHA}-buildspec"; \
	mv dist/buildspec "dist/$${BINARY_NAME}"; \
	echo "" > dist/.latest; \
	echo "$${BINARY_NAME}" > dist/.latest; \
	mkdir -p "$${HOME}/.local/bin"; \
	rm -f "$${HOME}/.local/bin/buildspec"; \
	ln -sf "$(PWD)/dist/$${BINARY_NAME}" "$${HOME}/.local/bin/buildspec"
	@echo ""
	@echo "✅ Binary built successfully: dist/$$(cat dist/.latest)"
	@echo "✅ Symlink updated: ~/.local/bin/buildspec -> dist/$$(cat dist/.latest)"
	@echo ""

install-binary: build install
	@echo "Installing standalone binary..."
	@echo ""
	@if [ ! -f dist/.latest ]; then \
		echo "❌ Error: No build found. Run 'make build' first."; \
		exit 1; \
	fi
	@BINARY_NAME=$$(cat dist/.latest); \
	mkdir -p "$${HOME}/.local/bin"; \
	rm -f "$${HOME}/.local/bin/buildspec"; \
	ln -s "$(PWD)/dist/$${BINARY_NAME}" "$${HOME}/.local/bin/buildspec"; \
	echo "✅ Symlink created: $${HOME}/.local/bin/buildspec -> $(PWD)/dist/$${BINARY_NAME}"
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

archive-epic:
	@echo "Archiving generated epic files..."
	@if [ -z "$(EPIC)" ]; then \
		echo "❌ Error: No epic specified"; \
		echo "Usage: make archive-epic EPIC=<epic-name>"; \
		echo ""; \
		echo "Available epics:"; \
		for dir in .epics/*/; do \
			if [ -d "$$dir" ]; then \
				basename "$$dir"; \
			fi; \
		done; \
		exit 1; \
	fi
	@if [ ! -d ".epics/$(EPIC)" ]; then \
		echo "❌ Error: No epic found at .epics/$(EPIC)"; \
		echo ""; \
		echo "Available epics:"; \
		for dir in .epics/*/; do \
			if [ -d "$$dir" ]; then \
				basename "$$dir"; \
			fi; \
		done; \
		exit 1; \
	fi
	@TIMESTAMP=$$(date +%s); \
	EPIC_NAME="$(EPIC)"; \
	ARCHIVE_DIR="/tmp/$${EPIC_NAME}/$${TIMESTAMP}-$${EPIC_NAME}"; \
	mkdir -p "$${ARCHIVE_DIR}"; \
	echo "📦 Creating archive: $${ARCHIVE_DIR}"; \
	echo ""; \
	for item in .epics/$${EPIC_NAME}/*; do \
		if [ -e "$$item" ]; then \
			BASENAME=$$(basename "$$item"); \
			if echo "$$BASENAME" | grep -q "spec\.md$$"; then \
				cp "$$item" "$${ARCHIVE_DIR}/$$BASENAME"; \
				echo "✅ Copied (preserved): $$BASENAME"; \
			else \
				mv "$$item" "$${ARCHIVE_DIR}/$$BASENAME"; \
				echo "✅ Moved: $$BASENAME"; \
			fi; \
		fi; \
	done
	@echo ""
	@TIMESTAMP=$$(date +%s); \
	EPIC_NAME="$(EPIC)"; \
	ARCHIVE_DIR="/tmp/$${EPIC_NAME}/$${TIMESTAMP}-$${EPIC_NAME}"; \
	echo "✅ Archive complete: $${ARCHIVE_DIR}"
