"""Tests for bounded, read-only project inventory."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from thalos_prime.experiments.project_inventory import ProjectInventoryBuilder


def test_inventory_digest_is_stable_and_tracks_file_content(tmp_path: Path) -> None:
    """Repeated scans of unchanged files have the same stable digest."""
    (tmp_path / "README.md").write_text("project notes", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
    builder = ProjectInventoryBuilder()
    first = builder.scan(tmp_path)
    second = builder.scan(tmp_path)
    assert first.project_digest == second.project_digest
    assert first.manifest_paths == ["pyproject.toml"]
    assert first.language_counts["markdown"] == 1
    assert "project notes" not in first.model_dump_json()

    (tmp_path / "README.md").write_text("changed notes", encoding="utf-8")
    third = builder.scan(tmp_path)
    assert third.project_digest != first.project_digest


def test_inventory_builds_local_python_import_graph(tmp_path: Path) -> None:
    """Local imports are resolved statically without importing the source."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "__init__.py").write_text("from . import operations\n", encoding="utf-8")
    (package / "operations.py").write_text("VALUE = 42\n", encoding="utf-8")
    (tmp_path / "main.py").write_text(
        "import package.operations\nprint('not executed')\n",
        encoding="utf-8",
    )
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    edges = {
        (edge.source_module, edge.target_module)
        for edge in inventory.python_import_edges
    }
    assert ("main", "package.operations") in edges
    assert ("package", "package.operations") in edges
    assert inventory.python_parse_issues == []


