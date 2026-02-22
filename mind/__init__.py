"""Mind CLI - Time logging and reporting automation."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("mind-cli")
except PackageNotFoundError:  # running from source without install
    __version__ = "0.0.0-dev"

__app_name__ = "mind"
