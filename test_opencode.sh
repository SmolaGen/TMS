#!/bin/bash
prompt="say hello"
output_file="out.json"
echo "Running opencode..."
opencode run "$prompt" --format json > "$output_file" 2>&1
echo "Done. Exit code: $?"
cat "$output_file"
