"""API routes."""

from fastapi import APIRouter

from .agents import router as agents_router
from .alerts import router as alerts_router
from .health import router as health_router
from .metrics import router as metrics_router
from .traces import router as traces_router
from .nl_query import router as nl_query_router
from .auth_sso import router as auth_sso_router
from .remediation import router as remediation_router
from .integrations import router as integrations_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["Health"])
api_router.include_router(traces_router, prefix="/traces", tags=["Traces"])
api_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(metrics_router, prefix="/metrics", tags=["Metrics"])
api_router.include_router(nl_query_router, prefix="/nlq", tags=["Natural Language Query"])
api_router.include_router(auth_sso_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(remediation_router, prefix="/remediation", tags=["Remediation"])
api_router.include_router(integrations_router, prefix="/integrations", tags=["Integrations"])

__all__ = ["api_router"]
