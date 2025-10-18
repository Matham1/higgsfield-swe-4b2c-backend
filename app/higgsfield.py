import httpx
from .config import HIGGSFIELD_API_BASE, HIGGSFIELD_API_KEY

async def call_higgsfield_generate(input_url: str, params: dict):
    """
    Simple async httpx example. Replace with real Higgsfield API calls.
    Returns: dict with {'status':'done','result_url': 'https://...'}
    """
    # This is a stub showing how you might call the remote API synchronously/asynchronously.
    headers = {"Authorization": f"Bearer {HIGGSFIELD_API_KEY}"} if HIGGSFIELD_API_KEY else {}
    async with httpx.AsyncClient(timeout=120) as client:
        # Example endpoint — replace with the real one from Higgsfield docs
        resp = await client.post(f"{HIGGSFIELD_API_BASE}/v1/generate", json={"input": input_url, "params": params}, headers=headers)
        resp.raise_for_status()
        return resp.json()
