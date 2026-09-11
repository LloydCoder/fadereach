"""
FadeReach — A/B Testing Engine + Spintax Engine
A/B: subject lines, first lines, CTAs, send times
Spintax: phrase rotation prevents spam fingerprinting
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from .deps import get_current_tenant
from middleware.plan_enforcement import enforce_feature_flag
import random, re, json, math
from typing import Optional
from datetime import datetime

router = APIRouter()

# ═══════════════════════════════════════════════
# A/B TESTING ENGINE
# ═══════════════════════════════════════════════
class ABTestCreateReq(BaseModel):
    campaign_id: int
    test_type:   str  # subject | first_line | cta | send_time
    variants:    list[dict]  # [{label, value}, ...]
    split_pct:   list[int]   # [50, 50] or [33, 33, 34]
    min_sample:  int = 100   # min sends before declaring winner

class ABTestResultReq(BaseModel):
    test_id: int
    variant: str  # a | b | c

@router.post("/ab/create")
async def create_ab_test(
    req:     ABTestCreateReq,
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """Create an A/B test for a campaign element"""
    db   = request.app.state.db
    plan = auth.get("plan", "trial")

    await enforce_feature_flag(plan, "a_b_testing", "A/B Testing")

    if len(req.variants) < 2:
        raise HTTPException(400, "A/B test requires at least 2 variants")
    if sum(req.split_pct) != 100:
        raise HTTPException(400, "Split percentages must sum to 100")
    if len(req.variants) != len(req.split_pct):
        raise HTTPException(400, "Variants and split_pct must have same length")

    async with db.acquire() as conn:
        # Create ab_tests table if not exists
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ab_tests (
                id          SERIAL PRIMARY KEY,
                tenant_id   TEXT NOT NULL,
                campaign_id INTEGER,
                test_type   TEXT NOT NULL,
                variants    JSONB NOT NULL,
                split_pct   JSONB NOT NULL,
                min_sample  INTEGER DEFAULT 100,
                status      TEXT DEFAULT 'running',
                winner      TEXT,
                started_at  TIMESTAMPTZ DEFAULT NOW(),
                ended_at    TIMESTAMPTZ,
                results     JSONB
            );
        """)

        test_id = await conn.fetchval("""
            INSERT INTO ab_tests
            (tenant_id, campaign_id, test_type, variants, split_pct, min_sample)
            VALUES ($1,$2,$3,$4,$5,$6) RETURNING id
        """, auth["sub"], req.campaign_id, req.test_type,
            json.dumps(req.variants), json.dumps(req.split_pct), req.min_sample)

    return {
        "test_id":    test_id,
        "test_type":  req.test_type,
        "variants":   req.variants,
        "split_pct":  req.split_pct,
        "status":     "running",
        "message":    f"A/B test created. Need {req.min_sample} sends per variant before results are significant."
    }

