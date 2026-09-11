"""
FadeReach — RBAC Router
Roles · Permissions · Sub-accounts (Agency plan)
Owner / Admin / Manager / SDR / Viewer
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from .deps import get_current_tenant
from middleware.plan_enforcement import enforce_feature_flag, get_plan_limit
from typing import Optional
import bcrypt, os

try:
    import nanoid
    def gen_id(): return nanoid.generate(size=10)
except:
    import uuid
    def gen_id(): return uuid.uuid4().hex[:10]

router = APIRouter()

RESEND_KEY = os.getenv("RESEND_API_KEY", "")
APP_URL    = os.getenv("APP_URL", "https://fadereach.tinlance.com")

# Role hierarchy and permissions
ROLES = {
    "owner": {
        "label":       "Owner",
        "description": "Full access. Manages billing, members, and all settings.",
        "permissions": ["*"],  # All permissions
        "level":       5,
    },
    "admin": {
        "label":       "Admin",
        "description": "Full access except billing and workspace deletion.",
        "permissions": [
            "campaigns:*", "leads:*", "domains:*",
            "inbox:*", "analytics:*", "members:read",
        ],
        "level": 4,
    },
    "manager": {
        "label":       "Manager",
        "description": "Creates and manages campaigns. Views all analytics.",
        "permissions": [
            "campaigns:*", "leads:*", "domains:read",
            "inbox:*", "analytics:*",
        ],
        "level": 3,
    },
    "sdr": {
        "label":       "SDR",
        "description": "Manages leads and inbox. Cannot create campaigns.",
        "permissions": [
            "leads:*", "inbox:*", "campaigns:read",
            "analytics:read",
        ],
        "level": 2,
    },
    "viewer": {
        "label":       "Viewer",
        "description": "Read-only access to campaigns and analytics.",
        "permissions": [
            "campaigns:read", "analytics:read",
            "leads:read", "inbox:read",
        ],
        "level": 1,
    },
}

class InviteMemberReq(BaseModel):
    email:   str
    role:    str
    name:    Optional[str] = None

class UpdateMemberReq(BaseModel):
    role:    Optional[str]  = None
    active:  Optional[bool] = None

class SubAccountCreateReq(BaseModel):
    name:    str
    email:   str

@router.get("/roles")
async def list_roles(auth: dict = Depends(get_current_tenant)):
    """Available roles and their permissions"""
    return {"roles": ROLES}

@router.get("/members")
async def list_members(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """List all workspace members"""
    db        = request.app.state.db
    tenant_id = auth["sub"]
    plan      = auth.get("plan", "trial")

    await enforce_feature_flag(plan, "rbac", "Team management")

    async with db.acquire() as conn:
        # Check if members table exists, create if not
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS workspace_members (
                id          SERIAL PRIMARY KEY,
                tenant_id   TEXT REFERENCES tenants(id) ON DELETE CASCADE,
                email       TEXT NOT NULL,
                name        TEXT,
                role        TEXT NOT NULL DEFAULT 'viewer',
                status      TEXT NOT NULL DEFAULT 'pending',
                invited_by  TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                last_active TIMESTAMPTZ,
                UNIQUE(tenant_id, email)
            );
        """)

        members = await conn.fetch("""
            SELECT id, email, name, role, status, created_at, last_active
            FROM workspace_members
            WHERE tenant_id=$1
            ORDER BY created_at
        """, tenant_id)

        # Include owner (the tenant itself)
        owner = await conn.fetchrow(
            "SELECT email, name FROM tenants WHERE id=$1", tenant_id
        )

    result = [{
        "id":          "owner",
        "email":       owner["email"],
        "name":        owner["name"],
        "role":        "owner",
        "status":      "active",
        "is_owner":    True,
    }] + [dict(m) for m in members]

    limit = get_plan_limit(plan, "sub_accounts")

    return {
        "members":     result,
        "total":       len(result),
        "limit":       limit,
        "can_add_more": limit == -1 or len(result) < limit + 1,
    }

