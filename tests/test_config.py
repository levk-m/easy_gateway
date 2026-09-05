from easy_gateway.config import read_config


def test_read_config_valid(tmp_path):
    path = tmp_path / "conf.yaml"
    path.write_text("server:\n  port: 8080\nroutes:\n  - path: /api/*\n")
    config = read_config(str(path))
    assert config["server"]["port"] == 8080
    assert config["routes"] == [{"path": "/api/*"}]


def test_read_config_missing_file(tmp_path):
    assert read_config(str(tmp_path / "missing.yaml")) == {}


def test_read_config_empty_file(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    assert read_config(str(path)) == {}


def test_read_config_comment_only(tmp_path):
    path = tmp_path / "comment.yaml"
    path.write_text("# just a comment\n")
    assert read_config(str(path)) == {}
