"""Data models used by web shipment tests."""

from dataclasses import dataclass

_RAID_LABELS = {
    (0, 0): "None",
    (0, 5): "raid5",
    (0, 6): "raid6",
}

_STORAGE_TYPE_LABELS = {
    "zfs": "File System",
    "block": "Block Store",
}


@dataclass(frozen=True)
class StorageVariant:
    """Represents one storage-format permutation from the shipment matrix."""

    filesystem: str
    encryption: bool
    raid_mode: tuple[int, int]
    io_size_kb: int
    data_sync: str
    dedup: bool
    compression: bool
    object_storage: bool
    mount_on_reboot: bool

    @property
    def id(self) -> str:
        """Return a deterministic id for pytest parameter display."""
        return (
            f"fs={self.filesystem}|enc={self.encryption}|raid={self.raid_mode[0]}_{self.raid_mode[1]}"
            f"|io={self.io_size_kb}|sync={self.data_sync}|dedup={self.dedup}|cmp={self.compression}"
            f"|obj={self.object_storage}"
        )

    @property
    def raid_label(self) -> str:
        """Return the UI dropdown label for this variant's raid mode."""
        if self.raid_mode not in _RAID_LABELS:
            raise ValueError(f"Unsupported raid mode: {self.raid_mode}")
        return _RAID_LABELS[self.raid_mode]

    @property
    def storage_type_label(self) -> str:
        """Return the UI dropdown label for this variant's filesystem/storage type."""
        if self.filesystem not in _STORAGE_TYPE_LABELS:
            raise ValueError(f"Unsupported filesystem/storage type: {self.filesystem}")
        return _STORAGE_TYPE_LABELS[self.filesystem]
