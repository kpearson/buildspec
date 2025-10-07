# Buildspec Distribution Strategy

**Goal:** Single-command installation that works on any platform without
requiring Python, git knowledge, or build tools.

## Option 3: Hybrid Distribution (Recommended)

### User Experience

```bash
# One command to install everything:
curl -sSL https://raw.githubusercontent.com/your-org/buildspec/main/install.sh | bash

# Or with wget:
wget -qO- https://raw.githubusercontent.com/your-org/buildspec/main/install.sh | bash
```

**What happens:**

1. Script detects OS and architecture
2. Downloads pre-built binary from GitHub Releases
3. Installs Claude Code files
4. Sets up configuration
5. Verifies installation
6. User runs `buildspec init` to customize config

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ GitHub Actions (CI/CD)                                      │
│                                                             │
│  On git tag (v0.1.0):                                       │
│    1. Build binaries for all platforms                      │
│    2. Package Claude Code files                             │
│    3. Create GitHub Release                                 │
│    4. Attach artifacts to release                           │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ User runs install script
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ install.sh (Shell Script)                                   │
│                                                             │
│  1. Detect platform (OS + architecture)                     │
│  2. Download binary from GitHub Releases                    │
│  3. Install to ~/.local/bin/buildspec                       │
│  4. Download/extract Claude Code files                      │
│  5. Symlink to ~/.claude/                                   │
│  6. Verify installation                                     │
│  7. Prompt user to run: buildspec init                      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ User's System                                               │
│                                                             │
│  ~/.local/bin/buildspec     (binary)                        │
│  ~/.claude/agents/          (symlinks)                      │
│  ~/.claude/commands/        (symlinks)                      │
│  ~/.claude/scripts/         (symlinks)                      │
│  ~/.config/buildspec/       (config after init)             │
└─────────────────────────────────────────────────────────────┘
```

---

## Component 1: GitHub Actions Workflow

**File:** `.github/workflows/release.yml`

### Triggers

- **Manual dispatch** - For testing builds
- **Git tags** - `v*` pattern (e.g., v0.1.0, v1.2.3)

### Build Matrix

| Platform     | OS Runner     | Architecture | Binary Name             |
| ------------ | ------------- | ------------ | ----------------------- |
| macOS ARM    | macos-14      | arm64        | buildspec-darwin-arm64  |
| macOS Intel  | macos-13      | x86_64       | buildspec-darwin-x86_64 |
| Linux x86_64 | ubuntu-latest | x86_64       | buildspec-linux-x86_64  |
| Linux ARM    | ubuntu-latest | arm64        | buildspec-linux-arm64   |

### Workflow Steps

1. **Checkout code**

   ```yaml
   - uses: actions/checkout@v4
   ```

2. **Set up Python** (for PyInstaller)

   ```yaml
   - uses: actions/setup-python@v5
     with:
       python-version: "3.11"
   ```

3. **Install dependencies**

   ```bash
   pip install -e .
   pip install pyinstaller
   ```

4. **Build binary**

   ```bash
   pyinstaller buildspec.spec --clean --noconfirm
   ```

5. **Rename binary for platform**

   ```bash
   mv dist/buildspec dist/buildspec-${{ matrix.platform }}
   ```

6. **Create checksums**

   ```bash
   shasum -a 256 dist/buildspec-${{ matrix.platform }} > dist/buildspec-${{ matrix.platform }}.sha256
   ```

7. **Package Claude Code files**

   ```bash
   tar -czf claude-files.tar.gz claude_files/
   ```

8. **Create GitHub Release** (once, not per platform)
   ```yaml
   - uses: softprops/action-gh-release@v1
     with:
       files: |
         dist/buildspec-*
         claude-files.tar.gz
       draft: false
       prerelease: false
   ```

### Outputs

Each release includes:

- `buildspec-darwin-arm64` + `.sha256`
- `buildspec-darwin-x86_64` + `.sha256`
- `buildspec-linux-x86_64` + `.sha256`
- `buildspec-linux-arm64` + `.sha256`
- `claude-files.tar.gz` (Claude Code files)
- Auto-generated release notes

---

## Component 2: Install Script

**File:** `install.sh` (in repo root)

### Detection Logic

```bash
# Detect OS
OS="$(uname -s)"
case "$OS" in
    Linux*)     OS="linux";;
    Darwin*)    OS="darwin";;
    *)          echo "Unsupported OS: $OS" && exit 1;;
