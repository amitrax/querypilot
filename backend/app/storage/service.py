import os
import re
import uuid
import shutil
import logging
from pathlib import Path
from typing import BinaryIO, Optional
from fastapi import HTTPException, status
from app.core.config import settings
from app.storage.supabase import SupabaseStorageClient

logger = logging.getLogger(__name__)


class StorageService:
    """
    Unified storage service supporting both local disk filesystem and
    persistent private Supabase Storage buckets with local transparent caching.
    """

    def __init__(self, base_dir: str = settings.STORAGE_DIR):
        self.base_dir = Path(base_dir).resolve()
        self.uploads_dir = self.base_dir / "uploads"
        self.reports_dir = self.base_dir / "reports"
        self.cache_dir = self.base_dir / "cache"

        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.supabase_client: Optional[SupabaseStorageClient] = None
        if (
            settings.STORAGE_BACKEND.lower() == "supabase"
            or (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)
        ):
            if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
                self.supabase_client = SupabaseStorageClient(
                    supabase_url=settings.SUPABASE_URL,
                    service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                    bucket_name=settings.SUPABASE_STORAGE_BUCKET,
                )
                logger.info(
                    f"Initialized Supabase Private Storage with bucket '{settings.SUPABASE_STORAGE_BUCKET}'"
                )

    @property
    def is_cloud_storage(self) -> bool:
        return self.supabase_client is not None

    def sanitize_filename(self, filename: str) -> str:
        """Sanitizes user filename to prevent path traversal and shell injection."""
        base_name = os.path.basename(filename)
        sanitized = re.sub(r"[^\w\s\.-]", "_", base_name).strip()
        if not sanitized:
            sanitized = "dataset.csv"
        return sanitized

    def save_upload(self, file_obj: BinaryIO, original_filename: str) -> tuple[str, str, int]:
        """
        Saves uploaded file securely to storage (local and private Supabase bucket).
        Returns: (storage_key, relative_or_cached_path, file_size)
        """
        clean_name = self.sanitize_filename(original_filename)
        storage_id = f"{uuid.uuid4().hex}_{clean_name}"
        dest_path = self.uploads_dir / storage_id

        # Write chunks and verify size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        bytes_written = 0
        file_obj.seek(0)

        with open(dest_path, "wb") as buffer:
            while chunk := file_obj.read(1024 * 1024):  # 1MB chunks
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB"
                    )
                buffer.write(chunk)

        # Ensure destination is inside uploads_dir (path traversal safety check)
        if not dest_path.resolve().is_relative_to(self.uploads_dir):
            dest_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path detected."
            )

        # If Supabase Storage is configured, persist to private bucket
        if self.is_cloud_storage and self.supabase_client:
            with open(dest_path, "rb") as f:
                content = f.read()
            uploaded = self.supabase_client.upload_file(
                remote_path=f"uploads/{storage_id}",
                data=content,
                content_type="text/csv",
            )
            if not uploaded:
                logger.warning(
                    f"Failed to persist {storage_id} to Supabase bucket. Retaining local cache copy."
                )

        return storage_id, str(dest_path), bytes_written

    def sync_file(self, storage_key: str, folder: str = "uploads") -> bool:
        """
        Syncs modified local cache file (e.g. after dataframe header normalization)
        back to persistent cloud storage.
        """
        if not self.is_cloud_storage or not self.supabase_client:
            return True

        safe_name = os.path.basename(storage_key)
        target_dir = self.reports_dir if folder == "reports" else self.uploads_dir
        local_path = (target_dir / safe_name).resolve()

        if local_path.exists() and local_path.is_relative_to(target_dir):
            with open(local_path, "rb") as f:
                content = f.read()
            return self.supabase_client.upload_file(
                remote_path=f"{folder}/{safe_name}",
                data=content,
                content_type="text/csv",
            )
        return False

    def get_file_path(self, storage_key: str, folder: str = "uploads") -> Path:
        """
        Resolves file path with path traversal protection.
        If file is missing in local cache and cloud storage is enabled, downloads
        it from Supabase private storage into local cache.
        """
        target_dir = self.reports_dir if folder == "reports" else self.uploads_dir
        safe_name = os.path.basename(storage_key)
        resolved = (target_dir / safe_name).resolve()

        if not resolved.is_relative_to(target_dir):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to path forbidden."
            )

        # If file exists in local cache, return it immediately
        if resolved.exists():
            return resolved

        # If missing on disk, try fetching from Supabase private bucket
        if self.is_cloud_storage and self.supabase_client:
            remote_path = f"{folder}/{safe_name}"
            content = self.supabase_client.download_file(remote_path)
            if content is not None:
                with open(resolved, "wb") as f:
                    f.write(content)
                return resolved

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested file does not exist on disk or in remote storage."
        )

    def delete_file(self, storage_key: str, folder: str = "uploads") -> bool:
        """Deletes file from both remote private storage and local disk/cache."""
        safe_name = os.path.basename(storage_key)
        target_dir = self.reports_dir if folder == "reports" else self.uploads_dir
        local_path = (target_dir / safe_name).resolve()

        deleted_remote = True
        if self.is_cloud_storage and self.supabase_client:
            deleted_remote = self.supabase_client.delete_file(f"{folder}/{safe_name}")

        deleted_local = False
        if local_path.exists() and local_path.is_relative_to(target_dir):
            try:
                local_path.unlink()
                deleted_local = True
            except Exception as e:
                logger.error(f"Failed to remove local file {local_path}: {e}")

        return deleted_remote or deleted_local

    def save_report_content(self, filename: str, content: str) -> tuple[str, str]:
        """Saves generated report content to reports folder and private bucket."""
        clean_name = self.sanitize_filename(filename)
        storage_id = f"{uuid.uuid4().hex}_{clean_name}"
        dest_path = self.reports_dir / storage_id

        # Ensure safe path
        if not dest_path.resolve().is_relative_to(self.reports_dir):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid report path."
            )

        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Upload to Supabase if enabled
        if self.is_cloud_storage and self.supabase_client:
            self.supabase_client.upload_file(
                remote_path=f"reports/{storage_id}",
                data=content.encode("utf-8"),
                content_type="text/csv",
            )

        return storage_id, str(dest_path)

    def create_signed_url(self, storage_key: str, folder: str = "uploads", expires_in: int = 3600) -> Optional[str]:
        """Creates a temporary signed download URL for private cloud storage."""
        if self.is_cloud_storage and self.supabase_client:
            safe_name = os.path.basename(storage_key)
            return self.supabase_client.create_signed_url(f"{folder}/{safe_name}", expires_in=expires_in)
        return None


storage_service = StorageService()
