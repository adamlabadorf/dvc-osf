"""End-to-end DVC push/pull integration tests.

These tests exercise actual `dvc push`, `dvc pull`, `dvc fetch`,
`dvc status`, `dvc gc`, and `dvc ls-url` commands against a real
OSF project, verifying that file content is correct and checksums match.

Required environment variables:
    OSF_TEST_TOKEN       - Personal Access Token with read/write access
    OSF_TEST_PROJECT_ID  - OSF project ID (e.g. "3eugf")

Run with:
    uv run pytest tests/integration/test_dvc_push_pull.py -v -m integration --no-cov
"""

import hashlib
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from dvc_osf.filesystem import OSFFileSystem

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EMPTY_FILE_MD5 = "d41d8cd98f00b204e9800998ecf8427e"


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(
    *args,
    cwd=None,
    env=None,
    check=True,
) -> subprocess.CompletedProcess:
    """Run a CLI command, returning CompletedProcess. Raises on non-zero by default."""
    cmd_env = os.environ.copy()
    # Propagate OSF token so commands like `dvc ls-url` that don't read DVC
    # remote config can still authenticate.
    osf_token = os.environ.get("OSF_TEST_TOKEN", "")
    cmd_env.update(
        {
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@test.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@test.com",
            "DVC_TEST": "true",
            "DVC_NO_ANALYTICS": "1",
            **({"OSF_TOKEN": osf_token} if osf_token else {}),
        }
    )
    if env:
        cmd_env.update(env)

    result = subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        cwd=cwd,
        env=cmd_env,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"Command {args} failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


# ---------------------------------------------------------------------------
# Module-level fixtures (credentials + filesystem)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def osf_credentials():
    """Skip if OSF credentials are not available."""
    token = os.getenv("OSF_TEST_TOKEN")
    project_id = os.getenv("OSF_TEST_PROJECT_ID")
    if not token or not project_id:
        pytest.skip(
            "OSF_TEST_TOKEN and OSF_TEST_PROJECT_ID must be set for integration tests"
        )
    return token, project_id


@pytest.fixture(scope="module")
def osf_fs(osf_credentials):
    """OSFFileSystem connected to the test project."""
    token, _ = osf_credentials
    return OSFFileSystem(token=token)


@pytest.fixture(scope="module")
def osf_base_path(osf_credentials):
    """Root osf:// path for the test project."""
    _, project_id = osf_credentials
    return f"osf://{project_id}/osfstorage"


# ---------------------------------------------------------------------------
# Per-test DVC repo fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def dvc_repo(tmp_path, osf_credentials):
    """
    Temporary git+DVC repo with OSF remote configured.

    Each test gets an isolated subdirectory on OSF under
    osfstorage/dvc-integration-tests/<uuid>/ so tests don't collide.
    The remote path is cleaned up after the test.
    """
    token, project_id = osf_credentials
    test_id = uuid.uuid4().hex[:12]
    remote_subpath = f"dvc-integration-tests/{test_id}"
    remote_url = f"osf://{project_id}/osfstorage/{remote_subpath}"

    repo = tmp_path / "repo"
    repo.mkdir()

    run("git", "init", cwd=str(repo))
    run("git", "config", "user.email", "test@test.com", cwd=str(repo))
    run("git", "config", "user.name", "Test", cwd=str(repo))
    run("dvc", "init", cwd=str(repo))
    run("dvc", "remote", "add", "-d", "myosf", remote_url, cwd=str(repo))
    run(
        "dvc",
        "remote",
        "modify",
        "--local",
        "myosf",
        "token",
        token,
        cwd=str(repo),
    )
    run("git", "add", ".", cwd=str(repo))
    run("git", "commit", "-m", "init dvc", cwd=str(repo))

    yield repo, remote_url

    # Cleanup remote test directory
    fs = OSFFileSystem(token=token)
    remote_osf_path = f"osf://{project_id}/osfstorage/{remote_subpath}"
    try:
        if fs.exists(remote_osf_path):
            fs.rm(remote_osf_path, recursive=True)
    except Exception:
        pass  # best-effort cleanup


# ---------------------------------------------------------------------------
# TestDvcPush
# ---------------------------------------------------------------------------


