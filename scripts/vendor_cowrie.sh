#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

COWRIE_TAG="${COWRIE_TAG:-v3.0.12}"

rm -rf vendor/cowrie
mkdir -p vendor
git clone --branch "$COWRIE_TAG" --depth 1 https://github.com/cowrie/cowrie.git vendor/cowrie

sed "s/__COWRIE_VERSION__/${COWRIE_TAG#v}/" patches/cowrie-Dockerfile > vendor/cowrie/docker/Dockerfile

echo "Vendored cowrie ${COWRIE_TAG} into vendor/cowrie with the patched docker/Dockerfile."
echo "Upstream bug reference: as of ${COWRIE_TAG}, docker/Dockerfile comments out the"
echo "'pip install -e .' step needed to generate src/cowrie/_version.py, so the stock"
echo "image crash-loops with 'Cowrie is not installed.' Our patch reorders the build so"
echo "the source is installed before pip is removed from the venv."
