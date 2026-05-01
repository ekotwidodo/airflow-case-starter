#!/bin/bash
# Wrapper to handle Oracle PDB already exists error
# Ignore ORA-65012 error and continue

# Run the original entrypoint but filter out the PDB error
exec /usr/local/bin/docker-entrypoint.sh "$@" 2>&1 | while IFS= read -r line; do
    # Ignore the PDB already exists error
    if [[ "$line" == *"ORA-65012"* ]]; then
        echo "Ignoring PDB already exists error (ORA-65012) - continuing..."
        continue
    fi
    echo "$line"
done
