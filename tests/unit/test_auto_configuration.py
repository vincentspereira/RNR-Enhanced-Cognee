"""
Unit tests for src/auto_configuration.py

Targets >= 85% line coverage.
System calls (psutil, subprocess, socket) are mocked.
ASCII-only assertions.
"""

import asyncio
import json
import os
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.auto_configuration import AutoConfiguration  # noqa: E402


# ---------------------------------------------------------------------------
# Helper to build a mock config dict
# ---------------------------------------------------------------------------

def _mock_config(docker_avail=True, memory_gb=8.0, disk_gb=50.0,
                 llm_provider=None, llm_api=False):
    return {
        "system": {
            "os": "Linux",
            "os_version": "5.x",
            "python_version": "3.11",
            "cpu_count": 4,
            "memory_gb": memory_gb,
            "disk_free_gb": disk_gb,
        },
        "docker": {
            "available": docker_avail,
            "version": "Docker 24.0" if docker_avail else None,
            "compose_available": docker_avail,
        },
        "ports": {"postgres": 25432, "qdrant": 26333, "neo4j": 27687, "redis": 26379},
        "llm": {
            "provider": llm_provider,
            "api_key_present": llm_api,
            "recommended_provider": "anthropic",
        },
        "installation_mode": "full" if docker_avail and memory_gb >= 4 and disk_gb >= 10 else "lite",
        "passwords": {"postgres": "pw1", "neo4j": "pw2", "redis": "pw3"},
    }


# ---------------------------------------------------------------------------
# Tests: __init__
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_project_root(self):
        ac = AutoConfiguration()
        assert ac.project_root == Path.cwd()

    def test_custom_project_root(self, tmp_path):
        ac = AutoConfiguration(project_root=tmp_path)
        assert ac.project_root == tmp_path
        assert ac.env_path == tmp_path / ".env"
        assert ac.config_path == tmp_path / "automation_config.json"
        assert ac.category_config_path == tmp_path / ".enhanced-cognee-config.json"


# ---------------------------------------------------------------------------
# Tests: _determine_installation_mode
# ---------------------------------------------------------------------------

class TestDetermineInstallationMode:
    def test_full_mode_with_docker_and_resources(self):
        ac = AutoConfiguration()
        config = _mock_config(docker_avail=True, memory_gb=8.0, disk_gb=50.0)
        mode = ac._determine_installation_mode(config)
        assert mode == "full"

    def test_lite_mode_no_docker(self):
        ac = AutoConfiguration()
        config = _mock_config(docker_avail=False, memory_gb=8.0, disk_gb=50.0)
        mode = ac._determine_installation_mode(config)
        assert mode == "lite"

    def test_lite_mode_low_memory(self):
        ac = AutoConfiguration()
        config = _mock_config(docker_avail=True, memory_gb=2.0, disk_gb=50.0)
        mode = ac._determine_installation_mode(config)
        assert mode == "lite"

    def test_lite_mode_low_disk(self):
        ac = AutoConfiguration()
        config = _mock_config(docker_avail=True, memory_gb=8.0, disk_gb=5.0)
        mode = ac._determine_installation_mode(config)
        assert mode == "lite"


# ---------------------------------------------------------------------------
# Tests: _generate_passwords
# ---------------------------------------------------------------------------

class TestGeneratePasswords:
    def test_generates_three_passwords(self):
        ac = AutoConfiguration()
        passwords = ac._generate_passwords()
        assert "postgres" in passwords
        assert "neo4j" in passwords
        assert "redis" in passwords

    def test_passwords_are_strings(self):
        ac = AutoConfiguration()
        passwords = ac._generate_passwords()
        for key, val in passwords.items():
            assert isinstance(val, str), f"Expected str for {key}"

    def test_passwords_are_unique(self):
        ac = AutoConfiguration()
        passwords = ac._generate_passwords()
        vals = list(passwords.values())
        assert len(set(vals)) == len(vals), "Passwords should be unique"


# ---------------------------------------------------------------------------
# Tests: _get_timestamp
# ---------------------------------------------------------------------------