@router.get("/ab/{test_id}/results")
async def get_ab_results(
    test_id: int,
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """Get A/B test results with statistical significance"""
    db = request.app.state.db
    async with db.acquire() as conn:
        test = await conn.fetchrow(
            "SELECT * FROM ab_tests WHERE id=$1 AND tenant_id=$2",
            test_id, auth["sub"]
        )
    if not test:
        raise HTTPException(404, "A/B test not found")

    variants    = json.loads(test["variants"])
    results     = json.loads(test["results"] or "{}") if test["results"] else {}

    # Calculate statistical significance for each variant
    variant_results = []
    for i, variant in enumerate(variants):
        label    = variant["label"]
        sent     = results.get(label, {}).get("sent", 0)
        replies  = results.get(label, {}).get("replies", 0)
        reply_rate = round(replies / sent * 100, 1) if sent > 0 else 0

        variant_results.append({
            "label":        label,
            "value":        variant["value"],
            "sent":         sent,
            "replies":      replies,
            "reply_rate":   reply_rate,
            "is_winner":    test["winner"] == label,
            "significant":  sent >= test["min_sample"],
        })

    # Determine winner if enough data
    winner = None
    if all(v["significant"] for v in variant_results):
        winner = max(variant_results, key=lambda v: v["reply_rate"])
        winner = winner["label"] if winner["reply_rate"] > 0 else None

    return {
        "test_id":      test_id,
        "test_type":    test["test_type"],
        "status":       test["status"],
        "variants":     variant_results,
        "winner":       winner,
        "significance": _calculate_significance(variant_results),
        "recommendation": _get_ab_recommendation(winner, variant_results),
    }

@router.get("/ab")
async def list_ab_tests(
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """List all A/B tests"""
    db = request.app.state.db
    async with db.acquire() as conn:
        tests = await conn.fetch("""
            SELECT id, campaign_id, test_type, status, winner, started_at
            FROM ab_tests WHERE tenant_id=$1
            ORDER BY started_at DESC LIMIT 20
        """, auth["sub"])
    return {"tests": [dict(t) for t in tests]}

# ═══════════════════════════════════════════════
# SPINTAX ENGINE
# Prevents spam filter fingerprinting
# {Hi|Hello|Hey} {first_name}
# ═══════════════════════════════════════════════
class SpintaxReq(BaseModel):
    template:   str
    variations: int = 5

class SpintaxBatchReq(BaseModel):
    template: str
    leads:    list[dict]

@router.post("/spintax/preview")
async def spintax_preview(
    req:     SpintaxReq,
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """
    Preview spintax variations before sending
    Syntax: {option1|option2|option3}
    Nested: {Hi|Hello {first_name}|Hey there}
    """
    variations = []
    for i in range(min(req.variations, 10)):
        try:
            variation = _resolve_spintax(req.template)
            variations.append(variation)
        except Exception as e:
            raise HTTPException(400, f"Invalid spintax: {str(e)}")

    unique    = list(set(variations))
    diversity = round(len(unique) / len(variations) * 100)

    return {
        "original":        req.template,
        "variations":      variations,
        "unique_count":    len(unique),
        "diversity_score": diversity,
        "is_valid":        _validate_spintax(req.template),
        "tip":             (
            "Great diversity!" if diversity > 70
            else "Add more options to each {spin} for better diversity"
        )
    }

@router.post("/spintax/apply")
async def apply_spintax_to_leads(
    req:     SpintaxBatchReq,
    request: Request,
    auth:    dict = Depends(get_current_tenant),
):
    """
    Apply spintax to a list of leads
    Each lead gets a unique variation + their data merged
    """
    results = []
    for lead in req.leads[:100]:  # Cap at 100
        resolved  = _resolve_spintax(req.template)
        # Merge lead data
        resolved  = resolved.replace("{{first_name}}", lead.get("first_name", "") or "there")
        resolved  = resolved.replace("{{company}}", lead.get("company", "") or "your company")
        resolved  = resolved.replace("{{title}}", lead.get("title", "") or "")
        first_line = lead.get("ai_first_line", "")
        resolved  = resolved.replace("{{first_line}}", first_line)

        results.append({
            "email":   lead.get("email"),
            "content": resolved,
        })

    return {
        "total":   len(results),
        "results": results,
        "note":    "Each lead received a unique variation to avoid spam fingerprinting",
    }

@router.get("/spintax/templates")
async def spintax_templates(auth: dict = Depends(get_current_tenant)):
    """Pre-built spintax templates for common cold email patterns"""
    return {
        "templates": [
            {
                "name":     "Subject line variations",
                "category": "subject",
                "examples": [
                    "{Quick question|Brief thought|One thing} about {{company}}",
                    "{Noticed|Saw|Came across} something interesting at {{company}}",
                    "{{company}} + {ThreatFade|our security tool|what we're building}",
                ],
            },
            {
                "name":     "Opening greeting",
                "category": "greeting",
                "examples": [
                    "{Hi|Hey|Hello} {{first_name}},",
                    "{Hi|Hey} {{first_name}} —",
                    "{{first_name}} —",
                ],
            },
            {
                "name":     "CTA variations",
                "category": "cta",
                "examples": [
                    "{Worth a quick chat?|Open to a 15-minute call?|Would this be relevant to explore?}",
                    "{Is this worth 15 minutes?|Any interest in a quick call?|Relevant to you right now?}",
                    "{Free for a call this week?|Open to connect?|Worth exploring?}",
                ],
            },
            {
                "name":     "Closing sign-off",
                "category": "closing",
                "examples": [
                    "{Best|Cheers|Thanks} — {Lloyd|Lloyd Chinaemerem}",
                    "{Kind regards|Warm regards|All the best},",
                ],
            },
        ]
    }

# ── Statistical helpers ─────────────────────────
def _calculate_significance(variants: list) -> dict:
    """
    Simple z-test for A/B significance
    Returns confidence level
    """
    if len(variants) < 2:
        return {"significant": False, "confidence": 0}

    a = variants[0]
    b = variants[1]

    if a["sent"] < 30 or b["sent"] < 30:
        return {
            "significant":    False,
            "confidence":     0,
            "message":        f"Need at least 30 sends per variant. Currently: A={a['sent']}, B={b['sent']}"
        }

    # Pooled proportion z-test
    p1 = a["replies"] / a["sent"] if a["sent"] > 0 else 0
    p2 = b["replies"] / b["sent"] if b["sent"] > 0 else 0
    n1, n2  = a["sent"], b["sent"]
    p_pool  = (a["replies"] + b["replies"]) / (n1 + n2)

    if p_pool == 0 or p_pool == 1:
        return {"significant": False, "confidence": 0, "message": "Insufficient reply data"}

    se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    if se == 0:
        return {"significant": False, "confidence": 0}

    z         = abs(p1 - p2) / se
    confidence = min(99, round(_z_to_confidence(z) * 100))

    return {
        "significant": confidence >= 95,
        "confidence":  confidence,
        "message": (
            f"{confidence}% confidence — result is {'statistically significant' if confidence >= 95 else 'not yet significant'}"
        )
    }

def _z_to_confidence(z: float) -> float:
    """Approximate z-score to confidence conversion"""
    if z >= 2.576: return 0.99
    if z >= 1.960: return 0.95
    if z >= 1.645: return 0.90
    if z >= 1.282: return 0.80
    return max(0.5, 0.5 + z * 0.15)

def _get_ab_recommendation(winner: Optional[str], variants: list) -> str:
    if not winner:
        return "Not enough data yet to declare a winner. Keep sending."
    best    = next((v for v in variants if v["label"] == winner), None)
    other   = next((v for v in variants if v["label"] != winner), None)
    if not best or not other:
        return f"Variant {winner} is winning."
    lift    = round((best["reply_rate"] - other["reply_rate"]) / other["reply_rate"] * 100) if other["reply_rate"] > 0 else 0
    return f"Variant {winner} wins with {best['reply_rate']}% reply rate — {lift}% higher than the alternative. Apply to remaining sends."

# ── Spintax helpers ─────────────────────────────
def _resolve_spintax(text: str) -> str:
    """Recursively resolve {option1|option2} spintax"""
    pattern = re.compile(r'\{([^{}]+)\}')
    max_iter = 20
    for _ in range(max_iter):
        match = pattern.search(text)
        if not match:
            break
        options = match.group(1).split('|')
        chosen  = random.choice(options)
        text    = text[:match.start()] + chosen + text[match.end():]
    return text

def _validate_spintax(text: str) -> bool:
    """Check spintax braces are balanced"""
    depth = 0
    for char in text:
        if char == '{': depth += 1
        elif char == '}': depth -= 1
        if depth < 0: return False
    return depth == 0
