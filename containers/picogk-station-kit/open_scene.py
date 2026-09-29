"""Open an explicitly selected local scene in the native Kit editor."""

import asyncio
import os
from pathlib import Path

import omni.usd


async def open_scene():
    value = os.environ.get("STATION_SCENE", "")
    if not value:
        return
    path = Path(value).resolve(strict=True)
    if path.suffix.lower() not in {".usd", ".usda", ".usdc"}:
        raise ValueError("STATION_SCENE must be a USD file")
    success, error = await omni.usd.get_context().open_stage_async(str(path))
    if not success:
        raise RuntimeError(f"Could not open station scene: {error}")
    print("Station scene opened; save edits as a separate working USD layer.")


asyncio.ensure_future(open_scene())
