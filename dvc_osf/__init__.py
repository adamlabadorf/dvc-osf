"""DVC-OSF: Open Science Framework plugin for DVC."""

__version__ = "0.1.0"

from dvc_osf.exceptions import OSFException
from dvc_osf.filesystem import OSFFileSystem

__all__ = ["OSFFileSystem", "OSFException", "__version__"]


def _register_with_dvc():
    """Register OSF scheme with DVC's filesystem registry and config schema.

    This runs at import time so that ``pip install dvc-osf`` is sufficient
    to make ``osf://`` URLs available in DVC commands.
    """
    # 1. Register in dvc-objects known_implementations / registry
    try:
        from dvc_objects.fs import known_implementations

        if "osf" not in known_implementations:
            known_implementations["osf"] = {
                "class": "dvc_osf.filesystem.OSFFileSystem",
                "err": "osf is supported, but requires 'dvc-osf' to be installed",
            }
    except ImportError:
        pass

    # 2. Register in DVC's config schema so ``dvc remote add`` accepts osf:// URLs
    try:
        from dvc.config_schema import REMOTE_SCHEMAS, REMOTE_COMMON, SCHEMA, ByUrl

        if "osf" not in REMOTE_SCHEMAS:
            REMOTE_SCHEMAS["osf"] = {
                "token": str,
                "endpoint_url": str,
                "project_id": str,
                "provider": str,
                **REMOTE_COMMON,
            }

            # Rebuild the SCHEMA remote validator to pick up the new scheme.
            # ByUrl() captures a snapshot of the mapping, so we must replace
            # the validator in SCHEMA after adding our scheme.
            SCHEMA["remote"] = {str: ByUrl(REMOTE_SCHEMAS)}
    except ImportError:
        pass


_register_with_dvc()

