"""Unit tests for src/memory_config.py

Coverage target: >=85%
Missing lines before this file: 115-120, 131, 140, 157, 208-244, 267-285
Lines 267-285 are the __main__ block -- untestable by design.
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the global config manager singleton before and after each test."""
    from src.memory_config import reset_config_manager
    reset_config_manager()
    yield
    reset_config_manager()


def _make_config_json(categories=None, agents=None):
    """Return a minimal config dict."""
    data = {}
    if categories is not None:
        data["categories"] = categories
    if agents is not None:
        data["agents"] = agents
    return data


# ---------------------------------------------------------------------------
# MemoryCategoryConfig dataclass
# ---------------------------------------------------------------------------

class TestMemoryCategoryConfig:
    def test_basic_construction(self):
        from src.memory_config import MemoryCategoryConfig
        cat = MemoryCategoryConfig(
            name="test",
            description="Test category",
            prefix="test_"
        )
        assert cat.name == "test"
        assert cat.description == "Test category"
        assert cat.prefix == "test_"
        assert cat.retention_days == 30  # default
        assert cat.priority == 1  # default

    def test_custom_retention_and_priority(self):
        from src.memory_config import MemoryCategoryConfig
        cat = MemoryCategoryConfig(
            name="important",
            description="High priority",
            prefix="imp_",
            retention_days=90,
            priority=5
        )
        assert cat.retention_days == 90
        assert cat.priority == 5


# ---------------------------------------------------------------------------
# AgentConfig dataclass
# ---------------------------------------------------------------------------

class TestAgentConfig:
    def test_basic_construction(self):
        from src.memory_config import AgentConfig
        agent = AgentConfig(
            agent_id="my-agent",
            category="trading",
            prefix="trd_",
            description="A trading agent"
        )
        assert agent.agent_id == "my-agent"
        assert agent.category == "trading"
        assert agent.prefix == "trd_"
        assert agent.memory_types == []  # default_factory
        assert agent.priority == 1
        assert agent.data_retention_days == 30

    def test_with_memory_types(self):
        from src.memory_config import AgentConfig
        agent = AgentConfig(
            agent_id="bot",
            category="dev",
            prefix="dev_",
            description="Dev bot",
            memory_types=["factual", "procedural"],
            priority=2,
            data_retention_days=60
        )
        assert agent.memory_types == ["factual", "procedural"]
        assert agent.priority == 2
        assert agent.data_retention_days == 60


# ---------------------------------------------------------------------------
# DefaultMemoryCategories
# ---------------------------------------------------------------------------

class TestDefaultMemoryCategories:
    def test_get_example_categories_keys(self):
        from src.memory_config import DefaultMemoryCategories
        cats = DefaultMemoryCategories.get_example_categories()
        assert "trading" in cats
        assert "development" in cats
        assert "coordination" in cats

    def test_get_example_categories_types(self):
        from src.memory_config import DefaultMemoryCategories, MemoryCategoryConfig
        cats = DefaultMemoryCategories.get_example_categories()
        for val in cats.values():
            assert isinstance(val, MemoryCategoryConfig)

    def test_get_example_categories_trading_prefix(self):
        from src.memory_config import DefaultMemoryCategories
        cats = DefaultMemoryCategories.get_example_categories()
        assert cats["trading"].prefix == "trading_"

    def test_get_default_categories_single_key(self):
        from src.memory_config import DefaultMemoryCategories
        cats = DefaultMemoryCategories.get_default_categories()
        assert "DEFAULT" in cats
        assert len(cats) == 1

    def test_get_default_categories_empty_prefix(self):
        from src.memory_config import DefaultMemoryCategories
        cats = DefaultMemoryCategories.get_default_categories()
        assert cats["DEFAULT"].prefix == ""

    def test_example_and_default_are_independent(self):
        from src.memory_config import DefaultMemoryCategories
        example = DefaultMemoryCategories.get_example_categories()
        default = DefaultMemoryCategories.get_default_categories()
        assert set(example.keys()).isdisjoint(set(default.keys()))


