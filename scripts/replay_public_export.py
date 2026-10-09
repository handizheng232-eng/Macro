"""Strip host-specific archive locations from the public replay data export."""
from pathlib import Path, PurePosixPath, PureWindowsPath


def _public_path(value: str, root: Path) -> str:
    windows = PureWindowsPath(value)
    if not windows.is_absolute() and not PurePosixPath(value).is_absolute():
        return value
    path = Path(value)
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        # The private PDF remains cited by title and hash, never by machine path.
        return windows.name if windows.is_absolute() else path.name


def public_snapshot(data: dict, root: Path) -> dict:
    """Return a public copy; keep the full paths in the local research artifact."""
    def clean(value, key=''):
        if isinstance(value, dict):
            return {name: clean(item, name) for name, item in value.items()}
        if isinstance(value, list):
            return [clean(item, key.removesuffix('s')) for item in value]
        if isinstance(value, str) and key.lower().endswith('path'):
            return _public_path(value, root)
        return value

    return clean(data)
