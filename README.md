# 🗂️ Python MCP Filesystem Server

This project is a Python-based MCP (Model Context Protocol) server that allows Claude Desktop, OpenCode and Antigravity CLI to perform secure and controlled local filesystem operations via natural language commands. It bridges the gap between conversational AI and direct file management by implementing the MCP 1.0 protocol with full support for read/write operations, file system traversal, metadata extraction, and more.

---

## 🚀 Features

- ✅ Fully compatible with Claude Desktop
- 📂 Read, write, move, delete, and search files
- 🔒 Thread-sade deterministic locking, stric path validation & permission control
- 🧠 JSON-RPC 2.0 communication over stdin/stdout
- 🔄 Asynchronous architecture with `asyncio`
- 🧪 Unit & integration tests included

---

## 🧰 Tech Stack

- **Python** 3.11
- **AsyncIO**, **Pathlib**, **JSON**, **Typing**
- **Claude Desktop**, **OpenCode**, **Antigravity CLI** (latest version)
- MCP Protocol (v1.0) implementation

---

## 📦 Installation

### Install `uv` (recommended)

On **Windows PowerShell**:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

On **Linux/Mac**:
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```
or if your system does not have ```curl```, try with ```wget```
```
wget -qO- https://astral.sh/uv/install.sh | sh
```
or install by requesting a specific version
```
curl -LsSf https://astral.sh/uv/0.7.20/install.sh | sh
```

> Make sure uv is available in your system PATH.

```bash
git clone https://github.com/yourusername/python-mcp-filesystem-server.git
cd python-mcp-filesystem-server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
````

---

## ⚙️ Configuration

Edit `config/windows.json`, `config/macos.json`, `config/default.json` to define allowed paths and other settings:

```json
windows.json
{
  "allowed_paths": [
    "~/Desktop",
    "~/Downloads"
  ],
  "max_file_size": "20MB",
  "allowed_extensions": [
    "txt", "md", "pdf", "png", "jpg","jpeg", "json", "docx", "doc", "ppt", "pptx", "xls", "xlsx"
  ]
}
```

```json
macos.json
{
  "allowed_paths": [
    "~/Desktop",
    "~/Downloads"
  ],
  "max_file_size": "20MB",
  "allowed_extensions": [
    "txt", "md", "pdf", "png", "jpg","jpeg", "json", "docx", "doc", "ppt", "pptx", "xls", "xlsx"
  ]
}
```
```json
default.json
{
  "allowed_paths": [
    "~/Desktop",
    "~/Downloads"
  ],
  "max_file_size": "20MB",
  "allowed_extensions": [
    "txt", "md", "pdf", "png", "jpg","jpeg", "json", "docx", "doc", "ppt", "pptx", "xls", "xlsx"
  ]
}
```

### Configure Claude Desktop as follows:

```json
{
  "mcpServers": {
    "python-filesystem": {
      "command": "C:\\Users\\username\\.local\\bin\\uv.EXE",
      "args":[
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

### Configure OpenCode as follows:

> Find your OpenCode global ".config" directory and open the "opencode.jsonc" file with your favorite IDE

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

### Configure Antigravity CLI as follows:

> Find your Antigravity CLI global standalone MCP Configuration file under ".gemini"->"config"->"mcp_config.json" and paste following mcp schema and adjust it to your system:

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

* `read_file`, `write_file`, `edit_file`
* `list_directory`, `create_directory`, `move_file`, `delete_file`
* `search_files`, `get_file_info`

All handlers are fully async and support detailed logging and secure validations.

---

## 🧪 Testing

```bash
pytest tests/
```

Includes unit tests for:

* File I/O
* Security module
* Server error handling
* Config parsing

### Experimental BoundaryAttest receipts

The server can optionally emit portable, Ed25519-signed BoundaryAttest Interop
Profile v0.1 receipts after successful `write_file`, `move_file`, and
`delete_file` operations. This proof of concept is off by default: ordinary
single-user/local MCP deployments generally get sufficient visibility from
their existing MCP and local logs, without signing-key or receipt-storage
overhead. The feature is aimed at shared, multi-tenant, enterprise, CI/CD, and
other trust-boundary environments where portable evidence may be useful.

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

Each successful covered operation writes one uniquely named JSON receipt. Clear
path references are relative to the matching configured allowed root, while the
signed `materialized_action_hash` binds the exact resolved internal path(s).
Writes bind the appended UTF-8 content digest plus exact pre/post file hashes;
moves bind the source and actual final destination (including an appended source
name when the destination argument is a directory); deletes bind the exact
pre-trash bytes and have no post-delete artifact at the original path. File
hashes are SHA-256 over raw bytes.

Verify with a public key obtained through a trusted path, optionally checking a
current artifact's exact bytes:

```bash
uv run --extra boundaryattest python src/verify_boundaryattest_receipt.py \
  RECEIPT.json EXPECTED_PUBLIC_KEY.pem --artifact FILE
```

A valid result proves only that the expected key signed the unchanged claim and,
when supplied, that the artifact bytes match the signed digest. It does not
prove truth, wisdom, authorization, policy compliance, signer trustworthiness,
runtime integrity, or production-grade key custody. The feature is experimental,
non-transactional, and external to the MCP server: if an action succeeds but
receipt emission fails, the action is not rolled back and the tool returns its
success message with a prominent attestation warning. This invited test
integration is not an endorsement, partnership, audit system, security
guarantee, or production key-management system.

---

## 🧯 Known Issue

We encountered a **Cool Tooling** issue due to agent/model capabilities and currently not supporting file types. Adjust the config policies for more file type support to solve the file type support problem.

### Temporary Workaround:

Ensure Python is globally available in your `$PATH` or use a wrapper script to launch the server. Also, double-check that `--config` paths are correct and readable.

---

## 🤝 Contributing

We welcome contributions! Whether it's bug fixes, new features, or documentation, feel free to fork the repo and submit a PR. Please check the `CONTRIBUTING.md` (coming soon) for guidelines.

---

## 📜 License

MIT License

---

## 🙌 Acknowledgements

* Inspired by the official [Filesystem MCP Server from Anthropic](https://www.anthropic.com/)
* Based on the MCP 1.0 Protocol Specification

```
