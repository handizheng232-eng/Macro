"""Explicit local research archive configuration; never discover sibling worktrees.

REPLAY_RESEARCH_ROOT is the absolute directory containing 美国宏观复盘, not a
stage directory. It selects INPUTS only. Code and public outputs stay in REPO_ROOT.
Unset preserves the historical in-repository layout. No files are copied.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ENV = 'REPLAY_RESEARCH_ROOT'


def research_root():
    value = os.environ.get(ARCHIVE_ENV)
    if value is None:
        return REPO_ROOT
    path = Path(value)
    if not value.strip() or not path.is_absolute() or not path.is_dir():
        raise ValueError(f'{ARCHIVE_ENV} must name an existing absolute directory')
    return path.resolve()


def require_writable_output(path):
    """Resolve symlinks/parent segments before allowing any output mutation."""
    archive = research_root()
    if archive != REPO_ROOT and Path(path).resolve().is_relative_to(archive):
        raise ValueError('Configured external research archive is read-only')
