import io
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from app.db.session import normalize_database_url, get_engine_config
from app.storage.supabase import SupabaseStorageClient
from app.storage.service import StorageService
from app.core.config import Settings


def test_normalize_database_url():
    # Test postgres:// normalization to postgresql+psycopg2://
    raw_postgres = "postgres://postgres:secret@db.xyz.supabase.co:5432/postgres"
    norm = normalize_database_url(raw_postgres)
    assert norm.startswith("postgresql+psycopg2://")

    # Test standard postgresql:// normalization
    raw_postgresql = "postgresql://postgres:secret@db.xyz.supabase.co:5432/postgres"
    norm2 = normalize_database_url(raw_postgresql)
    assert norm2.startswith("postgresql+psycopg2://")

    # Test already qualified postgresql+psycopg2://
    qualified = "postgresql+psycopg2://postgres:secret@db.xyz.supabase.co:5432/postgres"
    assert normalize_database_url(qualified) == qualified

    # Test sqlite unchanged
    sqlite_url = "sqlite:///./querypilot.db"
    assert normalize_database_url(sqlite_url) == sqlite_url

    # Test empty defaults to sqlite
    assert normalize_database_url("") == "sqlite:///./querypilot.db"


def test_get_engine_config_sqlite():
    target_url, connect_args, engine_kwargs = get_engine_config("sqlite:///./test.db")
    assert target_url == "sqlite:///./test.db"
    assert connect_args.get("check_same_thread") is False
    assert "pool_recycle" not in engine_kwargs


def test_get_engine_config_supabase():
    supabase_url = "postgresql://postgres.xyz:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    target_url, connect_args, engine_kwargs = get_engine_config(supabase_url)
    assert target_url.startswith("postgresql+psycopg2://")
    assert connect_args.get("sslmode") == "require"
    assert engine_kwargs.get("pool_recycle") == 300
    assert engine_kwargs.get("pool_pre_ping") is True


def test_supabase_storage_client_bucket_creation():
    client = SupabaseStorageClient(
        supabase_url="https://xyz.supabase.co",
        service_role_key="test-key",
        bucket_name="private-test-bucket",
    )

    mock_resp_404 = MagicMock()
    mock_resp_404.status_code = 404

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200

    with patch("httpx.Client.get", return_value=mock_resp_404), \
         patch("httpx.Client.post", return_value=mock_resp_200) as mock_post:
        success = client.ensure_private_bucket()
        assert success is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["public"] is False
        assert call_kwargs["json"]["id"] == "private-test-bucket"


def test_supabase_storage_client_upload_download_delete():
    client = SupabaseStorageClient(
        supabase_url="https://xyz.supabase.co",
        service_role_key="test-key",
        bucket_name="private-test-bucket",
    )

    client._bucket_checked = True

    # Test upload
    mock_upload_resp = MagicMock()
    mock_upload_resp.status_code = 200
    with patch("httpx.Client.post", return_value=mock_upload_resp) as mock_post:
        result = client.upload_file("uploads/test.csv", b"col1,col2\n1,2")
        assert result is True
        mock_post.assert_called_once()
        assert mock_post.call_args[1]["headers"]["x-upsert"] == "true"

    # Test download
    mock_download_resp = MagicMock()
    mock_download_resp.status_code = 200
    mock_download_resp.content = b"col1,col2\n1,2"
    with patch("httpx.Client.get", return_value=mock_download_resp):
        content = client.download_file("uploads/test.csv")
        assert content == b"col1,col2\n1,2"

    # Test delete
    mock_del_resp = MagicMock()
    mock_del_resp.status_code = 200
    with patch("httpx.Client.request", return_value=mock_del_resp) as mock_req:
        del_result = client.delete_file("uploads/test.csv")
        assert del_result is True
        assert mock_req.call_args[1]["json"] == {"prefixes": ["uploads/test.csv"]}

    # Test signed URL
    mock_sign_resp = MagicMock()
    mock_sign_resp.status_code = 200
    mock_sign_resp.json.return_value = {"signedURL": "/object/sign/private-test-bucket/uploads/test.csv?token=123"}
    with patch("httpx.Client.post", return_value=mock_sign_resp):
        signed_url = client.create_signed_url("uploads/test.csv", expires_in=1800)
        assert signed_url is not None
        assert "token=123" in signed_url


def test_storage_service_cloud_cache_miss_downloads(tmp_path):
    # Set up StorageService configured with mock Supabase client
    service = StorageService(base_dir=str(tmp_path))
    mock_client = MagicMock()
    mock_client.download_file.return_value = b"name,amount\nWidget,100"
    service.supabase_client = mock_client

    assert service.is_cloud_storage is True

    # Request a file that does not exist in local cache
    test_key = "abc123_test.csv"
    resolved_path = service.get_file_path(test_key, folder="uploads")
    
    # Verify it downloaded from Supabase and populated local cache
    assert resolved_path.exists()
    assert resolved_path.read_text(encoding="utf-8") == "name,amount\nWidget,100"
    mock_client.download_file.assert_called_once_with("uploads/abc123_test.csv")


def test_supabase_storage_client_sb_secret_key_format():
    # Test that new sb_secret_... key format (even with accidental quotes or whitespace) is properly handled
    raw_key = '  "sb_secret_samplekey1234567890abcdef" \n'
    client = SupabaseStorageClient(
        supabase_url="https://jftgezmavbtioxhyeysm.supabase.co",
        service_role_key=raw_key,
        bucket_name="querypilot-data",
    )
    assert client.service_role_key == "sb_secret_samplekey1234567890abcdef"
    headers = client.headers
    assert headers["apikey"] == "sb_secret_samplekey1234567890abcdef"
    assert headers["Authorization"] == "Bearer sb_secret_samplekey1234567890abcdef"
