"""Bounded, read-only project inventory for ThalosPrime's engineering workflow.

Adapts the useful project-discovery, dependency-analysis, and file-fingerprint
ideas from THALOS_PRIME_CORE_INTELLIGENCE without executing inspected code or
shell commands. Results contain metadata and hashes, not source contents.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
from itertools import islice
from collections import defaultdict
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


_IGNORED_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".terraform",
        ".pulumi",
        "dist",
        "build",
        "coverage",
        ".next",
        ".nuxt",
        "target",
        "vendor",
    }
)
_MANIFEST_NAMES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "pipfile",
        "pipfile.lock",
        "poetry.lock",
        "uv.lock",
        "pdm.lock",
        "requirements.lock",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "bun.lock",
        "bun.lockb",
        "cargo.toml",
        "cargo.lock",
        "go.mod",
        "go.sum",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "gemfile",
        "gemfile.lock",
        "composer.json",
        "composer.lock",
    }
)
_LANGUAGE_BY_SUFFIX: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".sql": "sql",
    ".sh": "shell",
    ".ps1": "powershell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
}
_SENSITIVE_NAMES: frozenset[str] = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        "credentials",
        "credentials.json",
        "id_rsa",
        "id_ed25519",
        ".npmrc",
        ".pypirc",
        ".netrc",
        ".git-credentials",
        "config.json",
        "secrets.json",
        "secrets.yaml",
        "secrets.yml",
        "terraform.tfstate",
        "terraform.tfstate.backup",
    }
)
_SENSITIVE_SUFFIXES: frozenset[str] = frozenset(
    {".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".tfstate"}
)
_MIN_POSITIVE_LIMIT = 1
_MIN_PYTHON_LINE = 1


class InventoryFile(BaseModel):
    """Safe metadata for one inspected file; source content is not returned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    language: str
    file_kind: str


class ImportEdge(BaseModel):
    """A statically resolved import between two files within the project."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_path: str
    source_module: str
    target_module: str


class PythonParseIssue(BaseModel):
    """A Python source parse issue; code is never executed."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    line: int = Field(ge=1)
    message: str


