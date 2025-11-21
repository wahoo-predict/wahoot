import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from wahoo.validator.init import check_virtual_env


class TestVirtualEnvironment:
    def test_detects_virtual_env_from_env_var(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "test_venv"
            venv_path.mkdir()

            with patch.dict(os.environ, {"VIRTUAL_ENV": str(venv_path)}):
                result = check_virtual_env()
                assert result is not None
                assert result == venv_path

    def test_detects_venv_directory_unix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            venv_dir = cwd / "venv"
            venv_dir.mkdir()
            (venv_dir / "bin").mkdir()
            (venv_dir / "bin" / "python").touch()

            with patch("wahoo.validator.init.Path.cwd", return_value=cwd):
                with patch.dict(os.environ, {"VIRTUAL_ENV": ""}, clear=False):
                    result = check_virtual_env()
                    assert result is not None
                    assert result == venv_dir

    def test_detects_env_directory_unix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            env_dir = cwd / "env"
            env_dir.mkdir()
            (env_dir / "bin").mkdir()
            (env_dir / "bin" / "python").touch()

            with patch("wahoo.validator.init.Path.cwd", return_value=cwd):
                with patch.dict(os.environ, {"VIRTUAL_ENV": ""}, clear=False):
                    result = check_virtual_env()
                    assert result is not None
                    assert result == env_dir

    def test_returns_none_when_no_venv(self):

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)

            with patch("wahoo.validator.init.Path.cwd", return_value=cwd):
                with patch.dict(os.environ, {"VIRTUAL_ENV": ""}, clear=False):
                    result = check_virtual_env()
                    assert result is None

    def test_prioritizes_env_var_over_directory(self):

        with tempfile.TemporaryDirectory() as tmpdir:
            env_var_venv = Path(tmpdir) / "env_var_venv"
            env_var_venv.mkdir()

            cwd = Path(tmpdir)
            venv_dir = cwd / "venv"
            venv_dir.mkdir()
            (venv_dir / "bin").mkdir()
            (venv_dir / "bin" / "python").touch()

            with patch("wahoo.validator.init.Path.cwd", return_value=cwd):
                with patch.dict(os.environ, {"VIRTUAL_ENV": str(env_var_venv)}):
                    result = check_virtual_env()
                    assert result == env_var_venv
                    assert result != venv_dir
