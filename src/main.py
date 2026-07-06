"""
Thread-Safe Filesystem Organizer MCP Server.
Provides secure, non-blocking, and concurrent filesystem operations.
"""

import os
import sys
import shutil
import asyncio
from typing import List, Dict, Any, Set
from pathlib import Path
from collections import defaultdict
from contextlib import asynccontextmanager
from send2trash import send2trash

from mcp.server.fastmcp import FastMCP
from utils.config import load_config

# 1. Load Configuration
config = load_config()
ALLOWED_PATHS: List[Path] = [Path(p).expanduser().resolve() for p in config.get("allowed_paths", [])]
MAX_FILE_SIZE: int = config.get("max_file_size", 20 * 1024 * 1024)
ALLOWED_EXTENSIONS: Set[str] = config.get("allowed_extensions", set())

# 2. Thread-Safety Mechanisms
PATH_LOCKS = defaultdict(asyncio.Lock)

def validate_path(path_str: str) -> Path:
    """
    Validates if the target path resides strictly within ALLOWED_PATHS.
    Resolves symbolic links to mitigate directory traversal exploits.
    """
    target_path = Path(path_str).expanduser().resolve()
    
    for base in ALLOWED_PATHS:
        if base == target_path or base in target_path.parents:
            return target_path
            
    raise ValueError(f"Access denied: Path '{target_path}' is out of allowed boundaries.")

def validate_file_policy(path: Path) -> None:
    """Enforces extension whitelist policies before write or move operations."""
    if ALLOWED_EXTENSIONS and path.suffix.lstrip('.').lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File extension '{path.suffix}' is restricted by system policy.")

@asynccontextmanager
async def acquire_deterministic_locks(*paths: Path):
    """
    Context manager to acquire multiple resource locks in a deterministic order.
    Sorting paths by string representation prevents classical dynamic circular deadlocks.
    """
    unique_keys = sorted(list({str(p) for p in paths}))
    locks = [PATH_LOCKS[key] for key in unique_keys]
    
    for lock in locks:
        await lock.acquire()
    try:
        yield
    finally:
        for lock in reversed(locks):
            lock.release()

# Initialize FastMCP Server
mcp = FastMCP("Filesystem Organizer Pro")

@mcp.tool()
async def list_files(path: str) -> List[str]:
    """
    Lists all files inside a directory asynchronously.
    
    Args:
        path (str): Target directory path.
    """
    dir_path = validate_path(path)
    
    def _list():
        if not dir_path.is_dir():
            raise NotADirectoryError(f"'{dir_path}' is not a valid directory.")
        return [f.name for f in dir_path.iterdir() if f.is_file()]
        
    return await asyncio.to_thread(_list)

@mcp.tool()
async def list_directories(path: str) -> List[str]:
    """
    Lists all subdirectories inside a directory safely.
    
    Args:
        path (str): Target directory path.
    """
    dir_path = validate_path(path)
    
    def _list_dirs():
        if not dir_path.is_dir():
            raise NotADirectoryError(f"'{dir_path}' is not a valid directory.")
        return [d.name for d in dir_path.iterdir() if d.is_dir()]
        
    return await asyncio.to_thread(_list_dirs)

@mcp.tool()
async def list_directory_content(path: str) -> List[str]:
    """
    Lists all directory entries (both files and folders) concurrently.
    
    Args:
        path (str): Target directory path.
    """
    dir_path = validate_path(path)
    
    def _list_all():
        if not dir_path.is_dir():
            raise NotADirectoryError(f"'{dir_path}' is not a valid directory.")
        return [entry.name for entry in dir_path.iterdir()]
        
    return await asyncio.to_thread(_list_all)

@mcp.tool()
async def get_file_info(path: str) -> Dict[str, Any]:
    """
    Retrieves safe system metadata for a file or directory.
    
    Args:
        path (str): Target filesystem object path.
    """
    target = validate_path(path)
    
    def _stat():
        if not target.exists():
            raise FileNotFoundError(f"Target object '{target}' does not exist.")
        stat = target.stat()
        return {
            "name": target.name,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "is_directory": target.is_dir()
        }
        
    return await asyncio.to_thread(_stat)

