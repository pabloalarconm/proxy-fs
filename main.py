import httpx, uvicorn, os, base64, json, re, asyncio
from fastapi import HTTPException, FastAPI, Request
from rdflib import Graph, URIRef, Literal, Namespace
from urllib.parse import urlparse
from rdflib.namespace import DCTERMS, XSD

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

# ═══════════════════════════════════════════════════════════════════
# Environment configuration
# ═══════════════════════════════════════════════════════════════════

AUTH_URL = os.getenv("AUTH_URL")
DATA_URL = os.getenv("DATA_URL")
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = "OSTrails"
GITHUB_REPO = "assessment-component-metadata-records"
GITHUB_BRANCH = "main"

# FAIRsharing GraphQL settings
FAIRSHARING_GRAPHQL_ENDPOINT = "https://api.fairsharing.org/graphql"
FAIRSHARING_GRAPHQL_KEY = "484de7ca-4496-4ee7-8cbf-578d2923c08f"

DCTERMS = Namespace("http://purl.org/dc/terms/")


# ═══════════════════════════════════════════════════════════════════
# Helper: Extract record_id, category, and uri_candidate
# ═══════════════════════════════════════════════════════════════════
def _extract_record_info(rdf_text: str):
    g = Graph()
    g.parse(data=rdf_text, format="turtle")

    uri_candidate = None
    for _, _, o in g.triples((None, DCTERMS.identifier, None)):
        if isinstance(o, URIRef):
            uri_candidate = str(o)
            break
        elif isinstance(o, Literal) and (o.datatype in (None, XSD.string)):
            uri_candidate = str(o)
            break

    if uri_candidate is None:
        for s in g.subjects():
            if isinstance(s, URIRef):
                uri_candidate = str(s)
                break

    if uri_candidate is None:
        return None

    path_parts = [p for p in urlparse(uri_candidate).path.split("/") if p]
    if len(path_parts) < 2:
        return None

    filename = path_parts[-1]
    category = path_parts[-2]
    record_id = re.sub(r"\.ttl$", "", filename, flags=re.IGNORECASE)

    return record_id, category, uri_candidate


# ═══════════════════════════════════════════════════════════════════
# 1. Commit RDF to GitHub, return commit SHA and info
# ═══════════════════════════════════════════════════════════════════
async def commit_rdf_to_github(client: httpx.AsyncClient, rdf_text: str):
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
        raise HTTPException(500, "GitHub env vars missing")

    info = _extract_record_info(rdf_text)
    if info is None:
        raise HTTPException(400, "Unable to find identifier URI inside RDF.")
    record_id, category, uri_candidate = info

    path = f"{category.rstrip('/')}/{record_id}.ttl"
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

    # Check if file exists
    sha = None
    pre = await client.get(url, headers=headers)
    if pre.status_code == 200:
        sha = pre.json().get("sha")
    elif pre.status_code not in (404,):
        raise HTTPException(500, f"GitHub pre-flight failed: {pre.text}")

    # Create or update file
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

    commit_sha = put.json()["content"]["sha"]
    return record_id, category, uri_candidate, url, commit_sha


# ═══════════════════════════════════════════════════════════════════
# 2. Poll GitHub until new commit is visible -- This step at the end is not neccesary becuase the commit is quite fast but the Github Pages are the one that take time to update. However I keep the function as a sanity check.
# ═══════════════════════════════════════════════════════════════════
async def wait_until_github_updated(client, url, headers, expected_sha, max_wait=10):
    """
    Polls GitHub until the committed file's SHA matches expected_sha.
    Waits up to max_wait seconds total.
    """
    print(f"⏳ Waiting for GitHub to propagate commit {expected_sha[:7]}...")
    
    await asyncio.sleep(50) ## Neccesary! Takes more than 40 secs to update the commit in the Github Page.

    for i in range(max_wait):
        try:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                current_sha = res.json().get("sha")
                if current_sha == expected_sha:
                    print(f"GitHub file updated (SHA {current_sha[:7]})")
                    return True
        except Exception as e:
            print(f"Poll attempt {i+1} failed: {e}")

    print("Timeout waiting for GitHub to propagate new content.")
    return False


# ═══════════════════════════════════════════════════════════════════
# 3. Notify FDP Proxy after Github commit
# ═══════════════════════════════════════════════════════════════════
async def notify_fdp_proxy(client: httpx.AsyncClient, uri_candidate: str):
    proxy_url = "https://tools.ostrails.eu/fdp-index-proxy/proxy"
    proxy_payload = {"clientUrl": uri_candidate}
    proxy_headers = {"content-type": "application/json"}

    try:
        resp = await client.post(proxy_url, json=proxy_payload, headers=proxy_headers, timeout=5)
        resp.raise_for_status()
        print(f"FDP proxy notified successfully for {uri_candidate}")
    except httpx.HTTPError as e:
        print(f"FDP proxy notification failed: {e}")


