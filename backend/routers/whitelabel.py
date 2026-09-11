"""
FadeReach — White-Label Router
Custom subdomain · Brand colors · Logo upload
Agency plan feature
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from .deps import get_current_tenant
from middleware.plan_enforcement import enforce_feature_flag
import subprocess, os
from typing import Optional

router = APIRouter()
APP_DOMAIN = os.getenv("APP_DOMAIN", "fadereach.tinlance.com")

class WhiteLabelConfigReq(BaseModel):
    subdomain:       Optional[str]  = None   # e.g. "outreach" → outreach.agency.com
    custom_domain:   Optional[str]  = None   # e.g. "outreach.agency.com"
    brand_name:      Optional[str]  = None
    brand_color:     Optional[str]  = None   # hex
    logo_url:        Optional[str]  = None
    support_email:   Optional[str]  = None
    hide_fadereach:  Optional[bool] = None   # Hide "Powered by FadeReach"

@router.get("/config")
async def get_whitelabel_config(
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Get current white-label configuration"""
    db        = request.app.state.db
    tenant_id = auth["sub"]
    plan      = auth.get("plan", "trial")

    await enforce_feature_flag(plan, "white_label", "White-label")

    redis = request.app.state.redis
    config = await redis.hgetall(f"whitelabel:{tenant_id}")

    return {
        "configured":    bool(config),
        "subdomain":     config.get("subdomain"),
        "custom_domain": config.get("custom_domain"),
        "brand_name":    config.get("brand_name", "FadeReach"),
        "brand_color":   config.get("brand_color", "#00E5A0"),
        "logo_url":      config.get("logo_url"),
        "support_email": config.get("support_email"),
        "hide_fadereach": config.get("hide_fadereach") == "true",
        "dashboard_url": f"https://{config.get('subdomain')}.{APP_DOMAIN}"
                         if config.get("subdomain") else None,
        "dns_instructions": _get_dns_instructions(config.get("custom_domain")),
    }

@router.post("/config")
async def update_whitelabel_config(
    req: WhiteLabelConfigReq,
    request: Request,
    auth: dict = Depends(get_current_tenant)
):
    """Update white-label configuration"""
    db        = request.app.state.db
    tenant_id = auth["sub"]
    plan      = auth.get("plan", "trial")

    await enforce_feature_flag(plan, "white_label", "White-label")

    redis = request.app.state.redis

    # Validate subdomain
    if req.subdomain:
        import re
        if not re.match(r'^[a-z0-9-]{3,30}$', req.subdomain):
            raise HTTPException(400,
                "Subdomain must be 3-30 characters, lowercase letters, numbers and hyphens only."
            )
        # Check not already taken
        existing = await redis.get(f"subdomain:{req.subdomain}")
        if existing and existing != tenant_id:
            raise HTTPException(409, f"Subdomain '{req.subdomain}' is already taken.")

        await redis.set(f"subdomain:{req.subdomain}", tenant_id)

    # Save config
    updates = {}
    for field in ["subdomain","custom_domain","brand_name","brand_color","logo_url","support_email"]:
        val = getattr(req, field)
        if val is not None:
            updates[field] = val
    if req.hide_fadereach is not None:
        updates["hide_fadereach"] = "true" if req.hide_fadereach else "false"

    if updates:
        await redis.hset(f"whitelabel:{tenant_id}", mapping=updates)

    # Provision subdomain in Nginx if subdomain set
    if req.subdomain:
        _provision_nginx_subdomain(req.subdomain, tenant_id)

    config = await redis.hgetall(f"whitelabel:{tenant_id}")

    return {
        "configured":    True,
        "subdomain":     config.get("subdomain"),
        "custom_domain": config.get("custom_domain"),
        "brand_name":    config.get("brand_name", "FadeReach"),
        "brand_color":   config.get("brand_color", "#00E5A0"),
        "dashboard_url": f"https://{config.get('subdomain')}.{APP_DOMAIN}"
                         if config.get("subdomain") else None,
        "dns_instructions": _get_dns_instructions(req.custom_domain),
        "message": "White-label configuration saved."
    }

def _provision_nginx_subdomain(subdomain: str, tenant_id: str):
    """Auto-provision Nginx config for white-label subdomain"""
    nginx_conf = f"""
# FadeReach White-Label: {subdomain}.{APP_DOMAIN}
# Tenant: {tenant_id}
server {{
    listen 443 ssl http2;
    server_name {subdomain}.{APP_DOMAIN};

    ssl_certificate /etc/letsencrypt/live/{APP_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{APP_DOMAIN}/privkey.pem;

    # Pass tenant context
    add_header X-Tenant-ID "{tenant_id}";
    add_header X-White-Label "true";

    # Serve same React app (branding loaded from API)
    location / {{
        root /opt/fadereach/frontend/dist;
        try_files $uri $uri/ /index.html;
        add_header X-Subdomain "{subdomain}";
    }}

    location /api/ {{
        proxy_pass http://localhost:8001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Tenant-ID "{tenant_id}";
    }}
}}
"""
    try:
        conf_path = f"/etc/nginx/sites-available/fadereach-wl-{subdomain}"
        with open(conf_path, "w") as f:
            f.write(nginx_conf)
        symlink = f"/etc/nginx/sites-enabled/fadereach-wl-{subdomain}"
        if not os.path.exists(symlink):
            os.symlink(conf_path, symlink)
        subprocess.run(["nginx", "-t"], capture_output=True)
        subprocess.run(["nginx", "-s", "reload"], capture_output=True)
    except Exception as e:
        print(f"Nginx provision error [{subdomain}]: {e}")

def _get_dns_instructions(custom_domain: Optional[str]) -> Optional[dict]:
    if not custom_domain:
        return None
    return {
        "step_1": {
            "type":  "CNAME",
            "name":  custom_domain,
            "value": APP_DOMAIN,
            "note":  f"Point {custom_domain} to FadeReach infrastructure",
        },
        "step_2": {
            "note": "DNS propagation takes 5–30 minutes. "
                    "Once propagated, your white-label dashboard will be live at "
                    f"https://{custom_domain}",
        }
    }
