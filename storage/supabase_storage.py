import os
# from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "reports")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def upload_bytes(data, storage_path, content_type="application/octet-stream"):
    if hasattr(data, "getvalue"):
        data = data.getvalue()
    elif hasattr(data, "read"):
        data = data.read()

    if isinstance(data, bytearray):
        data = bytes(data)

    response = supabase.storage.from_(SUPABASE_BUCKET).upload(
        path=storage_path,
        file=data,
        file_options={
            "content-type": content_type,
            "upsert": "true"
        }
    )

    return response


def create_test_run(model_name, base_url, summary=None):
    response = (
        supabase.table("test_runs")
        .insert({
            "model_name": model_name,
            "base_url": base_url,
            "summary": summary or {},
            "created_at": current_timestamp()
        })
        .execute()
    )

    return response.data[0]["id"]


def update_test_run(test_run_id, data):
    supabase.table("test_runs").update(data).eq("id", test_run_id).execute()


def save_file_record(test_run_id, file_type, storage_path):
    supabase.table("test_run_files").insert({
        "test_run_id": test_run_id,
        "file_type": file_type,
        "storage_path": storage_path,
        "created_at": current_timestamp()
    }).execute()