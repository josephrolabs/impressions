from pathlib import Path

import pytest

from impressions.core.config import ConfigError, load_project_config


VALID_CONFIG = """\
version = 1

[paths]
tasks = "tasks"
reports = "reports"
"""


def write_config(root: Path, content: str = VALID_CONFIG) -> Path:
    config = root / "impressions.toml"
    config.write_text(content, encoding="utf-8")
    return config


def test_load_project_config_success(tmp_path):
    config_path = write_config(tmp_path)

    config = load_project_config(tmp_path)

    assert config.root == tmp_path
    assert config.file_path == config_path
    assert config.version == 1
    assert config.paths.tasks == tmp_path / "tasks"
    assert config.paths.reports == tmp_path / "reports"


def test_load_project_config_allows_absolute_paths(tmp_path):
    tasks = tmp_path / "custom-tasks"
    reports = tmp_path / "custom-reports"
    write_config(
        tmp_path,
        f"""\
version = 1

[paths]
tasks = "{tasks.as_posix()}"
reports = "{reports.as_posix()}"
""",
    )

    config = load_project_config(tmp_path)

    assert config.paths.tasks == tasks
    assert config.paths.reports == reports


def test_load_project_config_rejects_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="Missing configuration file"):
        load_project_config(tmp_path)


def test_load_project_config_rejects_invalid_toml(tmp_path):
    write_config(tmp_path, "version =\n")

    with pytest.raises(ConfigError, match="Invalid TOML syntax"):
        load_project_config(tmp_path)


def test_load_project_config_rejects_missing_version(tmp_path):
    write_config(
        tmp_path,
        """\
[paths]
tasks = "tasks"
reports = "reports"
""",
    )

    with pytest.raises(ConfigError, match="Missing required value 'version'"):
        load_project_config(tmp_path)


def test_load_project_config_rejects_non_integer_version(tmp_path):
    write_config(
        tmp_path,
        """\
version = "1"

[paths]
tasks = "tasks"
reports = "reports"
""",
    )

    with pytest.raises(ConfigError, match="Expected 'version'.*integer"):
        load_project_config(tmp_path)


def test_load_project_config_rejects_unsupported_version(tmp_path):
    write_config(
        tmp_path,
        """\
version = 2

[paths]
tasks = "tasks"
reports = "reports"
""",
    )

    with pytest.raises(ConfigError, match="Unsupported configuration version"):
        load_project_config(tmp_path)


def test_load_project_config_rejects_missing_paths_section(tmp_path):
    write_config(tmp_path, "version = 1\n")

    with pytest.raises(ConfigError, match=r"Missing required section \[paths\]"):
        load_project_config(tmp_path)


def test_load_project_config_rejects_missing_tasks_path(tmp_path):
    write_config(
        tmp_path,
        """\
version = 1

[paths]
reports = "reports"
""",
    )

    with pytest.raises(ConfigError, match="Missing required value 'tasks'"):
        load_project_config(tmp_path)


def test_load_project_config_rejects_missing_reports_path(tmp_path):
    write_config(
        tmp_path,
        """\
version = 1

[paths]
tasks = "tasks"
""",
    )

    with pytest.raises(ConfigError, match="Missing required value 'reports'"):
        load_project_config(tmp_path)


def test_load_project_config_rejects_non_string_path(tmp_path):
    write_config(
        tmp_path,
        """\
version = 1

[paths]
tasks = ["tasks"]
reports = "reports"
""",
    )

    with pytest.raises(ConfigError, match="Expected 'tasks'.*string path"):
        load_project_config(tmp_path)


def test_load_project_config_rejects_empty_path(tmp_path):
    write_config(
        tmp_path,
        """\
version = 1

[paths]
tasks = ""
reports = "reports"
""",
    )

    with pytest.raises(ConfigError, match="non-empty path"):
        load_project_config(tmp_path)
