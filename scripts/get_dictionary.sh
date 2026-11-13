#!/usr/bin/env bash
# Download the pt_BR Hunspell dictionary (LibreOffice, VERO) to data/raw/.
# Step 2 reads it from `dictionary: data/raw/pt_BR` in config.yaml.
# data/raw/ is in .gitignore: the dictionary is downloaded, never committed.
set -euo pipefail

BASE_URL="https://raw.githubusercontent.com/LibreOffice/dictionaries/master/pt_BR"
TARGET="$(cd "$(dirname "$0")/.." && pwd)/data/raw"

mkdir -p "$TARGET"
for file in pt_BR.dic pt_BR.aff; do
    curl --fail --silent --show-error --location "$BASE_URL/$file" --output "$TARGET/$file"
    echo "Wrote $TARGET/$file"
done
