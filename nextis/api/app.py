"""Manus API — thin FastAPI layer for the Nextis Assembler.

All business logic lives in the nextis package. This module only wires
routes, middleware, and the application lifecycle.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nextis.api.routes import analytics, assembly, execution

logger = logging.getLogger(__name__)

app = FastAPI(title="Manus API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assembly.router, prefix="/assemblies", tags=["assemblies"])
app.include_router(execution.router, prefix="/execution", tags=["execution"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
