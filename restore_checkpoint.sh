#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <checkpoint_id> [target_dir]"
  exit 1
fi

CHECKPOINT_ID="$1"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="${2:-$ROOT_DIR}"
CHECKPOINT_DIR="$ROOT_DIR/backups/iteration_checkpoints/$CHECKPOINT_ID"
SNAPSHOT_FILE="$CHECKPOINT_DIR/snapshot_src.tar.gz"

if [[ ! -d "$CHECKPOINT_DIR" ]]; then
  echo "Checkpoint not found: $CHECKPOINT_DIR"
  exit 1
fi

if [[ ! -f "$SNAPSHOT_FILE" ]]; then
  echo "Snapshot not found: $SNAPSHOT_FILE"
  exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Target directory not found: $TARGET_DIR"
  exit 1
fi

echo "Restoring checkpoint: $CHECKPOINT_ID"
echo "Target directory: $TARGET_DIR"

tar -xzf "$SNAPSHOT_FILE" -C "$TARGET_DIR"
echo "Restore complete."
