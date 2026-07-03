import pytest

from impressions import __version__
from impressions.cli import main


def test_help_command(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    captured = capsys.readouterr()

    assert exc_info.value.code == 0
    assert "usage: impressions" in captured.out
    assert "version" in captured.out


def test_no_command_shows_help(capsys):
    exit_code = main([])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "usage: impressions" in captured.out


def test_version_command(capsys):
    exit_code = main(["version"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == f"impressions {__version__}"


def test_init_command_creates_project_scaffold(tmp_path, capsys):
    exit_code = main(["init", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Initialized Impressions project" in captured.out
    assert (tmp_path / "impressions.toml").is_file()
    assert "version = 1" in (tmp_path / "impressions.toml").read_text(
        encoding="utf-8"
    )
    assert "[paths]" in (tmp_path / "impressions.toml").read_text(
        encoding="utf-8"
    )
    assert (tmp_path / "tasks" / "example.yaml").is_file()
    assert (tmp_path / "reports").is_dir()


def test_init_command_does_not_overwrite_without_confirmation(
    tmp_path, monkeypatch, capsys
):
    config = tmp_path / "impressions.toml"
    config.write_text("custom = true\n", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    exit_code = main(["init", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Initialization cancelled." in captured.out
    assert config.read_text(encoding="utf-8") == "custom = true\n"


def test_init_command_overwrites_with_confirmation(tmp_path, monkeypatch):
    config = tmp_path / "impressions.toml"
    config.write_text("custom = true\n", encoding="utf-8")
    monkeypatch.setattr("builtins.input", lambda _prompt: "yes")

    exit_code = main(["init", str(tmp_path)])

    assert exit_code == 0
    assert "[paths]" in config.read_text(encoding="utf-8")
    assert (tmp_path / "tasks" / "example.yaml").is_file()
    assert (tmp_path / "reports").is_dir()


def test_init_command_force_overwrites_existing_files(tmp_path):
    example = tmp_path / "tasks" / "example.yaml"
    example.parent.mkdir()
    example.write_text("custom: true\n", encoding="utf-8")

    exit_code = main(["init", "--force", str(tmp_path)])

    assert exit_code == 0
    assert "id: example_task" in example.read_text(encoding="utf-8")


def test_init_command_rejects_incompatible_paths(tmp_path, capsys):
    reports = tmp_path / "reports"
    reports.write_text("not a directory\n", encoding="utf-8")

    exit_code = main(["init", "--force", str(tmp_path)])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "incompatible types" in captured.out
    assert reports.read_text(encoding="utf-8") == "not a directory\n"


def test_config_show_displays_loaded_configuration(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["config", "show"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Project Configuration" in captured.out
    assert "Configuration file:" in captured.out
    assert "impressions.toml" in captured.out
    assert "Paths" in captured.out
    assert "tasks: tasks/" in captured.out
    assert "reports: reports/" in captured.out


def test_config_show_reports_missing_configuration(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    exit_code = main(["config", "show"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Missing configuration file" in captured.out
    assert "impressions.toml" in captured.out


def test_tasks_list_displays_discovered_tasks(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    tasks_dir = tmp_path / "tasks"
    (tasks_dir / "summarize.yaml").write_text("id: summarize\n", encoding="utf-8")
    (tasks_dir / "classify.yaml").write_text("id: classify\n", encoding="utf-8")
    (tasks_dir / ".hidden.yaml").write_text("id: hidden\n", encoding="utf-8")
    (tasks_dir / "notes.txt").write_text("not a task\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["tasks", "list"])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.splitlines() == [
        "Discovered 3 task(s)",
        "",
        "- classify.yaml",
        "- example.yaml",
        "- summarize.yaml",
    ]


def test_tasks_list_reports_discovery_error(tmp_path, monkeypatch, capsys):
    main(["init", str(tmp_path)])
    capsys.readouterr()
    for task_file in (tmp_path / "tasks").iterdir():
        task_file.unlink()
    monkeypatch.chdir(tmp_path)

    exit_code = main(["tasks", "list"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "No task definition files found" in captured.out
