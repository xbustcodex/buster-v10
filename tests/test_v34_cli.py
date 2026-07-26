# tests/test_v34_cli.py
import pytest
from buster.cli import main


def test_cli_goal_execution(capsys):
    exit_code = main(["Please write a log and then read it back"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Mission Success!" in captured.out