# ═══════════════════════════════════════════════════════════════════
# 4. FastAPI endpoint
# ═══════════════════════════════════════════════════════════════════
@app.post("/questionnaire/push")
async def githubpush(request: Request):
    rdf_text = await request.body()
    rdf_text = rdf_text.decode("utf-8")

    async with httpx.AsyncClient() as client:
        record_id, category, uri_candidate, url, commit_sha = await commit_rdf_to_github(client, rdf_text)

        if category.lower() == "test":
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            }
            # Wait until GitHub confirms new commit is visible
            await wait_until_github_updated(client, url, headers, commit_sha, max_wait=10)
            # Then notify FDP proxy
            await notify_fdp_proxy(client, uri_candidate)

    return {
        "Submission": "Done",
        "Info": (
            "Your Github submission is located here: https://github.com/OSTrails/assessment-component-metadata-records"
            "if you submitted a test, check your test record here: https://tools.ostrails.eu/fdp-index/"
        ),
    }

# ═══════════════════════════════════════════════════════════════════
# Submit FAIRsharing endpoint
# ═══════════════════════════════════════════════════════════════════
@app.post("/questionnaire/submit")
async def submit_record(body: FairsharingRecordRequest):
    """
    Authenticate with FAIRsharing, replace subject/domain URIs with internal IDs,
    remove missing ones, and clean empty parameters.
    """

    async def fetch_internal_id(client: httpx.AsyncClient, iri: str, type_: str):
        if type_ == "subject":
            query_field = "searchSubjects"
        elif type_ == "domain":
            query_field = "searchDomains"
        else:
            raise ValueError("Unknown type_")

        query = {
            "query": f"""
            query {{
              {query_field}(q: "{iri}") {{
                id
                iri
              }}
            }}
            """
        }

        try:
            resp = await client.post(
                FAIRSHARING_GRAPHQL_ENDPOINT,
                json=query,
                headers={"x-graphql-key": FAIRSHARING_GRAPHQL_KEY},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", {}).get(query_field, [])
            if results and isinstance(results, list) and results[0].get("id"):
                return results[0]["id"]
        except Exception as e:
            print(f"GraphQL query failed for {iri}: {e}")
        return None

    # ─────────────────────────────────────────────────────────────
    # Helper: resolve subject/domain IDs (inside fairsharing_record)
    # ─────────────────────────────────────────────────────────────
    async def resolve_subject_domain_ids(body_dict: dict) -> dict:
        async with httpx.AsyncClient() as client:
            record = body_dict.get("fairsharing_record", {})

            # Resolve subjects
            if "subject_ids" in record and isinstance(record["subject_ids"], list):
                resolved_subjects = []
                for iri in record["subject_ids"]:
                    internal_id = await fetch_internal_id(client, iri, "subject")
                    if internal_id is not None:
                        resolved_subjects.append(internal_id)
                    else:
                        print(f"Removed subject URI without internal ID: {iri}")
                record["subject_ids"] = resolved_subjects

            # Resolve domains
            if "domain_ids" in record and isinstance(record["domain_ids"], list):
                resolved_domains = []
                for iri in record["domain_ids"]:
                    internal_id = await fetch_internal_id(client, iri, "domain")
                    if internal_id is not None:
                        resolved_domains.append(internal_id)
                    else:
                        print(f"Removed domain URI without internal ID: {iri}")
                record["domain_ids"] = resolved_domains

            body_dict["fairsharing_record"] = record
        return body_dict

    def remove_empty(obj):
        if isinstance(obj, dict):
            
            return {
                k: remove_empty(v)
                for k, v in obj.items()
                if v not in (None, "", [], {}) and remove_empty(v) != {}
            }
        elif isinstance(obj, list):
            cleaned = [remove_empty(v) for v in obj if v not in (None, "", [], {})]
            return [v for v in cleaned if v != {}]
        else:
            return obj

    body_dict = body.model_dump(mode="json")
    body_dict = await resolve_subject_domain_ids(body_dict)
    body_dict = remove_empty(body_dict)
    # print(json.dumps(body_dict, indent=2))  # Double-quoted JSON for readability
    
    # ─────────────────────────────────────────────────────────────
    # Authenticate and sent
    # ─────────────────────────────────────────────────────────────
    async with httpx.AsyncClient() as client:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        auth = await client.post(
            AUTH_URL,
            headers=headers,
            json={"user": {"login": USERNAME, "password": PASSWORD}},
            timeout=15.0,
        )
        auth.raise_for_status()
        token = auth.json().get("jwt")
        if not token:
            raise HTTPException(500, "Missing jwt token")

        headers["Authorization"] = f"Bearer {token}"
        data_response = await client.post(DATA_URL, json=body_dict, headers=headers)
        data_response.raise_for_status()

        return {
            "status": "success",
            "data_status_code": data_response.status_code,
            "response": data_response.json(),
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)