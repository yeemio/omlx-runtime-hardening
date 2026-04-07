# omlx-runtime-hardening

Runtime memory safety toolkit for [oMLX](https://github.com/nicholasgasior/omlx) on Apple Silicon.

## Problem

oMLX's multi-model switching on Apple Silicon (unified memory) has a critical gap:

**`unload ≠ reclaim`** — the engine pool reduces `estimated_size` after unloading a model, but does not verify that Metal buffers and KV caches have actually been released. Over time, this causes silent memory pressure buildup, eventually triggering macOS swap storms or OOM kills.

This toolkit patches oMLX 0.3.4 with swap-safe memory barriers and provides upgrade-survival tooling so patches persist across `brew upgrade`.

## What's Included

| File | Purpose |
|------|---------|
| `patch-guard.sh` | Check whether the swap-safe patch is intact, drifted, or missing |
| `apply-full-patch.py` | Restore the full patch from embedded payloads (safe: rejects unknown file states) |
| `validate-swap-safe-patch.py` | Structural validation of patch anchor points across 4 files |
| `omlx-safe-serve` | Startup wrapper: guard → auto-repair → re-check → launch |

## Patch Coverage

4 files patched in oMLX 0.3.4:

- **`engine_pool.py`** — Three-phase pre-load eviction (LRU → emergency reclaim → restart), active request protection, real-diff settle barrier, eviction diagnostics
- **`process_memory_enforcer.py`** — Watermark policy (green/yellow/red/fatal), pre-load budget with cache deduction and engine-type overhead scaling, unified executor
- **`admin/routes.py`** — `GET /admin/api/restart-status` with watermark, utilization, model details, last eviction; `POST /admin/api/restart-engine`
- **`engine/batched.py`** — Safe engine close with hasattr guard

## Quick Start

```bash
# 1. Check current patch state
bash patch-guard.sh

# 2. Apply patch (if exit code was 3 = missing/incomplete)
python3 apply-full-patch.py

# 3. Validate structural integrity
python3 validate-swap-safe-patch.py

# 4. Start with guard wrapper
./omlx-safe-serve --model-dir /path/to/models --port 8020
```

## Upgrade Playbook

After `brew upgrade omlx`:

```bash
# Check if patch survived
bash patch-guard.sh

# If exit 2 (version changed): patch needs porting to new version
# If exit 3 (patch missing): re-apply
python3 apply-full-patch.py

# Verify
python3 validate-swap-safe-patch.py
```

Or just use `omlx-safe-serve` — it runs this sequence automatically before every launch.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PATCH_VERSION` | `0.3.4` | Expected oMLX version |
| `OMLX_CELLAR_BASE` | `/opt/homebrew/Cellar/omlx` | Homebrew cellar path |
| `OMLX_SITE_OVERRIDE` | (auto) | Override site-packages path for testing |
| `OMLX_PYTHON` | `.../omlx/0.3.4/libexec/bin/python` | Python interpreter |
| `SAFE_PATH` | homebrew + system defaults | PATH for sanitized launch |

## Verified On

- Mac17,6 / Apple M5 Max / 128GB unified memory
- macOS 26.4 (25E246)
- oMLX 0.3.4 (Homebrew)
- MLX 0.24.x

## Test Results

- High-watermark switching (27B ↔ 120B): stable, zero drift
- 50-cycle soak test (27B ↔ 35B): zero accumulation after cycle 2, zero restarts
- Guard toolchain: all bad-state injection scenarios pass

## Known Limitation

- MLX/Metal `Device::Device()` can crash with `NSRangeException` when launched from sandboxed or restricted execution contexts (e.g., `CODEX_SANDBOX=1`). This is an upstream MLX issue, not a toolkit bug. Use a normal terminal session for startup.

## License

MIT