def test_python_source_is_never_executed(tmp_path: Path) -> None:
    """Inventory parsing must not cause source-level side effects."""
    sentinel = tmp_path / "should-not-exist.txt"
    source = tmp_path / "dangerous-looking.py"
    source.write_text(
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    ProjectInventoryBuilder().scan(tmp_path)
    assert not sentinel.exists()


def test_sensitive_files_are_skipped_before_reading(tmp_path: Path) -> None:
    """Known secret files are not included in the returned inventory."""
    (tmp_path / ".env").write_text("TOKEN=private-value", encoding="utf-8")
    (tmp_path / "service.pem").write_text("private-key-material", encoding="utf-8")
    (tmp_path / "credentials").write_text("cloud-secret", encoding="utf-8")
    (tmp_path / "safe.txt").write_text("public notes", encoding="utf-8")

    inventory = ProjectInventoryBuilder().scan(tmp_path)
    paths = {item.path for item in inventory.files}
    assert paths == {"safe.txt"}
    assert inventory.warning_counts["sensitive_path_skipped"] == 3
    serialized = inventory.model_dump_json()
    assert "private-value" not in serialized
    assert "private-key-material" not in serialized
    assert "cloud-secret" not in serialized


def test_symlinks_are_not_followed(tmp_path: Path) -> None:
    """A symlink to an external file is skipped and never enters the manifest."""
    external = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    external.write_text("external", encoding="utf-8")
    link = tmp_path / "linked.txt"
    try:
        os.symlink(external, link)
    except (OSError, NotImplementedError):
        external.unlink(missing_ok=True)
        return
    try:
        inventory = ProjectInventoryBuilder().scan(tmp_path)
        assert all(item.path != "linked.txt" for item in inventory.files)
        assert inventory.warning_counts["symlink_skipped"] == 1
    finally:
        external.unlink(missing_ok=True)


def test_file_limit_is_enforced_exactly(tmp_path: Path) -> None:
    """The scanner stops at the configured file limit and marks the result truncated."""
    for name in ("a.txt", "b.txt", "c.txt"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    inventory = ProjectInventoryBuilder(max_files=2).scan(tmp_path)
    assert len(inventory.files) == 2
    assert inventory.truncated_by_limits
    assert inventory.warning_counts["file_limit_reached"] == 1


def test_individual_file_size_limit_is_enforced(tmp_path: Path) -> None:
    """Files larger than the configured per-file budget are skipped."""
    (tmp_path / "large.txt").write_text("123456789", encoding="utf-8")
    (tmp_path / "small.txt").write_text("123", encoding="utf-8")
    inventory = ProjectInventoryBuilder(max_file_bytes=4).scan(tmp_path)
    assert {item.path for item in inventory.files} == {"small.txt"}
    assert inventory.warning_counts["oversize_file_skipped"] == 1
    assert inventory.truncated_by_limits


def test_total_read_budget_is_enforced(tmp_path: Path) -> None:
    """The scanner records only files that fit the total read budget."""
    (tmp_path / "a.txt").write_text("123", encoding="utf-8")
    (tmp_path / "b.txt").write_text("456", encoding="utf-8")
    inventory = ProjectInventoryBuilder(max_total_bytes=4).scan(tmp_path)
    assert {item.path for item in inventory.files} == {"a.txt"}
    assert inventory.total_bytes_read == 3
    assert inventory.truncated_by_limits
    assert inventory.warning_counts["total_size_limit_reached"] == 1


def test_identical_files_are_grouped_by_content_hash(tmp_path: Path) -> None:
    """Duplicate groups are based on exact byte equality."""
    (tmp_path / "one.txt").write_text("same content", encoding="utf-8")
    (tmp_path / "two.txt").write_text("same content", encoding="utf-8")
    (tmp_path / "different.txt").write_text("other content", encoding="utf-8")
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    assert len(inventory.duplicate_groups) == 1
    assert inventory.duplicate_groups[0].paths == ["one.txt", "two.txt"]


def test_syntax_errors_are_reported_without_aborting_scan(tmp_path: Path) -> None:
    """Broken Python files are inventoryable and reported as parse issues."""
    (tmp_path / "broken.py").write_text("def broken(:\n pass\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("still scanned", encoding="utf-8")
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    assert {item.path for item in inventory.files} == {"README.md", "broken.py"}
    assert len(inventory.python_parse_issues) == 1
    assert inventory.python_parse_issues[0].path == "broken.py"
    assert inventory.python_parse_issues[0].message == "python_syntax_error"


def test_root_must_be_an_existing_directory(tmp_path: Path) -> None:
    """Non-directories and missing roots fail explicitly."""
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")
    builder = ProjectInventoryBuilder()
    with pytest.raises(ValueError, match="directory"):
        builder.scan(file_path)


def test_nonpositive_limits_are_rejected() -> None:
    """Bounds must be positive to avoid ambiguous scan behavior."""
    with pytest.raises(ValueError, match="max_files"):
        ProjectInventoryBuilder(max_files=0)
    with pytest.raises(ValueError, match="max_file_bytes"):
        ProjectInventoryBuilder(max_file_bytes=0)
    with pytest.raises(ValueError, match="max_total_bytes"):
        ProjectInventoryBuilder(max_total_bytes=0)


def test_binary_files_count_toward_total_read_budget(tmp_path: Path) -> None:
    """Ignored binary bytes still consume the scanner's I/O budget."""
    (tmp_path / "a.bin").write_bytes(b"\x00abc")
    (tmp_path / "b.txt").write_text("xyz", encoding="utf-8")
    inventory = ProjectInventoryBuilder(max_total_bytes=4).scan(tmp_path)
    assert inventory.total_bytes_read == 4
    assert inventory.files == []
    assert inventory.warning_counts["binary_file_skipped"] == 1
    assert inventory.warning_counts["total_size_limit_reached"] == 1
    assert inventory.truncated_by_limits


def test_secret_like_filename_is_skipped(tmp_path: Path) -> None:
    """Secret-like file names are excluded even when their extension is ordinary."""
    (tmp_path / "service-secret.txt").write_text("must not read", encoding="utf-8")
    (tmp_path / "public.txt").write_text("safe", encoding="utf-8")
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    assert [item.path for item in inventory.files] == ["public.txt"]
    assert inventory.warning_counts["sensitive_path_skipped"] == 1


def test_common_lockfiles_and_versioned_requirements_are_manifests(tmp_path: Path) -> None:
    """Runtime manifests and dependency lockfiles are visible in the inventory."""
    names = [
        "requirements-dev.txt",
        "package-lock.json",
        "Cargo.lock",
        "go.sum",
        "pnpm-lock.yaml",
    ]
    for name in names:
        (tmp_path / name).write_text("manifest marker", encoding="utf-8")
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    assert inventory.manifest_paths == sorted(names)


def test_from_imports_capture_package_and_local_submodule_edges(tmp_path: Path) -> None:
    """A from-import records both the local package and its submodule when present."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "operations.py").write_text("VALUE = 42\n", encoding="utf-8")
    (tmp_path / "main.py").write_text(
        "from package import operations\n",
        encoding="utf-8",
    )
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    edges = {
        (edge.source_module, edge.target_module)
        for edge in inventory.python_import_edges
    }
    assert ("main", "package") in edges
    assert ("main", "package.operations") in edges


def test_relative_import_beyond_package_root_is_not_misresolved(tmp_path: Path) -> None:
    """An invalid upward relative import must not be mistaken for a top-level import."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "module.py").write_text(
        "from ..outside import helper\n",
        encoding="utf-8",
    )
    (tmp_path / "outside.py").write_text("helper = True\n", encoding="utf-8")
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    assert all(
        not (edge.source_module == "package.module" and edge.target_module == "outside")
        for edge in inventory.python_import_edges
    )


def test_deeply_nested_python_source_reports_parse_issue(tmp_path: Path) -> None:
    """One adversarially nested source file must not abort the entire inventory."""
    (tmp_path / "deep.py").write_text(
        "value = " + "(" * 2_000 + "1" + ")" * 2_000,
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("other files still scan", encoding="utf-8")
    inventory = ProjectInventoryBuilder().scan(tmp_path)
    assert {item.path for item in inventory.files} == {"README.md", "deep.py"}
    assert len(inventory.python_parse_issues) == 1
    assert inventory.python_parse_issues[0].message in {
        "python_syntax_error",
        "python_ast_recursion_limit",
    }


def test_directory_count_limit_marks_inventory_truncated(tmp_path: Path) -> None:
    """A project with too many directories is bounded before all trees are walked."""
    for name in ("one", "two", "three"):
        directory = tmp_path / name
        directory.mkdir()
        (directory / "README.md").write_text(name, encoding="utf-8")
    inventory = ProjectInventoryBuilder(max_directories=2).scan(tmp_path)
    assert inventory.truncated_by_limits
    assert inventory.warning_counts["directory_limit_reached"] == 1
    assert len(inventory.files) < 3


def test_nesting_depth_limit_marks_inventory_truncated(tmp_path: Path) -> None:
    """Deep directory chains are truncated at the configured depth."""
    current = tmp_path
    for index in range(4):
        current = current / f"level-{index}"
        current.mkdir()
    (current / "deep.txt").write_text("deep file", encoding="utf-8")
    inventory = ProjectInventoryBuilder(max_depth=2).scan(tmp_path)
    assert inventory.truncated_by_limits
    assert inventory.warning_counts["directory_depth_limit_reached"] >= 1
    assert "deep.txt" not in {record.path for record in inventory.files}


def test_nonpositive_directory_limit_and_negative_depth_are_rejected() -> None:
    """Directory and depth controls must have valid ranges."""
    with pytest.raises(ValueError, match="max_directories"):
        ProjectInventoryBuilder(max_directories=0)
    with pytest.raises(ValueError, match="max_depth"):
        ProjectInventoryBuilder(max_depth=-1)
