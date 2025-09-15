import httpx, uvicorn, os, base64
import uvicorn
import os, base64, httpx
from fastapi import HTTPException , FastAPI, Request
from rdflib import Graph, URIRef, Literal, Namespace
from urllib.parse import urlparse
from rdflib.namespace import DCTERMS, XSD
import re

from fsBaseModel import FairsharingRecordRequest

app = FastAPI(
    docs_url="/questionnaire/docs",
    redoc_url=None,
    openapi_url="/questionnaire/openapi.json",
)

@app.get("/questionnaire/")
async def health_check():
    return {
        "status": "ok",
        "message": "API is running, check /questionnaire/docs for extra documentation",
    }

# ------------------------  GitHub settings  ------------------------

# Configuration
# AUTH_URL = "https://dev-api.fairsharing.org/users/sign_in"
# DATA_URL = "https://dev-api.fairsharing.org/fairsharing_records/"
# USERNAME = ""
# PASSWORD = ""
# GITHUB_TOKEN  = ""

AUTH_URL = os.getenv("AUTH_URL")
DATA_URL =os.getenv("DATA_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD =os.getenv("PASSWORD")
GITHUB_TOKEN =os.getenv("GITHUB_TOKEN")

GITHUB_OWNER  = "OSTrails"
GITHUB_REPO   = "assessment-component-metadata-records"
GITHUB_BRANCH = "main"

# ═══════════════════════════════════════════════════════════════════
# 1. Extract information from the Turtle
# ═══════════════════════════════════════════════════════════════════
DCTERMS = Namespace("http://purl.org/dc/terms/")


# ═══════════════════════════════════════════════════════════════════
# 1. Extract the information from the RDF sample
# ═══════════════════════════════════════════════════════════════════
def _extract_record_info(rdf_text: str) -> tuple[str, str] | None:
    """
    From RDF text, extract (record_id, category) by:
      - Looking at the subject or dcterms:identifier (URIRef or string literal),
      - Parsing the last two parts of the URI path.

    Example:
      URI: .../metric/Filename_678.ttl → ('Filename_678', 'metric')
    """
    g = Graph()
    g.parse(data=rdf_text, format="turtle")

    uri_candidate = None

    # First try: dcterms:identifier
    for _, _, o in g.triples((None, DCTERMS.identifier, None)):
        if isinstance(o, URIRef):
            uri_candidate = str(o)
            break
        elif isinstance(o, Literal):
            # Accept string literal if it looks like a URI
            if o.datatype in (None, XSD.string):
                uri_candidate = str(o)
                break

    # Fallback: first subject URI
    if uri_candidate is None:
        for s in g.subjects():
            if isinstance(s, URIRef):
                uri_candidate = str(s)
                break

    if uri_candidate is None:
        return None  # no usable URI found

    # Parse last two segments of the URI path
    path_parts = [part for part in urlparse(uri_candidate).path.split("/") if part]
    if len(path_parts) < 2:
        return None

    filename = path_parts[-1]
    category = path_parts[-2]
    record_id = re.sub(r"\.ttl$", "", filename, flags=re.IGNORECASE)

    return record_id, category


# ═══════════════════════════════════════════════════════════════════
# 2. Commit to GitHub, with category as sub‑directory
# ═══════════════════════════════════════════════════════════════════
async def commit_rdf_to_github(
    client: httpx.AsyncClient,
    rdf_text: str,
) -> dict:
    """
    Commits `rdf_text` into …/<category>/<record_id>.ttl.
    Category and record_id are extracted from the RDF itself.
    """
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
        raise HTTPException(
            500, "GitHub env vars (GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO) not set"
        )

    info = _extract_record_info(rdf_text)
    if info is None:
        raise HTTPException(400, "Unable to find identifier URI inside RDF.")
    record_id, category = info

    # Build target path: /{category}/title.ttl
    path = f"{category.rstrip('/')}/{record_id}.ttl"
    url  = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    # ── Is it a new file or update? ─────────────────────────────────
    sha = None
    pre = await client.get(url, headers=headers)
    if pre.status_code == 200:
        sha = pre.json().get("sha")
    elif pre.status_code not in (404,):
        raise HTTPException(500, f"GitHub pre‑flight failed: {pre.text}")

    # ── PUT the blob ───────────────────────────────────────────────
    payload = {
        "message": f"Add/update RDF for record {record_id}",
        "content": base64.b64encode(rdf_text.encode()).decode(),
        "branch": GITHUB_BRANCH,
        **({"sha": sha} if sha else {}),
    }

    put = await client.put(url, headers=headers, json=payload)
    try:
        put.raise_for_status()
    except httpx.HTTPError:
        raise HTTPException(500, f"GitHub commit failed: {put.text}")

    return {"Submission":"Done",
            "Info":"Please check https://github.com/OSTrails/assessment-component-metadata-records if your record is included at this Github repo, it might take a few seconds."}


@app.post("/questionnaire/push")
async def githubpush(request: Request):
    rdf_text = await request.body()
    rdf_text = rdf_text.decode("utf-8")  # Convert bytes to string
    async with httpx.AsyncClient() as client:
        gh_json = await commit_rdf_to_github(client, rdf_text)
    return gh_json


@app.post("/questionnaire/submit")
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