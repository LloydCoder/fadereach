"""
FadeReach — Vertical Intelligence Packs
Deep market knowledge for each ICP

Four packs:
1. Nigerian Fintech (primary — home market)
2. African Dev Agency (core African market)
3. EU Security Team (ThreatFade/KalevioAI/TwinGuard/AI Shield buyers)
4. US PropTech (RealtyScreen AI buyers)

Each pack contains:
- ICP definition and scoring criteria
- Signal sources and trigger events
- Pre-built campaign sequences
- Objection handling
- Cultural context (Africa-first awareness)
- Regulatory context (NIS2, DORA, FCRA)
- Timing intelligence
- LinkedIn signal patterns
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from .deps import get_current_tenant
from typing import Optional

router = APIRouter()

VERTICAL_PACKS = {
    "nigerian_fintech": {
        "name":       "Nigerian Fintech",
        "emoji":      "🇳🇬",
        "market_size":"$12B+ Nigerian fintech market",
        "best_products": ["ThreatFade", "KalevioAI", "FadeReach", "Web-Temify"],
        "icp": {
            "titles":      ["CTO", "CISO", "Head of Engineering", "Head of Security",
                            "VP Engineering", "Technical Lead", "Infrastructure Lead"],
            "company_types": ["payment company", "lending platform", "digital bank",
                              "remittance service", "crypto exchange", "InsurTech"],
            "size":        "10-500 employees",
            "funding":     "Seed to Series B",
            "keywords":    ["Paystack", "Flutterwave", "Remita", "Interswitch",
                            "CBN", "PCIDSS", "KYC", "AML", "naira", "NGN"],
            "location":    ["Lagos", "Abuja", "Port Harcourt", "Ibadan"],
            "score_signals": {
                "tech_keywords": 20,
                "fintech_domain": 25,
                "cbn_regulated":  30,
                "hiring_security": 20,
                "recent_funding":  25,
            }
        },
        "pain_points": [
            "CBN mandates email authentication but implementation is unclear",
            "PCIDSS compliance gaps in email infrastructure",
            "Phishing attacks targeting customers via spoofed company emails",
            "No dedicated security team at <100 employee stage",
            "Security incidents damage customer trust = churn",
            "Manual KYC processes vulnerable to credential theft",
        ],
        "objections": {
            "We have internal security": "Most Nigerian fintechs have security policies but not dedicated infrastructure monitoring. ThreatFade runs passive — it doesn't require an internal security team to operate.",
            "Too expensive": "ThreatFade's free scan takes 10 minutes. If we find a gap, the cost of the tool is trivial compared to one customer phishing incident.",
            "Not a priority now": "PCIDSS renewal and CBN audits make this a board-level priority whether or not it feels urgent day-to-day. Happy to time outreach for Q4 before your audit cycle.",
            "We use X tool already": "Most tools monitor internal traffic. ThreatFade specifically monitors for external C2 patterns that target financial institutions — completely different threat model.",
        },
        "timing": {
            "best_days":   ["Tuesday", "Wednesday", "Thursday"],
            "best_hours":  "8:00–10:00 WAT (WAT = UTC+1)",
            "avoid":       ["Friday afternoons", "Monday mornings", "Nigerian public holidays"],
            "trigger_events": [
                "CBN audit season (Q4)",
                "PCIDSS renewal (varies)",
                "New CTO or CISO hired",
                "Funding announcement",
                "Security incident in the news (competitor)",
                "Product launch (new attack surface)",
            ]
        },
        "cultural_context": [
            "Nigerian B2B relationships are trust-based — reference a mutual connection if possible",
            "Direct approach is respected but pushy follow-up is not",
            "WhatsApp follow-up is sometimes appropriate at relationship stage",
            "Company names often reflect founder names or Yoruba/Igbo/Hausa heritage — personalize correctly",
            "Referencing specific CBN circulars shows expertise and builds credibility fast",
        ],
        "sample_sequences": [
            {
                "name":    "Security gap discovery",
                "trigger": "Missing DMARC detected by ThreatFade",
                "step1":   "Noticed {company}'s DMARC policy is p=none — emails spoofed in your name currently reach customers without any authentication warning. For a payment company at your scale, that's a phishing vector CBN auditors increasingly flag.",
                "step2":   "Sent a note last week. One question worth a minute: has {company} had any phishing reports from customers this year? Most Nigerian fintechs experience at least one before they address authentication.",
                "step3":   "Last note from me on this — ThreatFade detected the gap, and the fix is a 5-minute DNS change. Happy to walk your team through it on a call, or send the exact records to add.",
                "step4":   "Closing the loop. If the timing isn't right, I'll follow up after Q4 audit season. Good luck with the CBN review.",
                "cta":     "Worth a 15-minute call to review what we found?",
            }
        ]
    },

    "african_dev_agency": {
        "name":       "African Dev Agency",
        "emoji":      "🌍",
        "market_size":"$4.5B African tech services market",
        "best_products": ["Web-Temify", "FadeReach", "Olvrix", "HezCast"],
        "icp": {
            "titles":      ["Founder", "CEO", "CTO", "Head of Design",
                            "Lead Developer", "Technical Director"],
            "company_types": ["software agency", "web development company",
                              "digital studio", "IT consultancy", "design agency"],
            "size":        "2-50 employees",
            "funding":     "Bootstrapped",
            "keywords":    ["build", "clients", "projects", "agency", "studio",
                            "developers", "design", "web app", "mobile"],
            "location":    ["Lagos", "Accra", "Nairobi", "Cape Town", "Kampala",
                            "Kigali", "Dakar", "Johannesburg"],
        },
        "pain_points": [
            "Client acquisition is unpredictable — feast or famine",
            "Quoting projects takes time without good templates",
            "Team spends 40% of time on non-billable setup work",
            "Competition from offshore agencies undercuts on price",
            "No system for consistent lead generation",
            "Managing multiple clients manually in spreadsheets",
        ],
        "objections": {
            "We get clients through referrals": "Referrals are great but they're not predictable. FadeReach lets you build a second acquisition channel without hiring a salesperson.",
            "No time for outreach": "FadeReach runs the sequences automatically once set up. Your team spends 2 hours on setup, then monitors replies.",
            "Our clients don't respond to cold email": "The mistake most agencies make is targeting the wrong signal. Companies posting DevOps or engineering jobs right now are actively buying agency services — that's who to email.",
        },
        "timing": {
            "best_days":   ["Tuesday", "Wednesday"],
            "best_hours":  "9:00–11:00 local time",
            "trigger_events": [
                "Company posts developer job listing (buying signal)",
                "New product launch announcement",
                "Funding round closes",
                "Leadership hire announcement",
                "Website redesign (detectable via tech stack change)",
            ]
        },
        "cultural_context": [
            "Pan-African positioning works well — don't assume only Nigerian buyers",
            "Emphasize local understanding — many global tools don't understand African market context",
            "Pricing in local currency builds trust significantly",
            "Reference known African tech success stories as proof",
        ],
        "sample_sequences": [
            {
                "name":    "Job posting signal",
                "trigger": "Company posts developer hiring listing",
                "step1":   "Noticed {company} is hiring developers — agencies scaling teams often hit the same client acquisition wall at the same time. Worth sharing something that's worked for similar agencies in Lagos/Accra?",
                "cta":     "10 minutes to show you what we see working for African dev agencies right now?",
            }
        ]
    },

    "eu_security_team": {
        "name":       "EU Security Team",
        "emoji":      "🇪🇺",
        "market_size":"€45B EU cybersecurity market",
        "best_products": ["ThreatFade", "KalevioAI", "TwinGuard", "AI Shield", "FadeForge"],
        "icp": {
            "titles":      ["CISO", "Head of Security", "Security Architect",
                            "SOC Manager", "Compliance Officer", "NIS2 Lead",
                            "DORA Compliance Manager", "Threat Intelligence Lead"],
            "company_types": ["bank", "insurance company", "critical infrastructure",
                              "healthcare provider", "energy company", "government agency",
                              "EU enterprise", "financial institution"],
            "size":        "200-10,000 employees",
            "funding":     "Established",
            "keywords":    ["NIS2", "DORA", "GDPR", "ISO 27001", "SOC 2",
                            "threat intelligence", "SIEM", "EDR", "incident response"],
            "location":    ["Germany", "France", "Netherlands", "Sweden", "Finland",
                            "Denmark", "Belgium", "Austria", "Ireland"],
        },
        "pain_points": [
            "NIS2 implementation deadline pressure (active enforcement 2024–2026)",
            "DORA technical requirements for ICT risk management",
            "Alert fatigue — SOC teams drowning in false positives",
            "C2 beacons bypassing SIEM rules",
            "EU AI Act compliance for AI-powered security tools",
            "Supply chain security across third-party vendors",
        ],
        "regulatory_context": {
            "NIS2": {
                "deadline":  "October 2024 enforcement began — ongoing",
                "article_21":"Risk management measures including email authentication",
                "penalties": "Up to €10M or 2% global turnover",
                "trigger":   "Use in step 2 as urgency mechanism after no reply to step 1",
            },
            "DORA": {
                "deadline":  "January 17, 2025 — active enforcement",
                "scope":     "EU financial institutions and ICT service providers",
                "article_9": "ICT risk management framework documentation",
                "trigger":   "KalevioAI + ThreatFade combination pitch",
            },
            "EU_AI_Act": {
                "high_risk": "AI systems in critical infrastructure, biometrics, credit scoring",
                "article_9": "Risk management system documentation required",
                "trigger":   "TwinGuard + AI Shield pitch for AI-deploying enterprises",
            }
        },
        "timing": {
            "best_days":   ["Tuesday", "Wednesday", "Thursday"],
            "best_hours":  "08:30–10:00 CET/CEST",
            "avoid":       ["Summer (July–August reduced capacity)", "December",
                            "Around major EU conferences"],
            "trigger_events": [
                "NIS2 audit season",
                "DORA compliance reporting deadlines",
                "Security incident in their sector (news)",
                "New CISO hired",
                "Major product launch (expanded attack surface)",
                "Regulatory fine issued to competitor",
            ]
        },
        "cultural_context": [
            "EU buyers are formal — use proper titles and full names",
            "GDPR awareness is high — lead with data privacy and sovereignty",
            "Reference specific EU regulations accurately (don't get dates wrong)",
            "German buyers especially value technical precision over marketing language",
            "Nordic buyers respond to transparency and directness",
            "Case studies from EU companies build credibility fastest",
        ],
        "sample_sequences": [
            {
                "name":    "NIS2 compliance angle",
                "trigger": "Company in NIS2-regulated sector",
                "step1":   "NIS2 Article 21 requires documented measures for 'handling and disclosure of vulnerabilities' — most security teams at organizations like {company} have the policy but the technical implementation audit is where gaps emerge.",
                "step2":   "Quick follow-up — two questions worth 5 minutes: Is {company}'s NIS2 technical implementation documentation complete, and has your team run a gap assessment on email authentication infrastructure specifically?",
                "cta":     "Happy to share what we see most EU organizations miss — 15 minutes?",
            }
        ]
    },

    "us_proptech": {
        "name":       "US PropTech",
        "emoji":      "🇺🇸",
        "market_size":"$18B US proptech market",
        "best_products": ["RealtyScreen AI"],
        "icp": {
            "titles":      ["Property Manager", "Landlord", "Real Estate Investor",
                            "Leasing Director", "Operations Manager", "COO",
                            "Asset Manager", "Portfolio Manager"],
            "company_types": ["property management company", "real estate firm",
                              "multi-family operator", "commercial property group",
                              "REIT", "residential leasing company"],
            "size":        "50-500 units managed",
            "funding":     "Bootstrapped to PE-backed",
            "keywords":    ["tenant screening", "FCRA", "background check", "credit check",
                            "leasing", "vacancy", "eviction", "rental"],
            "location":    ["Texas", "Florida", "California", "New York", "Georgia",
                            "Arizona", "North Carolina", "Illinois"],
        },
        "pain_points": [
            "FCRA compliance violations are expensive — class action risk",
            "Manual screening takes 3-5 days — units sit vacant",
            "Inconsistent screening criteria creates fair housing risk",
            "Multiple screening vendors = multiple subscriptions",
            "Eviction rate increases without proper screening",
            "Fraudulent application documents hard to detect manually",
        ],
        "regulatory_context": {
            "FCRA": {
                "requirement": "Adverse action notices, permissible purpose, dispute resolution",
                "violations":  "Up to $1,000 per violation + attorney fees",
                "class_action":"Common — class action suits against property managers",
                "trigger":     "Lead with compliance risk, not just speed",
            }
        },
        "timing": {
            "best_days":   ["Tuesday", "Wednesday", "Thursday"],
            "best_hours":  "09:00–11:00 EST/CST",
            "avoid":       ["End of month (high leasing activity)", "Holidays"],
            "trigger_events": [
                "New property acquisition announced",
                "Portfolio expansion",
                "Hiring leasing staff",
                "FCRA lawsuit in the news",
                "Eviction moratorium changes",
            ]
        },
        "cultural_context": [
            "US property managers are time-poor — keep emails extremely short",
            "FCRA risk is the primary hook — compliance > features",
            "Reference specific state fair housing laws where relevant",
            "ROI framing works well — days vacancy = dollars lost",
            "Direct CTA performs better than soft asks",
        ],
        "sample_sequences": [
            {
                "name":    "FCRA compliance angle",
                "trigger": "Property management company in target state",
                "step1":   "Most property managers at {company}'s scale run FCRA risk without knowing it — the adverse action notice requirement alone accounts for 60% of class action filings we track. RealtyScreen AI handles this automatically.",
                "cta":     "Worth 15 minutes to see how we handle FCRA compliance automatically?",
            }
        ]
    }
}

class VerticalInsightReq(BaseModel):
    vertical:    str
    company:     str
    domain:      str
    title:       Optional[str] = None

@router.get("/packs")
async def list_vertical_packs(auth: dict = Depends(get_current_tenant)):
    """List all available vertical intelligence packs"""
    return {
        "packs": [
            {
                "id":           k,
                "name":         v["name"],
                "emoji":        v["emoji"],
                "market_size":  v["market_size"],
                "best_products":v["best_products"],
                "icp_titles":   v["icp"]["titles"][:4],
                "pain_points":  len(v["pain_points"]),
                "objections":   len(v["objections"]),
            }
            for k, v in VERTICAL_PACKS.items()
        ]
    }

@router.get("/packs/{vertical_id}")
async def get_vertical_pack(
    vertical_id: str,
    auth: dict = Depends(get_current_tenant),
):
    """Get complete vertical intelligence pack"""
    pack = VERTICAL_PACKS.get(vertical_id)
    if not pack:
        raise HTTPException(404, f"Vertical pack '{vertical_id}' not found. Available: {list(VERTICAL_PACKS.keys())}")
    return pack

@router.post("/packs/{vertical_id}/score-lead")
async def score_lead_against_vertical(
    vertical_id: str,
    req: VerticalInsightReq,
    auth: dict = Depends(get_current_tenant),
):
    """Score a specific lead against a vertical ICP definition"""
    pack = VERTICAL_PACKS.get(vertical_id)
    if not pack:
        raise HTTPException(404, f"Vertical '{vertical_id}' not found")

    icp   = pack["icp"]
    score = 0
    flags = []

    # Title match
    if req.title:
        title_lower = req.title.lower()
        for t in icp["titles"]:
            if t.lower() in title_lower:
                score += 25
                flags.append(f"Title match: {t}")
                break

    # Keyword match in domain/company
    text_to_check = f"{req.company} {req.domain}".lower()
    for kw in icp.get("keywords", []):
        if kw.lower() in text_to_check:
            score += 10
            flags.append(f"Keyword: {kw}")
            if score >= 60:
                break

    # Company type match
    for ct in icp.get("company_types", []):
        if any(word in text_to_check for word in ct.split()):
            score += 15
            flags.append(f"Company type: {ct}")
            break

    score     = min(score, 100)
    is_icp    = score >= 60
    best_seq  = pack.get("sample_sequences", [{}])[0] if pack.get("sample_sequences") else {}

    return {
        "vertical":     vertical_id,
        "company":      req.company,
        "icp_score":    score,
        "is_icp":       is_icp,
        "score_reasons":flags,
        "recommendation": "High fit — add to campaign" if score >= 80
            else "Good fit — add with personalization" if score >= 60
            else "Low fit — verify before adding",
        "suggested_sequence": best_seq.get("name"),
        "suggested_step1":    best_seq.get("step1","").replace("{company}", req.company),
        "best_products":      pack["best_products"],
        "pain_to_reference":  pack["pain_points"][0] if pack["pain_points"] else None,
    }

@router.get("/packs/{vertical_id}/timing")
async def get_vertical_timing(
    vertical_id: str,
    auth: dict = Depends(get_current_tenant),
):
    """Get optimal timing intelligence for a vertical"""
    pack = VERTICAL_PACKS.get(vertical_id)
    if not pack:
        raise HTTPException(404, f"Vertical '{vertical_id}' not found")
    return {
        "vertical":   vertical_id,
        "timing":     pack.get("timing", {}),
        "cultural":   pack.get("cultural_context", []),
        "regulatory": pack.get("regulatory_context", {}),
    }