esac

# Detect architecture
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)     ARCH="x86_64";;
    aarch64)    ARCH="arm64";;
    arm64)      ARCH="arm64";;
    *)          echo "Unsupported architecture: $ARCH" && exit 1;;
esac

PLATFORM="${OS}-${ARCH}"
```

### Download Strategy

**Option A: Download from latest release**

```bash
REPO="your-org/buildspec"
BINARY_NAME="buildspec-${PLATFORM}"
DOWNLOAD_URL="https://github.com/${REPO}/releases/latest/download/${BINARY_NAME}"

curl -L "$DOWNLOAD_URL" -o /tmp/buildspec
```

**Pros:**

- Always gets latest version
- Simple URL pattern
- No version tracking needed

**Cons:**

- Can't pin to specific version
- Breaking changes affect all users

**Option B: Download specific version**

```bash
VERSION="${BUILDSPEC_VERSION:-latest}"  # Allow override
if [ "$VERSION" = "latest" ]; then
    VERSION=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name":' | cut -d'"' -f4)
fi

DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${BINARY_NAME}"
```

**Pros:**

- Version pinning support
- User control over updates
- Safe for production

**Cons:**

- Extra API call for "latest"
- More complex logic

**Recommendation:** Use Option B with default "latest"

### Installation Steps

```bash
#!/bin/bash
set -e

REPO="your-org/buildspec"
INSTALL_DIR="$HOME/.local/bin"
CLAUDE_DIR="$HOME/.claude"

echo "Installing buildspec..."

# 1. Detect platform
OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64|amd64) ARCH="x86_64";;
    aarch64|arm64) ARCH="arm64";;
    *) echo "Unsupported architecture: $ARCH" && exit 1;;
esac
PLATFORM="${OS}-${ARCH}"

