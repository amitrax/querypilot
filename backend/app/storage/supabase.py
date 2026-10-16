import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


class SupabaseStorageClient:
    """
    Direct HTTP client for Supabase Storage API using the private Service Role Key.
    Guarantees private bucket isolation and secure uploads/downloads/signed URLs.
    """

    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        bucket_name: str = "querypilot-data",
        timeout: float = 30.0,
    ):
        self.supabase_url = supabase_url.rstrip("/") if supabase_url else ""
        self.service_role_key = (service_role_key or "").strip().strip("'\"")
        self.bucket_name = bucket_name
        self.timeout = timeout
        self.base_url = f"{self.supabase_url}/storage/v1" if self.supabase_url else ""
        self._bucket_checked = False

    @property
    def headers(self) -> dict:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }

    def ensure_private_bucket(self) -> bool:
        """
        Verifies that the private storage bucket exists in Supabase.
        If it does not exist, creates it with public=False (strict private access).
        """
        if self._bucket_checked:
            return True

        if not self.supabase_url or not self.service_role_key:
            return False

        try:
            with httpx.Client(timeout=self.timeout) as client:
                # 1. Check existing bucket
                resp = client.get(
                    f"{self.base_url}/bucket/{self.bucket_name}",
                    headers=self.headers,
                )
                if resp.status_code == 200:
                    self._bucket_checked = True
                    return True

                if resp.status_code == 404:
                    # 2. Create private bucket
                    create_resp = client.post(
                        f"{self.base_url}/bucket",
                        headers=self.headers,
                        json={
                            "id": self.bucket_name,
                            "name": self.bucket_name,
                            "public": False,
                            "file_size_limit": 50 * 1024 * 1024,
                        },
                    )
                    if create_resp.status_code in (200, 201):
                        logger.info(f"Created private Supabase bucket '{self.bucket_name}'.")
                        self._bucket_checked = True
                        return True
                    else:
                        logger.warning(
                            f"Failed to create Supabase bucket {self.bucket_name}: {create_resp.status_code} - {create_resp.text}"
                        )
                        return False
        except Exception as e:
            logger.error(f"Error checking/creating Supabase bucket '{self.bucket_name}': {e}")
            return False

        return False

    def upload_file(
        self,
        remote_path: str,
        data: bytes,
        content_type: str = "text/csv",
    ) -> bool:
        """
        Uploads or upserts an object into the private Supabase bucket.
        """
        self.ensure_private_bucket()
        clean_path = remote_path.lstrip("/")
        url = f"{self.base_url}/object/{self.bucket_name}/{clean_path}"

        headers = self.headers.copy()
        headers["Content-Type"] = content_type
        headers["x-upsert"] = "true"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, content=data)
                if resp.status_code in (200, 201):
                    return True
                logger.error(
                    f"Supabase upload failed for {clean_path}: {resp.status_code} {resp.text}"
                )
                return False
        except Exception as e:
            logger.error(f"Exception during Supabase upload for {clean_path}: {e}")
            return False

    def download_file(self, remote_path: str) -> Optional[bytes]:
        """
        Downloads a private object directly from Supabase Storage using authenticated endpoint.
        """
        self.ensure_private_bucket()
        clean_path = remote_path.lstrip("/")

        url = f"{self.base_url}/object/authenticated/{self.bucket_name}/{clean_path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    return resp.content
                
                # Fallback to standard object path with auth header
                fallback_url = f"{self.base_url}/object/{self.bucket_name}/{clean_path}"
                resp2 = client.get(fallback_url, headers=self.headers)
                if resp2.status_code == 200:
                    return resp2.content

                logger.error(
                    f"Supabase download failed for {clean_path}: {resp.status_code} {resp.text}"
                )
                return None
        except Exception as e:
            logger.error(f"Exception during Supabase download for {clean_path}: {e}")
            return None

    def delete_file(self, remote_path: str) -> bool:
        """
        Deletes an object from the private Supabase bucket.
        """
        clean_path = remote_path.lstrip("/")
        url = f"{self.base_url}/object/{self.bucket_name}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.request(
                    "DELETE",
                    url,
                    headers=self.headers,
                    json={"prefixes": [clean_path]},
                )
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Exception during Supabase delete for {clean_path}: {e}")
            return False

    def create_signed_url(self, remote_path: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generates a secure time-limited signed URL for private bucket downloads.
        """
        clean_path = remote_path.lstrip("/")
        url = f"{self.base_url}/object/sign/{self.bucket_name}/{clean_path}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    url,
                    headers=self.headers,
                    json={"expiresIn": expires_in},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    signed_subpath = data.get("signedURL")
                    if signed_subpath:
                        if signed_subpath.startswith("http"):
                            return signed_subpath
                        return f"{self.base_url}{signed_subpath}"
                return None
        except Exception as e:
            logger.error(f"Failed to generate signed URL for {clean_path}: {e}")
            return None