class TestDvcPush:
    """dvc push → verify content lands on OSF correctly."""

    def test_single_file_content_correct(self, dvc_repo, osf_fs):
        """Push a file and verify OSF has exact bytes (not empty).

        This is the regression test for the zero-byte upload bug:
        empty body on retry produced MD5 d41d8cd98f00b204e9800998ecf8427e.
        """
        repo, remote_url = dvc_repo
        data = b"hello dvc-osf integration test\n" * 100
        (repo / "data.bin").write_bytes(data)

        run("dvc", "add", "data.bin", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add data", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        # Read back via OSFFileSystem and compare bytes
        expected_md5 = hashlib.md5(data).hexdigest()
        remote_path = f"{remote_url}/files/md5/{expected_md5[:2]}/{expected_md5[2:]}"

        assert osf_fs.exists(remote_path), "File not found on OSF after push"
        info = osf_fs.info(remote_path)
        assert info.get("size") == len(data), "Size mismatch after push"
        assert info.get("checksum") == expected_md5, (
            f"Checksum mismatch: expected {expected_md5}, got {info.get('checksum')}. "
            f"If got {EMPTY_FILE_MD5!r} this is the zero-byte upload bug."
        )

    def test_push_checksum_matches_dvc_record(self, dvc_repo, osf_fs):
        """MD5 in the .dvc file must match what's stored on OSF."""
        repo, remote_url = dvc_repo
        content = b"checksum verification test content"
        (repo / "check.txt").write_bytes(content)

        run("dvc", "add", "check.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add check", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        # Parse MD5 from .dvc file
        import yaml

        dvc_file = repo / "check.txt.dvc"
        meta = yaml.safe_load(dvc_file.read_text())
        dvc_md5 = meta["outs"][0]["md5"]

        remote_path = f"{remote_url}/files/md5/{dvc_md5[:2]}/{dvc_md5[2:]}"
        info = osf_fs.info(remote_path)
        assert (
            info.get("checksum") == dvc_md5
        ), f"OSF checksum {info.get('checksum')} != DVC record {dvc_md5}"

    def test_push_multiple_files(self, dvc_repo, osf_fs):
        """Push 5 files at once; all must land with correct content."""
        repo, remote_url = dvc_repo
        files = {}
        for i in range(5):
            content = f"file {i} content {uuid.uuid4().hex}".encode()
            path = repo / f"multi_{i}.txt"
            path.write_bytes(content)
            files[f"multi_{i}.txt"] = content

        run("dvc", "add", *[f"multi_{i}.txt" for i in range(5)], cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add multi", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        import yaml

        for fname, content in files.items():
            dvc_file = repo / f"{fname}.dvc"
            meta = yaml.safe_load(dvc_file.read_text())
            dvc_md5 = meta["outs"][0]["md5"]
            remote_path = f"{remote_url}/files/md5/{dvc_md5[:2]}/{dvc_md5[2:]}"
            info = osf_fs.info(remote_path)
            assert info.get("checksum") == dvc_md5, f"Checksum mismatch for {fname}"

    def test_push_nested_subdir(self, dvc_repo, osf_fs):
        """Files in a subdirectory push correctly (tests _navigate_to_dir)."""
        repo, remote_url = dvc_repo
        subdir = repo / "data" / "nested"
        subdir.mkdir(parents=True)
        content = b"nested file content"
        (subdir / "nested.txt").write_bytes(content)

        run("dvc", "add", "data/nested/nested.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add nested", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        import yaml

        meta = yaml.safe_load((repo / "data/nested/nested.txt.dvc").read_text())
        dvc_md5 = meta["outs"][0]["md5"]
        remote_path = f"{remote_url}/files/md5/{dvc_md5[:2]}/{dvc_md5[2:]}"
        assert osf_fs.exists(remote_path), "Nested file not found on OSF"
        info = osf_fs.info(remote_path)
        assert info.get("checksum") == dvc_md5

    def test_push_idempotent(self, dvc_repo):
        """Second push should be a no-op (0 new files uploaded)."""
        repo, _ = dvc_repo
        (repo / "idem.txt").write_bytes(b"idempotent test")
        run("dvc", "add", "idem.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add idem", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        # Second push should report nothing to do
        result = run("dvc", "push", cwd=str(repo))
        assert (
            "Everything is up to date" in result.stdout
            or "0 file" in result.stdout
            or result.stdout.strip() == ""
        ), f"Expected no-op push, got: {result.stdout}"

    def test_push_binary_file(self, dvc_repo, osf_fs):
        """Non-UTF8 binary data round-trips correctly."""
        repo, remote_url = dvc_repo
        data = bytes(range(256)) * 100  # all byte values
        (repo / "binary.bin").write_bytes(data)

        run("dvc", "add", "binary.bin", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add binary", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        import yaml

        meta = yaml.safe_load((repo / "binary.bin.dvc").read_text())
        dvc_md5 = meta["outs"][0]["md5"]
        remote_path = f"{remote_url}/files/md5/{dvc_md5[:2]}/{dvc_md5[2:]}"
        info = osf_fs.info(remote_path)
        assert info.get("checksum") == dvc_md5
        assert info.get("size") == len(data)


# ---------------------------------------------------------------------------
# TestDvcPull
# ---------------------------------------------------------------------------


class TestDvcPull:
    """dvc pull → verify local file is restored correctly."""

    def _push_file(self, repo, content: bytes, fname: str = "pulled.txt"):
        """Helper: add, commit, push a file. Returns (local_path, dvc_md5)."""
        import yaml

        path = repo / fname
        path.write_bytes(content)
        run("dvc", "add", fname, cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", f"add {fname}", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))
        meta = yaml.safe_load((repo / f"{fname}.dvc").read_text())
        return path, meta["outs"][0]["md5"]

    def test_pull_restores_file(self, dvc_repo):
        """Push then delete local file; dvc pull must restore it."""
        repo, _ = dvc_repo
        content = b"pull restoration test " + uuid.uuid4().hex.encode()
        local_path, _ = self._push_file(repo, content)

        # Delete local file (keep .dvc) and clear cache
        local_path.unlink()
        shutil.rmtree(repo / ".dvc" / "cache", ignore_errors=True)

        run("dvc", "pull", cwd=str(repo))

        assert local_path.exists(), "File not restored by dvc pull"
        assert local_path.read_bytes() == content, "Content mismatch after pull"

    def test_pull_content_matches_original(self, dvc_repo):
        """Pulled file must be byte-for-byte identical to what was pushed."""
        repo, _ = dvc_repo
        content = os.urandom(4096)  # random bytes, definitely not empty
        local_path, _ = self._push_file(repo, content, "random.bin")

        local_path.unlink()
        shutil.rmtree(repo / ".dvc" / "cache", ignore_errors=True)
        run("dvc", "pull", cwd=str(repo))

        pulled = local_path.read_bytes()
        assert (
            pulled == content
        ), f"Pulled content ({len(pulled)} bytes) != original ({len(content)} bytes)"
        assert pulled != b"", "Pulled file is empty — upload or download bug"

    def test_pull_after_cache_cleared(self, dvc_repo):
        """Delete both workspace file and cache; pull must re-download from OSF."""
        repo, _ = dvc_repo
        content = b"cache cleared pull test " * 50
        local_path, _ = self._push_file(repo, content, "nocache.txt")

        local_path.unlink()
        shutil.rmtree(repo / ".dvc" / "cache", ignore_errors=True)

        run("dvc", "pull", cwd=str(repo))
        assert local_path.read_bytes() == content

    def test_pull_into_fresh_repo(self, tmp_path, osf_credentials):
        """Simulate a fresh clone: new repo, same OSF remote, dvc pull works."""
        token, project_id = osf_credentials
        test_id = uuid.uuid4().hex[:12]
        remote_subpath = f"dvc-integration-tests/{test_id}"
        remote_url = f"osf://{project_id}/osfstorage/{remote_subpath}"

        # Repo A: push a file
        repo_a = tmp_path / "repo_a"
        repo_a.mkdir()
        run("git", "init", cwd=str(repo_a))
        run("git", "config", "user.email", "t@t.com", cwd=str(repo_a))
        run("git", "config", "user.name", "T", cwd=str(repo_a))
        run("dvc", "init", cwd=str(repo_a))
        run("dvc", "remote", "add", "-d", "myosf", remote_url, cwd=str(repo_a))
        run(
            "dvc",
            "remote",
            "modify",
            "--local",
            "myosf",
            "token",
            token,
            cwd=str(repo_a),
        )
        content = b"fresh repo pull test content"
        (repo_a / "shared.txt").write_bytes(content)
        run("dvc", "add", "shared.txt", cwd=str(repo_a))
        run("git", "add", ".", cwd=str(repo_a))
        run("git", "commit", "-m", "init", cwd=str(repo_a))
        run("dvc", "push", cwd=str(repo_a))

        # Repo B: fresh init, same remote, pull
        repo_b = tmp_path / "repo_b"
        repo_b.mkdir()
        run("git", "init", cwd=str(repo_b))
        run("git", "config", "user.email", "t@t.com", cwd=str(repo_b))
        run("git", "config", "user.name", "T", cwd=str(repo_b))
        run("dvc", "init", cwd=str(repo_b))
        run("dvc", "remote", "add", "-d", "myosf", remote_url, cwd=str(repo_b))
        run(
            "dvc",
            "remote",
            "modify",
            "--local",
            "myosf",
            "token",
            token,
            cwd=str(repo_b),
        )
        # Copy just the .dvc tracking file (simulates git clone)
        shutil.copy(repo_a / "shared.txt.dvc", repo_b / "shared.txt.dvc")
        run("git", "add", ".", cwd=str(repo_b))
        run("git", "commit", "-m", "copy dvc file", cwd=str(repo_b))

        run("dvc", "pull", cwd=str(repo_b))
        pulled = (repo_b / "shared.txt").read_bytes()
        assert pulled == content, f"Fresh repo pull mismatch: {pulled!r} != {content!r}"

        # Cleanup
        fs = OSFFileSystem(token=token)
        try:
            fs.rm(f"osf://{project_id}/osfstorage/{remote_subpath}", recursive=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# TestDvcFetch
# ---------------------------------------------------------------------------


class TestDvcFetch:
    """dvc fetch downloads to cache but does not check out to workspace."""

    def test_fetch_populates_cache_not_workspace(self, dvc_repo):
        """After fetch, file is in cache but not in workspace."""
        import yaml

        repo, _ = dvc_repo
        content = b"fetch test content " + uuid.uuid4().hex.encode()
        (repo / "fetched.txt").write_bytes(content)
        run("dvc", "add", "fetched.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add fetched", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        # Clear everything local
        (repo / "fetched.txt").unlink()
        shutil.rmtree(repo / ".dvc" / "cache", ignore_errors=True)

        run("dvc", "fetch", cwd=str(repo))

        # Cache should be populated
        meta = yaml.safe_load((repo / "fetched.txt.dvc").read_text())
        dvc_md5 = meta["outs"][0]["md5"]
        cache_path = (
            repo / ".dvc" / "cache" / "files" / "md5" / dvc_md5[:2] / dvc_md5[2:]
        )
        assert cache_path.exists(), "Cache not populated by dvc fetch"
        assert cache_path.read_bytes() == content, "Cache content mismatch"

        # Workspace file should NOT be present yet
        assert not (
            repo / "fetched.txt"
        ).exists(), "dvc fetch should not check out workspace file"

    def test_fetch_then_checkout_restores_file(self, dvc_repo):
        """fetch + checkout == pull."""
        repo, _ = dvc_repo
        content = b"fetch checkout test " + uuid.uuid4().hex.encode()
        (repo / "fcheck.txt").write_bytes(content)
        run("dvc", "add", "fcheck.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add fcheck", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        (repo / "fcheck.txt").unlink()
        shutil.rmtree(repo / ".dvc" / "cache", ignore_errors=True)

        run("dvc", "fetch", cwd=str(repo))
        run("dvc", "checkout", cwd=str(repo))

        assert (repo / "fcheck.txt").read_bytes() == content


# ---------------------------------------------------------------------------
# TestDvcStatus
# ---------------------------------------------------------------------------


class TestDvcStatus:
    """dvc status -r reflects actual remote state."""

    def test_status_clean_after_push(self, dvc_repo):
        """After push, dvc status -r should show nothing to upload."""
        repo, _ = dvc_repo
        (repo / "status.txt").write_bytes(b"status test")
        run("dvc", "add", "status.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add status", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        result = run("dvc", "status", "-r", "myosf", cwd=str(repo))
        # Clean status varies by DVC version; treat any "in sync"/"up to date" message as clean
        out = result.stdout.strip().lower()
        clean = out == "" or "up to date" in out or "in sync" in out or "0 file" in out
        assert clean, f"Expected clean remote status, got:\n{result.stdout}"

    def test_status_detects_new_unpushed_file(self, dvc_repo):
        """A tracked but not-yet-pushed file should appear in remote status."""
        repo, _ = dvc_repo
        (repo / "unpushed.txt").write_bytes(b"not pushed")
        run("dvc", "add", "unpushed.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add unpushed", cwd=str(repo))

        # Status without pushing — should show file as new/modified
        result = run("dvc", "status", "-r", "myosf", cwd=str(repo), check=False)
        # Non-zero exit or output mentioning the file indicates it's detected
        has_diff = (
            result.returncode != 0
            or "new" in result.stdout.lower()
            or "modified" in result.stdout.lower()
            or "unpushed" in result.stdout
        )
        assert has_diff, "status -r should detect unpushed file"


# ---------------------------------------------------------------------------
# TestDvcGc
# ---------------------------------------------------------------------------


class TestDvcGc:
    """dvc gc --remote removes unreferenced files, preserves referenced ones."""

    def test_gc_removes_unreferenced_file(self, dvc_repo, osf_fs):
        """Push a file, stop tracking it, gc should remove it from OSF."""
        import yaml

        repo, remote_url = dvc_repo

        # Push file A (will be gc'd)
        content_a = b"file to be garbage collected " + uuid.uuid4().hex.encode()
        (repo / "gc_target.txt").write_bytes(content_a)
        run("dvc", "add", "gc_target.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add gc_target", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))
        meta_a = yaml.safe_load((repo / "gc_target.txt.dvc").read_text())
        md5_a = meta_a["outs"][0]["md5"]

        # Push file B (must survive gc)
        content_b = b"file to keep after gc " + uuid.uuid4().hex.encode()
        (repo / "keep.txt").write_bytes(content_b)
        run("dvc", "add", "keep.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add keep", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))
        meta_b = yaml.safe_load((repo / "keep.txt.dvc").read_text())
        md5_b = meta_b["outs"][0]["md5"]

        # Remove gc_target from DVC tracking
        run("dvc", "remove", "gc_target.txt.dvc", cwd=str(repo))
        (repo / "gc_target.txt").unlink(missing_ok=True)
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "remove gc_target from tracking", cwd=str(repo))

        # Run gc
        # DVC requires a revision/workspace scope for GC; `-w` is the most conservative.
        run("dvc", "gc", "-r", "myosf", "-w", "--force", cwd=str(repo))

        remote_a = f"{remote_url}/files/md5/{md5_a[:2]}/{md5_a[2:]}"
        remote_b = f"{remote_url}/files/md5/{md5_b[:2]}/{md5_b[2:]}"

        assert not osf_fs.exists(remote_a), "gc should have removed unreferenced file"
        assert osf_fs.exists(remote_b), "gc should not have removed referenced file"

    def test_gc_preserves_all_referenced_files(self, dvc_repo, osf_fs):
        """gc --remote must not delete any currently tracked files."""
        import yaml

        repo, remote_url = dvc_repo
        files = {}
        for i in range(3):
            content = f"keep file {i} ".encode() + uuid.uuid4().hex.encode()
            fname = f"keep_{i}.txt"
            (repo / fname).write_bytes(content)
            run("dvc", "add", fname, cwd=str(repo))
            meta = yaml.safe_load((repo / f"{fname}.dvc").read_text())
            files[fname] = meta["outs"][0]["md5"]

        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add keeps", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))
        run("dvc", "gc", "-r", "myosf", "-w", "--force", cwd=str(repo))

        for fname, dvc_md5 in files.items():
            remote_path = f"{remote_url}/files/md5/{dvc_md5[:2]}/{dvc_md5[2:]}"
            assert osf_fs.exists(
                remote_path
            ), f"gc incorrectly removed referenced file {fname}"


# ---------------------------------------------------------------------------
# TestDvcLsUrl
# ---------------------------------------------------------------------------


class TestDvcLsUrl:
    """dvc ls-url works against OSF paths."""

    def test_ls_url_lists_pushed_files(self, dvc_repo, osf_credentials):
        """After push, dvc ls-url on the remote path lists cache files."""
        repo, remote_url = dvc_repo
        token, project_id = osf_credentials

        content = b"ls-url test content"
        (repo / "listed.txt").write_bytes(content)
        run("dvc", "add", "listed.txt", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add listed", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        result = run(
            "dvc",
            "ls-url",
            f"{remote_url}/files/md5/",
            cwd=str(repo),
            check=False,
        )
        # Should list the two-char prefix dirs (e.g. "d4/", "ea/")
        assert result.returncode == 0 or len(result.stdout.strip()) > 0


# ---------------------------------------------------------------------------
# TestDvcPushPullLargeFile (slow)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestDvcPushPullLargeFile:
    """Large file tests (>5 MB) that exercise the chunked upload path."""

    def test_push_pull_10mb_file(self, dvc_repo):
        """10 MB file pushes and pulls back with correct content."""
        repo, _ = dvc_repo
        size = 10 * 1024 * 1024  # 10 MB
        data = os.urandom(size)
        (repo / "large.bin").write_bytes(data)

        run("dvc", "add", "large.bin", cwd=str(repo))
        run("git", "add", ".", cwd=str(repo))
        run("git", "commit", "-m", "add large", cwd=str(repo))
        run("dvc", "push", cwd=str(repo))

        (repo / "large.bin").unlink()
        shutil.rmtree(repo / ".dvc" / "cache", ignore_errors=True)
        run("dvc", "pull", cwd=str(repo))

        pulled = (repo / "large.bin").read_bytes()
        assert len(pulled) == size, f"Size mismatch: {len(pulled)} != {size}"
        assert pulled == data, "Content mismatch on large file pull"
        assert pulled[:4] != b"\x00\x00\x00\x00", "Suspiciously zero-filled start"
