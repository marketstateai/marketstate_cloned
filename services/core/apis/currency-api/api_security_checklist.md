FASTAPI API BUILD + SECURITY TODO CHECKLIST
===========================================

How to use this file:
- Mark each item as done: [x]
- Leave pending items as: [ ]
- Keep evidence links next to each completed task (PR, config file, test case, dashboard)


0) Scope and Requirements
-------------------------
[ ] Define API purpose, consumers, and trust boundaries
[ ] List resources and actions (read, write, delete, admin)
[ ] Define user roles and permissions matrix (who can do what)
[ ] Decide deployment model (single service vs microservices)
[ ] Capture compliance/security requirements (PII, GDPR, SOC2, etc.)
[ ] Create initial threat model before coding starts


1) Project Bootstrap (Python + FastAPI)
---------------------------------------
[ ] Create project folder and Python virtual environment
[ ] Pin Python version (e.g., 3.12+)
[ ] Install base dependencies:
    - fastapi
    - uvicorn[standard]
    - pydantic / pydantic-settings
    - sqlalchemy + alembic (if DB-backed)
    - python-jose or authlib (token handling)
    - passlib[bcrypt] (if password auth is needed)
    - httpx + pytest + pytest-asyncio
[ ] Add dependency management file (requirements.txt or pyproject.toml)
[ ] Create source layout:
    - app/main.py
    - app/api/v1/
    - app/core/
    - app/models/
    - app/schemas/
    - app/services/
    - tests/
[ ] Add `.env.example` with non-secret placeholders only
[ ] Add `.gitignore` for venv, secrets, cache, and build artifacts


2) Core App Foundation
----------------------
[ ] Initialize FastAPI app instance in `app/main.py`
[ ] Add health and readiness endpoints (`/health`, `/ready`)
[ ] Configure CORS explicitly (only approved origins/methods/headers)
[ ] Add request/response logging middleware with request ID
[ ] Add global config loader (environment-specific settings)
[ ] Add structured logging format for production use


3) Use HTTPS Everywhere (from image: "Use HTTPS")
-------------------------------------------------
[ ] Terminate TLS at trusted edge (load balancer, ingress, or gateway)
[ ] Redirect HTTP to HTTPS
[ ] Enforce HSTS in production
[ ] Disable weak TLS versions/ciphers at edge
[ ] Ensure cookies/tokens are only sent over secure channels
[ ] Verify internal service-to-service encryption where required


4) Authentication Strategy
--------------------------
[ ] Choose primary auth mechanism:
    - OAuth2/OIDC (recommended for user auth)
    - Leveled API keys (for service clients)
    - WebAuthn (for high-assurance authentication flows)
[ ] Document which client types use which auth method
[ ] Centralize token/key validation logic in dependencies/middleware
[ ] Reject requests with missing/invalid credentials by default


5) OAuth2 / OIDC (from image: "Use OAuth2")
-------------------------------------------
[ ] Select OAuth2 flow (Authorization Code + PKCE for user-facing apps)
[ ] Integrate trusted authorization server / IdP
[ ] Validate JWT signature, issuer, audience, expiry, not-before
[ ] Enforce scopes/claims per route
[ ] Handle key rotation (JWKS refresh/caching)
[ ] Implement refresh-token handling policy (if applicable)


6) WebAuthn (from image: "Use WebAuthn")
----------------------------------------
[ ] Decide if WebAuthn is required (MFA, sensitive operations, admin paths)
[ ] Implement registration and authentication ceremonies
[ ] Store public-key credentials securely
[ ] Verify challenge, origin, RP ID, and signature
[ ] Bind WebAuthn to user/session risk policies


7) Leveled API Keys (from image: "Use Leveled API Keys")
--------------------------------------------------------
[ ] Issue unique keys per client/environment
[ ] Assign key scopes/tiers (read-only, write, admin, internal)
[ ] Store only hashed API keys at rest
[ ] Support key rotation and revocation
[ ] Optionally require HMAC request signatures for high-risk endpoints
[ ] Track key usage and anomaly signals (spikes, geo anomalies, failures)


8) Authorization (from image: "Authorization")
----------------------------------------------
[ ] Enforce least privilege (deny by default)
[ ] Implement RBAC/ABAC policy checks in route dependencies
[ ] Separate read vs modify permissions explicitly
[ ] Protect object-level access (users only access permitted records)
[ ] Protect function-level access (admin actions locked down)
[ ] Add tests for forbidden paths (403) and hidden resources (404 where appropriate)


