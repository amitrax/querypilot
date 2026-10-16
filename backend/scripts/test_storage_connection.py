import os
import sys
import httpx

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings


def run_storage_test():
    print("=" * 60)
    print("QueryPilot - Supabase Storage Connectivity & Privacy Check")
    print("=" * 60)
    print(f"Configured Storage Backend: {settings.STORAGE_BACKEND}")
    print(f"Configured Supabase URL:    {settings.SUPABASE_URL if settings.SUPABASE_URL else '[EMPTY]'}")
    print(f"Configured Bucket Name:     {settings.SUPABASE_STORAGE_BUCKET}")
    
    raw_key = (settings.SUPABASE_SERVICE_ROLE_KEY or "").strip().strip("'\"")
    has_key = bool(raw_key)
    key_preview = f"Configured ({len(raw_key)} characters, [MASKED])" if has_key else "[NOT SET / EMPTY]"
    print(f"Service Role Secret Key:    {key_preview}")
    print("-" * 60)

    if not settings.SUPABASE_URL:
        print("[ERROR] SUPABASE_URL is not set.")
        return 1

    if not has_key:
        print("[INFO] SUPABASE_SERVICE_ROLE_KEY is not yet populated or saved in backend/.env.")
        print("[INFO] If you have pasted the key in your editor, please save the file (Ctrl+S).")
        return 0

    base_url = settings.SUPABASE_URL.rstrip("/") + "/storage/v1"
    headers = {
        "apikey": raw_key,
        "Authorization": f"Bearer {raw_key}",
    }

    bucket_name = settings.SUPABASE_STORAGE_BUCKET

    print(f"Testing non-destructive read-only bucket status for '{bucket_name}'...")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(f"{base_url}/bucket/{bucket_name}", headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                is_public = data.get("public", False)
                print(f"[SUCCESS] Connected to Supabase Storage API successfully!")
                print(f"Bucket '{bucket_name}' exists.")
                print(f"Privacy Setting: {'PUBLIC (WARNING!)' if is_public else 'PRIVATE (SECURE - public=False)'}")
                
                if is_public:
                    print("[WARNING] The bucket is currently PUBLIC. It should be set to PRIVATE to protect user datasets.")
                else:
                    print("[OK] Bucket is properly configured as PRIVATE. Only authenticated server requests can access datasets.")
                return 0
                
            elif resp.status_code == 404:
                print(f"[INFO] Connected to Supabase Storage API, but bucket '{bucket_name}' does not exist yet.")
                print(f"[INFO] The QueryPilot backend will automatically create it as a PRIVATE bucket (public=False) on first file upload, or you can create it in the Supabase Dashboard.")
                return 0
                
            elif resp.status_code == 401 or resp.status_code == 403:
                print(f"[ERROR] Authentication failed (HTTP {resp.status_code}). Please verify the SUPABASE_SERVICE_ROLE_KEY in backend/.env.")
                return 1
            else:
                print(f"[ERROR] Unexpected response from Supabase Storage: HTTP {resp.status_code} - {resp.text}")
                return 1
                
    except Exception as e:
        print(f"[ERROR] Connection to Supabase Storage failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_storage_test())
