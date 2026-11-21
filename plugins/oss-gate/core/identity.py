"""Compare package identities without treating a different release as equivalent."""

import re

from packaging.version import InvalidVersion, Version


def valid_pypi_version(value):
    if not isinstance(value, str) or not value:
        return False
    try:
        Version(value)
        return True
    except InvalidVersion:
        return False


def same_version(system, left, right):
    if not all(isinstance(v, str) and v for v in (left, right)):
        return False
    if str(system).lower() != "pypi":
        return left == right
    try:
        return Version(left) == Version(right)
    except InvalidVersion:
        return False


def same_name(system, left, right):
    if not all(isinstance(v, str) and v for v in (left, right)):
        return False
    if str(system).lower() == "pypi":
        return re.sub(r"[-_.]+", "-", left).lower() == re.sub(r"[-_.]+", "-", right).lower()
    return left == right
