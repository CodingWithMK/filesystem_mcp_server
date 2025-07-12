#!/usr/bin/env python3
"""
Filesystem Organizer MCP Server
Prototype implementation using FastMCP with basic filesystem tools.
"""
import os
import sys
import shutil
import asyncio
from typing import List, Dict, Any
from send2trash import send2trash
from mcp.server.fastmcp import FastMCP
from utils.config import load_config


# Load configuration for allowed paths
config = load_config()
# Convert Path objects to absolute string paths
ALLOWED_PATHS: List[str] = [os.path.abspath(os.path.expanduser(str(p))) for p in config.get("allowed_paths", [])]
MAX_FILE_SIZE = config.get("max_file_size")
ALLOWED_EXTENSIONS = set(config.get("allowed_extensions", []))


# Debug: print allowed paths to stderr
print(f"Allowed paths loaded: {ALLOWED_PATHS}", file=sys.stderr)

# Validator to ensure access within allowed paths
def validate_path(path: str) -> str:
    """
    Ensure given path is within allowed_paths; returns normalized absolute path.
    """
    path = os.path.abspath(os.path.expanduser(path))
    for base in ALLOWED_PATHS:
        try:
            if os.path.commonpath([path, base]) == base:
                return path
        except ValueError:
            continue
    raise ValueError(f"Access to path '{path}' is not allowed.")

# Initialize MCP server
mcp = FastMCP("Filesystem Organizer")

@mcp.tool()
def list_files(path: str) -> List[str]:
    """
    List all files in the specified directory.

    Args:
        path (str): Path to the directory.

    Returns:
        List[str]: List of filenames.
    """
    dir_path = validate_path(path)
    files = [file for file in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, file))]
    return files

@mcp.tool()
def list_directories(path: str) -> List[str]:
    """
    List all directories in the specified directory.

    Args:
        path (str): Path to the directory.

    Returns:
        List[str]: List of directory names.
    """
    dir_path = validate_path(path)
    directories = [dir for dir in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, dir))]
    return directories

@mcp.tool()
def list_directory_content(path: str) -> List[str]:
    """
    List all entries (files and directories) in the specified directory.

    Args:
        path (str): Path to the directory.

    Returns:
        List[str]: List of entry names.
    """
    dir_path = validate_path(path)
    dir_content = os.listdir(dir_path)
    return dir_content

@mcp.tool()
def get_file_info(path: str) -> Dict[str, Any]:
    """
    Get metadata for a file or directory.

    Args:
        path (str): Path to the file or directory.

    Returns:
        Dict[str, Any]: Dictionary with name, size, and modification time.
    """
    file_path = validate_path(path)
    file_metadata = {
        "name": os.path.basename(file_path),
        "size": os.path.getsize(file_path),
        "modified": os.path.getmtime(file_path)
    }
    return file_metadata

@mcp.tool()
def read_file(path: str) -> str:
    """
    Read and return the content of a file.

    Args:
        path (str): Path to the file.

    Returns:
        str: File content as text.
    """
    file_path = validate_path(path)
    with open(file_path, "r") as file:
        content = file.read()
    return content or "File is empty."

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """
    Write content to a file.

    Args:
        path (str): Path to the file.
        content (str): Content to write into the file.

    Returns:
        str: Confirmation message.
    """
    file_path = validate_path(path)
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    with open(file_path, "a+") as f:
        f.write(content)
    return f"Successfully wrote content to {file_path}"

@mcp.tool()
def delete_file(path: str) -> str:
    """
    Delete a file by moving it to the trash (send to recycle bin).

    Args:
        path (str): Path to the file to delete.

    Returns:
        str: Confirmation message indicating the file was trashed.
    """
    file_path = validate_path(path)
    send2trash(file_path)
    return f"Sent file successfully to trash {file_path}"

@mcp.tool()
def delete_directory(path: str) -> str:
    """
    Delete a directory by moving it to the trash (send to recycle bin).

    Args:
        path (str): Path to the directory to delete.

    Returns:
        str: Confirmation message indicating the directory was trashed.
    """
    dir_path = validate_path(path)
    send2trash(dir_path)
    return f"Sent directory successfully to trash {dir_path}"

@mcp.tool()
def create_directory(path: str) -> str:
    """
    Create a new directory.

    Args:
        path (str): Path to the directory to create.

    Returns:
        str: Confirmation message indicating the directory was created.
    """
    dir_path = validate_path(path)
    os.makedirs(dir_path, exist_ok=True)
    return f"Successfully created directory {dir_path}"

@mcp.tool()
def move_file(source: str, destination: str) -> str:
    """
    Move a file from one location to another.

    Args:
        source (str): Path to the source file.
        destination (str): Path to the destination directory.

    Returns:
        str: Confirmation message indicating the file was moved.
    """
    src = validate_path(source)
    dest = validate_path(destination)
    shutil.move(src, dest)
    return f"Successfully moved file {src} to {dest}"

@mcp.tool()
def move_directory(source: str, destination: str) -> str:
    """
    Move a directory from one location to another.

    Args:
        source (str): Path to the source directory.
        destination (str): Path to the destination directory.

    Returns:
        str: Confirmation message indicating the directory was moved.
    """
    src = validate_path(source)
    dest = validate_path(destination)
    shutil.move(src, dest)
    return f"Successfully moved directory {src} to {dest}"

@mcp.tool()
def copy_file(source: str, destination: str) -> str:
    """
    Copy a file from one location to another.

    Args:
        source (str): Path to the source file.
        destination (str): Path to the destination directory.

    Returns:
        str: Confirmation message indicating the file was copied.
    """
    src = validate_path(source)
    dest = validate_path(destination)
    shutil.copy(src, dest)
    return f"Successfully copied file {src} to {dest}"

@mcp.tool()
def copy_directory(source: str, destination: str) -> str:
    """
    Copy a directory from one location to another.

    Args:
        source (str): Path to the source directory.
        destination (str): Path to the destination directory.

    Returns:
        str: Confirmation message indicating the directory was copied.
    """
    src = validate_path(source)
    dest = validate_path(destination)
    shutil.copytree(src, dest)
    return f"Successfully copied directory {src} to {dest}"

@mcp.tool()
def search_file(path: str, keyword: str) -> List[str]:
    """
    Search for files containing the specified keyword in the specified directory.

    Args:
        path (str): Path to the directory.
        keyword (str): Keyword to search for.

    Returns:
        List[str]: List of file paths containing the keyword.
    """
    dir_path = validate_path(path)
    files = [file for file in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, file)) and keyword in file]
    return files

@mcp.tool()
def get_allowed_paths() -> List[str]:
    """Return a list of allowed paths."""
    return ALLOWED_PATHS

def main():
    """Entry point for the MCP server."""
    import asyncio
    print("Starting Filesystem Organizer MCP Server...", file=sys.stderr)
    print(f"Python version: {sys.version}", file=sys.stderr)
    print(f"Working directory: {os.getcwd()}", file=sys.stderr)
    
    try:
        asyncio.run(mcp.run())
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()