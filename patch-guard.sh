#!/usr/bin/env bash
# Copyright 2026 yeemio
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# SPDX-License-Identifier: Apache-2.0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PATCH_VERSION="${PATCH_VERSION:-0.3.4}"
CELLAR_BASE="${OMLX_CELLAR_BASE:-/opt/homebrew/Cellar/omlx}"
SITE_DEFAULT="${CELLAR_BASE}/${PATCH_VERSION}/libexec/lib/python3.11/site-packages/omlx"
SITE="${OMLX_SITE_OVERRIDE:-$SITE_DEFAULT}"
VALIDATE_SCRIPT="${VALIDATE_SCRIPT:-${SCRIPT_DIR}/validate-swap-safe-patch.py}"
QUIET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --quiet) QUIET=1; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

say() {
  [[ "$QUIET" -eq 1 ]] || echo "$@"
}

expected_hash() {
  case "$1" in
    "engine_pool.py") echo "37395b80a96538fe0dd70d04239956970567e4c47bcedd521d922c8d90e70d38" ;;
    "process_memory_enforcer.py") echo "4eb038b0982251251b02d52b76f17d3b3e286758d7573702d41b773dfb6cb468" ;;
    "admin/routes.py") echo "a23b6b74ea498ecb2ac561aa0ea69721ab0637e014729c67555cffb7b9739a34" ;;
    "engine/batched.py") echo "e8f44e2fa3530a3cea85cbaf32b45ff6dadfb3fbfc2b82eae22de55ce58bd291" ;;
    *) return 1 ;;
  esac
}

if [[ -z "${OMLX_SITE_OVERRIDE:-}" ]]; then
  if [[ ! -d "$CELLAR_BASE" ]]; then
    say "oMLX not installed under $CELLAR_BASE"
    exit 1
  fi
  INSTALLED_VERSION="$(ls "$CELLAR_BASE" 2>/dev/null | sort -V | tail -1)"
  if [[ -z "$INSTALLED_VERSION" ]]; then
    say "Unable to detect installed oMLX version"
    exit 1
  fi
  if [[ "$INSTALLED_VERSION" != "$PATCH_VERSION" ]]; then
    say "oMLX version changed: expected $PATCH_VERSION, found $INSTALLED_VERSION"
    exit 2
  fi
fi

all_match=1
for rel in "engine_pool.py" "process_memory_enforcer.py" "admin/routes.py" "engine/batched.py"; do
  target="$SITE/$rel"
  if [[ ! -f "$target" ]]; then
    say "Missing file: $target"
    exit 3
  fi
  actual="$(shasum -a 256 "$target" | awk '{print $1}')"
  expected="$(expected_hash "$rel")"
  if [[ "$actual" != "$expected" ]]; then
    all_match=0
    say "Hash drift: $rel"
  fi
done

if [[ "$all_match" -eq 1 ]]; then
  say "oMLX swap-safe patch intact"
  exit 0
fi

if python3 "$VALIDATE_SCRIPT" --omlx-version "$PATCH_VERSION" --site-packages "$SITE" >/tmp/omlx-patch-guard.validate.$$ 2>&1; then
  say "Hash drift detected but structural validation passed"
  [[ "$QUIET" -eq 1 ]] || cat /tmp/omlx-patch-guard.validate.$$
  rm -f /tmp/omlx-patch-guard.validate.$$
  exit 0
fi

[[ "$QUIET" -eq 1 ]] || cat /tmp/omlx-patch-guard.validate.$$
rm -f /tmp/omlx-patch-guard.validate.$$
say "Patch validation failed"
exit 3
