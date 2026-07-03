import pathlib

from impressions import cli


def test_init_creates_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    rc = cli.main(["init"])
    assert rc == 0

    toml = tmp_path / "impressions.toml"
    task = tmp_path / "tasks" / "example.yaml"
    reports = tmp_path / "reports"

    assert toml.exists()
    assert task.exists()
    assert reports.exists() and reports.is_dir()

    assert toml.read_text(encoding="utf-8") == cli.DEFAULT_TOML
    assert task.read_text(encoding="utf-8") == cli.DEFAULT_EXAMPLE_TASK


def test_init_prompt_skip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    toml = tmp_path / "impressions.toml"
    toml.write_text("original", encoding="utf-8")

    monkeypatch.setattr("builtins.input", lambda prompt='': "n")

    rc = cli.main(["init"])
    assert rc == 0

    assert toml.read_text(encoding="utf-8") == "original"


def test_init_force_overwrite(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    toml = tmp_path / "impressions.toml"
    toml.write_text("original", encoding="utf-8")

    rc = cli.main(["init", "--force"])
    assert rc == 0

    assert toml.read_text(encoding="utf-8") == cli.DEFAULT_TOML
