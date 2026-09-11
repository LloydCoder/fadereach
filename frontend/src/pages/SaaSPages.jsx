import { useState, useEffect, useCallback } from "react";

// ─────────────────────────────────────────────────────────
// FadeReach Phase 2 — SaaS Pages
// Pricing · Onboarding · Billing
// Same design tokens as App.jsx
// ─────────────────────────────────────────────────────────

const C = {
  void:    "#080C14",
  obs:     "#0E1420",
  slate:   "#131B2B",
  wire:    "#1A2540",
  signal:  "#00E5A0",
  signalD: "#00B87A",
  ember:   "#FF6B35",
  mist:    "#94A3B8",
  snow:    "#F0F4FF",
  red:     "#EF4444",
  amber:   "#F59E0B",
};

const S = {
  card: {
    background: C.obs,
    border: `1px solid ${C.wire}`,
    borderRadius: 12,
    padding: 22,
  },
  btn: (v = "primary") => ({
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: v === "sm" ? "6px 14px" : "11px 22px",
    fontSize: v === "sm" ? 12 : 13.5,
    fontWeight: 600,
    borderRadius: 8,
    border: "none",
    cursor: "pointer",
    transition: "opacity 0.15s, transform 0.1s",
    background: v === "ghost"
      ? "transparent"
      : v === "outline"
      ? `${C.signal}15`
      : C.signal,
    color: v === "ghost"
      ? C.mist
      : v === "outline"
      ? C.signal
      : "#000",
    border: v === "ghost" ? `1px solid ${C.wire}`
      : v === "outline" ? `1px solid ${C.signal}40`
      : "none",
    whiteSpace: "nowrap",
    textDecoration: "none",
    justifyContent: "center",
  }),
  label: {
    fontSize: 10,
    fontWeight: 700,
    color: C.signal,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    fontFamily: "'JetBrains Mono', monospace",
  },
  mono: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 12.5,
  },
  input: {
    background: C.slate,
    border: `1px solid ${C.wire}`,
    borderRadius: 8,
    padding: "9px 14px",
    color: C.snow,
    fontSize: 13.5,
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
    fontFamily: "inherit",
  },
};

const API_URL = typeof window !== "undefined"
  ? (window.location.hostname === "localhost" ? "http://localhost:8001" : "")
  : "";

function useApi() {
  const token = typeof window !== "undefined" ? localStorage.getItem("fr_token") : null;
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const get  = (path) => fetch(`${API_URL}${path}`, { headers }).then(r => r.json());
  const post = (path, body) => fetch(`${API_URL}${path}`, {
    method: "POST", headers, body: JSON.stringify(body)
  }).then(r => r.json());
  return { get, post };
}

