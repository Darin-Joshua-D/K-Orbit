from app.database.supabase_client import supabase

def fetch_user_by_email(email: str):
    """Fetch a user by email from the Supabase database."""
    response = supabase.table("users").select("*").eq("email", email).execute()
    if response.error:
        raise Exception(f"Error fetching user: {response.error.message}")
    return response.data