@mcp.tool()
async def read_file(path: str) -> str:
    """
    Reads plaintext content from an approved file safely via thread workers.
    
    Args:
        path (str): Path to the target file.
    """
    target = validate_path(path)
    
    async with PATH_LOCKS[str(target)]:
        def _read():
            if not target.is_file():
                raise FileNotFoundError(f"'{target}' is not a file or does not exist.")
            if target.stat().st_size > MAX_FILE_SIZE:
                raise ValueError("Target file size exceeds the configured max_file_size barrier.")
            with open(target, "r", encoding="utf-8") as f:
                return f.read()
                
        content = await asyncio.to_thread(_read)
        return content or "File is empty."

@mcp.tool()
async def write_file(path: str, content: str) -> str:
    """
    Writes or appends arbitrary string payloads to a file safely.
    
    Args:
        path (str): Output destination filepath.
        content (str): Text buffer data to commit.
    """
    target = validate_path(path)
    validate_file_policy(target)
    
    if len(content.encode('utf-8')) > MAX_FILE_SIZE:
        raise ValueError("Payload capacity violates configured max_file_size restrictions.")

    async with PATH_LOCKS[str(target)]:
        def _write():
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a+", encoding="utf-8") as f:
                f.write(content)
                
        await asyncio.to_thread(_write)
    return f"Successfully committed content to {target}"

@mcp.tool()
async def create_directory(path: str) -> str:
    """
    Creates structural directories recursively inside authorized scopes.
    
    Args:
        path (str): Directory tree path to construct.
    """
    target = validate_path(path)
    
    async with PATH_LOCKS[str(target)]:
        def _mkdir():
            target.mkdir(parents=True, exist_ok=True)
            
        await asyncio.to_thread(_mkdir)
    return f"Successfully spawned directory tree at {target}"

@mcp.tool()
async def delete_file(path: str) -> str:
    """
    Trashes a specified file asynchronously using operating system native recycling frameworks.
    
    Args:
        path (str): Target file configuration path.
    """
    target = validate_path(path)
    
    async with PATH_LOCKS[str(target)]:
        def _trash_file():
            if not target.is_file():
                raise FileNotFoundError(f"'{target}' does not exist or is not a file reference.")
            send2trash(str(target))
            
        await asyncio.to_thread(_trash_file)
    return f"Successfully dispatched file {target} to environment recycling bin."

@mcp.tool()
async def delete_directory(path: str) -> str:
    """
    Safely sends structural folders to the local desktop recycling bin system.
    
    Args:
        path (str): Target directory configuration path.
    """
    target = validate_path(path)
    
    async with PATH_LOCKS[str(target)]:
        def _trash_dir():
            if not target.is_dir():
                raise NotADirectoryError(f"'{target}' does not exist or is not a directory reference.")
            send2trash(str(target))
            
        await asyncio.to_thread(_trash_dir)
    return f"Successfully dispatched directory structure {target} to environment recycling bin."

@mcp.tool()
async def move_file(source: str, destination: str) -> str:
    """
    Moves files safely between distinct file coordinates under deterministic synchronization.
    
    Args:
        source (str): Source path reference.
        destination (str): Destination directory or explicit filepath.
    """
    src = validate_path(source)
    dest = validate_path(destination)
    
    if not dest.is_dir():
        validate_file_policy(dest)
    else:
        validate_file_policy(dest / src.name)

    async with acquire_deterministic_locks(src, dest):
        def _move():
            if not src.is_file():
                raise FileNotFoundError(f"Source object '{src}' is missing or invalid.")
            final_dest = dest / src.name if dest.is_dir() else dest
            shutil.move(str(src), str(final_dest))
        await asyncio.to_thread(_move)

    return f"Successfully moved '{src}' to '{dest}' coordinates."