// ═══════════════════════════════════════════════
// PRICING PAGE
// ═══════════════════════════════════════════════
export function PricingPage({ onNavigate }) {
  const { get, post } = useApi();
  const [plans,     setPlans]     = useState([]);
  const [billing,   setBilling]   = useState("monthly");
  const [currency,  setCurrency]  = useState("usd");
  const [loading,   setLoading]   = useState(true);
  const [checkingOut, setCheckingOut] = useState(null);
  const [toast,     setToast]     = useState(null);

  useEffect(() => {
    get(`/api/billing/plans?currency=${currency}&billing=${billing}`)
      .then(d => setPlans(d.plans || []))
      .finally(() => setLoading(false));
  }, [currency, billing]);

  const showToast = (msg, type = "success") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const checkout = async (planId, provider) => {
    setCheckingOut(`${planId}-${provider}`);
    try {
      const res = await post(`/api/billing/checkout/${provider}`, { plan_id: planId });
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      } else {
        showToast(res.detail || "Checkout failed", "error");
      }
    } catch {
      showToast("Connection error", "error");
    }
    setCheckingOut(null);
  };

  const currencySymbol = { usd: "$", ngn: "₦", eur: "€", gbp: "£" };
  const sym = currencySymbol[currency] || "$";

  const planColors = {
    early_adopter: C.signal,
    growth:        C.signal,
    agency:        "#818CF8",
    managed:       C.ember,
  };

  return (
    <div style={{ fontFamily: "'Inter', system-ui, sans-serif", color: C.snow }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');
        * { box-sizing: border-box; }
        button:hover { opacity: 0.87; }
        input:focus, select:focus { border-color: ${C.signal} !important; outline: none; }
      `}</style>

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 40 }}>
          <div style={{ ...S.label, marginBottom: 10 }}>Pricing</div>
          <h1 style={{
            fontFamily: "'Syne', sans-serif",
            fontWeight: 800, fontSize: 36,
            letterSpacing: "-0.04em", margin: "0 0 12px",
          }}>
            Honest pricing. No surprises.
          </h1>
          <p style={{ color: C.mist, fontSize: 15, margin: "0 0 28px", lineHeight: 1.6 }}>
            Every plan includes a 14-day free trial. No credit card needed. Cancel anytime.
          </p>

          {/* Toggles */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16, flexWrap: "wrap" }}>
            {/* Billing toggle */}
            <div style={{
              display: "flex", gap: 4,
              background: C.obs, border: `1px solid ${C.wire}`,
              borderRadius: 100, padding: 4,
            }}>
              {["monthly", "annual"].map(b => (
                <button key={b}
                  style={{
                    padding: "6px 16px", borderRadius: 100, border: "none",
                    fontSize: 12.5, fontWeight: 600, cursor: "pointer",
                    background: billing === b ? C.signal : "transparent",
                    color: billing === b ? "#000" : C.mist,
                    transition: "all 0.15s",
                  }}
                  onClick={() => setBilling(b)}
                >
                  {b === "monthly" ? "Monthly" : "Annual (2 months free)"}
                </button>
              ))}
            </div>

            {/* Currency selector */}
            <select
              style={{ ...S.input, width: "auto", padding: "7px 14px", fontSize: 13 }}
              value={currency}
              onChange={e => setCurrency(e.target.value)}
            >
              <option value="usd">USD $</option>
              <option value="ngn">NGN ₦</option>
              <option value="eur">EUR €</option>
              <option value="gbp">GBP £</option>
            </select>
          </div>
        </div>

        {/* Plan cards */}
        {loading ? (
          <div style={{ textAlign: "center", padding: 48, color: C.mist }}>Loading plans...</div>
        ) : (
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 16, marginBottom: 48,
          }}>
            {plans.map(plan => {
              const color    = planColors[plan.id] || C.signal;
              const isManaged = plan.id === "managed";

              return (
                <div key={plan.id} style={{
                  ...S.card,
                  position: "relative",
                  borderColor: plan.highlight ? C.signal
                    : isManaged ? `${C.ember}40`
                    : C.wire,
                  background: plan.highlight
                    ? `linear-gradient(160deg, ${C.signal}08, ${C.obs})`
                    : C.obs,
                  display: "flex", flexDirection: "column",
                }}>
                  {plan.badge && (
                    <div style={{
                      position: "absolute", top: -12, left: "50%",
                      transform: "translateX(-50%)",
                      background: plan.highlight ? C.signal : isManaged ? C.ember : C.wire,
                      color: plan.highlight || isManaged ? "#000" : C.snow,
                      fontSize: 9, fontWeight: 800,
                      padding: "3px 12px", borderRadius: 100,
                      letterSpacing: "0.1em",
                      fontFamily: "'JetBrains Mono', monospace",
                      whiteSpace: "nowrap",
                    }}>
                      {plan.badge}
                    </div>
                  )}

                  {/* Plan header */}
                  <div style={{ marginBottom: 20 }}>
                    <div style={{ ...S.label, color, marginBottom: 10 }}>{plan.name}</div>
                    <div style={{ display: "flex", alignItems: "flex-end", gap: 4, marginBottom: 4 }}>
                      <span style={{
                        fontFamily: "'Syne', sans-serif",
                        fontWeight: 800, fontSize: 36,
                        letterSpacing: "-0.04em", lineHeight: 1,
                        color: isManaged ? C.ember : C.snow,
                      }}>
                        {sym}{(billing === "annual" && plan.annual
                          ? Math.round(plan.annual / 12)
                          : plan.price
                        ).toLocaleString()}
                      </span>
                      <span style={{ fontSize: 12, color: C.mist, marginBottom: 6 }}>
                        /mo{billing === "annual" ? " (billed annually)" : ""}
                      </span>
                    </div>
                    <div style={{ fontSize: 12, color: C.mist }}>{plan.tagline}</div>
                  </div>

                  <hr style={{ border: "none", borderTop: `1px solid ${C.wire}`, margin: "0 0 18px" }} />

                  {/* Features */}
                  <ul style={{ listStyle: "none", margin: "0 0 24px", padding: 0, flex: 1 }}>
                    {plan.features.map((f, i) => (
                      <li key={i} style={{
                        display: "flex", alignItems: "flex-start", gap: 8,
                        fontSize: 13, color: C.mist, padding: "4px 0", lineHeight: 1.45,
                      }}>
                        <span style={{ color: color, fontSize: 12, marginTop: 1, flexShrink: 0 }}>✓</span>
                        {f}
                      </li>
                    ))}
                  </ul>

                  {/* CTA buttons */}
                  {isManaged ? (
                    <a href={plan.cta_url || "mailto:hello@fadereach.tinlance.com"}
                      style={{
                        ...S.btn("ghost"), width: "100%",
                        borderColor: `${C.ember}50`, color: C.ember,
                      }}>
                      {plan.cta}
                    </a>
                  ) : (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      {/* Primary: LemonSqueezy (global) */}
                      <button
                        style={{
                          ...S.btn(),
                          width: "100%",
                          background: plan.highlight ? C.signal : `${C.signal}15`,
                          color: plan.highlight ? "#000" : C.signal,
                          border: plan.highlight ? "none" : `1px solid ${C.signal}30`,
                        }}
                        onClick={() => checkout(plan.id, "lemonsqueezy")}
                        disabled={checkingOut === `${plan.id}-lemonsqueezy`}
                      >
                        {checkingOut === `${plan.id}-lemonsqueezy`
                          ? "Redirecting..."
                          : `${plan.cta} — Global`}
                      </button>

                      {/* Paystack: Africa */}
                      <button
                        style={{
                          ...S.btn("ghost"),
                          width: "100%", fontSize: 12,
                        }}
                        onClick={() => checkout(plan.id, "paystack")}
                        disabled={checkingOut === `${plan.id}-paystack`}
                      >
                        {checkingOut === `${plan.id}-paystack`
                          ? "Redirecting..."
                          : `Pay in NGN via Paystack`}
                      </button>

                      {/* Paddle: EU/UK (Agency+ only) */}
                      {(plan.id === "agency" || plan.id === "managed") && (
                        <button
                          style={{
                            ...S.btn("ghost"),
                            width: "100%", fontSize: 12,
                          }}
                          onClick={() => checkout(plan.id, "paddle")}
                          disabled={checkingOut === `${plan.id}-paddle`}
                        >
                          {checkingOut === `${plan.id}-paddle`
                            ? "Redirecting..."
                            : "EU/UK — Pay via Paddle (VAT included)"}
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Trust signals */}
        <div style={{
          display: "flex", justifyContent: "center",
          gap: 32, flexWrap: "wrap",
          fontSize: 12.5, color: C.mist,
        }}>
          {[
            "✓ 14-day free trial",
            "✓ No credit card needed",
            "✓ Paystack — pay in Naira",
            "✓ EU/UK VAT handled by Paddle",
            "✓ Cancel anytime",
          ].map(t => <span key={t}>{t}</span>)}
        </div>

        {/* FAQ */}
        <div style={{ marginTop: 56 }}>
          <h2 style={{
            fontFamily: "'Syne', sans-serif",
            fontWeight: 800, fontSize: 22,
            letterSpacing: "-0.03em",
            marginBottom: 24, textAlign: "center",
          }}>Common questions</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            {[
              {
                q: "Do I need a credit card for the trial?",
                a: "No. Start your 14-day trial with just your email. We ask for payment details when you upgrade.",
              },
              {
                q: "Can I pay in Naira?",
                a: "Yes. All plans are available in NGN via Paystack — bank transfer, USSD, card, and mobile money.",
              },
              {
                q: "What is BYOD?",
                a: "Bring Your Own Domain. You register a sending domain (separate from your main brand domain), and we guide you through DNS setup in under 5 minutes.",
              },
              {
                q: "What happens when my trial ends?",
                a: "Your account is preserved and you can still access your data. Sending is paused until you upgrade. No automatic charges.",
              },
              {
                q: "What is the Managed Growth tier?",
                a: "We run your entire outreach operation. Domain setup, warmup, lead building, email writing, campaign management, and weekly reports — done for you.",
              },
              {
                q: "Can I cancel anytime?",
                a: "Yes. Cancel from your billing page or email billing@fadereach.tinlance.com. No penalty, no questions. Managed Growth requires a 3-month minimum.",
              },
            ].map((faq, i) => (
              <div key={i} style={{ ...S.card }}>
                <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 8 }}>{faq.q}</div>
                <div style={{ fontSize: 13, color: C.mist, lineHeight: 1.65 }}>{faq.a}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div style={{
          position: "fixed", bottom: 24, right: 24, zIndex: 999,
          background: toast.type === "error" ? `${C.red}20` : `${C.signal}18`,
          border: `1px solid ${toast.type === "error" ? C.red : C.signal}`,
          borderRadius: 10, padding: "12px 18px",
          fontSize: 13.5, color: toast.type === "error" ? C.red : C.signal,
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// ONBOARDING WIZARD
// ═══════════════════════════════════════════════
export function OnboardingWizard({ onComplete, tenantName }) {
  const { get, post } = useApi();
  const [status,     setStatus]     = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [completing, setCompleting] = useState(null);

  const load = useCallback(() => {
    get("/api/onboarding/status")
      .then(setStatus)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, []);

  const completeStep = async (stepId) => {
    setCompleting(stepId);
    await post("/api/onboarding/complete-step", { step_id: stepId });
    load();
    setCompleting(null);
  };

  if (loading) return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "center",
      minHeight: "60vh", color: C.mist, fontFamily: "'Inter', sans-serif",
    }}>
      Setting up your workspace...
    </div>
  );

  if (!status) return null;

  if (status.all_done) {
    return (
      <div style={{
        minHeight: "60vh", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", textAlign: "center",
        fontFamily: "'Inter', sans-serif", color: C.snow, gap: 16,
      }}>
        <div style={{ fontSize: 48 }}>✦</div>
        <h2 style={{
          fontFamily: "'Syne', sans-serif", fontWeight: 800,
          fontSize: 28, letterSpacing: "-0.04em", margin: 0,
          color: C.signal,
        }}>
          You're ready to send.
        </h2>
        <p style={{ color: C.mist, fontSize: 14, maxWidth: 360, lineHeight: 1.65 }}>
          Setup complete. Your first campaign is built and warming up. Check your inbox for replies.
        </p>
        <button style={S.btn()} onClick={onComplete}>
          Go to dashboard →
        </button>
      </div>
    );
  }

  return (
    <div style={{
      fontFamily: "'Inter', system-ui, sans-serif",
      color: C.snow, maxWidth: 640, margin: "0 auto", padding: "32px 24px",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');
        * { box-sizing: border-box; }
        button:hover { opacity: 0.87; }
      `}</style>

      {/* Header */}
      <div style={{ marginBottom: 36 }}>
        <div style={{
          fontFamily: "'Syne', sans-serif", fontWeight: 800,
          fontSize: 22, letterSpacing: "-0.03em", marginBottom: 6,
        }}>
          Welcome{tenantName ? `, ${tenantName.split(" ")[0]}` : ""}. ✦
        </div>
        <div style={{ fontSize: 13.5, color: C.mist, marginBottom: 20 }}>
          {status.message}
        </div>

        {/* Progress bar */}
        <div>
          <div style={{
            display: "flex", justifyContent: "space-between",
            fontSize: 11, color: C.mist, marginBottom: 6,
          }}>
            <span>Setup progress</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", color: C.signal }}>
              {status.steps_done}/{status.steps_total} steps
            </span>
          </div>
          <div style={{ height: 5, background: C.wire, borderRadius: 3 }}>
            <div style={{
              height: "100%",
              width: `${status.progress}%`,
              background: C.signal, borderRadius: 3,
              transition: "width 0.8s ease",
            }} />
          </div>
        </div>
      </div>

      {/* Steps */}
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {(status.steps || []).map((step, i) => (
          <div key={step.id} style={{
            ...S.card,
            borderColor: step.is_next ? `${C.signal}50`
              : step.completed ? `${C.signal}20`
              : C.wire,
            background: step.is_next
              ? `linear-gradient(135deg, ${C.signal}06, ${C.obs})`
              : step.completed ? `${C.signal}04`
              : C.obs,
            opacity: !step.completed && !step.is_next ? 0.55 : 1,
          }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
              {/* Step indicator */}
              <div style={{
                width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
                background: step.completed ? C.signal
                  : step.is_next ? `${C.signal}20`
                  : C.wire,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: step.completed ? 14 : 12,
                color: step.completed ? "#000" : step.is_next ? C.signal : C.mist,
                fontWeight: 700,
                fontFamily: "'JetBrains Mono', monospace",
              }}>
                {step.completed ? "✓" : i + 1}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
                      {step.title}
                    </div>
                    <div style={{ fontSize: 12.5, color: C.mist, lineHeight: 1.6, marginBottom: step.tip ? 8 : 0 }}>
                      {step.description}
                    </div>
                    {step.tip && step.is_next && (
                      <div style={{
                        padding: "6px 10px",
                        background: `${C.signal}10`,
                        borderLeft: `2px solid ${C.signal}`,
                        borderRadius: "0 6px 6px 0",
                        fontSize: 11.5, color: C.signal,
                        lineHeight: 1.5,
                      }}>
                        Tip: {step.tip}
                      </div>
                    )}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0, marginLeft: 12 }}>
                    {step.time_est && !step.completed && (
                      <span style={{
                        fontSize: 10, color: C.mist,
                        fontFamily: "'JetBrains Mono', monospace",
                      }}>
                        ~{step.time_est}
                      </span>
                    )}
                    {step.cta && !step.completed && step.is_next && (
                      <button
                        style={S.btn("sm")}
                        onClick={() => {
                          completeStep(step.id);
                          if (onComplete && step.cta_url) {
                            onComplete(step.cta_url);
                          }
                        }}
                        disabled={completing === step.id}
                      >
                        {completing === step.id ? "..." : step.cta}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Skip option */}
      <div style={{ textAlign: "center", marginTop: 24 }}>
        <button style={{ ...S.btn("ghost"), fontSize: 12 }} onClick={onComplete}>
          Skip setup — go to dashboard
        </button>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════
// BILLING MANAGEMENT PAGE
// ═══════════════════════════════════════════════
export function BillingPage() {
  const { get } = useApi();
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get("/api/billing/current")
      .then(setBilling)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ padding: 48, textAlign: "center", color: C.mist, fontFamily: "'Inter', sans-serif" }}>
      Loading billing info...
    </div>
  );

  if (!billing) return null;

  const statusColor = s =>
    s === "active" ? C.signal
    : s === "trial" ? C.amber
    : s === "cancelled" ? C.mist
    : C.red;

  return (
    <div style={{ fontFamily: "'Inter', system-ui, sans-serif", color: C.snow }}>
      <style>{`* { box-sizing: border-box; }`}</style>

      <div style={{ marginBottom: 24 }}>
        <div style={{
          fontSize: 10, fontWeight: 700, color: C.signal,
          letterSpacing: "0.12em", textTransform: "uppercase",
          fontFamily: "'JetBrains Mono', monospace", marginBottom: 6,
        }}>Account</div>
        <h1 style={{
          margin: 0, fontSize: 22, fontWeight: 800,
          fontFamily: "'Syne', sans-serif", letterSpacing: "-0.03em",
        }}>Billing</h1>
      </div>

      {/* Current plan */}
      <div style={{
        ...S.card, marginBottom: 16,
        background: `linear-gradient(135deg, ${C.obs}, #0A1220)`,
        border: `1px solid ${C.signal}30`,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{
              fontSize: 10, fontWeight: 700, color: C.signal,
              letterSpacing: "0.12em", textTransform: "uppercase",
              fontFamily: "'JetBrains Mono', monospace", marginBottom: 8,
            }}>Current plan</div>
            <div style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 22, marginBottom: 4 }}>
              {billing.plan_name}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{
                display: "inline-flex", padding: "2px 9px",
                borderRadius: 20, fontSize: 10, fontWeight: 700,
                background: `${statusColor(billing.status)}18`,
                color: statusColor(billing.status),
                fontFamily: "'JetBrains Mono', monospace",
                textTransform: "uppercase",
              }}>
                {billing.status.replace(/_/g, " ")}
              </span>
              {billing.trial_days_left !== null && billing.trial_days_left !== undefined && (
                <span style={{ fontSize: 12, color: C.amber }}>
                  {billing.trial_days_left} days left in trial
                </span>
              )}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 24, fontWeight: 800, color: C.signal,
            }}>
              ${billing.price_usd}/mo
            </div>
            <div style={{ fontSize: 11, color: C.mist }}>
              ₦{(billing.price_ngn || 0).toLocaleString()}/mo via Paystack
            </div>
          </div>
        </div>
      </div>

      {/* Payment methods */}
      <div style={{ ...S.card, marginBottom: 16 }}>
        <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 16 }}>Payment options</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[
            {
              name: "LemonSqueezy",
              desc: "Global — USD, cards, PayPal",
              url: "https://app.lemonsqueezy.com/my-orders",
              flag: "🌍",
            },
            {
              name: "Paystack",
              desc: "Africa — NGN, bank transfer, USSD, mobile money",
              url: "https://paystack.com/pay",
              flag: "🇳🇬",
            },
            {
              name: "Paddle",
              desc: "EU/UK — EUR/GBP, VAT handled automatically",
              url: "https://customer.paddle.com",
              flag: "🇪🇺",
            },
          ].map(p => (
            <a key={p.name} href={p.url} target="_blank" rel="noopener noreferrer"
              style={{
                display: "flex", alignItems: "center", gap: 12,
                padding: "12px 16px",
                background: C.slate, borderRadius: 8,
                border: `1px solid ${C.wire}`,
                textDecoration: "none", color: C.snow,
                transition: "border-color 0.15s",
              }}
            >
              <span style={{ fontSize: 20 }}>{p.flag}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{p.name}</div>
                <div style={{ fontSize: 11.5, color: C.mist }}>{p.desc}</div>
              </div>
              <span style={{ color: C.mist, fontSize: 12 }}>Manage →</span>
            </a>
          ))}
        </div>
      </div>

      {/* Billing history */}
      {(billing.billing_events || []).length > 0 && (
        <div style={S.card}>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 16 }}>Billing history</div>
          {billing.billing_events.map((e, i) => (
            <div key={i} style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "10px 0", borderBottom: `1px solid ${C.wire}`,
              fontSize: 13,
            }}>
              <div>
                <div style={{ fontWeight: 500 }}>
                  {e.event_type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())}
                </div>
                <div style={{ fontSize: 11, color: C.mist, marginTop: 2 }}>
                  {e.provider} · {new Date(e.created_at).toLocaleDateString()}
                </div>
              </div>
              {e.amount && (
                <div style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontWeight: 700, color: C.signal,
                }}>
                  ${parseFloat(e.amount).toFixed(2)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upgrade CTA if on trial */}
      {billing.status === "trial" && (
        <div style={{
          ...S.card, marginTop: 16,
          background: `${C.signal}08`,
          border: `1px solid ${C.signal}30`,
          textAlign: "center",
          padding: 28,
        }}>
          <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>
            Ready to upgrade?
          </div>
          <div style={{ fontSize: 13, color: C.mist, marginBottom: 16 }}>
            Remove trial limits and unlock your full outreach engine.
          </div>
          <a href="/pricing" style={S.btn()}>
            View plans →
          </a>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// UPGRADE BANNER (dashboard widget)
// ═══════════════════════════════════════════════
export function UpgradeBanner({ plan, daysLeft, onUpgrade }) {
  if (plan !== "trial" || !daysLeft) return null;

  const urgent = daysLeft <= 3;

  return (
    <div style={{
      padding: "12px 18px",
      background: urgent ? `${C.ember}12` : `${C.signal}10`,
      border: `1px solid ${urgent ? C.ember : C.signal}30`,
      borderRadius: 10,
      display: "flex", alignItems: "center",
      justifyContent: "space-between", gap: 12,
      marginBottom: 20,
      fontFamily: "'Inter', sans-serif",
    }}>
      <div style={{ fontSize: 13, color: urgent ? C.ember : C.signal }}>
        {urgent
          ? `⚠️ Trial ends in ${daysLeft} day${daysLeft !== 1 ? "s" : ""} — upgrade to keep sending`
          : `✦ ${daysLeft} days left in trial — sending pauses when it ends`}
      </div>
      <button
        style={{
          ...S.btn("sm"),
          background: urgent ? C.ember : C.signal,
          color: "#000",
          flexShrink: 0,
        }}
        onClick={onUpgrade}
      >
        Upgrade now
      </button>
    </div>
  );
}
