# 🗂️ Python MCP Filesystem Server

This project is a Python-based MCP (Model Context Protocol) server that allows Claude Desktop, OpenCode, and Antigravity CLI to perform secure and controlled local filesystem operations via natural language commands. It bridges the gap between conversational AI and direct file management by implementing the MCP 1.0 protocol with full support for read/write operations, file system traversal, metadata extraction, and optional cryptographic operation receipts.

---

## 🚀 Features

- ✅ Fully compatible with Claude Desktop, OpenCode, and Antigravity CLI
- 📂 Read, write, move, copy, delete, and search files and directories
- 🔒 Thread-safe deterministic locking, strict path validation & extension policy enforcement
- 🧠 JSON-RPC 2.0 communication over `stdin`/`stdout`
- 🔄 Asynchronous architecture with `asyncio`
- 🧾 Optional Ed25519-signed BoundaryAttest receipts for high-impact file operations
- 🧪 Unit & integration tests included

---

## 🧰 Tech Stack

- **Python** >= 3.11
- **MCP SDK** (`mcp[cli] >= 1.10.1`), **send2trash**
- **AsyncIO**, **Pathlib**, **JSON**, **Typing**
- **Claude Desktop**, **OpenCode**, **Antigravity CLI**
- MCP Protocol (v1.0) implementation

---

## 📦 Installation

### 1. Install `uv` (recommended)

