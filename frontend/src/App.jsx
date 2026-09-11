import { useState, useEffect, useCallback } from "react";

// ─────────────────────────────────────────────────────────────
// DESIGN BRIEF
// Product: FadeReach — cold email OS for African founders
// Audience: Solo founders, agencies, dev shops
// Single job: Get leads → send campaigns → track replies
//
// DESIGN PLAN
// Palette:
//   Void      #080C14  deepest bg
//   Obsidian  #0E1420  card bg
//   Slate     #131B2B  surface
//   Wire      #1A2540  border
//   Signal    #00E5A0  primary accent (electric teal)
//   Ember     #FF6B35  urgency / hot leads
//   Mist      #94A3B8  muted text
//   Snow      #F0F4FF  primary text
//
// Type:
//   Syne 800    → page titles, nav logo (assertive, geometric)
//   Inter 400/600 → body, labels (clean utility)
//   JetBrains Mono → stats, codes, DNS values (precision data)
//
// Signature element:
//   The Deliverability Copilot ring — a single animated arc that
//   fills from 0→score on mount. Not a chart. Not a progress bar.
//   A single decisive number with a breathing glow. Every other
//   metric defers to it. It answers: "Will my email land?"
// ─────────────────────────────────────────────────────────────

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
  white:   "#FFFFFF",
  red:     "#EF4444",
  amber:   "#F59E0B",
};

// ── API layer ───────────────────────────────────────────────
const API_URL = typeof window !== "undefined"
  ? (window.location.hostname === "localhost" ? "http://localhost:8001" : "/api")
  : "/api";

function useApi() {
  const token = typeof window !== "undefined" ? localStorage.getItem("fr_token") : null;
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const get  = (path) => fetch(`${API_URL}${path}`, { headers }).then(r => r.json());
  const post = (path, body) => fetch(`${API_URL}${path}`, { method:"POST", headers, body: JSON.stringify(body) }).then(r => r.json());
  return { get, post };
}

// ── Inline styles ───────────────────────────────────────────
const S = {
  app: {
    fontFamily: "'Inter', system-ui, sans-serif",
    background: C.void,
    color: C.snow,
    minHeight: "100vh",
    display: "flex",
    WebkitFontSmoothing: "antialiased",
  },
  sidebar: {
    width: 220,
    background: C.obs,
    borderRight: `1px solid ${C.wire}`,
    display: "flex",
    flexDirection: "column",
    flexShrink: 0,
    position: "fixed",
    top: 0, bottom: 0, left: 0,
    zIndex: 50,
    overflowY: "auto",
  },
  main: {
    marginLeft: 220,
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minHeight: "100vh",
  },
  topbar: {
    height: 56,
    background: C.obs,
    borderBottom: `1px solid ${C.wire}`,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 28px",
    position: "sticky",
    top: 0,
    zIndex: 40,
    flexShrink: 0,
  },
  content: {
    flex: 1,
    padding: "28px",
    overflowY: "auto",
  },
  card: {
    background: C.obs,
    border: `1px solid ${C.wire}`,
    borderRadius: 12,
    padding: 22,
  },
  navItem: (active) => ({
    display: "flex",
    alignItems: "center",
    gap: 9,
    padding: "9px 18px",
    fontSize: 13,
    fontWeight: active ? 600 : 400,
    color: active ? C.snow : C.mist,
    background: active ? `${C.signal}12` : "transparent",
    borderLeft: `2px solid ${active ? C.signal : "transparent"}`,
    cursor: "pointer",
    transition: "all 0.15s",
    textDecoration: "none",
    userSelect: "none",
  }),
  btn: (v="primary") => ({
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    padding: v === "sm" ? "6px 14px" : "10px 20px",
    fontSize: v === "sm" ? 12 : 13.5,
    fontWeight: 600,
    borderRadius: 8,
    border: "none",
    cursor: "pointer",
    transition: "opacity 0.15s, transform 0.1s",
    background: v === "ghost"
      ? "transparent"
      : v === "danger"
      ? `${C.red}20`
      : C.signal,
    color: v === "ghost"
      ? C.mist
      : v === "danger"
      ? C.red
      : "#000",
    border: v === "ghost" ? `1px solid ${C.wire}` : "none",
    whiteSpace: "nowrap",
  }),
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
  badge: (color, bg) => ({
    display: "inline-flex",
    alignItems: "center",
    padding: "2px 9px",
    borderRadius: 20,
    fontSize: 10.5,
    fontWeight: 700,
    background: bg || `${color}18`,
    color: color,
    fontFamily: "'JetBrains Mono', monospace",
    letterSpacing: "0.06em",
    textTransform: "uppercase",
  }),
  mono: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 12.5,
  },
  label: {
    fontSize: 10,
    fontWeight: 700,
    color: C.signal,
    letterSpacing: "0.12em",
    textTransform: "uppercase",
    fontFamily: "'JetBrains Mono', monospace",
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: 700,
    fontFamily: "'Syne', sans-serif",
    letterSpacing: "-0.02em",
    margin: "0 0 18px",
  },
  divider: {
    height: 1,
    background: C.wire,
    margin: "18px 0",
    border: "none",
  },
};

// ── Tiny components ─────────────────────────────────────────
const Mono = ({ children, color, size }) => (
  <span style={{ ...S.mono, color: color || C.mist, fontSize: size || 12.5 }}>
    {children}
  </span>
);

const Badge = ({ children, color = C.signal }) => (
  <span style={S.badge(color)}>{children}</span>
);

const EmptyState = ({ icon, title, body, action }) => (
  <div style={{
    display: "flex", flexDirection: "column", alignItems: "center",
    justifyContent: "center", padding: "48px 24px", textAlign: "center", gap: 12,
  }}>
    <div style={{ fontSize: 32 }}>{icon}</div>
    <div style={{ fontWeight: 600, fontSize: 15 }}>{title}</div>
    <div style={{ color: C.mist, fontSize: 13, maxWidth: 320, lineHeight: 1.6 }}>{body}</div>
    {action}
  </div>
);

const Toast = ({ msg, type = "success", onClose }) => {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, []);
  return (
    <div style={{
      position: "fixed", bottom: 24, right: 24, zIndex: 999,
      background: type === "error" ? `${C.red}20` : `${C.signal}18`,
      border: `1px solid ${type === "error" ? C.red : C.signal}`,
      borderRadius: 10, padding: "12px 18px",
      fontSize: 13.5, color: type === "error" ? C.red : C.signal,
      maxWidth: 340, boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
    }}>
      {type === "success" ? "✓ " : "✕ "}{msg}
    </div>
  );
};

// ── SIGNATURE: Deliverability Copilot Ring ───────────────────
const CopilotRing = ({ score = 0, label = "Inbox probability" }) => {
  const [displayed, setDisplayed] = useState(0);
  useEffect(() => {
    let current = 0;
    const step = () => {
      current = Math.min(score, current + 2);
      setDisplayed(current);
      if (current < score) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [score]);

  const r    = 44;
  const circ = 2 * Math.PI * r;
  const fill = (displayed / 100) * circ;
  const color = displayed >= 85 ? C.signal : displayed >= 65 ? C.amber : C.red;
  const grade = displayed >= 90 ? "A" : displayed >= 75 ? "B" : displayed >= 60 ? "C" : "D";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
      <div style={{ position: "relative", width: 110, height: 110, flexShrink: 0 }}>
        <svg width="110" height="110" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="55" cy="55" r={r} fill="none" stroke={C.wire} strokeWidth="7" />
          <circle cx="55" cy="55" r={r} fill="none"
            stroke={color} strokeWidth="7"
            strokeDasharray={`${fill} ${circ}`}
            strokeLinecap="round"
            style={{ transition: "stroke 0.3s" }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
        }}>
          <span style={{
            fontSize: 26, fontWeight: 800, color,
            fontFamily: "'JetBrains Mono', monospace",
            lineHeight: 1,
          }}>{displayed}</span>
          <span style={{
            fontSize: 13, fontWeight: 700, color,
            fontFamily: "'Syne', sans-serif",
          }}>{grade}</span>
        </div>
      </div>
      <div>
        <div style={{ fontSize: 11, color: C.mist, marginBottom: 4, ...S.label }}>
          {label}
        </div>
        <div style={{ fontSize: 22, fontWeight: 800, color, fontFamily: "'Syne', sans-serif" }}>
          {displayed}% inbox rate
        </div>
        <div style={{ fontSize: 12.5, color: C.mist, marginTop: 4, lineHeight: 1.5 }}>
          {displayed >= 85
            ? "Strong — keep monitoring daily"
            : displayed >= 65
            ? "Needs attention — fix issues below"
            : "Critical — pause campaigns now"}
        </div>
      </div>
    </div>
  );
};

