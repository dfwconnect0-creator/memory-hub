from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
import cognee
import os
import uvicorn
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cognee-mcp-server")

app = FastAPI(title="Cognee Memory API Server")

# Simple API Key Authentication
API_KEYS = {"oc_sk_xxx", "ag_sk_xxx", "lc_sk_xxx"}


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key not in API_KEYS:
        logger.warning(f"Unauthorized access attempt with key: {x_api_key}")
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return x_api_key


class MemoryRequest(BaseModel):
    agent_id: str
    framework: str
    project: str
    content: str


class SearchRequest(BaseModel):
    agent_id: str
    query: str
    project: str


@app.on_event("startup")
async def startup_event():
    logger.info("Cognee Memory Server started.")


@app.post("/api/v1/memory", dependencies=[Depends(verify_api_key)])
async def add_memory(req: MemoryRequest):
    try:
        # Structured add to cognee
        await cognee.add(req.content)
        logger.info(f"Memory added by {req.agent_id} in project {req.project}")
        return {"status": "success", "agent": req.agent_id}
    except Exception as e:
        logger.error(f"Failed to add memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/memory/cognify", dependencies=[Depends(verify_api_key)])
async def run_cognify():
    try:
        await cognee.cognify()
        logger.info("Cognification triggered")
        return {"status": "success", "message": "Cognify completed"}
    except Exception as e:
        logger.error(f"Failed to cognify: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/memory/search", dependencies=[Depends(verify_api_key)])
async def search_memory(req: SearchRequest):
    try:
        results = await cognee.search(req.query)
        logger.info(f"Search query from {req.agent_id}: {req.query}")
        return {"results": results}
    except Exception as e:
        logger.error(f"Failed to search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