9) Input Validation (from image: "Input Validation")
----------------------------------------------------
[ ] Define request/response schemas with Pydantic models
[ ] Use strict field constraints (length, regex, numeric bounds, enums)
[ ] Validate headers/query/path/body consistently
[ ] Reject unexpected fields where feasible
[ ] Validate file uploads (type, size, malware scan policy)
[ ] Normalize and sanitize user-controlled input before use


10) Error Handling (from image: "Error Handling")
-------------------------------------------------
[ ] Add centralized exception handlers
[ ] Return consistent error schema (code, message, correlation ID)
[ ] Use correct HTTP status codes for each failure type
[ ] Never expose internal stack traces or sensitive internals
[ ] Keep client-facing messages clear and actionable
[ ] Log full internal details server-side only


11) Rate Limiting (from image: "Rate Limiting")
-----------------------------------------------
[ ] Define limits by IP, user, API key, and endpoint/action group
[ ] Apply stricter limits to auth and expensive endpoints
[ ] Return `429 Too Many Requests` with retry guidance
[ ] Emit rate-limit headers where appropriate
[ ] Add burst + sustained limits
[ ] Add distributed backing store (e.g., Redis) for multi-instance deployments


12) API Versioning (from image: "API Versioning")
-------------------------------------------------
[ ] Use explicit versioned paths (e.g., `/v1/...`)
[ ] Never ship unversioned production endpoints
[ ] Define deprecation and sunset policy per version
[ ] Publish migration notes before breaking changes
[ ] Keep backward compatibility window documented


13) Allowlisting (from image: "Allowlisting")
---------------------------------------------
[ ] Identify endpoints needing network-level restrictions
[ ] Apply IP allowlists for admin/internal routes
[ ] Restrict management endpoints to private networks/VPN
[ ] Maintain and audit allowlist change process
[ ] Test deny behavior for non-allowlisted sources


14) API Gateway / Edge Controls (from image: "Use API Gateway")
---------------------------------------------------------------
[ ] Choose and configure API gateway / ingress layer
[ ] Centralize auth enforcement where possible
[ ] Enforce rate limits and request size limits at edge
[ ] Add WAF/bot protection rules as needed
[ ] Forward trace/request IDs to downstream services
[ ] Configure standardized timeout and retry behavior


15) OWASP API Security Risks (from image: "Check OWASP API Security Risks")
---------------------------------------------------------------------------
[ ] Review OWASP API Security Top 10 and map controls to each risk
[ ] Add explicit checks for:
    - Broken object level authorization (BOLA)
    - Broken authentication
    - Broken object property level authorization
    - Unrestricted resource consumption
    - Broken function level authorization
    - Unrestricted access to sensitive business flows
    - Server side request forgery (SSRF)
    - Security misconfiguration
    - Improper inventory management
    - Unsafe consumption of APIs
[ ] Track uncovered risks and remediation owners


16) Data and Secrets Protection
-------------------------------
[ ] Store secrets in secret manager (not source control)
[ ] Encrypt sensitive data at rest
[ ] Minimize sensitive data in logs and error payloads
[ ] Apply data retention and deletion policies
[ ] Rotate secrets/keys/certs on a fixed schedule


17) Testing and Verification
----------------------------
[ ] Unit test route logic, schema validation, and service layer
[ ] Integration test auth, authz, and data access boundaries
[ ] Add negative tests for unauthorized and malformed requests
[ ] Add rate-limit and abuse scenario tests
[ ] Run SAST, dependency, and container vulnerability scans
[ ] Run DAST/security probes against staging


18) Observability and Incident Readiness
----------------------------------------
[ ] Emit metrics: latency, throughput, error rate, auth failures
[ ] Create alerts for suspicious patterns and SLA violations
[ ] Keep immutable audit logs for sensitive actions
[ ] Define incident response runbook (triage, containment, recovery)
[ ] Perform tabletop exercise for API abuse scenarios


19) Deployment and Operations
-----------------------------
[ ] Build reproducible artifact (container/image) with pinned deps
[ ] Apply least-privilege runtime permissions
[ ] Use zero-downtime rollout strategy (blue/green or canary)
[ ] Run DB migrations safely with rollback plan
[ ] Validate production config before release
[ ] Perform post-deploy smoke and security checks


