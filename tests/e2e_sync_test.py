import os
import sys
from memory_hub.app import create_app
from memory_hub.config import Settings
from fastapi.testclient import TestClient

def run_test():
    app = create_app()
    settings = Settings()
    hub_key = settings.HUB_API_KEY
    agent_key = "cc_career_a7f2k9m3"

    with TestClient(app) as client:
        print("====================================")
        print("1. Checking Health Endpoint")
        print("====================================")
        health_resp = client.get("/api/v1/health")
        print("Status:", health_resp.status_code)
        print("Body:", health_resp.json())
        
        print("\n====================================")
        print("2. Storing a new memory (Local Qdrant)")
        print("====================================")
        payload = {
            "content": "E2E Test Memory: The user loves local-first architecture.",
            "project": "test_project_e2e",
            "agent_id": "career_coach_agent",
            "category": "general",
        }
        add_resp = client.post("/api/v1/memory", json=payload, headers={"X-API-Key": agent_key})
        print("Status:", add_resp.status_code)
        print("Body:", add_resp.json())

        print("\n====================================")
        print("3. Triggering Cloud Sync (Backup)")
        print("====================================")
        sync_resp = client.post("/api/v1/sync", headers={"X-API-Key": hub_key})
        print("Status:", sync_resp.status_code)
        print("Body:", sync_resp.json())

if __name__ == "__main__":
    run_test()
