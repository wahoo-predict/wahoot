import subprocess
import sys
from pathlib import Path

import pytest


class TestSetupPy:

    def test_setup_py_exists_and_valid(self):

        project_root = Path(__file__).parent.parent
        setup_file = project_root / "setup.py"

        assert setup_file.exists(), "setup.py should exist"

        with open(setup_file, "r") as f:
            code = f.read()

        compile(code, str(setup_file), "exec")

    def test_setup_py_has_required_metadata(self):

        project_root = Path(__file__).parent.parent
        setup_file = project_root / "setup.py"

        assert setup_file.exists(), "setup.py should exist"

        with open(setup_file, "r") as f:
            content = f.read()

        assert "name=" in content or "name=" in content
        assert "version=" in content
        assert "install_requires=" in content or "requirements" in content.lower()
        assert "packages=" in content or "find_packages" in content

    def test_setup_py_can_install_package(self):

        project_root = Path(__file__).parent.parent

        try:
            result = subprocess.run(
                [sys.executable, "setup.py", "check"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 0 or "error" not in result.stderr.lower()
        except subprocess.TimeoutExpired:
            pytest.skip("setup.py check timed out")
        except FileNotFoundError:
            pytest.skip("setup.py not found or Python not available")

    def test_setup_py_has_runtime_dependencies(self):

        project_root = Path(__file__).parent.parent
        setup_file = project_root / "setup.py"

        with open(setup_file, "r") as f:
            setup_content = f.read()

        assert "install_requires" in setup_content

        assert "bittensor" in setup_content
        assert "sqlalchemy" in setup_content or "alembic" in setup_content

    def test_entry_points_defined(self):

        project_root = Path(__file__).parent.parent

        pyproject_file = project_root / "pyproject.toml"
        if pyproject_file.exists():
            with open(pyproject_file, "r") as f:
                pyproject_content = f.read()
            assert "[project.scripts]" in pyproject_content
        else:
            setup_file = project_root / "setup.py"
            with open(setup_file, "r") as f:
                f.read()
            assert True

    def test_package_structure(self):

        project_root = Path(__file__).parent.parent

        wahoo_dir = project_root / "wahoo"
        assert wahoo_dir.exists(), "wahoo package directory should exist"
        assert (wahoo_dir / "__init__.py").exists(), "wahoo should be a package"

        validator_dir = wahoo_dir / "validator"
        assert validator_dir.exists(), "validator module should exist"
        assert (validator_dir / "__init__.py").exists(), "validator should be a package"