20) Done Criteria (Release Gate)
--------------------------------
[ ] All mandatory checklist items completed or risk-accepted in writing
[ ] All critical/high vulnerabilities resolved
[ ] Security tests passing in CI/CD
[ ] API docs published (OpenAPI + auth/version guidance)
[ ] On-call ownership and monitoring confirmed
[ ] Version `v1` release approved


21) Specific Step-by-Step Example: Secure Currency Exchange API (FastAPI)
--------------------------------------------------------------------------
Goal:
- Build and run a secure `v1` API with:
  - HTTPS (via reverse proxy in front of FastAPI)
  - OAuth2 Bearer tokens (JWT)
  - Leveled API keys (`read`, `write`, `admin`)
  - Route authorization by OAuth2 scopes
  - Rate limiting
  - Input validation
  - Versioned endpoints (`/v1/...`)
  - Error-safe responses
  - Simple IP allowlisting for admin route

What this example exposes:
- `POST /v1/auth/token` -> get JWT access token
- `GET /v1/rates/{base}` -> read exchange rates
- `POST /v1/convert` -> convert amount between currencies
- `POST /v1/admin/rates` -> admin update for one rate pair

Exact tools and services used in this example (GCP + OSS + Cloudflare):
- API framework: `FastAPI` (open source)
- App server: `Uvicorn` (open source)
- Auth/token library: `python-jose`, `passlib` (open source)
- Validation: `Pydantic` (open source)
- In-app rate limiting: `slowapi` (open source)
- Runtime hosting: `Google Cloud Run`
- Container registry: `Artifact Registry`
- Secret storage: `Google Secret Manager`
- Build pipeline: `Cloud Build`
- Logs/metrics/alerts: `Cloud Logging` + `Cloud Monitoring`
- Edge DNS/TLS/WAF/rate-limit/DDoS: `Cloudflare`
- Optional stronger edge filtering in GCP: `External Application Load Balancer` + `Cloud Armor`

Cost notes for this stack (verify before purchase; pricing changes over time):
- Cloud Run includes a monthly free tier (requests + CPU + memory)
- Secret Manager includes monthly free usage for a small number of secret versions and accesses
- Cloudflare supports free/pro/business/enterprise plans; advanced API Shield features are enterprise-focused


Step 1) Create project and virtual environment
----------------------------------------------
```bash
mkdir -p currency-api-secure/app
cd currency-api-secure
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```


Step 2) Install dependencies
----------------------------
```bash
pip install fastapi uvicorn[standard] python-jose[cryptography] passlib[bcrypt] \
  pydantic-settings python-multipart slowapi
```

Create `requirements.txt`:
```bash
pip freeze > requirements.txt
```


Step 3) Create environment variables file
-----------------------------------------
Create `.env` in project root:
```env
APP_NAME=Secure Currency API
JWT_SECRET=REPLACE_WITH_REAL_SECRET_DO_NOT_COMMIT
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Demo placeholders only (never use in production, never commit real keys)
API_KEY_READ=REPLACE_WITH_REAL_KEY_READ
API_KEY_WRITE=REPLACE_WITH_REAL_KEY_WRITE
API_KEY_ADMIN=REPLACE_WITH_REAL_KEY_ADMIN

# Comma-separated list of allowed IPs for admin route
ALLOWLISTED_IPS=127.0.0.1,::1
```

Generate a real JWT secret:
```bash
python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
```
Copy that output into `JWT_SECRET`.


Step 4) Create the FastAPI app
------------------------------
Create file `app/main.py` with the following content:

