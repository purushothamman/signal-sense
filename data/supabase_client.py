"""
data/supabase_client.py
Centralized Supabase client singleton.
All modules use get_client() instead of sqlite3.connect().
"""

from supabase import create_client, Client
from utils.config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None


def get_client() -> Client:
    """Return a shared Supabase client instance (singleton)."""
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env or environment variables. "
                "Create a free project at https://supabase.com and copy your credentials."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
