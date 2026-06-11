#!/bin/bash

# JayaHo Appaji - Generate Parsed JSONs from 5G YAMLs
# Author: Babai with ChatGPT
# Date: 2025-06-10

# -------------------------------------------
# Paths
YAML_DIR="../Yaml-Files/5GC_APIs"
JSON_DIR="../Parsed-JSON"

# Create output dir if not exists
mkdir -p "$JSON_DIR"

echo "========================================"
echo "Deleting old JSONs..."
rm -f "$JSON_DIR"/*.json
rm -f ../index.json
echo "Old JSONs deleted."

echo "Generating Parsed JSONs from YAMLs"
echo "YAML DIR:  $YAML_DIR"
echo "JSON DIR:  $JSON_DIR"
echo "========================================"

# Loop through YAML files
for i in "$YAML_DIR"/*.yaml; do
    filename=$(basename "$i" .yaml)
    jsonfile="$JSON_DIR/$filename.json"

    echo "----------------------------------------"
    echo "Processing: $filename.yaml"

    echo "Bundling → $filename.json"
    swagger-cli bundle "$i" --outfile "$jsonfile" --type json
    if [ $? -eq 0 ]; then
        echo "✅ Success → $jsonfile"
    else
        echo "❌ ERROR → Failed to bundle $i"
    fi
done

echo "========================================"
echo "All YAMLs processed."
echo "========================================"