```python
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Secure Currency API"
    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_expire_minutes: int = 30

    api_key_read: str
    api_key_write: str
    api_key_admin: str

    allowlisted_ips: str = "127.0.0.1,::1"

    @property
    def allowed_ips_set(self) -> set[str]:
        return {ip.strip() for ip in self.allowlisted_ips.split(",") if ip.strip()}


settings = Settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/auth/token",
    scopes={
        "rates:read": "Read FX rates",
        "rates:write": "Create conversions",
        "rates:admin": "Admin rate updates",
    },
)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

app = FastAPI(title=settings.app_name, version="1.0.0")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ConvertRequest(BaseModel):
    from_currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    to_currency: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    amount: float = Field(..., gt=0, le=1_000_000)


class ConvertResponse(BaseModel):
    from_currency: str
    to_currency: str
    amount: float
    rate: float
    converted_amount: float


class AdminRateUpdate(BaseModel):
    base: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    quote: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    rate: float = Field(..., gt=0, le=1000)


# Demo user store. In production, use a database and salted password hashes.
fake_users = {
    "alice": {
        "username": "alice",
        "hashed_password": pwd_context.hash("alice_password"),
        "scopes": ["rates:read", "rates:write"],
    },
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin_password"),
        "scopes": ["rates:read", "rates:write", "rates:admin"],
    },
}


# In-memory rate table for demo purpose.
rates = {
    "USD": {"EUR": 0.91, "GBP": 0.78, "JPY": 151.0},
    "EUR": {"USD": 1.10, "GBP": 0.86, "JPY": 166.0},
}


def create_access_token(subject: str, scopes: list[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "scopes": scopes, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def verify_user(username: str, password: str):
    user = fake_users.get(username)
    if not user:
        return None
    if not pwd_context.verify(password, user["hashed_password"]):
        return None
    return user


def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_api_key(required_tier: str):
    tier_rank = {"read": 1, "write": 2, "admin": 3}
    keys = {
        settings.api_key_read: "read",
        settings.api_key_write: "write",
        settings.api_key_admin: "admin",
    }

    async def _guard(api_key: str | None = Security(api_key_header)):
        if not api_key or api_key not in keys:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        client_tier = keys[api_key]
        if tier_rank[client_tier] < tier_rank[required_tier]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key tier too low")
        return {"tier": client_tier}

    return _guard


def require_scope(required_scope: str):
    async def _guard(token: Annotated[str, Depends(oauth2_scheme)]):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
            token_scopes = payload.get("scopes", [])
            username = payload.get("sub")
            if not username:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        if required_scope not in token_scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
        return {"username": username, "scopes": token_scopes}

    return _guard


async def require_allowlisted_ip(request: Request):
    ip = get_client_ip(request)
    if ip not in settings.allowed_ips_set:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="IP not allowlisted")
    return ip


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"http_{exc.status_code}",
                "message": exc.detail,
                "path": request.url.path,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "path": request.url.path,
                "details": exc.errors(),
            }
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/auth/token", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = verify_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token = create_access_token(subject=user["username"], scopes=user["scopes"])
    return TokenResponse(access_token=token)


@app.get("/v1/rates/{base}")
@limiter.limit("60/minute")
async def get_rates(
    request: Request,
    base: str,
    _token_user: Annotated[dict, Depends(require_scope("rates:read"))],
    _api_key: Annotated[dict, Depends(check_api_key("read"))],
):
    base = base.upper()
    if base not in rates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Base currency not found")
    return {"base": base, "rates": rates[base]}


@app.post("/v1/convert", response_model=ConvertResponse)
@limiter.limit("30/minute")
async def convert(
    request: Request,
    payload: ConvertRequest,
    _token_user: Annotated[dict, Depends(require_scope("rates:write"))],
    _api_key: Annotated[dict, Depends(check_api_key("write"))],
):
    base_rates = rates.get(payload.from_currency)
    if not base_rates or payload.to_currency not in base_rates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency pair not found")
    rate = base_rates[payload.to_currency]
    converted = round(payload.amount * rate, 4)
    return ConvertResponse(
        from_currency=payload.from_currency,
        to_currency=payload.to_currency,
        amount=payload.amount,
        rate=rate,
        converted_amount=converted,
    )


@app.post("/v1/admin/rates")
@limiter.limit("15/minute")
async def admin_update_rate(
    request: Request,
    payload: AdminRateUpdate,
    _token_user: Annotated[dict, Depends(require_scope("rates:admin"))],
    _api_key: Annotated[dict, Depends(check_api_key("admin"))],
    _ip: Annotated[str, Depends(require_allowlisted_ip)],
):
    rates.setdefault(payload.base, {})
    rates[payload.base][payload.quote] = payload.rate
    return {"updated": True, "base": payload.base, "quote": payload.quote, "rate": payload.rate}
```


Step 5) Run the API locally
---------------------------
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```


Step 6) Get a JWT token (OAuth2 password flow for demo)
-------------------------------------------------------
In a new terminal:
```bash
curl -s -X POST "http://127.0.0.1:8000/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alice&password=alice_password" | jq
```
Copy `access_token` from response.


Step 7) Call read endpoint with token + API key
-----------------------------------------------
```bash
TOKEN="<paste_access_token>"
curl -s "http://127.0.0.1:8000/v1/rates/USD" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-api-key: read_demo_key_123" | jq
```


Step 8) Call conversion endpoint with write access
--------------------------------------------------
```bash
curl -s -X POST "http://127.0.0.1:8000/v1/convert" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-api-key: write_demo_key_123" \
  -d '{"from_currency":"USD","to_currency":"EUR","amount":250.00}' | jq
