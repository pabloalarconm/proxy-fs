from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import httpx
import uvicorn
import os

from fsBaseModel import InputBody, FairsharingRecordRequest

app = FastAPI()

# Configuration
# AUTH_URL = "https://dev-api.fairsharing.org/users/sign_in"
# DATA_URL = "https://dev-api.fairsharing.org/fairsharing_records/"
# USERNAME = ""
# PASSWORD = ""

AUTH_URL = os.getenv("AUTH_URL")
DATA_URL =os.getenv("DATA_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD =os.getenv("PASSWORD")

@app.post("/submit")
async def submit_record(body:FairsharingRecordRequest):

    # Step 1: Get JWT
    async with httpx.AsyncClient() as client:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        try:
            auth_response = await client.post(
                AUTH_URL,
                headers=headers,
                json={"user": {"login": USERNAME, "password": PASSWORD}}
            )
            auth_response.raise_for_status()
            token = auth_response.json().get("jwt")
            if not token:
                raise HTTPException(status_code=500, detail="No jwt token in auth response")
            # print(token)
            # return {"jwt": token}
        except httpx.HTTPError as e:
            print(f"Auth request failed: {e}")
            raise HTTPException(status_code=500, detail=f"Auth request failed: {str(e)}")

        # Step 2: Send data with JWT token
        headers_with_jwt = headers.copy()
        headers_with_jwt["Authorization"] = f"Bearer {token}"
        try:
            data_response = await client.post(DATA_URL, json=body.model_dump(), headers=headers_with_jwt)
            data_response.raise_for_status()
            return {
                "status": "success",
                "data_status_code": data_response.status_code,
                "response": data_response.json()
            }
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Data submission failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)