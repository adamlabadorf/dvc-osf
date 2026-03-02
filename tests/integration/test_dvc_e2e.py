"""End-to-end DVC integration tests (Phase 5, Tasks 5.1–5.5).

These tests exercise actual DVC commands with the OSF plugin.

Tests in TestDvcRemoteAdd, TestDvcPushPull, and TestDvcVersion require the
adamlabadorf/dvc fork (feature/plugin-schema-discovery) because standard DVC
does not recognise osf:// URLs in its config schema.  Those tests are
automatically skipped when the standard DVC is installed.
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def _dvc_supports_osf() -> bool:
    """Return True if the installed DVC accepts osf:// remote URLs."""
    import subprocess as _sp
    import tempfile as _tmp

    with _tmp.TemporaryDirectory() as d:
        _sp.run(["git", "init", d], capture_output=True)
        _sp.run(["dvc", "init", d], capture_output=True, cwd=d)
        result = _sp.run(
            ["dvc", "remote", "add", "_probe", "osf://probe/osfstorage"],
            capture_output=True,
            cwd=d,
        )
        return result.returncode == 0


requires_dvc_fork = pytest.mark.skipif(
    not _dvc_supports_osf(),
    reason="Requires adamlabadorf/dvc fork with osf:// schema support (PR #10994)",
)


def run_cmd(*args, cwd=None, env=None):
    """Run a command and return (returncode, stdout, stderr)."""
    cmd_env = os.environ.copy()
    cmd_env["GIT_AUTHOR_NAME"] = "Test"
    cmd_env["GIT_AUTHOR_EMAIL"] = "test@test.com"
    cmd_env["GIT_COMMITTER_NAME"] = "Test"
    cmd_env["GIT_COMMITTER_EMAIL"] = "test@test.com"
    # Suppress DVC analytics prompts
    cmd_env["DVC_TEST"] = "true"
    if env:
        cmd_env.update(env)

    result = subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
        env=cmd_env,
    )
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def dvc_repo(tmp_path):
    """Create a temporary DVC repository with OSF remote configured."""
    repo = tmp_path / "repo"
    repo.mkdir()

    run_cmd("git", "init", cwd=str(repo))
    run_cmd("git", "config", "user.email", "test@test.com", cwd=str(repo))
    run_cmd("git", "config", "user.name", "Test", cwd=str(repo))
    rc, _, err = run_cmd("dvc", "init", cwd=str(repo))
    assert rc == 0, f"dvc init failed: {err}"

    rc, _, err = run_cmd(
        "dvc",
        "remote",
        "add",
        "-d",
        "myosf",
        "osf://abc123/osfstorage",
        cwd=str(repo),
    )
    assert rc == 0, f"dvc remote add failed: {err}"

    rc, _, err = run_cmd(
        "dvc",
        "remote",
        "modify",
        "myosf",
        "token",
        "test_token_12345",
        cwd=str(repo),
    )
    assert rc == 0, f"dvc remote modify failed: {err}"

    run_cmd("git", "add", ".", cwd=str(repo))
    run_cmd("git", "commit", "-m", "init", cwd=str(repo))

    return repo


@requires_dvc_fork
class TestDvcRemoteAdd:
    """Task 5.2: DVC recognizes osf:// remote URLs."""

    def test_remote_add_osf(self, tmp_path):
        """dvc remote add with osf:// scheme should succeed."""
        repo = tmp_path / "repo"
        repo.mkdir()
        run_cmd("git", "init", cwd=str(repo))
        run_cmd("git", "config", "user.email", "t@t.com", cwd=str(repo))
        run_cmd("git", "config", "user.name", "T", cwd=str(repo))
        run_cmd("dvc", "init", cwd=str(repo))

        rc, out, err = run_cmd(
            "dvc",
            "remote",
            "add",
            "myosf",
            "osf://abc123/osfstorage",
            cwd=str(repo),
        )
        assert rc == 0, f"Failed: {err}"

    def test_remote_modify_token(self, dvc_repo):
        """dvc remote modify for token should succeed."""
        rc, out, err = run_cmd(
            "dvc",
            "remote",
            "modify",
            "myosf",
            "token",
            "new_token",
            cwd=str(dvc_repo),
        )
        assert rc == 0, f"Failed: {err}"

    def test_remote_list_shows_osf(self, dvc_repo):
        """dvc remote list should show the configured OSF remote."""
        rc, out, err = run_cmd("dvc", "remote", "list", cwd=str(dvc_repo))
        assert rc == 0
        assert "myosf" in out
        assert "osf://" in out


@requires_dvc_fork
class TestDvcPushPull:
    """Tasks 5.3-5.5: Push, pull, status with OSF remote.

    Note: These tests verify DVC command plumbing reaches the plugin.
    Actual OSF API calls would fail without a real token/project, so
    we verify the error is from OSF auth, not from DVC config/schema.
    """

    def test_push_reaches_plugin(self, dvc_repo):
        """dvc push should attempt to use OSF plugin (auth error expected)."""
        # Create a file to track
        data_file = dvc_repo / "data.txt"
        data_file.write_text("hello world")

        rc, _, err = run_cmd("dvc", "add", "data.txt", cwd=str(dvc_repo))
        assert rc == 0, f"dvc add failed: {err}"

        # Push should fail with an OSF-related error, NOT a schema error
        rc, out, err = run_cmd("dvc", "push", cwd=str(dvc_repo))
        # Should not be a "Unsupported URL type" error
        assert "Unsupported URL type" not in err
        # It will likely fail with an auth or connection error — that's fine,
        # it means the plugin was correctly invoked

    def test_status_remote_reaches_plugin(self, dvc_repo):
        """dvc status -r should attempt to use OSF plugin."""
        data_file = dvc_repo / "data.txt"
        data_file.write_text("test data")
        run_cmd("dvc", "add", "data.txt", cwd=str(dvc_repo))

        rc, out, err = run_cmd("dvc", "status", "-r", "myosf", cwd=str(dvc_repo))
        # Should not be a URL/schema error
        assert "Unsupported URL type" not in err


@requires_dvc_fork
class TestDvcVersion:
    """Verify plugin appears in dvc version output."""

    def test_dvc_version_shows_osf(self):
        """dvc version should list osf in Supports."""
        rc, out, err = run_cmd("dvc", "version")
        assert rc == 0
        assert "osf" in out.lower()


class TestFsspecDiscovery:
    """Task 4.1: Plugin discovered via fsspec."""

    def test_fsspec_discovers_osf(self):
        """fsspec should resolve 'osf' to OSFFileSystem."""
        import fsspec

        cls = fsspec.get_filesystem_class("osf")
        from dvc_osf.filesystem import OSFFileSystem

        assert cls is OSFFileSystem


class TestEntryPoints:
    """Task 4.2-4.3: Entry point verification."""

    def test_import_without_dvc_core(self):
        """OSFFileSystem can be imported (dvc-objects is the dependency, not dvc)."""
        from dvc_osf import OSFFileSystem

        assert OSFFileSystem.protocol == "osf"

    def test_pyproject_entry_points(self):
        """Verify pyproject.toml has correct entry points."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)

        eps = data.get("project", {}).get("entry-points", {})
        assert eps["fsspec.specs"]["osf"] == "dvc_osf.filesystem:OSFFileSystem"
        assert eps["dvc.fs"]["osf"] == "dvc_osf.filesystem:OSFFileSystem"