```


Step 9) Verify authorization failures work
------------------------------------------
Use read key on write endpoint (should return `403`):
```bash
curl -i -X POST "http://127.0.0.1:8000/v1/convert" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-api-key: read_demo_key_123" \
  -d '{"from_currency":"USD","to_currency":"EUR","amount":250.00}'
```

Call endpoint without token (should return `401`):
```bash
curl -i "http://127.0.0.1:8000/v1/rates/USD" -H "x-api-key: read_demo_key_123"
```


Step 10) Verify admin protections
---------------------------------
Get admin token:
```bash
ADMIN_TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin_password" | jq -r .access_token)
```

Call admin route:
```bash
curl -s -X POST "http://127.0.0.1:8000/v1/admin/rates" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "x-api-key: admin_demo_key_123" \
  -d '{"base":"USD","quote":"CHF","rate":0.89}' | jq
```


Step 11) Local HTTPS (dev only) with Caddy
------------------------------------------
Install `Caddy`, then create `Caddyfile`:
```txt
:8443 {
    tls internal
    reverse_proxy 127.0.0.1:8000
    header Strict-Transport-Security "max-age=31536000; includeSubDomains"
}
```

Run:
```bash
caddy run --config Caddyfile
```

Now call API over TLS:
```bash
curl -k "https://127.0.0.1:8443/health"
```


Step 12) Production prerequisites for GitHub Actions -> GCP
------------------------------------------------------------
Required tools/services:
- Local admin machine: `gcloud`, `jq`
- CI/CD: `GitHub Actions`
- Runtime: `Cloud Run`
- Registry: `Artifact Registry`
- Secrets: `Secret Manager`

One-time local setup:
```bash
gcloud auth login
gcloud auth application-default login

export PROJECT_ID="currency-api-prod-001"
export REGION="us-central1"
export SERVICE="currency-api"
export REPO="currency-api"
export GITHUB_REPO="YOUR_GITHUB_ORG/YOUR_REPO"   # example: acme/currency-api
export WIF_POOL_ID="github-pool"
export WIF_PROVIDER_ID="github-provider"

gcloud projects create "$PROJECT_ID"
gcloud config set project "$PROJECT_ID"
gcloud billing projects link "$PROJECT_ID" --billing-account "XXXXXX-XXXXXX-XXXXXX"
```

Enable required APIs:
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudresourcemanager.googleapis.com
```


Step 13) Bootstrap GCP IAM for GitHub OIDC (no JSON key files)
---------------------------------------------------------------
Create service accounts:
```bash
export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
export DEPLOYER_SA="github-deployer@$PROJECT_ID.iam.gserviceaccount.com"
export RUNTIME_SA="currency-api-runtime@$PROJECT_ID.iam.gserviceaccount.com"

gcloud iam service-accounts create github-deployer --display-name="GitHub Actions Deployer"
gcloud iam service-accounts create currency-api-runtime --display-name="Cloud Run Runtime"
```

Grant deploy permissions to `github-deployer`:
```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$DEPLOYER_SA" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$DEPLOYER_SA" \
  --role="roles/artifactregistry.writer"

gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --member="serviceAccount:$DEPLOYER_SA" \
  --role="roles/iam.serviceAccountUser"
```

Grant runtime permissions to `currency-api-runtime`:
```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$RUNTIME_SA" \
  --role="roles/secretmanager.secretAccessor"
```

Create Workload Identity Federation pool + provider:
```bash
gcloud iam workload-identity-pools create "$WIF_POOL_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER_ID" \
  --location="global" \
  --workload-identity-pool="$WIF_POOL_ID" \
  --display-name="GitHub Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref,attribute.actor=assertion.actor" \
  --attribute-condition="assertion.repository=='$GITHUB_REPO' && assertion.ref=='refs/heads/main'"
```

Allow identities from your repo to impersonate deployer SA:
```bash
gcloud iam service-accounts add-iam-policy-binding "$DEPLOYER_SA" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$WIF_POOL_ID/attribute.repository/$GITHUB_REPO"
```

