"""Mind CLI - Time logging and reporting automation."""

import os

import toml

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pyproject = os.path.join(root, "pyproject.toml")
if os.path.exists(pyproject):
    data = toml.load(pyproject)
    __version__ = data["project"]["version"]
else:
    __version__ = "0.0.0-dev"

__app_name__ = "mind"