# 2. Get version (use specified version or fetch latest)
VERSION="${BUILDSPEC_VERSION:-latest}"
if [ "$VERSION" = "latest" ]; then
    echo "Fetching latest release..."
    VERSION=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name":' | sed -E 's/.*"tag_name": "([^"]+)".*/\1/')
fi

echo "Installing buildspec ${VERSION} for ${PLATFORM}..."

# 3. Download binary
BINARY_NAME="buildspec-${PLATFORM}"
DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${VERSION}/${BINARY_NAME}"

echo "Downloading binary from ${DOWNLOAD_URL}..."
curl -L "$DOWNLOAD_URL" -o /tmp/buildspec

# 4. Verify checksum (optional but recommended)
curl -L "${DOWNLOAD_URL}.sha256" -o /tmp/buildspec.sha256
cd /tmp && shasum -a 256 -c buildspec.sha256 || {
    echo "Checksum verification failed!"
    exit 1
}

# 5. Install binary
mkdir -p "$INSTALL_DIR"
mv /tmp/buildspec "$INSTALL_DIR/buildspec"
chmod +x "$INSTALL_DIR/buildspec"

# 6. Download Claude Code files
echo "Installing Claude Code files..."
CLAUDE_FILES_URL="https://github.com/${REPO}/releases/download/${VERSION}/claude-files.tar.gz"
curl -L "$CLAUDE_FILES_URL" -o /tmp/claude-files.tar.gz

# 7. Extract and symlink Claude Code files
mkdir -p "$CLAUDE_DIR"/{agents,commands,scripts,hooks,mcp-servers}
tar -xzf /tmp/claude-files.tar.gz -C /tmp/
for dir in agents commands scripts hooks mcp-servers; do
    for file in /tmp/claude_files/$dir/*; do
        [ -f "$file" ] && ln -sf "$file" "$CLAUDE_DIR/$dir/"
    done
done

# 8. Cleanup
rm -rf /tmp/buildspec /tmp/buildspec.sha256 /tmp/claude-files.tar.gz /tmp/claude_files

# 9. Verify installation
if command -v buildspec >/dev/null 2>&1; then
    echo ""
    echo "✅ Buildspec installed successfully!"
    echo ""
    echo "Version: $(buildspec --version 2>/dev/null || echo $VERSION)"
    echo "Location: $(which buildspec)"
    echo ""
    echo "Next steps:"
    echo "  1. Run: buildspec init"
    echo "  2. Edit: ~/.config/buildspec/config.toml"
    echo "  3. Start using: buildspec create-epic <planning-doc>"
    echo ""
else
    echo ""
    echo "⚠️  Installation complete, but 'buildspec' command not found in PATH."
    echo ""
    echo "Add this to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    echo "Then reload your shell: source ~/.bashrc"
fi
```

### Error Handling

The script should handle:

1. **Unsupported platform**

   ```bash
   echo "Error: Platform ${PLATFORM} not supported"
   echo "Supported platforms: darwin-arm64, darwin-x86_64, linux-x86_64, linux-arm64"
   exit 1
   ```

2. **Download failures**

   ```bash
   if ! curl -L "$DOWNLOAD_URL" -o /tmp/buildspec; then
       echo "Error: Failed to download buildspec binary"
       echo "Check your internet connection or verify the release exists"
       exit 1
   fi
   ```

3. **Permission issues**

   ```bash
   if [ ! -w "$INSTALL_DIR" ]; then
       echo "Error: No write permission to $INSTALL_DIR"
       echo "Try running: mkdir -p $INSTALL_DIR && chmod u+w $INSTALL_DIR"
       exit 1
   fi
   ```

4. **PATH not set**
   - Detect shell (bash/zsh/fish)
   - Provide specific instructions
   - Offer to auto-update shell config (with permission)

---

## Component 3: Version Management

### Semantic Versioning

Use semver: `vMAJOR.MINOR.PATCH`

Examples:

- `v0.1.0` - Initial release
- `v0.2.0` - New features (create-tickets command)
- `v0.2.1` - Bug fixes
- `v1.0.0` - Stable release

### Release Process

```bash
# 1. Update version in pyproject.toml
version = "1.2.3"

# 2. Create and push tag
git tag -a v1.2.3 -m "Release v1.2.3: Add standalone binary support"
git push origin v1.2.3

# 3. GitHub Actions automatically:
#    - Builds binaries for all platforms
#    - Creates GitHub Release
#    - Attaches binaries and checksums
#    - Adds release notes
```

### Upgrade Path

Users can upgrade by re-running the install script:

```bash
# Upgrade to latest
curl -sSL https://raw.githubusercontent.com/your-org/buildspec/main/install.sh | bash

# Upgrade to specific version
BUILDSPEC_VERSION=v1.2.3 curl -sSL https://raw.githubusercontent.com/your-org/buildspec/main/install.sh | bash
```

Or with a dedicated update command:

```bash
buildspec update  # Future feature
```

---

## Alternative: Distribution via Homebrew

For macOS users, Homebrew is more familiar:

```bash
brew tap your-org/buildspec
brew install buildspec
```

**homebrew-buildspec/Formula/buildspec.rb:**

```ruby
class Buildspec < Formula
  desc "Claude Code workflow automation for epic-driven development"
  homepage "https://github.com/your-org/buildspec"
  version "0.1.0"

  if Hardware::CPU.arm?
    url "https://github.com/your-org/buildspec/releases/download/v0.1.0/buildspec-darwin-arm64"
    sha256 "..." # SHA256 of binary
  else
    url "https://github.com/your-org/buildspec/releases/download/v0.1.0/buildspec-darwin-x86_64"
    sha256 "..." # SHA256 of binary
  end

  def install
    bin.install "buildspec-darwin-#{Hardware::CPU.arch}" => "buildspec"

    # Install Claude Code files
    # ... (download and symlink claude_files)
  end

  test do
    system "#{bin}/buildspec", "--version"
  end
end
```

**Pros:**

- Familiar to Mac developers
- Auto-updates with `brew upgrade`
- Handles PATH automatically

**Cons:**

- macOS only
- Requires maintaining separate tap repo
- More complex setup

---

## Comparison: Distribution Methods

| Method              | Platforms    | Installation    | Updates          | Complexity |
| ------------------- | ------------ | --------------- | ---------------- | ---------- |
| **Curl script**     | All          | One command     | Re-run script    | Low        |
| **GitHub Releases** | All          | Manual download | Manual           | Medium     |
| **Homebrew**        | macOS only   | `brew install`  | `brew upgrade`   | High       |
| **Pip**             | All (Python) | `pip install`   | `pip install -U` | Low        |
| **Docker**          | All          | `docker pull`   | `docker pull`    | Medium     |

**Recommendation:** Start with curl script (Option 3), add Homebrew later if
demand exists.

---

## Security Considerations

### Checksum Verification

Always provide and verify SHA256 checksums:

```bash
# Generate during build
shasum -a 256 buildspec-darwin-arm64 > buildspec-darwin-arm64.sha256

# Verify during install
shasum -a 256 -c buildspec-darwin-arm64.sha256
```

### Code Signing (macOS)

For production, sign macOS binaries:

```bash
# Requires Apple Developer certificate
codesign --sign "Developer ID Application: Your Name" buildspec-darwin-arm64
```

Users won't see "unidentified developer" warnings.

### Supply Chain Security

- **Pin dependencies** in pyproject.toml
- **Lock file** (uv.lock) ensures reproducible builds
- **GitHub Actions audit** - Review workflow permissions
- **SBOM** (Software Bill of Materials) - Generate with `syft`

---

## Testing Strategy

### Test Matrix

| OS           | Architecture | Test Type |
| ------------ | ------------ | --------- |
| macOS 14     | ARM64        | Full      |
| macOS 13     | x86_64       | Full      |
| Ubuntu 22.04 | x86_64       | Full      |
| Ubuntu 22.04 | ARM64        | Smoke     |

### Test Script

```bash
#!/bin/bash
# test-installation.sh

set -e

echo "Testing buildspec installation..."

# Test 1: Binary exists and is executable
if ! command -v buildspec >/dev/null; then
    echo "FAIL: buildspec command not found"
    exit 1
fi

# Test 2: Help command works
if ! buildspec --help >/dev/null; then
    echo "FAIL: buildspec --help failed"
    exit 1
fi

# Test 3: Init command works
rm -rf ~/.config/buildspec
if ! buildspec init; then
    echo "FAIL: buildspec init failed"
    exit 1
fi

# Test 4: Config file created
if [ ! -f ~/.config/buildspec/config.toml ]; then
    echo "FAIL: Config file not created"
    exit 1
fi

# Test 5: Claude Code files installed
for dir in agents commands scripts; do
    if [ ! -d ~/.claude/$dir ]; then
        echo "FAIL: Claude Code directory missing: $dir"
        exit 1
    fi
done

echo "✅ All tests passed!"
```

---

## Documentation Updates

### README.md

Add installation section:

````markdown
## Installation

### Recommended: One-Command Install

```bash
curl -sSL https://raw.githubusercontent.com/your-org/buildspec/main/install.sh | bash
```
````

This installs the standalone binary that works on any project.

### Alternative: Manual Install

See [DISTRIBUTION.md](docs/DISTRIBUTION.md) for other installation methods.

````

### Website/Docs

Create getting-started guide:

1. Installation (curl script)
2. Initialize config (`buildspec init`)
3. Create first epic
4. Execute epic

---

## Migration Path

For existing users who installed via `make install`:

```bash
# Uninstall pip version
make uninstall

# Install standalone binary
curl -sSL https://raw.githubusercontent.com/your-org/buildspec/main/install.sh | bash

# Config is preserved (XDG-compliant location)
````

---

## Future Enhancements

1. **Auto-update mechanism**

   ```bash
   buildspec update  # Check and install latest version
   ```

2. **Version constraints**

   ```bash
   # In project's .buildspec-version file
   1.2.3  # Exact version
   ^1.2   # Compatible with 1.2.x
   ```

3. **Plugin system**
   - Download additional agents from registry
   - Community-contributed workflows

4. **Telemetry** (opt-in)
   - Track version usage
   - Identify breaking changes
   - Plan deprecations

---

## Summary

**Option 3 provides:**

- ✅ One-command installation
- ✅ Multi-platform support (macOS, Linux, ARM, x86_64)
- ✅ No Python dependency
- ✅ Automated CI/CD builds
- ✅ Secure distribution (checksums, signatures)
- ✅ Easy updates (re-run install script)
- ✅ Version pinning support

**Next steps:**

1. Implement `.github/workflows/release.yml`
2. Create `install.sh` script
3. Test on all platforms
4. Create v0.1.0 release
5. Update README with new installation method
