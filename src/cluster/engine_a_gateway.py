"""Engine A — Monetized REST API Gateway (FastAPI with RapidAPI & Direct Key Auth)."""
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Header, Query, status
from pydantic import BaseModel
from src.cluster.config import config
from src.cluster.storage import Database

app = FastAPI(
    title="Autonomous B2B Intelligence & Opportunities API",
    description="Monetized 24/7 Data Utility API providing verified public procurement, tech RFPs, and market compliance signals.",
    version="1.0.0"
)

# Shared DB instance
db = Database(config.db_path)

# Ensure master key is active at startup
db.register_api_key(
    key=config.master_api_key,
    client_name="Owner Master Key",
    tier="enterprise",
    monthly_quota=1000000
)

# Demo client key for testing
db.register_api_key(
    key="demo_tier_client_key_2026",
    client_name="RapidAPI / Demo Client",
    tier="pro",
    monthly_quota=10000
)

# Dependency for API Key Validation
async def verify_api_access(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_rapidapi_proxy_secret: Optional[str] = Header(None, alias="X-RapidAPI-Proxy-Secret"),
    x_rapidapi_user: Optional[str] = Header(None, alias="X-RapidAPI-User"),
    x_rapidapi_subscription: Optional[str] = Header(None, alias="X-RapidAPI-Subscription"),
    api_key: Optional[str] = Query(None)
) -> Dict[str, Any]:
    # 1. RapidAPI Marketplace integration check
    if x_rapidapi_user or x_rapidapi_subscription or (config.rapidapi_proxy_secret and x_rapidapi_proxy_secret == config.rapidapi_proxy_secret):
        client_name = x_rapidapi_user or "RapidAPI Subscriber"
        return {"client_name": f"RapidAPI ({client_name})", "tier": "rapidapi_pro"}

    # 2. Direct Header or Query Param Key check
    key = x_api_key or api_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required API key. Provide via header 'X-API-Key' or '?api_key='."
        )

    client = db.validate_api_key(key)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or deactivated API key."
        )
    return client

class OpportunityResponse(BaseModel):
    id: str
    title: str
    source: str
    category: str
    budget_eur: Optional[float]
    deadline: Optional[str]
    tags: List[str]
    created_at: str

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "system": "Autonomous Income Cluster", "mode": "simulation" if config.simulation_mode else "live"}

@app.get("/api/v1/metrics", tags=["Financials & Metrics"])
def get_metrics():
    """Returns cluster wide financial statistics, revenue counters and stored items."""
    stats = db.get_all_time_stats()
    return {
        "status": "active",
        "simulation_mode": config.simulation_mode,
        "financial_summary": stats
    }

@app.get("/api/v1/opportunities", response_model=List[OpportunityResponse], tags=["B2B Opportunities"])
def list_opportunities(
    category: Optional[str] = Query(None, description="Filter by category (e.g. cloud, security, software)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    client: Dict[str, Any] = Depends(verify_api_access)
):
    """
    Returns curated, real-time B2B tech opportunities and tender alerts.
    Consumes quota and credits financial ledger ($0.02 per query).
    """
    # Revenue attribution: 0.02 USD value per monetized API request
    revenue_usd = 0.02
    db.record_api_request(
        key=client.get("key", "rapidapi"),
        endpoint="/api/v1/opportunities",
        status_code=200,
        revenue_usd=revenue_usd
    )

    results = db.get_opportunities(limit=limit, offset=offset, category=category)
    return results

@app.post("/api/v1/keys/generate", tags=["Admin"])
def generate_client_key(
    client_name: str,
    tier: str = "standard",
    master_key: str = Header(..., alias="X-Master-Key")
):
    """Admin endpoint to provision a new monetized API key."""
    if master_key != config.master_api_key:
        raise HTTPException(status_code=403, detail="Invalid master key")
    
    import secrets
    new_key = f"ak_{secrets.token_hex(16)}"
    db.register_api_key(key=new_key, client_name=client_name, tier=tier)
    return {"key": new_key, "client_name": client_name, "tier": tier}