@mcp.tool()
async def move_directory(source: str, destination: str) -> str:
    """
    Moves folder trees sequentially with transaction protection locks.
    
    Args:
        source (str): Original folder location.
        destination (str): Target destination base directory.
    """
    src = validate_path(source)
    dest = validate_path(destination)
    
    async with acquire_deterministic_locks(src, dest):
        def _move_dir():
            if not src.is_dir():
                raise NotADirectoryError(f"Source folder '{src}' is invalid.")
            final_dest = dest / src.name if dest.is_dir() else dest
            shutil.move(str(src), str(final_dest))
        await asyncio.to_thread(_move_dir)

    return f"Successfully migrated directory '{src}' context to '{dest}' environment."

@mcp.tool()
async def copy_file(source: str, destination: str) -> str:
    """
    Copies safe binary payloads to configured directories under file tracking blocks.
    
    Args:
        source (str): Master source file path.
        destination (str): Isolated destination path.
    """
    src = validate_path(source)
    dest = validate_path(destination)
    
    if not dest.is_dir():
        validate_file_policy(dest)
    else:
        validate_file_policy(dest / src.name)

    async with acquire_deterministic_locks(src, dest):
        def _copy():
            if not src.is_file():
                raise FileNotFoundError(f"Master source payload '{src}' unavailable.")
            final_dest = dest / src.name if dest.is_dir() else dest
            shutil.copy2(str(src), str(final_dest))
        await asyncio.to_thread(_copy)

    return f"Successfully copied asset tracking properties from '{src}' to '{dest}' targets."

@mcp.tool()
async def copy_directory(source: str, destination: str) -> str:
    """
    Performs recursive disk deep cloning across validated mount profiles safely.
    
    Args:
        source (str): Input master directory folder.
        destination (str): Isolated deployment branch node.
    """
    src = validate_path(source)
    dest = validate_path(destination)
    
    async with acquire_deterministic_locks(src, dest):
        def _copytree():
            if not src.is_dir():
                raise NotADirectoryError(f"Source folder infrastructure '{src}' invalid.")
            final_dest = dest / src.name
            shutil.copytree(str(src), str(final_dest), dirs_exist_ok=True)
        await asyncio.to_thread(_copytree)

    return f"Successfully replicated operational directory branch assets from '{src}' into '{dest}' domains."

@mcp.tool()
async def search_file(path: str, keyword: str) -> List[str]:
    """
    Filters and scans filesystem string assets targeting keyword strings non-blockingly.
    
    Args:
        path (str): Base root scanning tree initialization directory.
        keyword (str): Query filter properties matching targeted records.
    """
    dir_path = validate_path(path)
    
    def _search():
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Target scope node '{dir_path}' cannot generate tree walks.")
        
        matches = []
        for entry in dir_path.rglob("*"):
            if entry.is_file() and keyword in entry.name:
                matches.append(str(entry))
        return matches
        
    return await asyncio.to_thread(_search)

@mcp.tool()
async def get_allowed_paths() -> List[str]:
    """Retrieves list profiles configuring current system structural boundary points."""
    return [str(p) for p in ALLOWED_PATHS]

async def run_server():
    """
    Explicitly binds the FastMCP server instance to strict stdio streams
    ensuring stdout is purely used for JSON-RPC 2.0 validation.
    """
    from mcp.server.stdio import stdio_server
    
    # Force all diagnostic messages to stderr to keep stdout pure
    print("Binding Filesystem Organizer Pro to strict JSON-RPC stdio channels...", file=sys.stderr)
    
    async with stdio_server() as (read_stream, write_stream):
        # mcp.run() uses the internal protocol handler; we inject it directly into the streams
        await mcp._mcp_server.run(
            read_stream,
            write_stream,
            mcp._mcp_server.create_initialization_options()
        )

def main():
    """Main process application thread launcher context."""
    try:
        asyncio.run(run_server())
    except Exception as e:
        print(f"Server termination sequence triggered due to high level failure: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()