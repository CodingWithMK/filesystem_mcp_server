# test_server.py
import subprocess
import sys

cmd = [
    sys.executable,
    "C:\\Users\\musab\\Documents\\filesystem_mcp_server\\src\\main.py"
]

process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
stdout, stderr = process.communicate(timeout=5)

print("STDOUT:", stdout)
print("STDERR:", stderr)
print("Return code:", process.returncode)