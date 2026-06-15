#!/usr/bin/env bash
# Convenience wrapper: ./run.sh run data/samples/   |   ./run.sh eval
cd "$(dirname "$0")"
PYTHONPATH=src python -m cli "$@"