Get provider resource name (needed in GitHub):
```bash
gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER_ID" \
  --location="global" \
  --workload-identity-pool="$WIF_POOL_ID" \
  --format="value(name)"
```


Step 14) Create Artifact Registry and production secrets
--------------------------------------------------------
Create Docker repository:
```bash
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION"
```

Create secrets:
```bash
printf "%s" "replace_with_long_random_secret" | gcloud secrets create jwt-secret --data-file=-
printf "%s" "read_prod_key_replace" | gcloud secrets create api-key-read --data-file=-
printf "%s" "write_prod_key_replace" | gcloud secrets create api-key-write --data-file=-
printf "%s" "admin_prod_key_replace" | gcloud secrets create api-key-admin --data-file=-
```


Step 15) Add production `Dockerfile` (if missing)
-------------------------------------------------
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```


Step 16) Configure GitHub repo variables, secrets, and environment
-------------------------------------------------------------------
GitHub repository variables (`Settings -> Secrets and variables -> Actions -> Variables`):
- `GCP_PROJECT_ID` = your project ID
- `GCP_REGION` = `us-central1`
- `CLOUD_RUN_SERVICE` = `currency-api`
- `ARTIFACT_REPO` = `currency-api`
- `GCP_RUNTIME_SA` = `currency-api-runtime@<project-id>.iam.gserviceaccount.com`
- `ALLOWLISTED_IPS` = comma-separated allowlist
- `GCP_WIF_PROVIDER` = output from Step 13 describe command
- `GCP_DEPLOYER_SA` = `github-deployer@<project-id>.iam.gserviceaccount.com`

GitHub environment:
- Create environment `production`
- Add required reviewers for deployment approval
- Add wait timer if required by your change policy


Step 17) Add CI workflow (required before deploy)
-------------------------------------------------
Create `.github/workflows/ci.yml`:
```yaml
name: ci

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install --upgrade pip
      - run: pip install -r requirements.txt pytest
      - run: pytest -q
```


Step 18) Add production deploy workflow (GitHub Actions -> Cloud Run)
---------------------------------------------------------------------
Create `.github/workflows/deploy-prod.yml`:
```yaml
name: deploy-prod

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read
  id-token: write

concurrency:
  group: deploy-prod
  cancel-in-progress: false

