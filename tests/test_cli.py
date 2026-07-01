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