# ---------------------------------------------------------------------------
# MemoryConfigManager - init paths
# ---------------------------------------------------------------------------

class TestMemoryConfigManagerInit:
    def test_loads_defaults_when_no_config_found(self):
        """Lines 115-120: no config file found -> use example categories."""
        from src.memory_config import MemoryConfigManager
        with patch.object(MemoryConfigManager, "_find_config_file", return_value=None):
            mgr = MemoryConfigManager()
        # Should fall back to example categories
        cats = mgr.get_all_categories()
        assert "trading" in cats

    def test_loads_from_json_when_path_provided(self, tmp_path):
        from src.memory_config import MemoryConfigManager
        config_data = _make_config_json(
            categories={
                "mycat": {
                    "name": "mycat",
                    "description": "My category",
                    "prefix": "mc_",
                    "retention_days": 30,
                    "priority": 1
                }
            }
        )
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        mgr = MemoryConfigManager(config_path=str(config_file))
        assert mgr.get_category("mycat") is not None
        assert mgr.get_category("mycat").prefix == "mc_"

    def test_explicit_config_path_used(self, tmp_path):
        from src.memory_config import MemoryConfigManager
        config_data = _make_config_json(categories={
            "proj": {
                "name": "proj",
                "description": "Project",
                "prefix": "proj_",
                "retention_days": 30,
                "priority": 1
            }
        })
        config_file = tmp_path / ".enhanced-cognee-config.json"
        config_file.write_text(json.dumps(config_data))
        mgr = MemoryConfigManager(config_path=str(config_file))
        assert mgr.get_category("proj") is not None


# ---------------------------------------------------------------------------
# MemoryConfigManager._find_config_file
# ---------------------------------------------------------------------------

class TestFindConfigFile:
    def test_returns_explicit_path_when_set(self, tmp_path):
        from src.memory_config import MemoryConfigManager
        config_file = tmp_path / "custom.json"
        config_file.write_text("{}")
        # Pass as constructor arg; config_path is stored, _find_config_file returns it
        mgr = MemoryConfigManager.__new__(MemoryConfigManager)
        mgr.config_path = str(config_file)
        mgr.categories = {}
        mgr.agents = {}
        found = mgr._find_config_file()
        assert found == str(config_file)

    def test_returns_env_var_path_when_no_explicit_path(self, tmp_path):
        """Line 131: env_path returned when config_path is None."""
        from src.memory_config import MemoryConfigManager
        env_file = tmp_path / "env_config.json"
        env_file.write_text("{}")
        mgr = MemoryConfigManager.__new__(MemoryConfigManager)
        mgr.config_path = None
        mgr.categories = {}
        mgr.agents = {}
        with patch.dict(os.environ, {"ENHANCED_COGNEE_CONFIG_PATH": str(env_file)}):
            found = mgr._find_config_file()
        assert found == str(env_file)

    def test_returns_none_when_no_file_found(self, tmp_path):
        """Line 140: returns None when no config file in directory tree."""
        from src.memory_config import MemoryConfigManager
        mgr = MemoryConfigManager.__new__(MemoryConfigManager)
        mgr.config_path = None
        mgr.categories = {}
        mgr.agents = {}
        # Use a directory guaranteed to not have .enhanced-cognee-config.json
        # by patching Path.cwd() and ensuring no parent has the file
        with patch.dict(os.environ, {}, clear=False):
            # Remove env var if present
            env_backup = os.environ.pop("ENHANCED_COGNEE_CONFIG_PATH", None)
            try:
                with patch("src.memory_config.Path") as mock_path_cls:
                    # Make cwd() return a path with no config file in any parent
                    mock_cwd = MagicMock()
                    mock_cwd.parents = []
                    fake_config = MagicMock()
                    fake_config.exists.return_value = False
                    mock_cwd.__truediv__ = MagicMock(return_value=fake_config)
                    mock_path_cls.cwd.return_value = mock_cwd
                    found = mgr._find_config_file()
            finally:
                if env_backup is not None:
                    os.environ["ENHANCED_COGNEE_CONFIG_PATH"] = env_backup
        assert found is None

    def test_finds_config_in_parent_directory(self, tmp_path):
        """Config file in a parent directory is found."""
        from src.memory_config import MemoryConfigManager
        # Create a config file in tmp_path
        config_file = tmp_path / ".enhanced-cognee-config.json"
        config_data = _make_config_json(categories={
            "found_cat": {
                "name": "found_cat",
                "description": "Found",
                "prefix": "fc_",
                "retention_days": 30,
                "priority": 1
            }
        })
        config_file.write_text(json.dumps(config_data))

        # Create a subdirectory and make it the "cwd" so the search climbs to tmp_path
        sub_dir = tmp_path / "subdir"
        sub_dir.mkdir()

        env_backup = os.environ.pop("ENHANCED_COGNEE_CONFIG_PATH", None)
        try:
            with patch("src.memory_config.Path") as mock_path_cls:
                mock_path_cls.cwd.return_value = Path(str(sub_dir))
                # Allow Path(str) calls to work normally for exists() check
                mock_path_cls.side_effect = lambda x: Path(x)
                mock_path_cls.cwd.return_value = Path(str(sub_dir))
                mgr = MemoryConfigManager.__new__(MemoryConfigManager)
                mgr.config_path = None
                mgr.categories = {}
                mgr.agents = {}
                found = mgr._find_config_file()
        finally:
            if env_backup is not None:
                os.environ["ENHANCED_COGNEE_CONFIG_PATH"] = env_backup

        assert found == str(config_file)