// ── Stat card ────────────────────────────────────────────────
const StatCard = ({ label, value, sub, color, mono, trend }) => (
  <div style={{ ...S.card, flex: 1, minWidth: 0 }}>
    <div style={{ ...S.label, marginBottom: 8 }}>{label}</div>
    <div style={{
      fontSize: 28, fontWeight: 800, lineHeight: 1,
      color: color || C.snow,
      fontFamily: mono ? "'JetBrains Mono', monospace" : "'Syne', sans-serif",
      letterSpacing: "-0.02em",
      marginBottom: 4,
    }}>{value}</div>
    {sub && <div style={{ fontSize: 12, color: C.mist }}>{sub}</div>}
    {trend && (
      <div style={{ fontSize: 11, color: trend > 0 ? C.signal : C.red, marginTop: 4 }}>
        {trend > 0 ? "↑" : "↓"} {Math.abs(trend)}% vs last week
      </div>
    )}
  </div>
);

// ── DNS status row ───────────────────────────────────────────
const DNSRow = ({ record, valid, value, fix }) => (
  <div style={{
    display: "flex", alignItems: "flex-start", gap: 12,
    padding: "12px 0", borderBottom: `1px solid ${C.wire}`,
  }}>
    <div style={{
      width: 22, height: 22, borderRadius: "50%", flexShrink: 0, marginTop: 1,
      background: valid ? `${C.signal}18` : `${C.red}18`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 11, color: valid ? C.signal : C.red, fontWeight: 700,
    }}>
      {valid ? "✓" : "✕"}
    </div>
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>{record}</div>
      {value && (
        <div style={{ ...S.mono, color: C.mist, fontSize: 11, wordBreak: "break-all" }}>
          {value}
        </div>
      )}
      {!valid && fix && (
        <div style={{
          marginTop: 6, padding: "6px 10px",
          background: `${C.ember}10`, borderRadius: 6,
          fontSize: 11.5, color: C.ember, lineHeight: 1.5,
        }}>
          Fix: {fix}
        </div>
      )}
    </div>
    <Badge color={valid ? C.signal : C.red}>{valid ? "PASS" : "FAIL"}</Badge>
  </div>
);

// ── Warmup progress bar ──────────────────────────────────────
const WarmupBar = ({ day = 0, limit = 5 }) => {
  const pct   = Math.min((day / 35) * 100, 100);
  const color = pct < 30 ? C.amber : pct < 70 ? C.signal : C.signal;
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 12 }}>
        <span style={{ color: C.mist }}>Warmup day {day}/35</span>
        <span style={{ color, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}>
          {limit}/day
        </span>
      </div>
      <div style={{ height: 5, background: C.wire, borderRadius: 3 }}>
        <div style={{
          height: "100%", width: `${pct}%`, background: color,
          borderRadius: 3, transition: "width 1s ease",
        }} />
      </div>
    </div>
  );
};

// ── Intent pill ──────────────────────────────────────────────
const IntentPill = ({ intent }) => {
  const map = {
    interested:     [C.signal, "Interested"],
    more_info:      [C.signalD, "Wants info"],
    referral:       ["#818CF8", "Referral"],
    not_now:        [C.amber, "Not now"],
    not_interested: [C.red, "Not interested"],
    out_of_office:  [C.mist, "OOO"],
    unknown:        [C.mist, "Unknown"],
  };
  const [color, label] = map[intent] || [C.mist, intent];
  return <Badge color={color}>{label}</Badge>;
};

// ═══════════════════════════════════════════════════════════
// VIEWS
// ═══════════════════════════════════════════════════════════

