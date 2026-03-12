import sqlite3

from smap_service.db.provider_credentials import SQLiteProviderCredentialStore


def test_provider_credentials_round_trip_encrypted(tmp_path) -> None:
    db_path = tmp_path / "runtime.sqlite3"
    key_path = tmp_path / "credentials.key"
    store = SQLiteProviderCredentialStore(db_path=db_path, key_path=key_path)

    store.save_selection(
        provider="upstox",
        credentials={"api_key": "abc123", "api_secret": "secret456"},
    )
    selection = store.get_selection()
    assert selection.provider == "upstox"
    assert selection.has_credentials is True

    creds = store.get_credentials("upstox")
    assert creds is not None
    assert creds["api_key"] == "abc123"
    assert creds["api_secret"] == "secret456"

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT credential_blob FROM provider_credentials WHERE provider = ?",
            ("upstox",),
        ).fetchone()
    assert row is not None
    assert "abc123" not in row[0]
    assert "secret456" not in row[0]
