import { useState, useEffect, useCallback } from "react";

// ─────────────────────────────────────────────────────────
// FadeReach Phase 4 — Ecosystem Moat Pages
// Ecosystem Dashboard · Vertical Packs · Managed Services
// Public API Management · Flywheel Metrics
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
  purple:  "#818CF8",
  blue:    "#60A5FA",
};

const S = {
  card: {
    background: C.obs, border: `1px solid ${C.wire}`,
    borderRadius: 12, padding: 22,
  },
  btn: (v = "primary") => ({
    display: "inline-flex", alignItems: "center", gap: 6,
    padding: v === "sm" ? "5px 12px" : "10px 20px",
    fontSize: v === "sm" ? 11.5 : 13.5, fontWeight: 600,
    borderRadius: 8, border: "none", cursor: "pointer",
    transition: "opacity 0.15s",
    background: v === "ghost" ? "transparent" : v === "ember" ? C.ember : C.signal,
    color: v === "ghost" ? C.mist : "#000",
    border: v === "ghost" ? `1px solid ${C.wire}` : "none",
    whiteSpace: "nowrap", textDecoration: "none",
  }),
  label: {
    fontSize: 10, fontWeight: 700, color: C.signal,
    letterSpacing: "0.12em", textTransform: "uppercase",
    fontFamily: "'JetBrains Mono', monospace",
  },
  mono:  { fontFamily: "'JetBrains Mono', monospace", fontSize: 12.5 },
  badge: (color) => ({
    display: "inline-flex", padding: "2px 9px", borderRadius: 20,
    fontSize: 10, fontWeight: 700, background: `${color}18`, color,
    fontFamily: "'JetBrains Mono', monospace",
    textTransform: "uppercase", letterSpacing: "0.06em",
  }),
  sectionTitle: {
    fontSize: 17, fontWeight: 700,
    fontFamily: "'Syne', sans-serif",
    letterSpacing: "-0.02em", margin: "0 0 16px",
  },
  divider: { height: 1, background: C.wire, margin: "16px 0", border: "none" },
  input: {
    background: C.slate, border: `1px solid ${C.wire}`,
    borderRadius: 8, padding: "9px 14px", color: C.snow,
    fontSize: 13.5, outline: "none", width: "100%",
    boxSizing: "border-box", fontFamily: "inherit",
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
  const get  = p => fetch(`${API_URL}${p}`, { headers }).then(r => r.json());
  const post = (p, b) => fetch(`${API_URL}${p}`, {
    method: "POST", headers, body: JSON.stringify(b)
  }).then(r => r.json());
  const del  = p => fetch(`${API_URL}${p}`, { method: "DELETE", headers }).then(r => r.json());
  return { get, post, del };
}

const Badge  = ({ children, color = C.signal }) => <span style={S.badge(color)}>{children}</span>;
const Loader = () => (
  <div style={{ display:"flex", alignItems:"center", justifyContent:"center", padding:"48px 0" }}>
    <div style={{
      width: 24, height: 24, borderRadius: "50%",
      border: `3px solid ${C.wire}`, borderTopColor: C.signal,
      animation: "spin 0.8s linear infinite",
    }} />
  </div>
);

// ═══════════════════════════════════════════════
// ECOSYSTEM DASHBOARD
// The full 17-wire flywheel — live status
// ═══════════════════════════════════════════════
export function EcosystemView({ onToast }) {
  const { get, post } = useApi();
  const [status,   setStatus]   = useState(null);
  const [metrics,  setMetrics]  = useState(null);
  const [campaigns,setCampaigns]= useState(null);
  const [loading,  setLoading]  = useState(true);
  const [launching,setLaunching]= useState(null);
  const [syncing,  setSyncing]  = useState(null);

  useEffect(() => {
    Promise.all([
      get("/api/ecosystem/status"),
      get("/api/ecosystem/flywheel/metrics"),
      get("/api/ecosystem/campaigns/available"),
    ]).then(([s, m, c]) => {
      setStatus(s);
      setMetrics(m);
      setCampaigns(c);
    }).finally(() => setLoading(false));
  }, []);

  const launchCampaign = async (product, segment) => {
    const key = `${product}-${segment}`;
    setLaunching(key);
    const res = await post(`/api/ecosystem/campaigns/launch?product=${product}&segment=${segment}`, {});
    if (res.campaign_id) {
      onToast(`${product} → ${segment} campaign created (#${res.campaign_id})`);
    } else {
      onToast(res.detail || "Failed to launch", "error");
    }
    setLaunching(null);
  };

  const syncSource = async (source) => {
    setSyncing(source);
    const res = await post(`/api/ecosystem/${source}/sync`, {});
    onToast(res.message || `${source} syncing`);
    setSyncing(null);
  };

  const serviceColor = s =>
    s === "online" ? C.signal : s === "error" ? C.amber : C.red;

  const PRODUCT_COLORS = {
    threatfade: C.red,    fusionops: C.amber,  reconos: C.purple,
    bugflow: C.amber,     twinguard: C.purple,  ai_shield: C.blue,
    kalevioai: C.signal,  hezcast: C.signal,   federx: C.blue,
    resonaforge: C.purple,realtyscreen: C.blue, fadeforge: C.red,
    resilientai: C.amber, giftmode: C.ember,    fdse: C.red,
    webtemify: C.signal,  olvrix: C.ember,
  };

  if (loading) return <Loader />;

  const svc      = status?.services || {};
  const fw       = metrics?.flywheel || {};
  const bySource = metrics?.signal_sources || {};
  const prods    = metrics?.product_breakdown || [];

  return (
    <div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } } * { box-sizing: border-box; }`}</style>

      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.label, marginBottom: 6 }}>Tinlance Ecosystem</div>
        <h1 style={{ margin:0, fontSize:22, fontWeight:800, fontFamily:"'Syne', sans-serif", letterSpacing:"-0.03em" }}>
          The 17-Wire Flywheel
        </h1>
        <div style={{ color: C.mist, fontSize: 13, marginTop: 4 }}>
          {status?.online || 0} of 17 services online ·{" "}
          {fw.wires_active || 0} wires active ·{" "}
          {fw.total_leads || 0} total leads
        </div>
      </div>

      {/* Flywheel stats */}
      <div style={{ display:"flex", gap: 14, marginBottom: 20, flexWrap:"wrap" }}>
        {[
          { label:"Total leads",       value:(fw.total_leads||0).toLocaleString(),  color: C.snow },
          { label:"Campaigns run",     value: fw.total_campaigns||0,               color: C.snow },
          { label:"Total replies",     value: fw.total_replies||0,                  color: C.signal },
          { label:"Hot leads",         value: fw.hot_leads||0,                      color: C.ember },
          { label:"Opp signals",       value: fw.opportunity_signals||0,            color: C.purple },
          { label:"Flywheel velocity", value: `${fw.flywheel_velocity||0}x`,        color: C.signal },
        ].map((s, i) => (
          <div key={i} style={{ ...S.card, flex: 1, minWidth: 120 }}>
            <div style={{ ...S.label, marginBottom: 6 }}>{s.label}</div>
            <div style={{
              fontSize: 24, fontWeight: 800, color: s.color,
              fontFamily: "'JetBrains Mono', monospace", letterSpacing: "-0.02em",
            }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* Service grid — all 17 wires */}
      <div style={{ ...S.card, marginBottom: 20 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom: 16 }}>
          <h3 style={{ ...S.sectionTitle, margin: 0 }}>17 Product Wires</h3>
          <div style={{ display:"flex", gap: 12, fontSize: 11, color: C.mist }}>
            <span style={{ color: C.signal }}>● Online</span>
            <span style={{ color: C.amber }}>● Error</span>
            <span style={{ color: C.red }}>● Offline</span>
          </div>
        </div>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: 10,
        }}>
          {Object.entries(svc).map(([name, info]) => {
            const color = serviceColor(info.status);
            const pColor = PRODUCT_COLORS[name] || C.mist;
            return (
              <div key={name} style={{
                padding:"10px 14px", background: C.slate,
                borderRadius: 8, border: `1px solid ${C.wire}`,
                borderLeft: `3px solid ${pColor}`,
              }}>
                <div style={{ display:"flex", alignItems:"center", gap: 8, marginBottom: 4 }}>
                  <div style={{
                    width: 7, height: 7, borderRadius: "50%",
                    background: color, flexShrink: 0,
                  }} />
                  <span style={{ fontSize: 12.5, fontWeight: 600 }}>
                    {name.replace(/_/g," ").replace(/\b\w/g, c => c.toUpperCase())}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: C.mist, ...S.mono }}>
                  {info.status}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick sync actions */}
      <div style={{ ...S.card, marginBottom: 20 }}>
        <h3 style={{ ...S.sectionTitle }}>Sync data from ecosystem</h3>
        <div style={{ display:"flex", gap: 10, flexWrap:"wrap" }}>
          {[
            { key:"olvrix",       label:"Sync Olvrix CRM + Widgets", color: C.ember },
            { key:"resonaforge",  label:"Sync ResonaForge signals",   color: C.purple },
          ].map(s => (
            <button key={s.key}
              style={{
                ...S.btn("ghost"),
                borderColor: `${s.color}40`,
                color: s.color,
              }}
              onClick={() => syncSource(s.key)}
              disabled={syncing === s.key}
            >
              {syncing === s.key ? "Syncing..." : s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Pre-built campaigns */}
      <div style={S.card}>
        <h3 style={{ ...S.sectionTitle }}>
          Pre-built campaigns ({campaigns?.total || 0} available)
        </h3>
        <div style={{ display:"flex", flexDirection:"column", gap: 10 }}>
          {(campaigns?.campaigns || []).slice(0, 8).map((c, i) => {
            const key   = `${c.product}-${c.segment}`;
            const color = PRODUCT_COLORS[c.product] || C.mist;
            return (
              <div key={i} style={{
                display:"flex", justifyContent:"space-between", alignItems:"center",
                padding:"12px 16px", background: C.slate, borderRadius: 8,
                border: `1px solid ${C.wire}`, borderLeft: `3px solid ${color}`,
              }}>
                <div>
                  <div style={{ display:"flex", alignItems:"center", gap: 8, marginBottom: 4 }}>
                    <span style={{ ...S.badge(color) }}>{c.product}</span>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>→</span>
                    <span style={{ fontSize: 13, color: C.snow }}>{c.segment_label}</span>
                  </div>
                  <div style={{ fontSize: 11.5, color: C.mist, fontStyle:"italic" }}>
                    "{c.step1_preview}"
                  </div>
                </div>
                <button
                  style={S.btn("sm")}
                  onClick={() => launchCampaign(c.product, c.segment)}
                  disabled={launching === key}
                >
                  {launching === key ? "..." : "Launch"}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════
// VERTICAL INTELLIGENCE PACKS
// ═══════════════════════════════════════════════
export function VerticalsView({ onToast }) {
  const { get, post } = useApi();
  const [packs,    setPacks]    = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail,   setDetail]   = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [scoring,  setScoring]  = useState(false);
  const [scoreForm,setScoreForm]= useState({ company:"", domain:"", title:"" });
  const [scoreResult,setScoreResult] = useState(null);

  useEffect(() => {
    get("/api/verticals/packs")
      .then(d => setPacks(d.packs || []))
      .finally(() => setLoading(false));
  }, []);

  const loadDetail = async (id) => {
    setSelected(id);
    setDetail(null);
    setScoreResult(null);
    const res = await get(`/api/verticals/packs/${id}`);
    setDetail(res);
  };

  const scoreLead = async () => {
    if (!scoreForm.company) return;
    setScoring(true);
    const res = await post(`/api/verticals/packs/${selected}/score-lead`, {
      vertical: selected,
      ...scoreForm,
    });
    setScoreResult(res);
    setScoring(false);
  };

  const packColors = {
    nigerian_fintech:   C.signal,
    african_dev_agency: C.amber,
    eu_security_team:   C.purple,
    us_proptech:        C.blue,
  };

  if (loading) return <Loader />;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.label, marginBottom: 6 }}>Market intelligence</div>
        <h1 style={{ margin:0, fontSize:22, fontWeight:800, fontFamily:"'Syne', sans-serif", letterSpacing:"-0.03em" }}>
          Vertical Intelligence Packs
        </h1>
        <div style={{ color: C.mist, fontSize: 13, marginTop: 4 }}>
          Deep ICP knowledge, timing intelligence, cultural context, regulatory hooks
        </div>
      </div>

      {/* Pack selector */}
      <div style={{ display:"flex", gap: 12, marginBottom: 24, flexWrap:"wrap" }}>
        {packs.map(p => {
          const color = packColors[p.id] || C.signal;
          return (
            <div key={p.id}
              onClick={() => loadDetail(p.id)}
              style={{
                ...S.card, cursor:"pointer", flex: 1, minWidth: 200,
                borderColor: selected === p.id ? color : C.wire,
                background: selected === p.id ? `${color}08` : C.obs,
                transition: "all 0.15s",
              }}
            >
              <div style={{ fontSize: 24, marginBottom: 8 }}>{p.emoji}</div>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 4 }}>{p.name}</div>
              <div style={{ fontSize: 11.5, color: C.mist, marginBottom: 12 }}>{p.market_size}</div>
              <div style={{ display:"flex", flexWrap:"wrap", gap: 4 }}>
                {p.best_products.slice(0,3).map(prod => (
                  <span key={prod} style={{ ...S.badge(color), fontSize: 9 }}>{prod}</span>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Pack detail */}
      {detail && selected && (
        <div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap: 16, marginBottom: 16 }}>
            {/* ICP definition */}
            <div style={S.card}>
              <h3 style={S.sectionTitle}>ICP Definition</h3>
              <div style={{ marginBottom: 12 }}>
                <div style={{ ...S.label, marginBottom: 6 }}>Target titles</div>
                <div style={{ display:"flex", flexWrap:"wrap", gap: 5 }}>
                  {(detail.icp?.titles || []).map((t, i) => (
                    <span key={i} style={{
                      fontSize: 11.5, padding:"2px 8px",
                      background: C.slate, borderRadius: 4, color: C.snow,
                    }}>{t}</span>
                  ))}
                </div>
              </div>
              <div style={{ marginBottom: 12 }}>
                <div style={{ ...S.label, marginBottom: 6 }}>Company types</div>
                <div style={{ display:"flex", flexWrap:"wrap", gap: 5 }}>
                  {(detail.icp?.company_types || []).map((t, i) => (
                    <span key={i} style={{
                      fontSize: 11.5, padding:"2px 8px",
                      background: C.slate, borderRadius: 4, color: C.mist,
                    }}>{t}</span>
                  ))}
                </div>
              </div>
              <div>
                <div style={{ ...S.label, marginBottom: 6 }}>Signal keywords</div>
                <div style={{ ...S.mono, fontSize: 11, color: C.mist, lineHeight: 1.8 }}>
                  {(detail.icp?.keywords || []).join(" · ")}
                </div>
              </div>
            </div>

            {/* Pain points */}
            <div style={S.card}>
              <h3 style={S.sectionTitle}>Pain points</h3>
              {(detail.pain_points || []).map((p, i) => (
                <div key={i} style={{
                  display:"flex", alignItems:"flex-start", gap: 8,
                  padding:"7px 0", borderBottom:`1px solid ${C.wire}`,
                }}>
                  <span style={{ color: C.signal, fontSize: 12, flexShrink: 0, marginTop: 1 }}>→</span>
                  <span style={{ fontSize: 13, color: C.snow, lineHeight: 1.5 }}>{p}</span>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap: 16, marginBottom: 16 }}>
            {/* Objection handling */}
            <div style={S.card}>
              <h3 style={S.sectionTitle}>Objection handling</h3>
              {Object.entries(detail.objections || {}).map(([obj, res], i) => (
                <div key={i} style={{ marginBottom: 14 }}>
                  <div style={{
                    fontSize: 12.5, fontWeight: 600, color: C.amber,
                    marginBottom: 4,
                  }}>"{obj}"</div>
                  <div style={{ fontSize: 12.5, color: C.snow, lineHeight: 1.6 }}>{res}</div>
                </div>
              ))}
            </div>

            {/* Timing intelligence */}
            <div style={S.card}>
              <h3 style={S.sectionTitle}>Timing intelligence</h3>
              <div style={{ marginBottom: 14 }}>
                <div style={{ ...S.label, marginBottom: 6 }}>Best days</div>
                <div style={{ display:"flex", gap: 6 }}>
                  {(detail.timing?.best_days || []).map(d => (
                    <Badge key={d} color={C.signal}>{d}</Badge>
                  ))}
                </div>
              </div>
              <div style={{ marginBottom: 14 }}>
                <div style={{ ...S.label, marginBottom: 6 }}>Best hours</div>
                <div style={{ ...S.mono, fontSize: 13, color: C.snow }}>
                  {detail.timing?.best_hours}
                </div>
              </div>
              <div>
                <div style={{ ...S.label, marginBottom: 6 }}>Trigger events</div>
                {(detail.timing?.trigger_events || []).map((e, i) => (
                  <div key={i} style={{
                    fontSize: 12.5, color: C.mist,
                    padding:"4px 0", borderBottom:`1px solid ${C.wire}`,
                  }}>{e}</div>
                ))}
              </div>
            </div>
          </div>

          {/* Cultural context */}
          {(detail.cultural_context || []).length > 0 && (
            <div style={{ ...S.card, marginBottom: 16 }}>
              <h3 style={S.sectionTitle}>Cultural context</h3>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap: 8 }}>
                {detail.cultural_context.map((ctx, i) => (
                  <div key={i} style={{
                    padding:"10px 14px", background: C.slate, borderRadius: 8,
                    fontSize: 13, color: C.snow, lineHeight: 1.55,
                    borderLeft: `2px solid ${C.signal}`,
                  }}>
                    {ctx}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Lead scorer */}
          <div style={S.card}>
            <h3 style={S.sectionTitle}>Score a lead against this ICP</h3>
            <div style={{ display:"flex", gap: 10, marginBottom: 12, flexWrap:"wrap" }}>
              <input style={{ ...S.input, flex: 1, minWidth: 160 }}
                placeholder="Company name"
                value={scoreForm.company}
                onChange={e => setScoreForm({...scoreForm, company:e.target.value})} />
              <input style={{ ...S.input, flex: 1, minWidth: 140 }}
                placeholder="Domain (e.g. paystack.com)"
                value={scoreForm.domain}
                onChange={e => setScoreForm({...scoreForm, domain:e.target.value})} />
              <input style={{ ...S.input, flex: 1, minWidth: 140 }}
                placeholder="Title (e.g. CTO)"
                value={scoreForm.title}
                onChange={e => setScoreForm({...scoreForm, title:e.target.value})} />
              <button style={S.btn("sm")} onClick={scoreLead} disabled={scoring || !scoreForm.company}>
                {scoring ? "..." : "Score lead"}
              </button>
            </div>

            {scoreResult && (
              <div style={{
                padding:"16px", background: C.slate, borderRadius: 10,
                border: `1px solid ${scoreResult.is_icp ? C.signal : C.wire}`,
              }}>
                <div style={{ display:"flex", alignItems:"center", gap: 12, marginBottom: 12 }}>
                  <div style={{
                    width: 56, height: 56, borderRadius: "50%",
                    background: scoreResult.is_icp ? `${C.signal}18` : `${C.mist}18`,
                    display:"flex", alignItems:"center", justifyContent:"center",
                    fontSize: 20, fontWeight: 800, color: scoreResult.is_icp ? C.signal : C.mist,
                    fontFamily: "'JetBrains Mono', monospace", flexShrink: 0,
                  }}>
                    {scoreResult.icp_score}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>
                      {scoreResult.recommendation}
                    </div>
                    <div style={{ fontSize: 12, color: C.mist, marginTop: 3 }}>
                      {(scoreResult.score_reasons || []).join(" · ")}
                    </div>
                  </div>
                </div>
                {scoreResult.suggested_step1 && (
                  <div style={{
                    padding:"10px 14px", background: `${C.signal}08`,
                    borderRadius: 8, fontSize: 12.5, fontStyle:"italic",
                    borderLeft: `2px solid ${C.signal}`,
                  }}>
                    💬 "{scoreResult.suggested_step1}"
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// PUBLIC API MANAGEMENT
// ═══════════════════════════════════════════════
export function PublicAPIView({ onToast }) {
  const { get, post, del } = useApi();
  const [keys,       setKeys]       = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [creating,   setCreating]   = useState(false);
  const [newKey,     setNewKey]     = useState(null);
  const [docs,       setDocs]       = useState(null);
  const [form, setForm] = useState({
    name: "", description: "",
    scopes: ["leads:read", "campaigns:read"],
  });

  const SCOPES = [
    "leads:read", "leads:write",
    "campaigns:read", "campaigns:write",
    "inbox:read", "analytics:read",
    "opportunities:read", "domains:read",
    "webhooks:write",
  ];

  useEffect(() => {
    Promise.all([
      get("/api/public/keys"),
      get("/api/public/v1/docs"),
    ]).then(([k, d]) => {
      setKeys(k.api_keys || []);
      setDocs(d);
    }).finally(() => setLoading(false));
  }, []);

  const createKey = async () => {
    if (!form.name) { onToast("Name required", "error"); return; }
    setCreating(true);
    const res = await post("/api/public/keys", form);
    if (res.api_key) {
      setNewKey(res.api_key);
      setKeys(prev => [...prev, { ...res, name: form.name }]);
      setForm({ name:"", description:"", scopes:["leads:read","campaigns:read"] });
      onToast("API key created — save it now, shown once only");
    } else {
      onToast(res.detail || "Failed to create key", "error");
    }
    setCreating(false);
  };

  const revokeKey = async (keyId) => {
    await del(`/api/public/keys/${keyId}`);
    setKeys(prev => prev.filter(k => k.id !== keyId));
    onToast("API key revoked");
  };

  const toggleScope = (scope) => {
    setForm(prev => ({
      ...prev,
      scopes: prev.scopes.includes(scope)
        ? prev.scopes.filter(s => s !== scope)
        : [...prev.scopes, scope],
    }));
  };

  if (loading) return <Loader />;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.label, marginBottom: 6 }}>Integration</div>
        <h1 style={{ margin:0, fontSize:22, fontWeight:800, fontFamily:"'Syne', sans-serif", letterSpacing:"-0.03em" }}>
          Public API
        </h1>
        <div style={{ color: C.mist, fontSize: 13, marginTop: 4 }}>
          Connect FadeReach to Zapier, Make, n8n, and custom workflows
        </div>
      </div>

      {/* New key created — show once */}
      {newKey && (
        <div style={{
          ...S.card, marginBottom: 20,
          background: `${C.signal}08`,
          border: `1px solid ${C.signal}40`,
        }}>
          <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: C.signal }}>
            ⚠️ Save this API key now — shown only once
          </div>
          <div style={{
            ...S.mono, fontSize: 13, color: C.snow,
            padding:"12px 16px", background: C.slate, borderRadius: 8,
            wordBreak:"break-all", userSelect:"all",
          }}>
            {newKey}
          </div>
          <button style={{ ...S.btn("sm"), marginTop: 10 }}
            onClick={() => { navigator.clipboard.writeText(newKey); onToast("Copied"); }}>
            Copy to clipboard
          </button>
          <button style={{ ...S.btn("ghost"), marginTop: 10, marginLeft: 8 }}
            onClick={() => setNewKey(null)}>
            I've saved it
          </button>
        </div>
      )}

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap: 16, marginBottom: 16 }}>
        {/* Create key */}
        <div style={S.card}>
          <h3 style={S.sectionTitle}>Create API key</h3>
          <div style={{ marginBottom: 12 }}>
            <div style={{ ...S.label, marginBottom: 6 }}>Key name</div>
            <input style={S.input} placeholder="e.g. Zapier integration"
              value={form.name}
              onChange={e => setForm({...form, name:e.target.value})} />
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ ...S.label, marginBottom: 8 }}>Scopes</div>
            <div style={{ display:"flex", flexWrap:"wrap", gap: 6 }}>
              {SCOPES.map(scope => (
                <button key={scope}
                  style={{
                    padding:"4px 10px", borderRadius: 100, border:"none",
                    fontSize: 11, fontWeight: 600, cursor:"pointer",
                    background: form.scopes.includes(scope) ? C.signal : C.slate,
                    color: form.scopes.includes(scope) ? "#000" : C.mist,
                    fontFamily: "'JetBrains Mono', monospace",
                    transition:"all 0.15s",
                  }}
                  onClick={() => toggleScope(scope)}
                >
                  {scope}
                </button>
              ))}
            </div>
          </div>
          <button style={S.btn()} onClick={createKey} disabled={creating}>
            {creating ? "Creating..." : "Create API key"}
          </button>
        </div>

        {/* Active keys */}
        <div style={S.card}>
          <h3 style={S.sectionTitle}>Active keys ({keys.length}/5)</h3>
          {keys.length === 0 ? (
            <div style={{ fontSize: 13, color: C.mist }}>No API keys yet.</div>
          ) : keys.map(k => (
            <div key={k.id} style={{
              padding:"10px 0", borderBottom:`1px solid ${C.wire}`,
              display:"flex", justifyContent:"space-between", alignItems:"flex-start",
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{k.name}</div>
                <div style={{ ...S.mono, fontSize: 11, color: C.mist }}>{k.key_prefix}</div>
                {k.last_used && (
                  <div style={{ fontSize: 11, color: C.mist }}>
                    Last used: {new Date(k.last_used).toLocaleDateString()}
                  </div>
                )}
              </div>
              <button
                style={{ ...S.btn("ghost"), fontSize: 11, color: C.red, borderColor:`${C.red}30` }}
                onClick={() => revokeKey(k.id)}
              >
                Revoke
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Integration examples */}
      {docs?.integration_examples && (
        <div style={S.card}>
          <h3 style={S.sectionTitle}>Integration examples</h3>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap: 10 }}>
            {Object.entries(docs.integration_examples).map(([tool, example]) => (
              <div key={tool} style={{
                padding:"12px 14px", background: C.slate, borderRadius: 8,
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4, textTransform:"capitalize" }}>
                  {tool}
                </div>
                <div style={{ ...S.mono, fontSize: 11, color: C.mist, lineHeight: 1.6 }}>
                  {example}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// MANAGED SERVICES VIEW (Managed clients only)
// ═══════════════════════════════════════════════
export function ManagedView({ onToast }) {
  const { get } = useApi();
  const [client,  setClient]  = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get current tenant's managed client record
    get("/api/tenant/me").then(t => {
      if (t.plan === "managed") {
        setClient(t);
      }
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  if (!client || client.plan !== "managed") {
    return (
      <div style={{
        display:"flex", flexDirection:"column",
        alignItems:"center", justifyContent:"center",
        padding:"64px 24px", textAlign:"center", gap: 16,
        fontFamily:"'Inter', sans-serif", color: C.snow,
      }}>
        <div style={{ fontSize: 40 }}>✦</div>
        <h2 style={{
          fontFamily:"'Syne', sans-serif", fontWeight: 800,
          fontSize: 22, margin: 0, color: C.ember,
        }}>
          Managed Growth — $999/mo
        </h2>
        <p style={{ color: C.mist, fontSize: 14, maxWidth: 400, lineHeight: 1.65 }}>
          Done-for-you cold outreach. Lloyd manages your entire outreach operation —
          domain setup, warmup, lead building, campaigns, and weekly reports.
        </p>
        <div style={{ display:"flex", flexDirection:"column", gap: 8, maxWidth: 360, width:"100%" }}>
          {[
            "Domain purchase + DNS setup",
            "35-day inbox warmup, fully managed",
            "500 verified leads built monthly",
            "AI-written 4-step email sequences",
            "Weekly performance report",
            "Monthly strategy call (60 min)",
            "ThreatFade email security audit",
          ].map((f, i) => (
            <div key={i} style={{
              display:"flex", alignItems:"center", gap: 10,
              fontSize: 13, color: C.snow,
            }}>
              <span style={{ color: C.signal }}>✓</span>{f}
            </div>
          ))}
        </div>
        <a
          href="mailto:hello@fadereach.tinlance.com?subject=Managed Growth Enquiry"
          style={{
            ...S.btn("ember"),
            background: C.ember, color:"#000",
            padding:"13px 32px", fontSize: 14, borderRadius: 10,
            textDecoration:"none",
          }}
        >
          Book a call with Lloyd →
        </a>
        <div style={{ fontSize: 12, color: C.mist }}>3-month minimum · $999/mo</div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <div style={{ ...S.label, marginBottom: 6, color: C.ember }}>Managed Growth</div>
        <h1 style={{ margin:0, fontSize:22, fontWeight:800, fontFamily:"'Syne', sans-serif", letterSpacing:"-0.03em" }}>
          Your Managed Campaign
        </h1>
        <div style={{ color: C.mist, fontSize: 13, marginTop: 4 }}>
          Lloyd is managing your entire outreach operation.
        </div>
      </div>

      <div style={{
        ...S.card,
        background: `linear-gradient(135deg, ${C.ember}08, ${C.obs})`,
        border: `1px solid ${C.ember}30`,
        marginBottom: 20,
      }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>Active — Managed Growth</div>
        <div style={{ fontSize: 13, color: C.mist, lineHeight: 1.65 }}>
          Your outreach is running. Check your dashboard for campaign metrics,
          inbox replies, and hot leads flagged by the system.
        </div>
        <div style={{ marginTop: 16 }}>
          <a
            href="mailto:hello@fadereach.tinlance.com?subject=Strategy call request"
            style={{
              ...S.btn(), background: C.ember, color:"#000",
              textDecoration:"none",
            }}
          >
            Request strategy call
          </a>
        </div>
      </div>

      <div style={{ ...S.card }}>
        <h3 style={S.sectionTitle}>What Lloyd manages for you</h3>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap: 10 }}>
          {[
            { icon:"🌐", task:"Sending domain configured and verified" },
            { icon:"🔥", task:"35-day warmup running automatically" },
            { icon:"👥", task:"500 verified leads built this month" },
            { icon:"📧", task:"4-step sequence live and sending" },
            { icon:"📊", task:"Weekly performance report — every Sunday" },
            { icon:"🔴", task:"Hot leads flagged and routed to you instantly" },
            { icon:"📞", task:"Monthly strategy call scheduled" },
            { icon:"🛡️", task:"ThreatFade email security audit complete" },
          ].map((item, i) => (
            <div key={i} style={{
              display:"flex", gap: 10, padding:"10px 14px",
              background: C.slate, borderRadius: 8, alignItems:"center",
            }}>
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              <span style={{ fontSize: 13, color: C.snow }}>{item.task}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
