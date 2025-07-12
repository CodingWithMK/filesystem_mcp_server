# 🗂️ Python MCP Filesystem Server

This project is a Python-based MCP (Model Context Protocol) server that allows Claude Desktop to perform secure and controlled local filesystem operations via natural language commands. It bridges the gap between conversational AI and direct file management by implementing the MCP 1.0 protocol with full support for read/write operations, file system traversal, metadata extraction, and more.

---

## 🚀 Features

- ✅ Fully compatible with Claude Desktop
- 📂 Read, write, move, delete, and search files
- 🔒 Path validation & permission control
- 🧠 JSON-RPC 2.0 communication over stdin/stdout
- 🔄 Asynchronous architecture with `asyncio`
- 🧪 Unit & integration tests included

---

## 🧰 Tech Stack

- **Python** 3.11
- **AsyncIO**, **Pathlib**, **JSON**, **Typing**
- **Claude Desktop** (latest version)
- MCP Protocol (v1.0) implementation

---

## 📦 Installation

```bash
git clone https://github.com/yourusername/python-mcp-filesystem-server.git
cd python-mcp-filesystem-server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
````

---

## ⚙️ Configuration

Edit `config/server_config.json` to define allowed paths and other settings:

```json
{
  "security": {
    "allowed_paths": ["/Users/you/Documents", "/Users/you/Desktop"],
    "max_file_size": "10MB",
    "allowed_extensions": [".txt", ".md", ".py", ".json"],
    "enable_audit_log": true
  }
}
```

Configure Claude Desktop as follows:

```json
{
  "mcpServers": {
    "python-filesystem": {
      "command": "python",
      "args": [
        "/absolute/path/to/src/server.py",
        "--config",
        "/absolute/path/to/config/server_config.json"
      ]
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

---

## 🧯 Known Issue

We encountered a **server startup failure** caused by Claude Desktop not correctly spawning the Python subprocess for MCP communication. This is likely due to how Claude resolves binary paths, especially on Windows or when the virtual environment is not activated globally.

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
