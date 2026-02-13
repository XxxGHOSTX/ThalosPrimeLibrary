import json
import logging
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ThalosArchitect:
    """Autonomous environment bootstrapper and launcher for Thalos Prime."""

    REQUIRED_FILES = {
        "README.md": "Project overview and quickstart.",
        "LICENSE": "License declaration.",
        ".env.example": "Environment variable template.",
        "infra/docker/Dockerfile": "Container build definition.",
        "src/thalosprime/cli.py": "CLI entrypoint for standalone mode.",
        "docs/architecture.md": "Architecture and component interactions.",
    }

    STRUCTURE = [
        "src/thalosprime/core",
        "src/thalosprime/api",
        "src/thalosprime/sharding",
        "src/thalosprime/generators",
        "src/thalosprime/decoders",
        "src/thalosprime/indexers",
        "src/thalosprime/storage",
        "src/thalosprime/integrations",
        "scripts",
        "tests/unit",
        "tests/integration",
        "data/shards",
        "data/logs",
        "infra/docker",
        "exports/provenance",
        "docs",
    ]

    def __init__(self) -> None:
        self.root = Path(__file__).parent.absolute()
        self.manifest_path = self.root / "BABEL_ENGINE_MANIFEST.txt"
        self.requirements_path = self.root / "requirements.txt"
        self.os_type = platform.system()
        self.skip_install = str(self._read_env("TPAA_SKIP_INSTALL", "0")).lower() in {"1", "true", "yes"}

        self.log_path = self.root / "data/logs/architect_audit.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="[TPAA-BRAIN] %(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(self.log_path),
                logging.StreamHandler(sys.stdout),
            ],
        )
        self.logger = logging.getLogger("ThalosArchitect")

        self.audit: Dict[str, object] = {
            "root": str(self.root),
            "os": self.os_type,
            "timestamp": int(time.time()),
            "steps": [],
            "checks": {},
            "deployment": {},
        }

    @staticmethod
    def _read_env(name: str, default: str = "") -> str:
        return os.environ.get(name, default)

    def _record_step(self, step: str, ok: bool, details: str = "") -> None:
        payload = {"step": step, "ok": ok, "details": details, "ts": int(time.time())}
        self.audit["steps"].append(payload)
        if ok:
            self.logger.info("%s: OK %s", step, f"- {details}" if details else "")
        else:
            self.logger.warning("%s: FAIL %s", step, f"- {details}" if details else "")

    def auto_install_dependencies(self) -> bool:
        """Automate installation of Python dependencies."""
        if self.skip_install:
            self._record_step("dependencies", True, "Skipping install due to TPAA_SKIP_INSTALL")
            return True

        self.logger.info("Synchronizing environment dependencies...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
            if self.requirements_path.exists():
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", str(self.requirements_path)]
                )
            else:
                base_pkgs = [
                    "fastapi",
                    "uvicorn",
                    "pydantic",
                    "psutil",
                    "gmpy2",
                    "pycryptodome",
                    "h5py",
                    "httpx",
                ]
                subprocess.check_call([sys.executable, "-m", "pip", "install", *base_pkgs])
            self._record_step("dependencies", True, "Dependency sync completed")
            return True
        except subprocess.CalledProcessError as exc:
            self._record_step("dependencies", False, f"Command failed: {exc}")
            return False

    def validate_brain_integrity(self) -> bool:
        """Validate math and crypto runtime capabilities."""
        self.logger.info("Commencing neural integrity check...")
        checks = {"math": False, "crypto": False, "storage": False}

        try:
            import gmpy2

            ctx = gmpy2.get_context()
            ctx.precision = 2048
            checks["math"] = True
        except Exception as exc:
            self.logger.error("Math kernel failure: %s", exc)

        try:
            from Crypto.Cipher import AES  # noqa: F401

            checks["crypto"] = True
        except Exception as exc:
            self.logger.error("Crypto kernel failure: %s", exc)

        try:
            test_path = self.root / "data/shards/.write_check"
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text("ok", encoding="utf-8")
            test_path.unlink(missing_ok=True)
            checks["storage"] = True
        except Exception as exc:
            self.logger.error("Storage kernel failure: %s", exc)

        self.audit["checks"] = checks
        self._record_step("integrity", all(checks.values()), json.dumps(checks))
        return all(checks.values())

    def enforce_structure(self) -> None:
        """Create required directories and missing placeholder modules."""
        for folder in self.STRUCTURE:
            path = self.root / folder
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                self.logger.info("Structural enforcement: created %s", folder)

        package_markers = [
            "src/thalosprime/__init__.py",
            "src/thalosprime/api/__init__.py",
            "src/thalosprime/core/__init__.py",
            "src/thalosprime/integrations/__init__.py",
        ]
        for marker in package_markers:
            marker_path = self.root / marker
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            if not marker_path.exists():
                marker_path.write_text("", encoding="utf-8")

        self._record_step("structure", True, "Directory structure enforced")

    def ensure_bootstrap_files(self) -> None:
        """Create non-destructive stubs for critical bootstrap files when missing."""
        templates = {
            ".env.example": "TPAA_SKIP_INSTALL=0\nTPAA_DEPLOY_MODE=auto\nTPAA_HEALTH_PORT=8000\n",
            "src/thalosprime/cli.py": (
                "def main() -> int:\n"
                "    print('Thalos Prime CLI is initialized.')\n"
                "    return 0\n\n"
                "if __name__ == '__main__':\n"
                "    raise SystemExit(main())\n"
            ),
            "docs/architecture.md": "# Thalos Prime Architecture\n\nAutogenerated bootstrap placeholder.\n",
            "infra/docker/Dockerfile": (
                "FROM python:3.11-slim\n"
                "WORKDIR /app\n"
                "COPY . /app\n"
                "RUN pip install --upgrade pip && pip install -r requirements.txt\n"
                "CMD [\"python\", \"run_thalos.py\"]\n"
            ),
        }
        created = []
        for relative, content in templates.items():
            file_path = self.root / relative
            if not file_path.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
                created.append(relative)

        details = "Created: " + ", ".join(created) if created else "No bootstrap files needed"
        self._record_step("bootstrap_files", True, details)

    def validate_repo_contract(self) -> Tuple[bool, List[str]]:
        """Validate repository has expected standalone scaffolding."""
        missing = [path for path in self.REQUIRED_FILES if not (self.root / path).exists()]
        valid = not missing
        detail = "all required files present" if valid else f"missing: {', '.join(missing)}"
        self._record_step("repo_contract", valid, detail)
        return valid, missing

    def _port_open(self, host: str, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.75)
            return sock.connect_ex((host, port)) == 0

    def deploy_standalone(self) -> bool:
        """Launch Thalos Prime in local python mode or docker mode."""
        mode = self._read_env("TPAA_DEPLOY_MODE", "auto").lower()
        health_port = int(self._read_env("TPAA_HEALTH_PORT", "8000"))
        entry_points = ["run_thalos.py", "main.py", "src/thalosprime/api/server.py"]
        target = next((ep for ep in entry_points if (self.root / ep).exists()), None)

        if mode in {"auto", "docker"} and (self.root / "infra/docker/Dockerfile").exists():
            try:
                image = "thalos-prime:auto"
                subprocess.check_call(["docker", "build", "-t", image, "-f", "infra/docker/Dockerfile", "."], cwd=self.root)
                subprocess.Popen(["docker", "run", "--rm", "-p", f"{health_port}:{health_port}", image], cwd=self.root)
                self.audit["deployment"] = {"mode": "docker", "port": health_port, "image": image}
                self._record_step("deploy", True, f"Docker deployment started on port {health_port}")
                return True
            except Exception as exc:
                self.logger.warning("Docker deployment failed, falling back to local mode: %s", exc)

        if target:
            subprocess.Popen(
                [sys.executable, target],
                cwd=self.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self.audit["deployment"] = {"mode": "local", "entrypoint": target, "port": health_port}
            self._record_step("deploy", True, f"Local deployment started using {target}")
            return True

        self._record_step("deploy", False, "No valid entrypoint found")
        return False

    def wait_for_readiness(self, timeout: int = 20) -> bool:
        """Best-effort readiness wait by probing configured localhost port."""
        port = int(self._read_env("TPAA_HEALTH_PORT", "8000"))
        for _ in range(timeout):
            if self._port_open("127.0.0.1", port):
                self._record_step("readiness", True, f"Port {port} is reachable")
                return True
            time.sleep(1)
        self._record_step("readiness", False, f"Port {port} not reachable after {timeout}s")
        return False

    def write_audit_snapshot(self) -> None:
        snapshot = self.root / "exports/provenance/tpaa_audit_snapshot.json"
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_text(json.dumps(self.audit, indent=2), encoding="utf-8")
        self.logger.info("Audit snapshot written to %s", snapshot)

    def run_automated_lifecycle(self) -> None:
        print(
            r"""
=================================================
THALOS PRIME AUTONOMOUS ARCHITECT [TPAA]
BUILDING: STANDALONE BABEL BRAIN
=================================================
"""
        )

        self.enforce_structure()
        self.ensure_bootstrap_files()
        contract_ok, missing = self.validate_repo_contract()

        if not contract_ok:
            self.logger.warning("Repository missing canonical files: %s", ", ".join(missing))

        if not self.auto_install_dependencies():
            self.write_audit_snapshot()
            print("\n[!] DEPENDENCY INSTALL FAILED: Check architect_audit.log")
            return

        if not self.validate_brain_integrity():
            self.write_audit_snapshot()
            print("\n[!] INTEGRITY ERROR: System math/crypto/storage checks failed.")
            return

        print("\n[SUCCESS] Environment ready. Deploying in 2 seconds...")
        time.sleep(2)

        deployed = self.deploy_standalone()
        if deployed:
            self.wait_for_readiness(timeout=10)
            print("\n=================================================")
            print("THALOS PRIME IS NOW OPERATIONAL")
            print(f"MONITORING: {self.log_path}")
            print("=================================================")
        else:
            print("\n[!] DEPLOYMENT FAILED: Check logs for details.")

        self.write_audit_snapshot()


if __name__ == "__main__":
    architect = ThalosArchitect()
    architect.run_automated_lifecycle()
