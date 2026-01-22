#!/bin/bash
prompt="say hello"
output_file="out_bg.json"
echo "Running opencode in background..."
opencode run --prompt "$prompt" --format json > "$output_file" 2>&1 &
pid=$!
wait $pid
echo "Done. Exit code: $?"
cat "$output_file"
