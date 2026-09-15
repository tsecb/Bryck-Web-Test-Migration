"""Generate storage variants from config while preserving shipment constraints."""

from __future__ import annotations

from typing import Iterable

from web_shipment.core.models import StorageVariant


INVALID_DEDUP_RAID = {(0, 5), (0, 6)}


def build_storage_variants(matrix: dict) -> list[StorageVariant]:
    """Build a deterministic list of test variants from matrix config."""
    variants: list[StorageVariant] = []
    mount_on_reboot = bool(matrix.get("mount_on_reboot", False))

    for filesystem in matrix.get("filesystem", ["zfs"]):
        for encryption in matrix.get("encryption", [True, False]):
            for raid in _to_raid_modes(matrix.get("raid_levels", [[0, 5]])):
                for io_size in matrix.get("io_size_kb", [512]):
                    for sync_mode in matrix.get("data_sync", ["application sync"]):
                        for dedup in matrix.get("dedup", [False]):
                            for compression in matrix.get("compression", [False]):
                                if dedup and compression:
                                    continue
                                if dedup and raid in INVALID_DEDUP_RAID:
                                    continue
                                for object_storage in matrix.get("object_storage", [False]):
                                    variants.append(
                                        StorageVariant(
                                            filesystem=filesystem,
                                            encryption=bool(encryption),
                                            raid_mode=raid,
                                            io_size_kb=int(io_size),
                                            data_sync=str(sync_mode),
                                            dedup=bool(dedup),
                                            compression=bool(compression),
                                            object_storage=bool(object_storage),
                                            mount_on_reboot=mount_on_reboot,
                                        )
                                    )
    return variants


def _to_raid_modes(raw_raid_modes: Iterable[Iterable[int]]) -> list[tuple[int, int]]:
    modes: list[tuple[int, int]] = []
    for value in raw_raid_modes:
        pair = tuple(value)
        if len(pair) != 2:
            raise ValueError(f"Raid mode must contain exactly two numbers: {value}")
        modes.append((int(pair[0]), int(pair[1])))
    return modes