env:
  PROJECT_ID: ${{ vars.GCP_PROJECT_ID }}
  REGION: ${{ vars.GCP_REGION }}
  SERVICE: ${{ vars.CLOUD_RUN_SERVICE }}
  REPO: ${{ vars.ARTIFACT_REPO }}
  RUNTIME_SA: ${{ vars.GCP_RUNTIME_SA }}
  IMAGE: ${{ vars.GCP_REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/${{ vars.ARTIFACT_REPO }}/${{ vars.CLOUD_RUN_SERVICE }}:${{ github.sha }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.GCP_WIF_PROVIDER }}
          service_account: ${{ vars.GCP_DEPLOYER_SA }}

      - name: Setup gcloud
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker auth for Artifact Registry
        run: gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

      - name: Build image
        run: docker build -t "${IMAGE}" .

      - name: Push image
        run: docker push "${IMAGE}"

      - name: Deploy Cloud Run
        run: |
          gcloud run deploy "${SERVICE}" \
            --image "${IMAGE}" \
            --region "${REGION}" \
            --platform managed \
            --service-account "${RUNTIME_SA}" \
            --allow-unauthenticated \
            --min-instances 1 \
            --max-instances 20 \
            --cpu 1 \
            --memory 512Mi \
            --set-env-vars APP_NAME="Secure Currency API",JWT_ALG=HS256,ACCESS_TOKEN_EXPIRE_MINUTES=30,ALLOWLISTED_IPS="${{ vars.ALLOWLISTED_IPS }}" \
            --set-secrets JWT_SECRET=jwt-secret:latest,API_KEY_READ=api-key-read:latest,API_KEY_WRITE=api-key-write:latest,API_KEY_ADMIN=api-key-admin:latest

      - name: Smoke test
        run: |
          URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')"
          curl -fsS "${URL}/health"
```

Production note:
- Pin third-party actions to immutable commit SHAs before go-live.


Step 19) Enforce GitHub production controls
-------------------------------------------
Repository settings:
- Protect `main` branch:
  - Require pull request
  - Require status check `ci / test`
  - Require up-to-date branch before merge
  - Restrict force-push and direct pushes
- Require `production` environment approval for deploy workflow
- Require CODEOWNERS review for `.github/workflows/*` and `app/security-*` files


Step 20) Put Cloudflare in front of Cloud Run (exact edge stack)
----------------------------------------------------------------
In Cloudflare dashboard (for your zone):
1. DNS:
   - Create `CNAME` record `api` -> Cloud Run hostname (without `https://`)
   - Set to `Proxied` (orange cloud)
2. SSL/TLS:
   - Set encryption mode to `Full (strict)`
   - Enable `Always Use HTTPS`
3. Security:
   - Enable WAF managed rules (Free Managed Ruleset available; broader coverage varies by plan)
   - Add rate-limit rule `POST /v1/auth/token`: 5 req/min per IP
   - Add rate-limit rule `POST /v1/convert`: 120 req/min per IP
4. API schema protection:
   - Upload OpenAPI schema for `/v1/*`
   - Start in `log`, then move to `block`
5. Optional:
   - Enable mTLS for partner/admin clients


Step 21) (Optional but stronger) Prevent origin bypass in GCP
--------------------------------------------------------------
For stricter origin protection:
- Put Cloud Run behind `External Application Load Balancer` using `Serverless NEG`
- Attach `Cloud Armor` policy with:
  - OWASP preconfigured WAF rules
  - Rate-based ban rules
  - Allowlist-only rules for admin paths
- Set Cloud Run ingress to `internal-and-cloud-load-balancing`


Step 22) Replace demo auth with production IdP
-----------------------------------------------
Choose one:
- Low-ops GCP-native: `Identity Platform` (OIDC/OAuth2)
- Open-source: `Keycloak` on GCP (Cloud Run + Cloud SQL/PostgreSQL)

Then update API token validation to trusted issuer + JWKS.


Step 23) Monitoring, alerting, and incident signals
---------------------------------------------------
Configure:
- Cloud Logging metrics for `401`, `403`, `429`, and admin route access
- Cloud Monitoring alerts:
  - p95 latency > 500ms (5 min)
  - `5xx` error rate > 1%
  - auth-failure surge
- GitHub Actions alerts for failed production deploy jobs
- Cloudflare Security Events monitoring for blocked/challenged traffic


Step 24) Low-cost industry-standard add-ons (optional)
------------------------------------------------------
- `Sentry` for error tracking
- `Upstash Redis` for distributed rate limiting state (if not using Memorystore)
- `UptimeRobot` or `Better Stack Uptime` for external probes


Step 25) Production hardening checklist (GitHub Actions + GCP)
---------------------------------------------------------------
[ ] GitHub OIDC/WIF is used (no long-lived JSON service account keys)
[ ] `main` branch protected and deploy gated by environment approval
[ ] Production deploy only from reviewed commits to `main`
[ ] Secrets exist only in Secret Manager
[ ] Cloud Run runtime SA has minimum required IAM roles
[ ] Cloudflare proxy + TLS Full (strict) + WAF/rate-limit enabled
[ ] OAuth2 issuer is external IdP (Identity Platform or Keycloak)
[ ] CI enforces tests for `401`, `403`, `404`, `422`, `429`
[ ] Alerting configured for auth abuse, deployment failures, and error spikes


Step 26) Definition of "secure and running" for this production setup
---------------------------------------------------------------------
[ ] API is reachable at `https://api.<your-domain>/v1/...` and `/health`
[ ] GitHub Actions deploys to Cloud Run using OIDC federation
[ ] Every deploy is auditable by commit SHA and GitHub run ID
[ ] All business endpoints require Bearer token + API key tier
[ ] Admin route requires admin scope + admin key tier + allowlisted IP
[ ] Invalid input returns `422`; excessive traffic returns `429`
[ ] End-to-end traffic is HTTPS with Cloudflare `Full (strict)`


22) OWASP Top 10:2025 Summary Reference
---------------------------------------
The following section is consolidated from the previous `top_10_owasp.txt` file.

OWASP Top 10:2025 - Summarized Risk Factors
Source: https://owasp.org/Top10/2025/
Retrieved: 2026-04-18

1) A01:2025 - Broken Access Control
- Summary: Authorization rules are missing, inconsistent, or bypassable, allowing users to access or modify resources outside their permissions.
- Common patterns: IDOR, missing checks on POST/PUT/DELETE, force browsing, privilege escalation, token/cookie tampering, CORS abuse.
- Mitigation focus: Deny-by-default, server-side centralized authorization, record-ownership checks, short-lived tokens, and authorization tests in CI.

2) A02:2025 - Security Misconfiguration
- Summary: Insecure defaults, overly permissive settings, exposed debug/error detail, and inconsistent hardening across environments.
- Common patterns: Default credentials, unnecessary services/features, weak headers, cloud IAM/storage misconfig, outdated security settings.
- Mitigation focus: Repeatable automated hardening baseline, minimal platform install, patch/config review, environment parity, and automated config verification.

3) A03:2025 - Software Supply Chain Failures
- Summary: Compromise or weakness in dependencies, build tools, registries, CI/CD, or developer tooling introduces vulnerable/malicious software.
- Common patterns: Untracked transitive deps, delayed patching, untrusted package sources, insecure CI/CD controls, poor change governance.
- Mitigation focus: SBOM + SCA, dependency/version inventory, trusted/signed sources, staged rollouts, hardened CI/CD, strict branch/release controls.

4) A04:2025 - Cryptographic Failures
- Summary: Sensitive data is not properly protected in transit/at rest, or uses weak crypto, poor key management, or unsafe randomness.
- Common patterns: Weak/deprecated algorithms, key reuse/leakage, bad certificate validation, insecure protocols, weak password hashing.
- Mitigation focus: TLS 1.2+ and HSTS, strong modern algorithms, proper key lifecycle/HSM, authenticated encryption, and adaptive salted password hashing.

5) A05:2025 - Injection
- Summary: Untrusted input reaches an interpreter (SQL/NoSQL/OS/LDAP/template/etc.) and is executed as commands or queries.
- Common patterns: String concatenation in queries/commands, missing validation/sanitization, unsafe ORM query construction.
- Mitigation focus: Parameterized queries/safe APIs, strict server-side validation, contextual escaping only as fallback, and SAST/DAST/IAST + fuzzing.

6) A06:2025 - Insecure Design
- Summary: Security controls are missing at architecture/design time; secure implementation alone cannot fully fix missing design controls.
- Common patterns: Unmodeled abuse cases, flawed business logic, weak tenant isolation, missing failure-state design.
- Mitigation focus: Threat modeling, secure design patterns, security requirements in user stories, secure SDLC, and misuse-case testing.

7) A07:2025 - Authentication Failures
- Summary: Authentication/session mechanisms can be bypassed, guessed, replayed, or abused to impersonate users.
- Common patterns: Credential stuffing/brute force, weak/default/breached passwords, weak recovery flows, poor session invalidation, weak MFA.
- Mitigation focus: MFA enforcement, breached-password checks, anti-automation controls, secure session management, and proper JWT claim validation.

8) A08:2025 - Software or Data Integrity Failures
- Summary: Systems trust software/data artifacts without integrity verification (code, updates, serialized objects, build artifacts).
- Common patterns: Unsigned updates, untrusted repositories, tamperable serialized data, weak CI/CD integrity controls.
- Mitigation focus: Signature/provenance checks, trusted repositories, strict change review, CI/CD segregation and access control, anti-tamper checks.

9) A09:2025 - Security Logging and Alerting Failures
- Summary: Security-relevant events are not logged, monitored, correlated, or alerted effectively, delaying detection and response.
- Common patterns: Missing failed-login logs, tamperable logs, no suspicious activity monitoring, local-only logs, no tuned alert playbooks.
- Mitigation focus: Complete auditable event logging, centralized tamper-resistant logs, SOC-ready alerting thresholds, and tested incident playbooks.

10) A10:2025 - Mishandling of Exceptional Conditions
- Summary: Applications fail to correctly handle abnormal states/errors, causing fail-open behavior, undefined states, crashes, or exploitable logic flaws.
- Common patterns: Inconsistent exception handling, partial transaction recovery, missing rollbacks, poor resilience under resource/network faults.
- Mitigation focus: Catch errors close to origin, fail closed, rollback/retry safely, global exception handling + observability, and rate/resource limits.

Practical implementation notes
- Treat A01/A07/A09 as operationally critical controls for early detection and blast-radius reduction.
- Treat A03/A08 as software factory risks: secure your pipeline and artifact trust chain, not only runtime code.
- Treat A06/A10 as engineering process risks: most fixes require design and lifecycle changes, not only patches.