class DuplicateFileGroup(BaseModel):
    """Files with identical bytes, useful for identifying duplicated modules."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sha256: str = Field(min_length=64, max_length=64)
    paths: list[str] = Field(min_length=2)


class ProjectInventory(BaseModel):
    """Stable snapshot of a bounded project's file and import structure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(default=2, ge=1)
    root_name: str
    files: list[InventoryFile]
    language_counts: dict[str, int]
    manifest_paths: list[str]
    test_paths: list[str]
    duplicate_groups: list[DuplicateFileGroup]
    python_import_edges: list[ImportEdge]
    python_parse_issues: list[PythonParseIssue]
    warning_counts: dict[str, int]
    total_bytes_read: int = Field(ge=0)
    truncated_by_limits: bool
    project_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class ProjectInventoryBuilder:
    """Inspect a project without imports, subprocesses, or repository code execution."""

    schema_version: ClassVar[int] = 2

    def __init__(
        self,
        *,
        max_files: int = 5000,
        max_file_bytes: int = 1_048_576,
        max_total_bytes: int = 100 * 1_048_576,
        max_directories: int = 20_000,
        max_depth: int = 50,
        max_entries_per_directory: int = 20_000,
    ) -> None:
        """Set explicit work limits for project scanning."""
        if max_files < _MIN_POSITIVE_LIMIT:
            raise ValueError("max_files must be at least 1")
        if max_file_bytes < _MIN_POSITIVE_LIMIT:
            raise ValueError("max_file_bytes must be at least 1")
        if max_total_bytes < _MIN_POSITIVE_LIMIT:
            raise ValueError("max_total_bytes must be at least 1")
        if max_directories < _MIN_POSITIVE_LIMIT:
            raise ValueError("max_directories must be at least 1")
        if max_depth < 0:
            raise ValueError("max_depth must not be negative")
        if max_entries_per_directory < _MIN_POSITIVE_LIMIT:
            raise ValueError("max_entries_per_directory must be at least 1")
        self._max_files = max_files
        self._max_file_bytes = max_file_bytes
        self._max_total_bytes = max_total_bytes
        self._max_directories = max_directories
        self._max_depth = max_depth
        self._max_entries_per_directory = max_entries_per_directory

    def scan(self, root: str | Path) -> ProjectInventory:
        """Create a deterministic metadata snapshot for a local project directory."""
        root_path = Path(root).expanduser().resolve(strict=True)
        if not root_path.is_dir():
            raise ValueError("root must resolve to a directory")

        warning_counts: dict[str, int] = defaultdict(int)
        candidate_paths, truncated = self._collect_candidate_paths(root_path, warning_counts)
        (
            file_records,
            source_bytes,
            digest_paths,
            total_bytes_read,
            read_truncated,
        ) = self._read_candidate_files(root_path, candidate_paths, warning_counts)
        truncated = truncated or read_truncated

        file_records.sort(key=lambda item: item.path)
        language_counts: dict[str, int] = defaultdict(int)
        for record in file_records:
            language_counts[record.language] += 1

        module_to_path = self._build_module_index(source_bytes)
        python_import_edges, parse_issues = self._analyze_python_imports(
            source_bytes,
            module_to_path,
        )
        duplicate_groups = [
            DuplicateFileGroup(sha256=digest, paths=sorted(paths))
            for digest, paths in sorted(digest_paths.items())
            if len(paths) > 1
        ]
        manifest_paths = sorted(
            record.path
            for record in file_records
            if self._is_manifest_name(Path(record.path).name)
        )
        test_paths = sorted(
            record.path for record in file_records if record.file_kind == "test"
        )

        digest_payload = {
            "schema_version": self.schema_version,
            "root_name": root_path.name,
            "limits": {
                "max_files": self._max_files,
                "max_file_bytes": self._max_file_bytes,
                "max_total_bytes": self._max_total_bytes,
                "max_directories": self._max_directories,
                "max_depth": self._max_depth,
                "max_entries_per_directory": self._max_entries_per_directory,
            },
            "files": [record.model_dump(mode="json") for record in file_records],
            "language_counts": dict(sorted(language_counts.items())),
            "manifest_paths": manifest_paths,
            "test_paths": test_paths,
            "duplicate_groups": [
                group.model_dump(mode="json") for group in duplicate_groups
            ],
            "python_import_edges": [
                edge.model_dump(mode="json") for edge in python_import_edges
            ],
            "python_parse_issues": [
                issue.model_dump(mode="json") for issue in parse_issues
            ],
            "warning_counts": dict(sorted(warning_counts.items())),
            "total_bytes_read": total_bytes_read,
            "truncated_by_limits": truncated,
        }
        digest_bytes = json.dumps(
            digest_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        project_digest = hashlib.sha256(digest_bytes).hexdigest()

        return ProjectInventory(
            schema_version=self.schema_version,
            root_name=root_path.name,
            files=file_records,
            language_counts=dict(sorted(language_counts.items())),
            manifest_paths=manifest_paths,
            test_paths=test_paths,
            duplicate_groups=duplicate_groups,
            python_import_edges=python_import_edges,
            python_parse_issues=parse_issues,
            warning_counts=dict(sorted(warning_counts.items())),
            total_bytes_read=total_bytes_read,
            truncated_by_limits=truncated,
            project_digest=project_digest,
        )

    def _collect_candidate_paths(
        self,
        root_path: Path,
        warning_counts: dict[str, int],
    ) -> tuple[list[Path], bool]:
        """Collect eligible paths with deterministic file, directory, and depth caps."""
        candidate_paths: list[Path] = []
        pending_directories: list[tuple[Path, int]] = [(root_path, 0)]
        truncated = False
        visited_directories = 0

        while pending_directories:
            if visited_directories >= self._max_directories:
                warning_counts["directory_limit_reached"] += 1
                truncated = True
                break

            directory, depth = pending_directories.pop()
            visited_directories += 1
            try:
                entries = list(
                    islice(
                        directory.iterdir(),
                        self._max_entries_per_directory + 1,
                    )
                )
            except OSError as error:
                warning_counts[f"directory_read_error:{type(error).__name__}"] += 1
                truncated = True
                continue

            if len(entries) > self._max_entries_per_directory:
                warning_counts["directory_entry_limit_reached"] += 1
                truncated = True
                continue
            entries.sort(key=lambda entry: entry.name)

            directories: list[tuple[Path, int]] = []
            for entry in entries:
                if entry.is_symlink():
                    warning_counts["symlink_skipped"] += 1
                    continue
                if entry.is_dir():
                    if entry.name.lower() in _IGNORED_DIRECTORIES:
                        warning_counts["ignored_directory_skipped"] += 1
                    elif depth >= self._max_depth:
                        warning_counts["directory_depth_limit_reached"] += 1
                        truncated = True
                    else:
                        directories.append((entry, depth + 1))
                    continue
                if not entry.is_file():
                    continue
                if self._is_sensitive_path(entry.relative_to(root_path)):
                    warning_counts["sensitive_path_skipped"] += 1
                    continue
                candidate_paths.append(entry)
                if len(candidate_paths) > self._max_files:
                    truncated = True
                    warning_counts["file_limit_reached"] += 1
                    break

            if len(candidate_paths) > self._max_files:
                break
            pending_directories.extend(reversed(directories))

        candidate_paths.sort(key=lambda path: path.relative_to(root_path).as_posix())
        return candidate_paths[: self._max_files], truncated

    def _read_candidate_files(
        self,
        root_path: Path,
        candidate_paths: list[Path],
        warning_counts: dict[str, int],
    ) -> tuple[
        list[InventoryFile],
        dict[str, bytes],
        dict[str, list[str]],
        int,
        bool,
    ]:
        """Read bounded file bytes and reject files that change during inspection."""
        file_records: list[InventoryFile] = []
        source_bytes: dict[str, bytes] = {}
        digest_paths: dict[str, list[str]] = defaultdict(list)
        total_bytes_read = 0
        truncated = False

        for path in candidate_paths:
            relative = path.relative_to(root_path).as_posix()
            try:
                path_stat = path.lstat()
                if stat.S_ISLNK(path_stat.st_mode):
                    warning_counts["symlink_skipped"] += 1
                    continue
                if not stat.S_ISREG(path_stat.st_mode):
                    warning_counts["non_regular_file_skipped"] += 1
                    continue
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                descriptor = os.open(path, flags)
            except OSError as error:
                warning_counts[f"file_open_error:{type(error).__name__}"] += 1
                continue

            with os.fdopen(descriptor, "rb") as handle:
                try:
                    opened_stat = os.fstat(handle.fileno())
                except OSError as error:
                    warning_counts[f"file_stat_error:{type(error).__name__}"] += 1
                    continue
                if (
                    not stat.S_ISREG(opened_stat.st_mode)
                    or path_stat.st_dev != opened_stat.st_dev
                    or path_stat.st_ino != opened_stat.st_ino
                ):
                    warning_counts["file_replaced_before_read"] += 1
                    truncated = True
                    continue

                file_size = opened_stat.st_size
                if file_size > self._max_file_bytes:
                    warning_counts["oversize_file_skipped"] += 1
                    truncated = True
                    continue

                remaining_budget = self._max_total_bytes - total_bytes_read
                if remaining_budget <= 0:
                    warning_counts["total_size_limit_reached"] += 1
                    truncated = True
                    break
                if file_size > remaining_budget:
                    warning_counts["total_size_limit_reached"] += 1
                    truncated = True
                    continue

                read_limit = min(self._max_file_bytes, remaining_budget)
                try:
                    data = handle.read(read_limit)
                    after_read_stat = os.fstat(handle.fileno())
                except OSError as error:
                    warning_counts[f"file_read_error:{type(error).__name__}"] += 1
                    continue
                total_bytes_read += len(data)

                changed_during_read = (
                    opened_stat.st_dev != after_read_stat.st_dev
                    or opened_stat.st_ino != after_read_stat.st_ino
                    or opened_stat.st_size != after_read_stat.st_size
                    or opened_stat.st_mtime_ns != after_read_stat.st_mtime_ns
                    or opened_stat.st_ctime_ns != after_read_stat.st_ctime_ns
                    or len(data) != file_size
                )
                if changed_during_read:
                    warning_counts["file_changed_during_scan"] += 1
                    truncated = True
                    continue
                if b"\x00" in data:
                    warning_counts["binary_file_skipped"] += 1
                    continue

            language = _LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "other")
            sha256 = hashlib.sha256(data).hexdigest()
            file_records.append(
                InventoryFile(
                    path=relative,
                    size_bytes=len(data),
                    sha256=sha256,
                    language=language,
                    file_kind=self._classify_file(path, relative),
                )
            )
            digest_paths[sha256].append(relative)
            if language == "python":
                source_bytes[relative] = data

        return file_records, source_bytes, digest_paths, total_bytes_read, truncated

    @staticmethod
    def _is_sensitive_path(relative: Path) -> bool:
        """Reject known secret files and private-key suffixes before reading bytes."""
        name = relative.name.lower()
        if name in _SENSITIVE_NAMES or name.endswith(tuple(_SENSITIVE_SUFFIXES)):
            return True
        if name.startswith(".env."):
            return True
        if any(
            marker in name
            for marker in ("secret", "credential", "private-key", "private_key")
        ):
            return True
        if name.startswith(("id_rsa", "id_ed25519")) and not name.endswith(".pub"):
            return True
        if any(
            part.lower() in {".ssh", ".aws", ".azure", ".kube", ".docker"}
            for part in relative.parts[:-1]
        ):
            return name not in {"config.example", "credentials.example"}
        return False

    @staticmethod
    def _is_manifest_name(name: str) -> bool:
        """Recognize common manifests, lockfiles, and versioned requirements files."""
        normalized = name.lower()
        return normalized in _MANIFEST_NAMES or (
            normalized.startswith("requirements") and normalized.endswith(".txt")
        )

    @staticmethod
    def _classify_file(path: Path, relative: str) -> str:
        """Classify a file as a manifest, test, source, documentation, or other."""
        name = path.name.lower()
        parts = {part.lower() for part in Path(relative).parts}
        if ProjectInventoryBuilder._is_manifest_name(name):
            return "manifest"
        if (
            "test" in parts
            or "tests" in parts
            or name.startswith("test_")
            or ".test." in name
            or ".spec." in name
            or name.endswith("_test.go")
        ):
            return "test"
        if path.suffix.lower() in {".md", ".rst", ".txt"}:
            return "documentation"
        if path.suffix.lower() in {
            ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
            ".java", ".kt", ".go", ".rs", ".c", ".h", ".cc", ".cpp",
            ".cxx", ".hpp", ".hh", ".cs", ".rb", ".php", ".swift",
        }:
            return "source"
        return "other"

    @staticmethod
    def _module_name(relative: str) -> str | None:
        """Convert a Python source path to a best-effort importable module name."""
        source_path = Path(relative)
        if source_path.suffix.lower() not in {".py", ".pyi"}:
            return None
        without_suffix = source_path.with_suffix("")
        components = list(without_suffix.parts)
        if components and components[-1] == "__init__":
            components.pop()
        if not components or any(not component.isidentifier() for component in components):
            return None
        return ".".join(components)

    @classmethod
    def _build_module_index(cls, source_bytes: dict[str, bytes]) -> dict[str, str]:
        """Map importable module names to their project-relative file paths."""
        index: dict[str, str] = {}
        for relative in sorted(source_bytes):
            module_name = cls._module_name(relative)
            if module_name is not None and module_name not in index:
                index[module_name] = relative
        return index

    @staticmethod
    def _resolve_local_module(
        candidate: str,
        module_to_path: dict[str, str],
    ) -> str | None:
        """Resolve the longest matching project-local module prefix."""
        parts = candidate.split(".")
        for end in range(len(parts), 0, -1):
            prefix = ".".join(parts[:end])
            if prefix in module_to_path:
                return prefix
        return None

    @classmethod
    def _analyze_python_imports(
        cls,
        source_bytes: dict[str, bytes],
        module_to_path: dict[str, str],
    ) -> tuple[list[ImportEdge], list[PythonParseIssue]]:
        """Parse Python imports without importing or executing inspected modules."""
        edge_keys: set[tuple[str, str, str]] = set()
        parse_issues: list[PythonParseIssue] = []

        for relative, content in sorted(source_bytes.items()):
            module_name = cls._module_name(relative)
            if module_name is None:
                continue
            try:
                source = content.decode("utf-8")
                tree = ast.parse(source, filename=relative)
            except UnicodeDecodeError:
                parse_issues.append(
                    PythonParseIssue(
                        path=relative,
                        line=1,
                        message="python_source_not_utf8",
                    )
                )
                continue
            except SyntaxError as error:
                parse_issues.append(
                    PythonParseIssue(
                        path=relative,
                        line=max(_MIN_PYTHON_LINE, error.lineno or _MIN_PYTHON_LINE),
                        message="python_syntax_error",
                    )
                )
                continue
            except RecursionError:
                parse_issues.append(
                    PythonParseIssue(
                        path=relative,
                        line=_MIN_PYTHON_LINE,
                        message="python_ast_recursion_limit",
                    )
                )
                continue

            current_package = (
                module_name
                if Path(relative).name in {"__init__.py", "__init__.pyi"}
                else module_name.rpartition(".")[0]
            )
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    candidates = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    base_parts = current_package.split(".") if current_package else []
                    if node.level:
                        if node.level > len(base_parts):
                            continue
                        trim_count = node.level - 1
                        base_parts = base_parts[: len(base_parts) - trim_count]
                    if node.module:
                        base_module = ".".join(base_parts + node.module.split("."))
                        candidates = [base_module]
                    else:
                        base_module = ".".join(base_parts)
                        candidates = [base_module] if base_module else []
                    if base_module:
                        candidates.extend(
                            f"{base_module}.{alias.name}" for alias in node.names
                        )
                else:
                    continue

                for candidate in candidates:
                    target_module = cls._resolve_local_module(candidate, module_to_path)
                    if target_module is not None and target_module != module_name:
                        edge_keys.add((relative, module_name, target_module))

        edges = [
            ImportEdge(
                source_path=source_path,
                source_module=source_module,
                target_module=target_module,
            )
            for source_path, source_module, target_module in sorted(edge_keys)
        ]
        parse_issues.sort(key=lambda issue: (issue.path, issue.line, issue.message))
        return edges, parse_issues


__all__ = [
    "DuplicateFileGroup",
    "ImportEdge",
    "InventoryFile",
    "ProjectInventory",
    "ProjectInventoryBuilder",
    "PythonParseIssue",
]