# ---------------------------------------------------------------------------
# MemoryConfigManager._load_from_json
# ---------------------------------------------------------------------------

class TestLoadFromJson:
    def test_loads_categories_from_json(self, tmp_path):
        from src.memory_config import MemoryConfigManager
        config_data = _make_config_json(
            categories={
                "alpha": {
                    "name": "alpha",
                    "description": "Alpha cat",
                    "prefix": "a_",
                    "retention_days": 45,
                    "priority": 2
                }
            }
        )
        config_file = tmp_path / "cfg.json"
        config_file.write_text(json.dumps(config_data))
        mgr = MemoryConfigManager(config_path=str(config_file))
        cat = mgr.get_category("alpha")
        assert cat is not None
        assert cat.prefix == "a_"
        assert cat.retention_days == 45

    def test_loads_agents_from_json(self, tmp_path):
        """Line 157: agents section loaded from JSON."""
        from src.memory_config import MemoryConfigManager
        config_data = _make_config_json(
            categories={
                "cat1": {
                    "name": "cat1",
                    "description": "Cat 1",
                    "prefix": "c1_",
                    "retention_days": 30,
                    "priority": 1
                }
            },
            agents={
                "agent-one": {
                    "agent_id": "agent-one",
                    "category": "cat1",
                    "prefix": "c1_",
                    "description": "First agent",
                    "memory_types": ["factual"],
                    "priority": 1,
                    "data_retention_days": 30
                }
            }
        )
        config_file = tmp_path / "full.json"
        config_file.write_text(json.dumps(config_data))
        mgr = MemoryConfigManager(config_path=str(config_file))
        agent = mgr.get_agent_config("agent-one")
        assert agent is not None
        assert agent.category == "cat1"
        assert agent.memory_types == ["factual"]

    def test_falls_back_to_defaults_on_json_error(self, tmp_path):
        """Error loading JSON -> fall back to example categories."""
        from src.memory_config import MemoryConfigManager
        config_file = tmp_path / "bad.json"
        config_file.write_text("{not valid json!!!")
        mgr = MemoryConfigManager(config_path=str(config_file))
        # Should fall back to example categories
        cats = mgr.get_all_categories()
        assert "trading" in cats

    def test_config_without_categories_key_leaves_empty(self, tmp_path):
        """JSON without 'categories' key leaves categories dict empty."""
        from src.memory_config import MemoryConfigManager
        config_data = {"project_name": "test"}
        config_file = tmp_path / "no_cats.json"
        config_file.write_text(json.dumps(config_data))
        mgr = MemoryConfigManager(config_path=str(config_file))
        assert mgr.get_all_categories() == {}

    def test_config_without_agents_key_leaves_empty(self, tmp_path):
        """JSON without 'agents' key leaves agents dict empty."""
        from src.memory_config import MemoryConfigManager
        config_data = _make_config_json(categories={
            "x": {"name": "x", "description": "X", "prefix": "x_",
                  "retention_days": 30, "priority": 1}
        })
        config_file = tmp_path / "no_agents.json"
        config_file.write_text(json.dumps(config_data))
        mgr = MemoryConfigManager(config_path=str(config_file))
        assert mgr.get_all_agents() == {}


