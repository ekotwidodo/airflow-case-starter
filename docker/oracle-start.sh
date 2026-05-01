#!/bin/bash
# Wrapper to handle Oracle PDB already exists error
set -e

# Start Oracle normally
exec /usr/local/bin/docker-entrypoint.sh "$@" 2>&1 | while IFS= read -r line; do
    # Ignore the PDB already exists error
    if echo "$line" | grep -q "ORA-65012"; then
        echo "Ignoring PDB already exists error (ORA-65012)"
        continue
    fi
    echo "$line"
done