On **Windows PowerShell**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
```

On **Linux / macOS**:

```bash
curl -LsSf [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```

Or if your system does not have `curl`, use `wget`:

```bash
wget -qO- [https://astral.sh/uv/install.sh](https://astral.sh/uv/install.sh) | sh
```

> Make sure `uv` is available in your system `PATH`.

### 2. Clone & Sync Dependencies

```bash
git clone [https://github.com/CodingWithMK/filesystem_mcp_server.git](https://github.com/CodingWithMK/filesystem_mcp_server.git)
cd filesystem_mcp_server
uv sync
```

To install optional dependencies for testing or BoundaryAttest receipts:

```bash
# Install test dependencies (pytest, cryptography)
uv sync --extra test

# Install optional BoundaryAttest receipt signing dependency (cryptography)
uv sync --extra boundaryattest
```

---

## ⚙️ Configuration

Edit `config/windows.json`, `config/macos.json`, or `config/default.json` to define allowed paths, maximum file size, and allowed file extensions:

**`config/windows.json`**
```json
{
  "allowed_paths": [
    "~/Desktop",
    "~/Downloads"
  ],
  "max_file_size": "20MB",
  "allowed_extensions": [
    "txt", "md", "pdf", "png", "jpg", "jpeg", "json", "docx", "doc", "ppt",
    "pptx", "xls", "xlsx", "mp4", "mp3", "wav", "avi", "mov", "zip", "rar",
    "msi", "exe", "dll", "py", "c", "cpp", "java", "js", "html", "css", "xml", "csv", "ts",
    "CATPart", "CATProduct", "CATDrawing", "CATProcess"
  ]
}
```

**`config/macos.json`**
```json
{
  "allowed_paths": [
    "~/Desktop",
    "~/Downloads"
  ],
  "max_file_size": "20MB",
  "allowed_extensions": [
    "txt", "md", "pdf", "png", "jpg", "jpeg", "json", "docx", "doc", "ppt",
    "pptx", "xls", "xlsx", "mp4", "mp3", "wav", "avi", "mov", "zip", "rar",
    "pkg", "dmg", "dll", "py", "c", "cpp", "java", "js", "html", "css", "xml", "csv", "ts"
  ]
}
```

**`config/default.json`**
```json
{
  "allowed_paths": [
    "~/Desktop",
    "~/Downloads"
  ],
  "max_file_size": "20MB",
  "allowed_extensions": [
    "txt", "md", "pdf", "png", "jpg", "jpeg", "json", "docx", "doc", "ppt",
    "pptx", "xls", "xlsx", "mp4", "mp3", "wav", "avi", "mov", "zip", "rar",
    "msi", "exe", "pkg", "dmg", "dll", "py", "c", "cpp", "java", "js", "html", "css", "xml", "csv", "ts",
    "CATPart", "CATProduct", "CATDrawing", "CATProcess"
  ]
}
```

### Environment Variable Overrides

You can optionally override the JSON configuration via environment variables:

- `FILESYSTEM_ALLOWED_PATHS`: OS path-separated list of allowed directories (e.g., `:` on Linux/macOS, `;` on Windows)
- `FILESYSTEM_MAX_FILE_SIZE`: Maximum allowed file size (e.g., `20MB`, `500KB`, `1GB`)
- `FILESYSTEM_ALLOWED_EXTENSIONS`: Comma-separated list of allowed extensions (e.g., `txt,md,py,json`)

---

### Configure Claude Desktop

```json
{
  "mcpServers": {
    "python-filesystem": {
      "command": "C:\\Users\\username\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "C:\\Users\\username\\Documents\\filesystem_mcp_server\\src\\main.py"
      ]
    }
  }
}
```

### Configure OpenCode

> Open your global OpenCode `.config` directory and edit `opencode.jsonc`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "filesystem_mcp_server": {
      "type": "local",
      "enabled": true,
      "command": [
        "C:\\Users\\username\\.local\\bin\\uv.exe",
        "run",
        "--project",
        "C:\\Users\\username\\Documents\\filesystem_mcp_server",
        "python",
        "C:\\Users\\username\\Documents\\filesystem_mcp_server\\src\\main.py"
      ]
    }
  }
}
```

### Configure Antigravity CLI

> Open your global standalone Antigravity CLI MCP configuration file under `.gemini/config/mcp_config.json` and adjust the paths to your system:

```json
{
  "mcpServers": {
    "filesystem-mcp-server": {
      "command": "C:\\Users\\username\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "--project",
        "C:\\Users\\username\\Documents\\filesystem_mcp_server",
        "python",
        "C:\\Users\\username\\Documents\\filesystem_mcp_server\\src\\main.py"
      ],
      "env": {}
    }
  }
}
```

---

## 🛠️ Tools / API Functions

### File Operations
- `read_file`: Reads plaintext UTF-8 content from an approved file
- `write_file`: Writes or appends UTF-8 text payloads to a file safely
- `move_file`: Moves files safely under deterministic synchronization locks
- `copy_file`: Copies files with metadata preservation (`shutil.copy2`)
- `delete_file`: Moves a file to the operating system recycling bin via `send2trash`
- `search_file`: Recursively searches for files matching a keyword in their filename
- `get_file_info`: Retrieves safe metadata (`name`, `size`, `modified`, `is_directory`)

### Directory & Policy Operations
- `list_files`: Lists all files inside a directory
- `list_directories`: Lists all subdirectories inside a directory
- `list_directory_content`: Lists all entries (both files and folders) in a directory
- `create_directory`: Recursively creates directories inside authorized paths
- `move_directory`: Moves folder trees with deterministic locking
- `copy_directory`: Performs recursive directory cloning
- `delete_directory`: Moves a directory structure to the OS recycling bin
- `get_allowed_paths`: Returns the currently configured allowed root paths

All handlers run asynchronously via worker threads and enforce path boundary checks, extension whitelists, and deadlock-free locking.

---

## 🧪 Testing

Run the BoundaryAttest and core operation test suite using `uv`:

```bash
uv run --extra test pytest tests/test_boundaryattest.py
```

Includes tests for:
- File I/O (`write_file`, `move_file`, `delete_file`) & exact byte preservation
- Path validation & deterministic lock verification
- Optional BoundaryAttest receipt signing, verification, and tamper detection

---

### Experimental BoundaryAttest Receipts

The server can optionally emit portable, Ed25519-signed BoundaryAttest Interop Profile v0.1 receipts after successful `write_file`, `move_file`, and `delete_file` operations. This proof of concept is **off by default**: ordinary single-user/local MCP deployments generally get sufficient visibility from their existing MCP and local logs, without signing-key or receipt-storage overhead. The feature is aimed at shared, multi-tenant, enterprise, CI/CD, and other trust-boundary environments where portable evidence may be useful.

Install the optional dependency and configure the server process:

```bash
uv sync --extra boundaryattest
export BOUNDARYATTEST_ENABLED=true
export BOUNDARYATTEST_PRIVATE_KEY=/secure/path/ed25519-private-key.pem
export BOUNDARYATTEST_RECEIPT_DIR=/secure/path/filesystem-receipts
```

For development only, generate an Ed25519 PKCS #8 key (never commit it):

```bash
openssl genpkey -algorithm Ed25519 -out boundaryattest-dev-private.pem
openssl pkey -in boundaryattest-dev-private.pem -pubout -out boundaryattest-dev-public.pem
```

Each successful covered operation writes one uniquely named JSON receipt. Clear path references are relative to the matching configured allowed root, while the signed `materialized_action_hash` binds the exact resolved internal path(s). Writes bind the appended UTF-8 content digest plus exact pre/post file hashes; moves bind the source and actual final destination (including an appended source name when the destination argument is a directory); deletes bind the exact pre-trash bytes and have no post-delete artifact at the original path. File hashes are SHA-256 over raw bytes.

Verify with a public key obtained through a trusted path, optionally checking a current artifact's exact bytes:

```bash
uv run --extra boundaryattest python src/verify_boundaryattest_receipt.py \
  RECEIPT.json EXPECTED_PUBLIC_KEY.pem --artifact FILE
```

A valid result proves only that the expected key signed the unchanged claim and, when supplied, that the artifact bytes match the signed digest. It does not prove truth, wisdom, authorization, policy compliance, signer trustworthiness, runtime integrity, or production-grade key custody. The feature is experimental, non-transactional, and external to the MCP server: if an action succeeds but receipt emission fails, the action is not rolled back and the tool returns its success message with a prominent attestation warning. This invited test integration is not an endorsement, partnership, audit system, security guarantee, or production key-management system.

---

## 🧯 Known Issues & Troubleshooting

- **Unsupported File Extensions:** If an agent cannot read or write a specific file type, add the extension to `allowed_extensions` in `config/windows.json`, `config/macos.json`, or `config/default.json` (or via `FILESYSTEM_ALLOWED_EXTENSIONS`).
- **Path / `uv` Resolution:** Ensure `uv` is installed and referenced with its full path in your MCP client config if the client does not inherit your shell `PATH`.

---

## 🤝 Contributing

Contributions are welcome! Whether it's bug fixes, new features, or documentation improvements, feel free to fork the repository and submit a Pull Request.

---

## 📜 License

MIT License

---

## 🙌 Acknowledgements

- Inspired by the official [Filesystem MCP Server from Anthropic](https://www.anthropic.com/)
- Based on the MCP 1.0 Protocol Specification