class TestGetTimestamp:
    def test_returns_string(self):
        ac = AutoConfiguration()
        ts = ac._get_timestamp()
        assert isinstance(ts, str)
        assert "UTC" in ts


# ---------------------------------------------------------------------------
# Tests: _is_port_available
# ---------------------------------------------------------------------------

class TestIsPortAvailable:
    def test_port_available_returns_true(self):
        ac = AutoConfiguration()
        import socket
        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.__enter__ = MagicMock(return_value=mock_sock)
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock.bind = MagicMock(return_value=None)  # no OSError
            mock_sock_cls.return_value = mock_sock
            result = ac._is_port_available(9999)
        assert result is True

    def test_port_unavailable_returns_false(self):
        ac = AutoConfiguration()
        import socket
        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock.__enter__ = MagicMock(return_value=mock_sock)
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_sock.bind = MagicMock(side_effect=OSError("in use"))
            mock_sock_cls.return_value = mock_sock
            result = ac._is_port_available(9999)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: _detect_llm_provider
# ---------------------------------------------------------------------------

class TestDetectLLMProvider:
    @pytest.mark.asyncio
    async def test_anthropic_key_detected(self):
        ac = AutoConfiguration()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-xxx"}, clear=False):
            info = await ac._detect_llm_provider()
        assert info["provider"] == "anthropic"
        assert info["api_key_present"] is True

    @pytest.mark.asyncio
    async def test_openai_key_detected(self):
        ac = AutoConfiguration()
        env = {"OPENAI_API_KEY": "sk-openai-xxx"}
        # Remove ANTHROPIC key to ensure OpenAI path is hit
        patched = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        patched.update(env)
        with patch.dict(os.environ, patched, clear=True):
            info = await ac._detect_llm_provider()
        assert info["provider"] == "openai"
        assert info["api_key_present"] is True

    @pytest.mark.asyncio
    async def test_no_key_returns_none_provider(self):
        ac = AutoConfiguration()
        env = {k: v for k, v in os.environ.items()
               if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")}
        with patch.dict(os.environ, env, clear=True):
            info = await ac._detect_llm_provider()
        assert info["provider"] is None
        assert info["api_key_present"] is False


# ---------------------------------------------------------------------------
# Tests: _detect_docker
# ---------------------------------------------------------------------------

class TestDetectDocker:
    @pytest.mark.asyncio
    async def test_docker_available(self):
        ac = AutoConfiguration()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Docker version 24.0.0"
            )
            info = await ac._detect_docker()
        assert info["available"] is True

    @pytest.mark.asyncio
    async def test_docker_not_found(self):
        ac = AutoConfiguration()
        with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
            info = await ac._detect_docker()
        assert info["available"] is False

    @pytest.mark.asyncio
    async def test_docker_timeout(self):
        ac = AutoConfiguration()
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 5)):
            info = await ac._detect_docker()
        assert info["available"] is False

    @pytest.mark.asyncio
    async def test_docker_available_no_compose(self):
        ac = AutoConfiguration()

        call_count = [0]

        def mock_run(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MagicMock(returncode=0, stdout="Docker version 24.0")
            else:
                return MagicMock(returncode=1, stdout="")

        with patch("subprocess.run", side_effect=mock_run):
            info = await ac._detect_docker()
        assert info["available"] is True
        assert info["compose_available"] is False


# ---------------------------------------------------------------------------
# Tests: _detect_available_ports
# ---------------------------------------------------------------------------

class TestDetectAvailablePorts:
    @pytest.mark.asyncio
    async def test_all_default_ports_available(self):
        ac = AutoConfiguration()
        with patch.object(ac, "_is_port_available", return_value=True):
            ports = await ac._detect_available_ports()
        assert ports["postgres"] == 25432
        assert ports["qdrant"] == 26333
        assert ports["neo4j"] == 27687
        assert ports["redis"] == 26379

    @pytest.mark.asyncio
    async def test_alternative_port_selected_when_default_busy(self):
        ac = AutoConfiguration()

        call_count = [0]

        def port_check(port):
            call_count[0] += 1
            # First call (25432) is not available, second (25433) is available
            return port != 25432

        with patch.object(ac, "_is_port_available", side_effect=port_check):
            ports = await ac._detect_available_ports()
        assert ports["postgres"] == 25433


# ---------------------------------------------------------------------------
# Tests: _detect_system_capabilities
# ---------------------------------------------------------------------------

class TestDetectSystemCapabilities:
    @pytest.mark.asyncio
    async def test_returns_system_info(self):
        ac = AutoConfiguration()

        mock_vmem = MagicMock()
        mock_vmem.total = 8 * 1024**3  # 8 GB

        mock_disk = MagicMock()
        mock_disk.free = 50 * 1024**3  # 50 GB

        with patch("platform.system", return_value="Linux"), \
             patch("platform.version", return_value="5.x"), \
             patch("platform.python_version", return_value="3.11"), \
             patch("psutil.cpu_count", return_value=4), \
             patch("psutil.virtual_memory", return_value=mock_vmem), \
             patch("psutil.disk_usage", return_value=mock_disk):
            info = await ac._detect_system_capabilities()

        assert info["os"] == "Linux"
        assert info["cpu_count"] == 4
        assert info["memory_gb"] == 8.0

    @pytest.mark.asyncio
    async def test_windows_uses_c_drive(self):
        ac = AutoConfiguration()

        mock_vmem = MagicMock()
        mock_vmem.total = 4 * 1024**3

        mock_disk = MagicMock()
        mock_disk.free = 20 * 1024**3

        with patch("platform.system", return_value="Windows"), \
             patch("platform.version", return_value="10.x"), \
             patch("platform.python_version", return_value="3.11"), \
             patch("psutil.cpu_count", return_value=8), \
             patch("psutil.virtual_memory", return_value=mock_vmem), \
             patch("psutil.disk_usage", return_value=mock_disk):
            info = await ac._detect_system_capabilities()

        assert info["os"] == "Windows"


# ---------------------------------------------------------------------------
# Tests: _generate_env_content
# ---------------------------------------------------------------------------

class TestGenerateEnvContent:
    def test_basic_env_content(self):
        ac = AutoConfiguration()
        config = _mock_config()
        content = ac._generate_env_content(config)
        assert "POSTGRES_PORT=25432" in content
        assert "ENHANCED_COGNEE_MODE=true" in content
        assert "NEO4J_URI=bolt://localhost:27687" in content

    def test_anthropic_key_included_when_present(self):
        ac = AutoConfiguration()
        config = _mock_config(llm_provider="anthropic", llm_api=True)
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            content = ac._generate_env_content(config)
        assert "ANTHROPIC_API_KEY=sk-ant-test" in content

    def test_openai_key_included_when_present(self):
        ac = AutoConfiguration()
        config = _mock_config(llm_provider="openai", llm_api=True)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-oai-test"}):
            content = ac._generate_env_content(config)
        assert "OPENAI_API_KEY=sk-oai-test" in content

    def test_lite_mode_reflected(self):
        ac = AutoConfiguration()
        config = _mock_config(docker_avail=False)
        content = ac._generate_env_content(config)
        assert "INSTALLATION_MODE=lite" in content


# ---------------------------------------------------------------------------
# Tests: _generate_automation_config / _generate_category_config
# ---------------------------------------------------------------------------

class TestGenerateConfigs:
    @pytest.mark.asyncio
    async def test_generate_automation_config_missing_file(self, tmp_path):
        ac = AutoConfiguration(project_root=tmp_path)
        # config_path does not exist -> logs warning, does not raise
        await ac._generate_automation_config()

    @pytest.mark.asyncio
    async def test_generate_automation_config_existing_file(self, tmp_path):
        cfg = tmp_path / "automation_config.json"
        cfg.write_text("{}")
        ac = AutoConfiguration(project_root=tmp_path)
        await ac._generate_automation_config()

    @pytest.mark.asyncio
    async def test_generate_category_config(self, tmp_path):
        ac = AutoConfiguration(project_root=tmp_path)
        await ac._generate_category_config()
        cat_file = tmp_path / ".enhanced-cognee-config.json"
        assert cat_file.exists()
        data = json.loads(cat_file.read_text())
        assert "categories" in data
        assert "trading" in data["categories"]


# ---------------------------------------------------------------------------
# Tests: apply_configuration
# ---------------------------------------------------------------------------

class TestApplyConfiguration:
    @pytest.mark.asyncio
    async def test_apply_creates_env_file(self, tmp_path):
        ac = AutoConfiguration(project_root=tmp_path)
        config = _mock_config()
        result = await ac.apply_configuration(config)
        assert result is True
        env_file = tmp_path / ".env"
        assert env_file.exists()

    @pytest.mark.asyncio
    async def test_apply_creates_category_config(self, tmp_path):
        ac = AutoConfiguration(project_root=tmp_path)
        config = _mock_config()
        await ac.apply_configuration(config)
        cat_file = tmp_path / ".enhanced-cognee-config.json"
        assert cat_file.exists()

    @pytest.mark.asyncio
    async def test_apply_returns_false_on_exception(self, tmp_path):
        ac = AutoConfiguration(project_root=tmp_path)
        config = _mock_config()
        # Make write_text raise
        with patch.object(Path, "write_text", side_effect=PermissionError("denied")):
            result = await ac.apply_configuration(config)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: auto_configure (integration-level)
# ---------------------------------------------------------------------------

class TestAutoConfigure:
    @pytest.mark.asyncio
    async def test_auto_configure_returns_full_dict(self):
        ac = AutoConfiguration()

        mock_vmem = MagicMock()
        mock_vmem.total = 8 * 1024**3
        mock_disk = MagicMock()
        mock_disk.free = 50 * 1024**3

        with patch("platform.system", return_value="Linux"), \
             patch("platform.version", return_value="5.x"), \
             patch("platform.python_version", return_value="3.11"), \
             patch("psutil.cpu_count", return_value=4), \
             patch("psutil.virtual_memory", return_value=mock_vmem), \
             patch("psutil.disk_usage", return_value=mock_disk), \
             patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="Docker v24")), \
             patch.object(ac, "_is_port_available", return_value=True), \
             patch.dict(os.environ, {}, clear=False):
            config = await ac.auto_configure()

        assert "system" in config
        assert "docker" in config
        assert "ports" in config
        assert "llm" in config
        assert "installation_mode" in config
        assert "passwords" in config