# ---------------------------------------------------------------------------
# MemoryConfigManager public API
# ---------------------------------------------------------------------------

class TestMemoryConfigManagerAPI:
    def _make_mgr(self, tmp_path):
        from src.memory_config import MemoryConfigManager
        config_data = _make_config_json(
            categories={
                "cat_a": {
                    "name": "cat_a",
                    "description": "Cat A",
                    "prefix": "ca_",
                    "retention_days": 30,
                    "priority": 1
                },
                "cat_b": {
                    "name": "cat_b",
                    "description": "Cat B",
                    "prefix": "cb_",
                    "retention_days": 60,
                    "priority": 2
                }
            },
            agents={
                "agent-a": {
                    "agent_id": "agent-a",
                    "category": "cat_a",
                    "prefix": "ca_",
                    "description": "Agent A",
                    "memory_types": [],
                    "priority": 1,
                    "data_retention_days": 30
                }
            }
        )
        config_file = tmp_path / "mgr.json"
        config_file.write_text(json.dumps(config_data))
        return MemoryConfigManager(config_path=str(config_file))

    def test_get_category_existing(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        cat = mgr.get_category("cat_a")
        assert cat.name == "cat_a"

    def test_get_category_nonexistent_returns_none(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        assert mgr.get_category("nonexistent") is None

    def test_get_all_categories_returns_all(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        cats = mgr.get_all_categories()
        assert set(cats.keys()) == {"cat_a", "cat_b"}

    def test_get_agent_config_existing(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        agent = mgr.get_agent_config("agent-a")
        assert agent.agent_id == "agent-a"

    def test_get_agent_config_nonexistent_returns_none(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        assert mgr.get_agent_config("no-such-agent") is None

    def test_get_all_agents_returns_all(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        agents = mgr.get_all_agents()
        assert "agent-a" in agents

    def test_add_category(self, tmp_path):
        from src.memory_config import MemoryCategoryConfig
        mgr = self._make_mgr(tmp_path)
        new_cat = MemoryCategoryConfig(
            name="cat_c",
            description="Cat C",
            prefix="cc_"
        )
        mgr.add_category("cat_c", new_cat)
        assert mgr.get_category("cat_c") is not None
        assert mgr.get_category("cat_c").prefix == "cc_"

    def test_add_category_overwrites_existing(self, tmp_path):
        from src.memory_config import MemoryCategoryConfig
        mgr = self._make_mgr(tmp_path)
        updated = MemoryCategoryConfig(
            name="cat_a",
            description="Updated",
            prefix="new_"
        )
        mgr.add_category("cat_a", updated)
        assert mgr.get_category("cat_a").prefix == "new_"

    def test_add_agent(self, tmp_path):
        from src.memory_config import AgentConfig
        mgr = self._make_mgr(tmp_path)
        new_agent = AgentConfig(
            agent_id="agent-b",
            category="cat_b",
            prefix="cb_",
            description="Agent B"
        )
        mgr.add_agent("agent-b", new_agent)
        assert mgr.get_agent_config("agent-b") is not None

    def test_validate_category_existing_returns_true(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        assert mgr.validate_category("cat_a") is True

    def test_validate_category_nonexistent_returns_false(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        assert mgr.validate_category("no_such_cat") is False

    def test_get_prefix_for_existing_category(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        prefix = mgr.get_prefix_for_category("cat_a")
        assert prefix == "ca_"

    def test_get_prefix_for_nonexistent_category_returns_empty(self, tmp_path):
        mgr = self._make_mgr(tmp_path)
        prefix = mgr.get_prefix_for_category("missing")
        assert prefix == ""


# ---------------------------------------------------------------------------
# create_project_config_example
# ---------------------------------------------------------------------------

class TestCreateProjectConfigExample:
    def test_creates_file_at_output_path(self, tmp_path):
        """Lines 208-244: function creates a JSON file and returns config dict."""
        from src.memory_config import create_project_config_example
        output_file = str(tmp_path / "my-config.json")
        result = create_project_config_example(output_path=output_file)
        assert Path(output_file).exists()

    def test_returns_config_dict(self, tmp_path):
        from src.memory_config import create_project_config_example
        output_file = str(tmp_path / "out.json")
        result = create_project_config_example(output_path=output_file)
        assert isinstance(result, dict)
        assert "categories" in result
        assert "agents" in result

    def test_written_file_is_valid_json(self, tmp_path):
        from src.memory_config import create_project_config_example
        output_file = str(tmp_path / "valid.json")
        create_project_config_example(output_path=output_file)
        with open(output_file) as f:
            data = json.load(f)
        assert "categories" in data

    def test_example_contains_two_categories(self, tmp_path):
        from src.memory_config import create_project_config_example
        output_file = str(tmp_path / "two.json")
        result = create_project_config_example(output_path=output_file)
        assert len(result["categories"]) == 2

    def test_example_contains_one_agent(self, tmp_path):
        from src.memory_config import create_project_config_example
        output_file = str(tmp_path / "agent.json")
        result = create_project_config_example(output_path=output_file)
        assert len(result["agents"]) == 1

    def test_default_output_path_used_when_not_specified(self, tmp_path):
        """Test that default output path (.enhanced-cognee-config.json) is used."""
        from src.memory_config import create_project_config_example
        default_path = tmp_path / ".enhanced-cognee-config.json"
        # Call with explicit default path in tmp_path to avoid polluting cwd
        result = create_project_config_example(output_path=str(default_path))
        assert default_path.exists()
        assert result is not None


# ---------------------------------------------------------------------------
# Singleton: get_config_manager / reset_config_manager
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_config_manager_returns_instance(self):
        from src.memory_config import get_config_manager, MemoryConfigManager
        mgr = get_config_manager()
        assert isinstance(mgr, MemoryConfigManager)

    def test_get_config_manager_returns_same_instance_on_repeat_calls(self):
        from src.memory_config import get_config_manager
        mgr1 = get_config_manager()
        mgr2 = get_config_manager()
        assert mgr1 is mgr2

    def test_reset_config_manager_clears_singleton(self):
        from src.memory_config import get_config_manager, reset_config_manager
        mgr1 = get_config_manager()
        reset_config_manager()
        mgr2 = get_config_manager()
        assert mgr1 is not mgr2

    def test_reset_config_manager_idempotent_when_already_none(self):
        from src.memory_config import reset_config_manager
        reset_config_manager()  # Already None from fixture
        reset_config_manager()  # Should not raise

    def test_get_config_manager_with_env_config(self, tmp_path):
        """Singleton picks up env var config path."""
        from src.memory_config import get_config_manager, reset_config_manager
        config_data = _make_config_json(categories={
            "env_cat": {
                "name": "env_cat",
                "description": "From env",
                "prefix": "env_",
                "retention_days": 30,
                "priority": 1
            }
        })
        config_file = tmp_path / "env.json"
        config_file.write_text(json.dumps(config_data))

        reset_config_manager()
        with patch.dict(os.environ, {"ENHANCED_COGNEE_CONFIG_PATH": str(config_file)}):
            mgr = get_config_manager()
            cat = mgr.get_category("env_cat")
        assert cat is not None
        assert cat.prefix == "env_"
