import pytest
from loguru import logger

from easy_gateway.cli import main, setup_logger, validate_config
from easy_gateway.config import read_config


def test_validate_config_valid(tmp_path):
    path = tmp_path / "conf.yaml"
    path.write_text("server:\n  host: 0.0.0.0\n  port: 8000\n")
    assert validate_config(path) is True


def test_validate_config_missing(tmp_path):
    assert validate_config(tmp_path / "missing.yaml") is False


def test_validate_config_is_directory(tmp_path):
    assert validate_config(tmp_path) is False


def test_validate_config_invalid_yaml(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(": : : not really yaml[\n")
    assert read_config(str(path)) == {}


def test_setup_logger_configures_handler():
    setup_logger()
    assert len(logger._core.handlers) >= 1


def test_main_exits_on_invalid_config(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "sys.argv", ["easy-gateway", "-c", str(tmp_path / "missing.yaml")]
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_version_flag(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["easy-gateway", "--version"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "0.1.14" in capsys.readouterr().out


def test_main_starts_gateway(tmp_path, monkeypatch):
    conf = tmp_path / "conf.yaml"
    conf.write_text("server:\n  host: 0.0.0.0\n  port: 8000\n")
    monkeypatch.setattr("sys.argv", ["easy-gateway", "-c", str(conf)])

    started = {}

    class FakeGateway:
        def __init__(self, config_path="easy_conf.yaml", config=None):
            started["config_path"] = config_path
            started["closed"] = False

        def run(self):
            started["closed"] = True

    monkeypatch.setattr("easy_gateway.cli.EasyGateway", FakeGateway)
    main()
    assert started["config_path"] == str(conf)
    assert started["closed"] is True


def test_main_handles_keyboard_interrupt(tmp_path, monkeypatch):
    conf = tmp_path / "conf.yaml"
    conf.write_text("server:\n  host: 0.0.0.0\n  port: 8000\n")
    monkeypatch.setattr("sys.argv", ["easy-gateway", "-c", str(conf)])

    class FakeGateway:
        def __init__(self, config_path="easy_conf.yaml", config=None):
            pass

        def run(self):
            raise KeyboardInterrupt

    monkeypatch.setattr("easy_gateway.cli.EasyGateway", FakeGateway)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
