# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

# Sourced by the scripts here. heavy <seconds> <command...> runs 1 heavy step with a time limit;
# the alarm reaches the command itself. $HEAVY_SERIAL, if set, names a lock script, called as
# HEAVY_SLOTS=1 $HEAVY_SERIAL <dir> <command...>, that runs the command once it holds the lock.
LOCK=${HEAVY_SERIAL:-}

heavy() {
  limit=$1; shift
  if [ -x "$LOCK" ]; then
    HEAVY_SLOTS=1 "$LOCK" "$PWD" perl -e 'alarm shift; exec @ARGV' "$limit" "$@"
  else
    perl -e 'alarm shift; exec @ARGV' "$limit" "$@"
  fi
}