@router.post("/members/invite")
async def invite_member(
    req: InviteMemberReq,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Invite a new team member"""
    db        = request.app.state.db
    tenant_id = auth["sub"]
    plan      = auth.get("plan", "trial")

    await enforce_feature_flag(plan, "rbac", "Team management")

    if req.role not in ROLES:
        raise HTTPException(400, f"Invalid role: {req.role}. Valid: {list(ROLES.keys())}")

    if req.role == "owner":
        raise HTTPException(403, "Cannot assign owner role. Transfer ownership separately.")

    # Check member limit
    async with db.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS workspace_members (
                id SERIAL PRIMARY KEY,
                tenant_id TEXT REFERENCES tenants(id) ON DELETE CASCADE,
                email TEXT NOT NULL, name TEXT, role TEXT NOT NULL DEFAULT 'viewer',
                status TEXT NOT NULL DEFAULT 'pending', invited_by TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(), last_active TIMESTAMPTZ,
                UNIQUE(tenant_id, email)
            );
        """)

        count = await conn.fetchval(
            "SELECT COUNT(*) FROM workspace_members WHERE tenant_id=$1 AND status='active'",
            tenant_id
        )
        limit = get_plan_limit(plan, "sub_accounts")
        if limit != -1 and count >= limit:
            raise HTTPException(403,
                f"Member limit reached ({limit} on {plan} plan). Upgrade to add more."
            )

        # Insert member
        try:
            member_id = await conn.fetchval("""
                INSERT INTO workspace_members (tenant_id, email, name, role, invited_by)
                VALUES ($1,$2,$3,$4,$5)
                RETURNING id
            """, tenant_id, req.email.lower(), req.name, req.role, auth["sub"])
        except Exception:
            raise HTTPException(409, "This email is already a member")

        # Get tenant info for email
        owner = await conn.fetchrow(
            "SELECT name, email FROM tenants WHERE id=$1", tenant_id
        )

    # Send invite email via Resend
    if RESEND_KEY:
        import httpx
        role_info = ROLES[req.role]
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {RESEND_KEY}"},
                    json={
                        "from": "FadeReach <hello@fadereach.tinlance.com>",
                        "to":   req.email,
                        "subject": f"{owner['name']} invited you to FadeReach",
                        "html": f"""
                        <div style="font-family:Inter,sans-serif;max-width:520px">
                        <h2>You've been invited to FadeReach</h2>
                        <p>{owner['name']} has invited you to join their FadeReach workspace
                        as <strong>{role_info['label']}</strong>.</p>
                        <p><em>{role_info['description']}</em></p>
                        <p>
                          <a href="{APP_URL}/accept-invite?token={member_id}"
                             style="background:#00E5A0;color:#000;padding:12px 24px;
                                    border-radius:8px;text-decoration:none;font-weight:600">
                            Accept invitation →
                          </a>
                        </p>
                        <p style="font-size:12px;color:#666">
                          FadeReach — Cold email OS by Tinlance Limited
                        </p>
                        </div>
                        """
                    }
                )
        except Exception as e:
            print(f"Invite email error: {e}")

    return {
        "member_id": member_id,
        "email":     req.email,
        "role":      req.role,
        "status":    "pending",
        "message":   f"Invitation sent to {req.email}"
    }

@router.patch("/members/{member_id}")
async def update_member(
    member_id: int,
    req: UpdateMemberReq,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Update member role or deactivate"""
    db        = request.app.state.db
    tenant_id = auth["sub"]
    plan      = auth.get("plan", "trial")

    await enforce_feature_flag(plan, "rbac", "Team management")

    if req.role and req.role not in ROLES:
        raise HTTPException(400, f"Invalid role: {req.role}")

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, role FROM workspace_members WHERE id=$1 AND tenant_id=$2",
            member_id, tenant_id
        )
        if not row:
            raise HTTPException(404, "Member not found")

        updates = {}
        if req.role   is not None: updates["role"]   = req.role
        if req.active is not None: updates["status"]  = "active" if req.active else "inactive"

        if updates:
            set_clause = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates))
            await conn.execute(
                f"UPDATE workspace_members SET {set_clause} WHERE id=$1",
                member_id, *list(updates.values())
            )

    return {"member_id": member_id, "updated": updates}

@router.delete("/members/{member_id}")
async def remove_member(
    member_id: int,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Remove a workspace member"""
    db        = request.app.state.db
    tenant_id = auth["sub"]
    plan      = auth.get("plan", "trial")

    await enforce_feature_flag(plan, "rbac", "Team management")

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM workspace_members WHERE id=$1 AND tenant_id=$2 RETURNING id, email",
            member_id, tenant_id
        )
        if not row:
            raise HTTPException(404, "Member not found")

    return {"removed": True, "email": row["email"]}