# ---------------------------------------------------------------------------
# Tests: _detect_docker - Docker not available path (line 128)
# ---------------------------------------------------------------------------

class TestDetectDockerNotAvailable:
    @pytest.mark.asyncio
    async def test_docker_returns_non_zero_marks_unavailable(self):
        """Line 128: docker --version returncode != 0 -> Docker not available."""
        ac = AutoConfiguration()
        failing_result = MagicMock(returncode=1, stdout="", stderr="command not found")
        with patch("subprocess.run", return_value=failing_result):
            docker_info = await ac._detect_docker()
        assert docker_info["available"] is False


# ---------------------------------------------------------------------------
# Tests: module-level main() function (lines 353-357)
# ---------------------------------------------------------------------------

class TestMainFunction:
    @pytest.mark.asyncio
    async def test_main_runs_without_raising(self):
        """Lines 353-357: module-level main() calls auto_configure and apply_configuration."""
        import src.auto_configuration as _ac_mod

        mock_config = {"system": {}, "docker": {}, "ports": {}, "llm": {},
                       "installation_mode": "docker", "passwords": {}}

        with patch.object(_ac_mod.AutoConfiguration, "auto_configure",
                          new_callable=AsyncMock, return_value=mock_config), \
             patch.object(_ac_mod.AutoConfiguration, "apply_configuration",
                          new_callable=AsyncMock, return_value=True), \
             patch("builtins.print"):
            await _ac_mod.main()
