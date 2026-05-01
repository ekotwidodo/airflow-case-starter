#!/usr/bin/env python3
"""
Wrapper for Oracle container to ignore ORA-65012 (PDB already exists) error
"""
import subprocess
import sys

proc = subprocess.Popen(
    ["/usr/local/bin/docker-entrypoint.sh"] + sys.argv[1:],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

for line in proc.stdout:
    decoded = line.decode('utf-8', errors='ignore')
    if 'ORA-65012' not in decoded:
        sys.stdout.write(decoded)
        sys.stdout.flush()

proc.wait()
sys.exit(proc.returncode)
