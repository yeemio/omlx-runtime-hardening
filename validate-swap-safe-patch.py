#!/usr/bin/env python3
"""
Validate Swap-Safe Memory Patch

Validates that the swap-safe patch was correctly applied to oMLX.

Usage:
    python3 validate-swap-safe-patch.py [--omlx-version VERSION] [--site-packages PATH]

Exit codes:
    0 = All validations pass
    1 = Patch not applied or validation failed
"""

import argparse
import subprocess
import sys
from pathlib import Path

OMLX_CELLAR_BASE = Path("/opt/homebrew/Cellar/omlx")


def get_omlx_version(default: str = "0.3.4") -> str:
    """Detect installed oMLX version."""
    try:
        result = subprocess.run(
            ["omlx-cli", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    for cellars in OMLX_CELLAR_BASE.glob("*"):
        if cellars.is_dir():
            return cellars.name
    return default


def get_site_packages(version: str) -> Path:
    return OMLX_CELLAR_BASE / version / "libexec/lib/python3.11/site-packages/omlx"


def validate_engine_pool(site_packages: Path) -> tuple[bool, str]:
    """Validate engine_pool.py patch."""
    file_path = site_packages / "engine_pool.py"
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    content = file_path.read_text()

    checks = {
        "_restart_requested": "_restart_requested flag",
        "def restart_requested": "restart_requested property",
        "def restart_reason": "restart_reason property",
        "def clear_restart_request": "clear_restart_request method",
        "Emergency reclaim failed": "Emergency reclaim in barrier",
        "self._restart_requested = True": "Setting restart_requested flag",
        "pre_load_check": "pre_load_check integration",
        "action.value": "action.value usage (WatermarkAction duck typing)",
        "Evicting LRU model": "Hot-cache LRU eviction in watermark check",
        "watermark_before": "Pre-load summary logging",
        "freed_model_est_gb": "Eviction metrics in summary log",
        "if e.engine.has_active_requests():": "P0: Active request protection in LRU victim",
        "Skipping victim '{mid}': has active requests": "P0: Active request skip log",
        "min_expected_freed = max(0, entry.estimated_size - settle_tolerance)": "P1: Real-diff settle barrier",
        "actual_freed = pre_unload_active - active_now": "P1: Freed delta tracking in settle barrier",
        "self._last_eviction: dict | None = None": "P3: Last eviction init",
        "def get_loaded_model_details(self) -> list[dict]:": "P3: Loaded model details method",
        "[swap-safe] Eviction candidates:": "P3: Candidate list logging",
    }

    failed = []
    for check, desc in checks.items():
        if check not in content:
            failed.append(desc)

    if failed:
        return False, f"Missing: {', '.join(failed)}"
    return True, "All checks passed"


def validate_process_memory_enforcer(site_packages: Path) -> tuple[bool, str]:
    """Validate process_memory_enforcer.py patch."""
    file_path = site_packages / "process_memory_enforcer.py"
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    content = file_path.read_text()

    checks = {
        "class MemoryWatermark(Enum)": "MemoryWatermark enum",
        "class WatermarkAction(Enum)": "WatermarkAction enum",
        "def get_watermark_level": "get_watermark_level method",
        "def get_memory_diagnostics": "get_memory_diagnostics method",
        "async def pre_load_check": "pre_load_check method",
        "async def emergency_reclaim": "emergency_reclaim method",
        "from_utilization": "MemoryWatermark.from_utilization",
        "get_mlx_executor": "P1: Unified executor in emergency_reclaim",
        "effective_current": "P2: Cache-deducted effective current",
        "overhead_pct": "P2: Engine-type-scaled overhead",
    }

    failed = []
    for check, desc in checks.items():
        if check not in content:
            failed.append(desc)

    if failed:
        return False, f"Missing: {', '.join(failed)}"
    return True, "All checks passed"


def validate_admin_routes(site_packages: Path) -> tuple[bool, str]:
    """Validate admin/routes.py patch."""
    file_path = site_packages / "admin" / "routes.py"
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    content = file_path.read_text()

    checks = {
        "/api/restart-status": "GET /api/restart-status endpoint",
        "/api/restart-engine": "POST /api/restart-engine endpoint",
        "restart_requested": "restart_requested in endpoint",
        "engine_pool.restart_requested": "Accessing restart_requested from engine_pool",
        "effective_active_gb": "P3: Effective active memory in restart-status",
        "watermark_str": "P3: Watermark in restart-status",
        "loaded_model_details": "P3: Model details in restart-status",
        "last_eviction": "P3: Last eviction in restart-status",
    }

    failed = []
    for check, desc in checks.items():
        if check not in content:
            failed.append(desc)

    if failed:
        return False, f"Missing: {', '.join(failed)}"
    return True, "All checks passed"


def validate_batched_engine(site_packages: Path) -> tuple[bool, str]:
    """Validate engine/batched.py patch."""
    file_path = site_packages / "engine" / "batched.py"
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    content = file_path.read_text()

    checks = {
        "engine.close()": "engine.close() call in stop()",
        "swap-safe": "swap-safe comment marker",
    }

    failed = []
    for check, desc in checks.items():
        if check not in content:
            failed.append(desc)

    if failed:
        return False, f"Missing: {', '.join(failed)}"
    return True, "All checks passed"


def main():
    parser = argparse.ArgumentParser(description="Validate swap-safe patch")
    parser.add_argument(
        "--omlx-version", default=None, help="oMLX version (default: auto-detect)"
    )
    parser.add_argument(
        "--site-packages",
        default=None,
        help="Explicit oMLX site-packages path to validate",
    )
    args = parser.parse_args()

    version = args.omlx_version or get_omlx_version()
    site_packages = Path(args.site_packages) if args.site_packages else get_site_packages(version)

    print(f"\nSwap-Safe Memory Patch Validation")
    print(f"=" * 50)
    print(f"oMLX version: {version}")
    print(f"Site packages: {site_packages}")
    print()

    if not site_packages.exists():
        print(f"✗ Site packages directory not found: {site_packages}")
        return 1

    validators = {
        "engine_pool.py": validate_engine_pool,
        "process_memory_enforcer.py": validate_process_memory_enforcer,
        "admin/routes.py": validate_admin_routes,
        "engine/batched.py": validate_batched_engine,
    }

    all_passed = True
    for name, validator in validators.items():
        passed, message = validator(site_packages)
        status = "✓" if passed else "✗"
        print(f"  {status} {name}: {message}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✓ All validations passed - swap-safe patch is correctly applied")
        return 0
    else:
        print("✗ Some validations failed - patch may not be correctly applied")
        return 1


if __name__ == "__main__":
    sys.exit(main())