// ── Overview ─────────────────────────────────────────────────
function OverviewView() {
  const { get } = useApi();
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get("/api/analytics/overview")
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  const d = data || {};
  const rates = d.rates || {};
  const totals = d.totals || {};
  const domains = d.domains || [];
  const benchmarks = d.benchmarks || {};

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.label, marginBottom: 6 }}>FadeReach</div>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, fontFamily: "'Syne', sans-serif", letterSpacing: "-0.03em" }}>
          Overview
        </h1>
        <div style={{ color: C.mist, fontSize: 13, marginTop: 4 }}>
          {totals.active_campaigns || 0} active campaigns ·{" "}
          {totals.hot_leads || 0} hot leads waiting
        </div>
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 14, marginBottom: 20, flexWrap: "wrap" }}>
        <StatCard
          label="Emails sent"
          value={(totals.total_sent || 0).toLocaleString()}
          sub="all time"
          mono
        />
        <StatCard
          label="Open rate"
          value={`${rates.open_rate || 0}%`}
          sub={`Industry avg ${benchmarks.open_rate?.industry || 21.3}%`}
          color={(rates.open_rate || 0) > 21 ? C.signal : C.amber}
          mono
        />
        <StatCard
          label="Reply rate"
          value={`${rates.reply_rate || 0}%`}
          sub={`Industry avg ${benchmarks.reply_rate?.industry || 3.4}%`}
          color={(rates.reply_rate || 0) > 3.4 ? C.signal : C.amber}
          mono
        />
        <StatCard
          label="Bounce rate"
          value={`${rates.bounce_rate || 0}%`}
          sub="Limit: 2.0%"
          color={(rates.bounce_rate || 0) < 1.5 ? C.signal : C.red}
          mono
        />
        <StatCard
          label="Hot leads"
          value={totals.hot_leads || 0}
          sub="replies flagged interested"
          color={C.ember}
        />
      </div>

      {/* Domain health */}
      {domains.length > 0 && (
        <div style={{ ...S.card, marginBottom: 20 }}>
          <h3 style={{ ...S.sectionTitle, margin: "0 0 16px" }}>Domain health</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {domains.map((d, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 16,
                padding: "12px 0",
                borderBottom: i < domains.length - 1 ? `1px solid ${C.wire}` : "none",
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13.5, marginBottom: 4 }}>
                    {d.domain}
                  </div>
                  <WarmupBar day={d.warmup_day || 0} limit={d.daily_limit || 5} />
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{
                    fontSize: 22, fontWeight: 800,
                    color: (d.health_score || 0) >= 80 ? C.signal : C.amber,
                    fontFamily: "'JetBrains Mono', monospace",
                  }}>
                    {d.health_score || 0}
                  </div>
                  <div style={{ fontSize: 10, color: C.mist }}>health score</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Intent breakdown */}
      {(d.intent_breakdown || []).length > 0 && (
        <div style={S.card}>
          <h3 style={{ ...S.sectionTitle, margin: "0 0 16px" }}>Reply breakdown</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {(d.intent_breakdown || []).map((item, i) => (
              <div key={i} style={{
                ...S.card, padding: "12px 18px",
                display: "flex", alignItems: "center", gap: 10,
              }}>
                <IntentPill intent={item.intent} />
                <span style={{
                  fontSize: 18, fontWeight: 800,
                  fontFamily: "'JetBrains Mono', monospace",
                }}>{item.count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!data && (
        <EmptyState
          icon="📊"
          title="No data yet"
          body="Launch your first campaign to see analytics here."
        />
      )}
    </div>
  );
}

// ── Domains ──────────────────────────────────────────────────
function DomainsView({ onToast }) {
  const { get, post } = useApi();
  const [domains,  setDomains]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [adding,   setAdding]   = useState(false);
  const [newDomain,setNewDomain]= useState("");
  const [copilot,  setCopilot]  = useState(null);
  const [checking, setChecking] = useState(null);

  const load = useCallback(() => {
    get("/api/domains")
      .then(d => setDomains(d.domains || []))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, []);

  const addDomain = async () => {
    if (!newDomain.trim()) return;
    setAdding(true);
    const res = await post("/api/domains/add", { domain: newDomain.trim() });
    if (res.domain_id) {
      onToast("Domain added — checking DNS...");
      setNewDomain("");
      setTimeout(load, 3000);
    } else {
      onToast(res.detail || "Failed to add domain", "error");
    }
    setAdding(false);
  };

  const checkCopilot = async (id) => {
    setChecking(id);
    const res = await get(`/api/domains/${id}/copilot`);
    setCopilot(res);
    setChecking(null);
  };

  const recheck = async (id) => {
    setChecking(id);
    await post(`/api/domains/${id}/check`, {});
    onToast("DNS re-check started");
    setTimeout(load, 2000);
    setChecking(null);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ ...S.label, marginBottom: 6 }}>Sending infrastructure</div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, fontFamily: "'Syne', sans-serif", letterSpacing: "-0.03em" }}>
            Domains
          </h1>
        </div>
      </div>

      {/* Add domain */}
      <div style={{ ...S.card, marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
          Add sending domain
        </div>
        <div style={{ fontSize: 12, color: C.mist, marginBottom: 14 }}>
          Use a domain you own — not tinlance.com. Keep your brand domain separate from cold outreach.
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <input
            style={S.input}
            placeholder="e.g. tinlance-reach.com"
            value={newDomain}
            onChange={e => setNewDomain(e.target.value)}
            onKeyDown={e => e.key === "Enter" && addDomain()}
          />
          <button style={S.btn()} onClick={addDomain} disabled={adding || !newDomain.trim()}>
            {adding ? "Adding..." : "Add domain"}
          </button>
        </div>
      </div>

      {/* Copilot panel */}
      {copilot && (
        <div style={{
          ...S.card, marginBottom: 20,
          border: `1px solid ${C.signal}30`,
          background: `linear-gradient(135deg, ${C.obs}, #0A1220)`,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
            <div>
              <div style={{ ...S.label, marginBottom: 6 }}>Deliverability Copilot</div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>{copilot.domain}</div>
            </div>
            <button style={S.btn("ghost")} onClick={() => setCopilot(null)}>✕</button>
          </div>

          <CopilotRing score={copilot.inbox_probability || 0} />

          {copilot.explanation && (
            <div style={{
              margin: "20px 0",
              padding: "14px 16px",
              background: C.slate,
              borderRadius: 8,
              fontSize: 13.5,
              lineHeight: 1.65,
              color: C.snow,
              borderLeft: `3px solid ${C.signal}`,
            }}>
              {copilot.explanation}
            </div>
          )}

          {/* DNS status */}
          <div style={{ marginBottom: 16 }}>
            {["spf", "dkim", "dmarc"].map(rec => {
              const dns   = copilot.dns_status || {};
              const valid = dns[rec];
              const fixes = {
                spf:   "Add TXT record: v=spf1 ip4:13.50.16.19 ~all",
                dkim:  "Run setup.sh → copy mail._domainkey TXT value",
                dmarc: "Add TXT to _dmarc: v=DMARC1; p=none; rua=mailto:dmarc@yourdomain",
              };
              return (
                <DNSRow key={rec}
                  record={rec.toUpperCase()}
                  valid={valid}
                  fix={!valid ? fixes[rec] : null}
                />
              );
            })}
          </div>

          {/* Issues */}
          {(copilot.issues || []).length > 0 && (
            <div>
              <div style={{ ...S.label, marginBottom: 10 }}>Issues to fix</div>
              {copilot.issues.map((issue, i) => (
                <div key={i} style={{
                  padding: "10px 14px", marginBottom: 8,
                  background: issue.severity === "critical"
                    ? `${C.red}10`
                    : issue.severity === "high"
                    ? `${C.amber}10`
                    : C.slate,
                  borderRadius: 8,
                  borderLeft: `3px solid ${
                    issue.severity === "critical" ? C.red
                    : issue.severity === "high" ? C.amber
                    : C.mist
                  }`,
                }}>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                    {issue.message}
                  </div>
                  <div style={{ fontSize: 12, color: C.mist }}>
                    {issue.fix}
                  </div>
                </div>
              ))}
            </div>
          )}

          {copilot.all_clear && (
            <div style={{
              padding: "12px 16px",
              background: `${C.signal}12`,
              border: `1px solid ${C.signal}30`,
              borderRadius: 8,
              fontSize: 13,
              color: C.signal,
              fontWeight: 600,
            }}>
              ✓ All clear — this domain is ready to send
            </div>
          )}
        </div>
      )}

      {/* Domain list */}
      {loading ? <Loader /> : domains.length === 0 ? (
        <EmptyState
          icon="🌐"
          title="No domains added yet"
          body="Add your first sending domain above. Use a dedicated domain, not tinlance.com."
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {domains.map(d => (
            <div key={d.id} style={S.card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                    <span style={{ fontWeight: 700, fontSize: 15, fontFamily: "'JetBrains Mono', monospace" }}>
                      {d.domain}
                    </span>
                    <Badge color={
                      d.warmup_status === "warming" ? C.signal
                      : d.warmup_status === "ready" ? C.signalD
                      : d.warmup_status === "dns_incomplete" ? C.amber
                      : C.mist
                    }>
                      {d.warmup_status || "checking"}
                    </Badge>
                  </div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {["spf_valid","dkim_valid","dmarc_valid"].map(k => (
                      <span key={k} style={{
                        fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
                        color: d[k] ? C.signal : C.red, fontWeight: 600,
                      }}>
                        {k.replace("_valid","").toUpperCase()} {d[k] ? "✓" : "✕"}
                      </span>
                    ))}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    style={S.btn("ghost")}
                    onClick={() => recheck(d.id)}
                    disabled={checking === d.id}
                  >
                    {checking === d.id ? "..." : "Re-check"}
                  </button>
                  <button
                    style={S.btn("sm")}
                    onClick={() => checkCopilot(d.id)}
                    disabled={checking === d.id}
                  >
                    Copilot
                  </button>
                </div>
              </div>
              <WarmupBar day={d.warmup_day || 0} limit={d.daily_limit || 5} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Leads ────────────────────────────────────────────────────
function LeadsView({ onToast }) {
  const { get, post } = useApi();
  const [leads,       setLeads]       = useState([]);
  const [loading,     setLoading]     = useState(false);
  const [searching,   setSearching]   = useState(false);
  const [generating,  setGenerating]  = useState(false);
  const [searchDomain,setSearchDomain]= useState("");
  const [product,     setProduct]     = useState("ThreatFade");
  const [searchResult,setSearchResult]= useState(null);
  const [selected,    setSelected]    = useState(new Set());

  const load = useCallback(() => {
    setLoading(true);
    get("/api/leads?limit=50")
      .then(d => setLeads(d.leads || []))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, []);

  const search = async () => {
    if (!searchDomain.trim()) return;
    setSearching(true);
    const res = await get(`/api/leads/search?company_domain=${encodeURIComponent(searchDomain)}&limit=10`);
    // Wait — search is POST
    const res2 = await post("/api/leads/search", { company_domain: searchDomain, limit: 10 });
    setSearchResult(res2);
    setSearching(false);
  };

  const generateFirstLines = async () => {
    const toProcess = leads.filter(l => selected.has(l.id) && !l.ai_first_line);
    if (!toProcess.length) {
      onToast("Select leads without first lines to generate", "error");
      return;
    }
    setGenerating(true);
    const res = await post("/api/leads/ai/first-lines", {
      leads: toProcess,
      product,
      tone: "professional",
    });
    if (res.success) {
      onToast(`Generated ${res.generated} first lines — cost: ~$${(res.generated * 0.018).toFixed(2)}`);
      load();
    } else {
      onToast(res.detail || "Generation failed", "error");
    }
    setGenerating(false);
  };

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected(prev => prev.size === leads.length ? new Set() : new Set(leads.map(l => l.id)));
  };

  const statusColor = (s) =>
    s === "replied_positive" ? C.signal
    : s === "replied" ? C.mist
    : s === "uncontacted" ? C.snow
    : C.mist;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ ...S.label, marginBottom: 6 }}>Prospect database</div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, fontFamily: "'Syne', sans-serif", letterSpacing: "-0.03em" }}>
            Lead Builder
          </h1>
        </div>
        {selected.size > 0 && (
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span style={{ fontSize: 12, color: C.mist }}>{selected.size} selected</span>
            <select
              style={{ ...S.input, width: "auto", padding: "8px 12px", fontSize: 12 }}
              value={product}
              onChange={e => setProduct(e.target.value)}
            >
              {["ThreatFade","FusionOps","Web-Temify","GiftMode","RealtyScreen AI",
                "KalevioAI","AI Shield","TwinGuard","FadeReach","Olvrix"].map(p => (
                <option key={p}>{p}</option>
              ))}
            </select>
            <button style={S.btn()} onClick={generateFirstLines} disabled={generating}>
              {generating ? "Generating..." : `Generate AI first lines (${selected.size})`}
            </button>
          </div>
        )}
      </div>

      {/* Search */}
      <div style={{ ...S.card, marginBottom: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
          Find leads by domain
        </div>
        <div style={{ fontSize: 12, color: C.mist, marginBottom: 14 }}>
          Hunter.io + Apollo waterfall — automatically uses whichever API is configured.
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <input
            style={S.input}
            placeholder="e.g. paystack.com, flutterwave.com"
            value={searchDomain}
            onChange={e => setSearchDomain(e.target.value)}
            onKeyDown={e => e.key === "Enter" && search()}
          />
          <button style={S.btn()} onClick={search} disabled={searching || !searchDomain.trim()}>
            {searching ? "Searching..." : "Find leads"}
          </button>
        </div>

        {searchResult && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 12, color: C.mist, marginBottom: 10 }}>
              {searchResult.emails_found || 0} emails found via {searchResult.source || "search"}
            </div>
            {(searchResult.leads || []).map((lead, i) => (
              <div key={i} style={{
                padding: "10px 0",
                borderBottom: `1px solid ${C.wire}`,
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600 }}>
                    {lead.first_name} {lead.last_name}
                    {lead.title && <span style={{ color: C.mist, fontWeight: 400 }}> · {lead.title}</span>}
                  </div>
                  <Mono color={C.signal}>{lead.email}</Mono>
                </div>
                <Badge color={
                  (lead.confidence || 0) >= 80 ? C.signal
                  : (lead.confidence || 0) >= 50 ? C.amber
                  : C.mist
                }>
                  {lead.confidence || "?"}%
                </Badge>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Lead table */}
      {loading ? <Loader /> : leads.length === 0 ? (
        <EmptyState
          icon="👥"
          title="No leads yet"
          body="Search for leads above or import a CSV to get started."
        />
      ) : (
        <div style={S.card}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ fontSize: 13, color: C.mist }}>
              {leads.length} leads
            </div>
            <button style={S.btn("ghost")} onClick={toggleAll}>
              {selected.size === leads.length ? "Deselect all" : "Select all"}
            </button>
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["", "Contact", "Company", "Status", "Score", "First line"].map(h => (
                  <th key={h} style={{
                    textAlign: "left", padding: "0 8px 10px 0",
                    fontSize: 10, color: C.mist, fontWeight: 700,
                    textTransform: "uppercase", letterSpacing: "0.08em",
                    borderBottom: `1px solid ${C.wire}`,
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {leads.map(lead => (
                <tr key={lead.id} style={{
                  borderBottom: `1px solid ${C.wire}`,
                  background: selected.has(lead.id) ? `${C.signal}06` : "transparent",
                }}>
                  <td style={{ padding: "12px 8px 12px 0", width: 24 }}>
                    <input
                      type="checkbox"
                      checked={selected.has(lead.id)}
                      onChange={() => toggleSelect(lead.id)}
                      style={{ accentColor: C.signal }}
                    />
                  </td>
                  <td style={{ padding: "12px 8px 12px 0" }}>
                    <div style={{ fontSize: 13.5, fontWeight: 600 }}>
                      {lead.first_name} {lead.last_name}
                    </div>
                    <Mono size={11}>{lead.email}</Mono>
                  </td>
                  <td style={{ padding: "12px 8px 12px 0" }}>
                    <div style={{ fontSize: 13 }}>{lead.company || "—"}</div>
                    <div style={{ fontSize: 11, color: C.mist }}>{lead.title || ""}</div>
                  </td>
                  <td style={{ padding: "12px 8px 12px 0" }}>
                    <Badge color={statusColor(lead.status)}>
                      {(lead.status || "uncontacted").replace(/_/g," ")}
                    </Badge>
                  </td>
                  <td style={{ padding: "12px 8px 12px 0" }}>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 13, fontWeight: 700,
                      color: (lead.icp_score || 0) >= 70 ? C.signal : C.mist,
                    }}>
                      {lead.icp_score || "—"}
                    </span>
                  </td>
                  <td style={{ padding: "12px 0 12px 0", maxWidth: 260 }}>
                    {lead.ai_first_line ? (
                      <div style={{
                        fontSize: 12, color: C.snow, lineHeight: 1.5,
                        fontStyle: "italic",
                        overflow: "hidden", textOverflow: "ellipsis",
                        display: "-webkit-box", WebkitLineClamp: 2,
                        WebkitBoxOrient: "vertical",
                      }}>
                        "{lead.ai_first_line}"
                      </div>
                    ) : (
                      <span style={{ fontSize: 11, color: C.mist }}>Not generated</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Campaigns ────────────────────────────────────────────────
function CampaignsView({ onToast }) {
  const { get, post } = useApi();
  const [campaigns,  setCampaigns]  = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [creating,   setCreating]   = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [auditing,   setAuditing]   = useState(false);
  const [auditResult,setAuditResult]= useState(null);
  const [form,       setForm]       = useState({
    name: "", subject: "", body_html: "",
    product: "ThreatFade", target_segment: "",
  });

  useEffect(() => {
    get("/api/campaigns")
      .then(d => setCampaigns(d.campaigns || []))
      .finally(() => setLoading(false));
  }, []);

  const auditCampaign = async () => {
    if (!form.subject || !form.body_html) return;
    setAuditing(true);
    const res = await post("/api/campaigns/audit", {
      subject: form.subject,
      body_html: form.body_html,
    });
    setAuditResult(res);
    setAuditing(false);
  };

  const createCampaign = async () => {
    if (!form.name || !form.subject || !form.body_html) {
      onToast("Fill in name, subject and body", "error");
      return;
    }
    setCreating(true);
    const res = await post("/api/campaigns/create", form);
    if (res.campaign_id) {
      onToast("Campaign created — AI auditor running");
      setShowCreate(false);
      setForm({ name:"", subject:"", body_html:"", product:"ThreatFade", target_segment:"" });
      setAuditResult(null);
      const d = await get("/api/campaigns");
      setCampaigns(d.campaigns || []);
    } else {
      onToast(res.detail || "Failed to create campaign", "error");
    }
    setCreating(false);
  };

  const toggleStatus = async (id, currentStatus) => {
    const action = currentStatus === "active" ? "pause" : "resume";
    await post(`/api/campaigns/${id}/${action}`, {});
    const d = await get("/api/campaigns");
    setCampaigns(d.campaigns || []);
    onToast(`Campaign ${action}d`);
  };

  const statusColor = s =>
    s === "active" ? C.signal : s === "paused" ? C.amber
    : s === "draft" ? C.mist : C.mist;

  const scoreColor = s => s >= 80 ? C.signal : s >= 60 ? C.amber : C.red;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ ...S.label, marginBottom: 6 }}>Outreach</div>
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, fontFamily: "'Syne', sans-serif", letterSpacing: "-0.03em" }}>
            Campaigns
          </h1>
        </div>
        <button style={S.btn()} onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "Cancel" : "+ New campaign"}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div style={{ ...S.card, marginBottom: 20 }}>
          <h3 style={{ ...S.sectionTitle, marginBottom: 20 }}>New campaign</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 }}>
            <div>
              <div style={{ ...S.label, marginBottom: 6 }}>Campaign name</div>
              <input style={S.input} placeholder="ThreatFade → Nigerian Fintechs"
                value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
            </div>
            <div>
              <div style={{ ...S.label, marginBottom: 6 }}>Product</div>
              <select style={S.input} value={form.product}
                onChange={e => setForm({...form, product: e.target.value})}>
                {["ThreatFade","FusionOps","ReconOS","Web-Temify","GiftMode",
                  "RealtyScreen AI","KalevioAI","AI Shield","TwinGuard",
                  "FadeReach","Olvrix","FederX AI","ResonaForge"].map(p => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </div>
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ ...S.label, marginBottom: 6 }}>Subject line</div>
            <input style={S.input}
              placeholder="Your email infrastructure has a gap"
              value={form.subject}
              onChange={e => setForm({...form, subject: e.target.value})} />
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ ...S.label, marginBottom: 6 }}>Email body</div>
            <textarea
              style={{ ...S.input, height: 160, resize: "vertical", lineHeight: 1.6 }}
              placeholder={`Hi {{first_name}},\n\n[AI first line here]\n\n[Value proposition — 2-3 sentences max]\n\n[One clear CTA]\n\n— Lloyd\nTinlance Limited`}
              value={form.body_html}
              onChange={e => setForm({...form, body_html: e.target.value})}
            />
          </div>

          {/* Audit result */}
          {auditResult && (
            <div style={{
              ...S.card, marginBottom: 14,
              background: C.slate,
              borderColor: scoreColor(auditResult.score || 0) + "40",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
                <div style={{
                  width: 56, height: 56, borderRadius: "50%",
                  background: `${scoreColor(auditResult.score || 0)}18`,
                  display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center",
                  flexShrink: 0,
                }}>
                  <span style={{
                    fontSize: 18, fontWeight: 800,
                    color: scoreColor(auditResult.score || 0),
                    fontFamily: "'JetBrains Mono', monospace",
                  }}>{auditResult.score}</span>
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14 }}>
                    Campaign score: {auditResult.grade}
                  </div>
                  <div style={{ fontSize: 12, color: C.mist }}>
                    {auditResult.issues_count} issues · {auditResult.metrics?.word_count} words
                  </div>
                </div>
                <Badge color={auditResult.ready_to_send ? C.signal : C.amber}>
                  {auditResult.ready_to_send ? "Ready to send" : "Fix issues first"}
                </Badge>
              </div>
              {(auditResult.recommendations || []).map((r, i) => (
                <div key={i} style={{
                  padding: "8px 12px", marginBottom: 6,
                  background: C.obs, borderRadius: 6,
                  fontSize: 12.5, color: C.snow, lineHeight: 1.5,
                  borderLeft: `2px solid ${C.amber}`,
                }}>{r}</div>
              ))}
            </div>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <button style={S.btn("ghost")} onClick={auditCampaign} disabled={auditing}>
              {auditing ? "Auditing..." : "Run AI audit first"}
            </button>
            <button style={S.btn()} onClick={createCampaign} disabled={creating}>
              {creating ? "Creating..." : "Create campaign"}
            </button>
          </div>
        </div>
      )}

      {/* Campaign list */}
      {loading ? <Loader /> : campaigns.length === 0 ? (
        <EmptyState
          icon="📧"
          title="No campaigns yet"
          body="Create your first campaign above. The AI auditor will review it before you send."
          action={<button style={S.btn()} onClick={() => setShowCreate(true)}>Create first campaign</button>}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {campaigns.map(c => (
            <div key={c.id} style={S.card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                    <span style={{ fontWeight: 700, fontSize: 15 }}>{c.name}</span>
                    <Badge color={statusColor(c.status)}>{c.status}</Badge>
                    {c.audit_score && (
                      <Badge color={scoreColor(c.audit_score)}>
                        Audit: {c.audit_score}
                      </Badge>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: C.mist }}>
                    {c.subject}
                    {c.product && <span> · {c.product}</span>}
                  </div>
                </div>
                {c.status !== "draft" && (
                  <button
                    style={S.btn("ghost")}
                    onClick={() => toggleStatus(c.id, c.status)}
                  >
                    {c.status === "active" ? "Pause" : "Resume"}
                  </button>
                )}
              </div>

              <div style={{ display: "flex", gap: 24 }}>
                {[
                  ["Sent",    c.emails_sent, C.snow],
                  ["Opens",   `${c.open_rate || 0}%`,  (c.open_rate||0) > 20 ? C.signal : C.mist],
                  ["Replies", `${c.reply_rate || 0}%`, (c.reply_rate||0) > 3 ? C.signal : C.mist],
                  ["Bounces", `${c.bounce_rate || 0}%`,(c.bounce_rate||0) < 2 ? C.mist : C.red],
                ].map(([label, val, color]) => (
                  <div key={label}>
                    <div style={{ fontSize: 10, color: C.mist, marginBottom: 2, ...S.label }}>
                      {label}
                    </div>
                    <div style={{
                      fontSize: 18, fontWeight: 800, color,
                      fontFamily: "'JetBrains Mono', monospace",
                    }}>{val}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Inbox ────────────────────────────────────────────────────
function InboxView({ onToast }) {
  const { get, post } = useApi();
  const [replies,  setReplies]  = useState([]);
  const [summary,  setSummary]  = useState({});
  const [loading,  setLoading]  = useState(true);
  const [filter,   setFilter]   = useState("all");
  const [selected, setSelected] = useState(null);

  const load = useCallback(() => {
    const isHot = filter === "hot" ? "true" : undefined;
    const intent = filter !== "all" && filter !== "hot" ? filter : undefined;
    let url = "/api/inbox?limit=50";
    if (isHot)  url += `&is_hot=true`;
    if (intent) url += `&intent=${intent}`;
    get(url)
      .then(d => setReplies(d.replies || []))
      .finally(() => setLoading(false));
    get("/api/inbox/stats/summary").then(setSummary);
  }, [filter]);

  useEffect(() => { load(); }, [filter]);

  const markRead = async (id) => {
    await post(`/api/inbox/${id}/mark-read`, {});
    setReplies(prev => prev.map(r => r.id === id ? {...r, is_read: true} : r));
  };

  const filters = [
    { key: "all",          label: "All replies",  count: summary.total },
    { key: "hot",          label: "Hot leads 🔥", count: summary.hot },
    { key: "interested",   label: "Interested",   count: summary.interested },
    { key: "more_info",    label: "Wants info",   count: summary.more_info },
    { key: "not_now",      label: "Not now",      count: summary.not_now },
    { key: "out_of_office",label: "OOO",          count: summary.ooo },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.label, marginBottom: 6 }}>Unified inbox</div>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, fontFamily: "'Syne', sans-serif", letterSpacing: "-0.03em" }}>
          Replies
        </h1>
        {(summary.hot || 0) > 0 && (
          <div style={{
            marginTop: 8, display: "inline-flex", alignItems: "center", gap: 8,
            padding: "6px 14px",
            background: `${C.ember}18`, border: `1px solid ${C.ember}30`,
            borderRadius: 20, fontSize: 12.5, color: C.ember, fontWeight: 600,
          }}>
            🔥 {summary.hot} hot lead{summary.hot > 1 ? "s" : ""} waiting
          </div>
        )}
      </div>

      {/* Filter tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
        {filters.map(f => (
          <button key={f.key}
            style={{
              padding: "6px 14px", borderRadius: 20, border: "none",
              fontSize: 12, fontWeight: 600, cursor: "pointer",
              background: filter === f.key ? C.signal : C.slate,
              color: filter === f.key ? "#000" : C.mist,
              transition: "all 0.15s",
            }}
            onClick={() => setFilter(f.key)}
          >
            {f.label} {f.count ? `(${f.count})` : ""}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 16 }}>
        {/* Reply list */}
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 10 }}>
          {loading ? <Loader /> : replies.length === 0 ? (
            <EmptyState
              icon="📬"
              title="No replies yet"
              body="Replies from your campaigns appear here automatically. Hot leads are flagged immediately."
            />
          ) : replies.map(r => (
            <div key={r.id}
              onClick={() => { setSelected(r); markRead(r.id); }}
              style={{
                ...S.card, cursor: "pointer",
                borderColor: r.is_hot ? `${C.ember}50`
                  : selected?.id === r.id ? `${C.signal}40`
                  : C.wire,
                opacity: r.is_read ? 0.75 : 1,
                transition: "border-color 0.15s",
                background: selected?.id === r.id ? `${C.signal}06` : C.obs,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {!r.is_read && (
                    <div style={{
                      width: 7, height: 7, borderRadius: "50%",
                      background: r.is_hot ? C.ember : C.signal,
                      flexShrink: 0,
                    }} />
                  )}
                  <span style={{ fontWeight: 600, fontSize: 13.5 }}>
                    {r.first_name} {r.last_name || ""}
                    {r.company && <span style={{ color: C.mist, fontWeight: 400 }}> · {r.company}</span>}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {r.is_hot && <Badge color={C.ember}>Hot lead</Badge>}
                  <IntentPill intent={r.intent} />
                </div>
              </div>
              <div style={{ fontSize: 12.5, color: C.mist, marginBottom: 6 }}>{r.from_email}</div>
              <div style={{
                fontSize: 13, color: C.snow, lineHeight: 1.5,
                overflow: "hidden", textOverflow: "ellipsis",
                display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
              }}>
                {r.body}
              </div>
              {r.campaign_name && (
                <div style={{ marginTop: 8, fontSize: 11, color: C.mist }}>
                  Campaign: {r.campaign_name}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Reply detail panel */}
        {selected && (
          <div style={{
            ...S.card, width: 340, flexShrink: 0,
            position: "sticky", top: 76, alignSelf: "flex-start",
            maxHeight: "calc(100vh - 120px)", overflowY: "auto",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>Reply detail</div>
              <button style={{ background:"none", border:"none", color: C.mist, cursor:"pointer", fontSize: 16 }}
                onClick={() => setSelected(null)}>✕</button>
            </div>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>
                {selected.first_name} {selected.last_name}
              </div>
              <Mono>{selected.from_email}</Mono>
              {selected.company && (
                <div style={{ fontSize: 12, color: C.mist, marginTop: 2 }}>
                  {selected.title} · {selected.company}
                </div>
              )}
            </div>
            <hr style={S.divider} />
            <div style={{ marginBottom: 10 }}>
              <div style={{ ...S.label, marginBottom: 6 }}>Subject</div>
              <div style={{ fontSize: 13 }}>{selected.subject}</div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ ...S.label, marginBottom: 6 }}>Message</div>
              <div style={{
                fontSize: 13, lineHeight: 1.7, color: C.snow,
                whiteSpace: "pre-wrap", wordBreak: "break-word",
              }}>
                {selected.body}
              </div>
            </div>
            <hr style={S.divider} />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <IntentPill intent={selected.intent} />
              {selected.is_hot && <Badge color={C.ember}>Hot lead</Badge>}
              <Badge color={C.mist}>{selected.sentiment}</Badge>
            </div>
            {selected.campaign_name && (
              <div style={{ marginTop: 10, fontSize: 11, color: C.mist }}>
                From: {selected.campaign_name}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Analytics ────────────────────────────────────────────────
function AnalyticsView() {
  const { get } = useApi();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    get("/api/analytics/overview")
      .then(setData)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;
  if (!data) return <EmptyState icon="📊" title="No data yet" body="Launch a campaign to see analytics." />;

  const bm = data.benchmarks || {};
  const mo = data.this_month || {};
  const wk = data.this_week  || {};

  const BenchRow = ({ label, yours, compare, unit = "%" }) => {
    const better = yours > compare;
    return (
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", padding:"12px 0", borderBottom:`1px solid ${C.wire}` }}>
        <span style={{ fontSize: 13, color: C.mist }}>{label}</span>
        <div style={{ display:"flex", alignItems:"center", gap: 14 }}>
          <span style={{ fontSize: 11, color: C.mist }}>{compare}{unit} avg</span>
          <span style={{
            fontFamily:"'JetBrains Mono', monospace", fontWeight:700, fontSize:15,
            color: better ? C.signal : C.amber,
          }}>{yours}{unit}</span>
        </div>
      </div>
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.label, marginBottom: 6 }}>Performance</div>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, fontFamily: "'Syne', sans-serif", letterSpacing: "-0.03em" }}>
          Analytics
        </h1>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        {/* Benchmarks */}
        <div style={S.card}>
          <h3 style={{ ...S.sectionTitle }}>vs Industry average</h3>
          <BenchRow label="Open rate"   yours={bm.open_rate?.yours || 0}  compare={bm.open_rate?.industry || 21.3} />
          <BenchRow label="Reply rate"  yours={bm.reply_rate?.yours || 0} compare={bm.reply_rate?.industry || 3.4} />
          <BenchRow label="Bounce rate" yours={bm.bounce_rate?.yours || 0} compare={bm.bounce_rate?.limit || 2.0} unit="%" />
        </div>

        {/* Period breakdown */}
        <div style={S.card}>
          <h3 style={{ ...S.sectionTitle }}>Activity</h3>
          <div style={{ display:"flex", gap: 16, marginBottom: 20 }}>
            <div>
              <div style={{ ...S.label, marginBottom: 4 }}>This week</div>
              <div style={{ fontFamily:"'JetBrains Mono', monospace", fontSize:22, fontWeight:800 }}>
                {wk.sent || 0}
              </div>
              <div style={{ fontSize:11, color:C.mist }}>sent · {wk.replies || 0} replies</div>
            </div>
            <div>
              <div style={{ ...S.label, marginBottom: 4 }}>This month</div>
              <div style={{ fontFamily:"'JetBrains Mono', monospace", fontSize:22, fontWeight:800 }}>
                {mo.sent_mo || 0}
              </div>
              <div style={{ fontSize:11, color:C.mist }}>sent · {mo.replies_mo || 0} replies</div>
            </div>
          </div>
          <div style={{ ...S.label, marginBottom: 8 }}>Intent breakdown</div>
          {(data.intent_breakdown || []).map((item, i) => (
            <div key={i} style={{
              display:"flex", alignItems:"center", gap:10,
              padding:"6px 0", borderBottom:`1px solid ${C.wire}`,
            }}>
              <IntentPill intent={item.intent} />
              <span style={{ fontFamily:"'JetBrains Mono', monospace", fontSize:14, fontWeight:700 }}>
                {item.count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Warmup */}
      <div style={S.card}>
        <h3 style={{ ...S.sectionTitle }}>Domain warmup status</h3>
        {(data.domains || []).map((d, i) => (
          <div key={i} style={{
            padding:"14px 0",
            borderBottom: i < (data.domains.length-1) ? `1px solid ${C.wire}` : "none",
          }}>
            <div style={{ display:"flex", justifyContent:"space-between", marginBottom:8 }}>
              <Mono color={C.snow} size={13}>{d.domain}</Mono>
              <div style={{ display:"flex", gap:8 }}>
                <Badge color={d.spf_valid ? C.signal : C.red}>SPF</Badge>
                <Badge color={d.dkim_valid ? C.signal : C.red}>DKIM</Badge>
                <Badge color={d.dmarc_valid ? C.signal : C.red}>DMARC</Badge>
              </div>
            </div>
            <WarmupBar day={d.warmup_day || 0} limit={d.daily_limit || 5} />
          </div>
        ))}
        {(data.domains || []).length === 0 && (
          <div style={{ fontSize:13, color:C.mist }}>No domains added yet.</div>
        )}
      </div>
    </div>
  );
}

// ── Settings ─────────────────────────────────────────────────
function SettingsView({ onToast }) {
  const { get, post } = useApi();
  const [tenant,  setTenant]  = useState(null);
  const [usage,   setUsage]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving,  setSaving]  = useState(false);
  const [form,    setForm]    = useState({ name:"", company:"" });

  useEffect(() => {
    Promise.all([get("/api/tenant/me"), get("/api/tenant/usage")])
      .then(([t, u]) => {
        setTenant(t);
        setUsage(u);
        setForm({ name: t.name || "", company: t.company || "" });
      })
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    const res = await post("/api/tenant/me", form);  // Should be PATCH
    if (res.message) onToast("Profile saved");
    else onToast(res.detail || "Save failed", "error");
    setSaving(false);
  };

  if (loading) return <Loader />;

  const u = usage?.usage || {};
  const planDisplay = (tenant?.plan || "trial").replace(/_/g," ").replace(/\b\w/g, c => c.toUpperCase());

  const UsageRow = ({ label, used, limit }) => {
    const pct = limit === -1 ? 0 : limit > 0 ? Math.round(used/limit*100) : 100;
    return (
      <div style={{ marginBottom: 14 }}>
        <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom:5 }}>
          <span style={{ color:C.mist }}>{label}</span>
          <span style={{ fontFamily:"'JetBrains Mono', monospace" }}>
            {used.toLocaleString()} / {limit === -1 ? "∞" : limit.toLocaleString()}
          </span>
        </div>
        {limit !== -1 && (
          <div style={{ height:4, background:C.wire, borderRadius:2 }}>
            <div style={{
              height:"100%", width:`${Math.min(pct,100)}%`, borderRadius:2,
              background: pct > 85 ? C.red : pct > 60 ? C.amber : C.signal,
              transition:"width 0.8s ease",
            }} />
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.label, marginBottom:6 }}>Account</div>
        <h1 style={{ margin:0, fontSize:22, fontWeight:800, fontFamily:"'Syne', sans-serif", letterSpacing:"-0.03em" }}>
          Settings
        </h1>
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        {/* Profile */}
        <div style={S.card}>
          <h3 style={S.sectionTitle}>Profile</h3>
          <div style={{ marginBottom:12 }}>
            <div style={{ ...S.label, marginBottom:6 }}>Name</div>
            <input style={S.input} value={form.name}
              onChange={e => setForm({...form, name:e.target.value})} />
          </div>
          <div style={{ marginBottom:12 }}>
            <div style={{ ...S.label, marginBottom:6 }}>Company</div>
            <input style={S.input} value={form.company}
              onChange={e => setForm({...form, company:e.target.value})} />
          </div>
          <div style={{ marginBottom:20 }}>
            <div style={{ ...S.label, marginBottom:6 }}>Email</div>
            <input style={{ ...S.input, opacity:0.6 }} value={tenant?.email || ""} disabled />
          </div>
          <button style={S.btn()} onClick={save} disabled={saving}>
            {saving ? "Saving..." : "Save changes"}
          </button>
        </div>

        {/* Plan + usage */}
        <div style={S.card}>
          <h3 style={S.sectionTitle}>Plan & usage</h3>
          <div style={{
            display:"flex", alignItems:"center", justifyContent:"space-between",
            marginBottom:20,
            padding:"12px 16px",
            background:C.slate, borderRadius:8,
          }}>
            <div>
              <div style={{ fontWeight:700, fontSize:15 }}>{planDisplay}</div>
              {tenant?.trial_days_left !== null && tenant?.trial_days_left !== undefined && (
                <div style={{ fontSize:12, color:C.amber }}>
                  {tenant.trial_days_left} days left in trial
                </div>
              )}
            </div>
            <a href="#pricing" style={{
              ...S.btn("sm"), background:C.signal, color:"#000",
              textDecoration:"none",
            }}>
              Upgrade
            </a>
          </div>
          {usage && (
            <div>
              <UsageRow label="Emails this month" used={u.emails?.used||0}    limit={u.emails?.limit||50} />
              <UsageRow label="Contacts"           used={u.contacts?.used||0}  limit={u.contacts?.limit||500} />
              <UsageRow label="Domains"            used={u.domains?.used||0}   limit={u.domains?.limit||1} />
              <UsageRow label="AI credits"         used={u.ai_credits?.used||0} limit={u.ai_credits?.limit||50} />
            </div>
          )}
        </div>
      </div>

      {/* Billing info */}
      <div style={{ ...S.card, marginTop:16 }}>
        <h3 style={S.sectionTitle}>Billing</h3>
        <div style={{ display:"flex", gap:12, flexWrap:"wrap" }}>
          {[
            { label:"Paystack", desc:"NGN / African payments", href:"https://paystack.com" },
            { label:"LemonSqueezy", desc:"Global / USD", href:"https://app.lemonsqueezy.com" },
            { label:"Paddle", desc:"EU / UK / Enterprise", href:"https://vendors.paddle.com" },
          ].map(b => (
            <a key={b.label} href={b.href} target="_blank" rel="noopener noreferrer"
              style={{
                ...S.card, padding:"14px 18px", textDecoration:"none",
                flex:1, minWidth:160,
              }}>
              <div style={{ fontWeight:600, fontSize:13, marginBottom:3 }}>{b.label}</div>
              <div style={{ fontSize:11.5, color:C.mist }}>{b.desc}</div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Loader ────────────────────────────────────────────────────
function Loader() {
  return (
    <div style={{ display:"flex", alignItems:"center", justifyContent:"center", padding:"64px 0" }}>
      <div style={{
        width:28, height:28, borderRadius:"50%",
        border:`3px solid ${C.wire}`,
        borderTopColor: C.signal,
        animation:"spin 0.8s linear infinite",
      }} />
    </div>
  );
}

// ── Auth screens ─────────────────────────────────────────────
function AuthScreen({ onLogin }) {
  const [mode,    setMode]    = useState("login");
  const [form,    setForm]    = useState({ email:"", password:"", name:"", company:"" });
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");

  const submit = async () => {
    setError("");
    setLoading(true);
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/signup";
      const res  = await fetch(`${API_URL}${path}`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(form),
      }).then(r => r.json());

      if (res.token) {
        localStorage.setItem("fr_token", res.token);
        onLogin(res);
      } else {
        setError(res.detail || "Something went wrong");
      }
    } catch {
      setError("Connection error — is the API running?");
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight:"100vh", background:C.void,
      display:"flex", alignItems:"center", justifyContent:"center",
      fontFamily:"'Inter', system-ui, sans-serif",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');
        * { box-sizing: border-box; }
        @keyframes spin { to { transform: rotate(360deg); } }
        input:focus { border-color: ${C.signal} !important; box-shadow: 0 0 0 2px ${C.signal}20; }
        button:hover { opacity: 0.88; }
      `}</style>

      <div style={{ width:"100%", maxWidth:400, padding:"0 20px" }}>
        <div style={{ textAlign:"center", marginBottom:36 }}>
          <div style={{
            fontFamily:"'Syne', sans-serif", fontWeight:800,
            fontSize:28, letterSpacing:"-0.04em", marginBottom:8,
          }}>
            Fade<span style={{ color:C.signal }}>Reach</span>
          </div>
          <div style={{ fontSize:13, color:C.mist }}>
            {mode === "login"
              ? "Sign in to your workspace"
              : "Start your 14-day free trial"}
          </div>
        </div>

        <div style={{ ...S.card }}>
          {mode === "signup" && (
            <>
              <div style={{ marginBottom:14 }}>
                <div style={{ ...S.label, marginBottom:6 }}>Full name</div>
                <input style={S.input} placeholder="Lloyd Chinaemerem"
                  value={form.name} onChange={e => setForm({...form, name:e.target.value})} />
              </div>
              <div style={{ marginBottom:14 }}>
                <div style={{ ...S.label, marginBottom:6 }}>Company</div>
                <input style={S.input} placeholder="Tinlance Limited"
                  value={form.company} onChange={e => setForm({...form, company:e.target.value})} />
              </div>
            </>
          )}
          <div style={{ marginBottom:14 }}>
            <div style={{ ...S.label, marginBottom:6 }}>Email</div>
            <input style={S.input} type="email" placeholder="you@company.com"
              value={form.email} onChange={e => setForm({...form, email:e.target.value})} />
          </div>
          <div style={{ marginBottom:20 }}>
            <div style={{ ...S.label, marginBottom:6 }}>Password</div>
            <input style={S.input} type="password" placeholder="••••••••"
              value={form.password}
              onChange={e => setForm({...form, password:e.target.value})}
              onKeyDown={e => e.key === "Enter" && submit()} />
          </div>

          {error && (
            <div style={{
              padding:"10px 14px", marginBottom:14,
              background:`${C.red}12`, borderRadius:8,
              fontSize:13, color:C.red,
            }}>{error}</div>
          )}

          <button style={{ ...S.btn(), width:"100%", justifyContent:"center" }}
            onClick={submit} disabled={loading}>
            {loading ? "..." : mode === "login" ? "Sign in" : "Create account — free"}
          </button>

          {mode === "signup" && (
            <div style={{ fontSize:11, color:C.mist, textAlign:"center", marginTop:10 }}>
              No credit card · 14 days free · Paystack accepted
            </div>
          )}
        </div>

        <div style={{ textAlign:"center", marginTop:16, fontSize:13, color:C.mist }}>
          {mode === "login" ? (
            <>No account? <span style={{ color:C.signal, cursor:"pointer" }}
              onClick={() => setMode("signup")}>Start free trial</span></>
          ) : (
            <>Already have an account? <span style={{ color:C.signal, cursor:"pointer" }}
              onClick={() => setMode("login")}>Sign in</span></>
          )}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// ROOT APP
// ═══════════════════════════════════════════════════════════
export default function App() {
  const [authed,   setAuthed]   = useState(!!localStorage.getItem("fr_token"));
  const [tenant,   setTenant]   = useState(null);
  const [nav,      setNav]      = useState("overview");
  const [toast,    setToast]    = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  const showToast = (msg, type="success") => {
    setToast({ msg, type });
  };

  const logout = () => {
    localStorage.removeItem("fr_token");
    setAuthed(false);
    setTenant(null);
  };

  if (!authed) {
    return <AuthScreen onLogin={(data) => { setAuthed(true); setTenant(data); }} />;
  }

  const navItems = [
    { id:"overview",   icon:"▦",  label:"Overview" },
    { id:"domains",    icon:"◎",  label:"Domains" },
    { id:"leads",      icon:"◈",  label:"Leads" },
    { id:"campaigns",  icon:"◉",  label:"Campaigns" },
    { id:"inbox",      icon:"◐",  label:"Inbox" },
    { id:"analytics",  icon:"◑",  label:"Analytics" },
    { id:"settings",   icon:"◔",  label:"Settings" },
  ];

  const renderView = () => {
    const props = { onToast: showToast };
    switch(nav) {
      case "overview":  return <OverviewView {...props} />;
      case "domains":   return <DomainsView {...props} />;
      case "leads":     return <LeadsView {...props} />;
      case "campaigns": return <CampaignsView {...props} />;
      case "inbox":     return <InboxView {...props} />;
      case "analytics": return <AnalyticsView {...props} />;
      case "settings":  return <SettingsView {...props} />;
      default:          return <OverviewView {...props} />;
    }
  };

  return (
    <div style={S.app}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: ${C.void}; }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: ${C.void}; }
        ::-webkit-scrollbar-thumb { background: ${C.wire}; border-radius: 3px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        button { cursor: pointer; }
        button:hover { opacity: 0.85; }
        input:focus, textarea:focus, select:focus {
          outline: none;
          border-color: ${C.signal} !important;
          box-shadow: 0 0 0 2px ${C.signal}15;
        }
        @media (max-width: 768px) {
          .sidebar { transform: translateX(-220px); transition: transform 0.25s; }
          .sidebar.open { transform: translateX(0); }
          .main { margin-left: 0 !important; }
        }
      `}</style>

      {/* Sidebar */}
      <aside style={S.sidebar} className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div style={{ padding:"18px 18px 16px", borderBottom:`1px solid ${C.wire}` }}>
          <div style={{
            fontFamily:"'Syne', sans-serif", fontWeight:800,
            fontSize:18, letterSpacing:"-0.04em",
          }}>
            Fade<span style={{ color:C.signal }}>Reach</span>
          </div>
          <div style={{ fontSize:10, color:C.mist, marginTop:2, fontFamily:"'JetBrains Mono', monospace" }}>
            by Tinlance Limited
          </div>
        </div>

        <div style={{ flex:1, padding:"10px 0" }}>
          {navItems.map(item => (
            <div key={item.id}
              style={S.navItem(nav === item.id)}
              onClick={() => { setNav(item.id); setMobileOpen(false); }}
            >
              <span style={{ fontSize:14, lineHeight:1 }}>{item.icon}</span>
              {item.label}
            </div>
          ))}
        </div>

        <div style={{ padding:"14px 18px", borderTop:`1px solid ${C.wire}` }}>
          <div style={{ fontSize:11, color:C.mist, marginBottom:6 }}>
            {tenant?.plan?.replace(/_/g," ").toUpperCase() || "TRIAL"}
          </div>
          <button
            style={{ ...S.btn("ghost"), width:"100%", justifyContent:"center", fontSize:12 }}
            onClick={logout}
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div style={S.main} className="main">
        {/* Topbar */}
        <header style={S.topbar}>
          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            <button
              style={{ background:"none", border:"none", color:C.mist, fontSize:18, display:"none" }}
              className="mobile-menu-btn"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              ☰
            </button>
            <span style={{ fontSize:13, color:C.mist }}>
              {navItems.find(n => n.id === nav)?.label}
            </span>
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            <a href="#pricing" style={{ ...S.btn("sm"), background:`${C.signal}18`, color:C.signal, textDecoration:"none" }}>
              Upgrade plan
            </a>
            <div style={{
              width:32, height:32, borderRadius:"50%",
              background:`${C.signal}20`, border:`1px solid ${C.signal}30`,
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize:13, fontWeight:700, color:C.signal,
              fontFamily:"'Syne', sans-serif",
            }}>
              {(tenant?.name || "L")[0].toUpperCase()}
            </div>
          </div>
        </header>

        {/* Content */}
        <main style={S.content}>
          {renderView()}
        </main>
      </div>

      {/* Toast */}
      {toast && (
        <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)} />
      )}

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          style={{
            position:"fixed", inset:0, background:"rgba(0,0,0,0.5)", zIndex:49,
          }}
          onClick={() => setMobileOpen(false)}
        />
      )}
    </div>
  );
}
