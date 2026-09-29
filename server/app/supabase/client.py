from app.core.config import settings
from app.core.exceptions import AionError

from supabase import Client, create_client


class SupabaseConfigurationError(AionError):
    error_code = "SUPABASE_CONFIGURATION_ERROR"


class SupabaseClient:
    _client: Client | None = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._client is None:
            if not settings.supabase_url or not settings.supabase_service_role_key:
                raise SupabaseConfigurationError("Supabase URL and service role key are required.")
            cls._client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key,
            )
        return cls._client


supabase: Client | None = None
