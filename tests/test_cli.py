import importlib

from bilanco.cli import main


def test_import_never_collects_financial_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import bilanco

    importlib.reload(bilanco)
    assert not list(tmp_path.iterdir())


def test_unsupported_date_stops_before_database_or_network(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["analyze", "--company", "enron", "--as-of", "1999-04-05"]) == 2
    assert "yalnız" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_missing_contact_stops_before_collection(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BILANCO_SEC_CONTACT", raising=False)
    assert main(["analyze", "--company", "enron", "--as-of", "2000-03-31"]) == 2
    assert "BILANCO_SEC_CONTACT" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())
