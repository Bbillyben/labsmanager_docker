from . import lab_version
import re

def labsVersionTuple():
    """Return the Labsmanager version string as (maj, min, sub) tuple."""
    if version is None:
        version = lab_version.LABSMANAGER_VERSION
    match = re.match(r'^.*(\d+)\.(\d+)\.(\d+).*$', str(version))

    return [int(g) for g in match.groups()]