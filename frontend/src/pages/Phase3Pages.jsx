import { useState, useEffect, useCallback } from "react";

// ─────────────────────────────────────────────────────────
// FadeReach Phase 3 — Competitive Edge Pages
// Opportunity Feed · Learning Engine · A/B Testing · Graphify
// Same design tokens as App.jsx and SaaSPages.jsx
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
};

const S = {
  card: {
    background: C.obs,
    border: `1px solid ${C.wire}`,
    borderRadius: 12,
    padding: 22,
  },
  btn: (v = "primary") => ({
    display: "inline-flex", alignItems: "center", gap: 6,
    padding: v === "sm" ? "5px 12px" : "10px 20px",
    fontSize: v === "sm" ? 11.5 : 13.5, fontWeight: 600,
    borderRadius: 8, border: "none", cursor: "pointer",
    transition: "opacity 0.15s",
    background: v === "ghost" ? "transparent" : v === "danger" ? `${C.red}15` : C.signal,
    color: v === "ghost" ? C.mist : v === "danger" ? C.red : "#000",
    border: v === "ghost" ? `1px solid ${C.wire}` : "none",
    whiteSpace: "nowrap", textDecoration: "none",
  }),
  label: {
    fontSize: 10, fontWeight: 700, color: C.signal,
    letterSpacing: "0.12em", textTransform: "uppercase",
    fontFamily: "'JetBrains Mono', monospace",
  },
  mono: { fontFamily: "'JetBrains Mono', monospace", fontSize: 12.5 },
  badge: (color) => ({
    display: "inline-flex", padding: "2px 9px", borderRadius: 20,
    fontSize: 10, fontWeight: 700,
    background: `${color}18`, color: color,
    fontFamily: "'JetBrains Mono', monospace",
    textTransform: "uppercase", letterSpacing: "0.06em",
  }),
  input: {
    background: C.slate, border: `1px solid ${C.wire}`,
    borderRadius: 8, padding: "9px 14px", color: C.snow,
    fontSize: 13.5, outline: "none", width: "100%",
    boxSizing: "border-box", fontFamily: "inherit",
  },
  sectionTitle: {
    fontSize: 17, fontWeight: 700,
    fontFamily: "'Syne', sans-serif",
    letterSpacing: "-0.02em", margin: "0 0 16px",
  },
  divider: { height: 1, background: C.wire, margin: "16px 0", border: "none" },
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

// ── Mini components ─────────────────────────────
const Badge = ({ children, color = C.signal }) => (
  <span style={S.badge(color)}>{children}</span>
);

const Loader = () => (
  <div style={{ display:"flex", alignItems:"center", justifyContent:"center", padding:"48px 0" }}>
    <div style={{
      width: 24, height: 24, borderRadius: "50%",
      border: `3px solid ${C.wire}`, borderTopColor: C.signal,
      animation: "spin 0.8s linear infinite",
    }} />
  </div>
);

const EmptyState = ({ icon, title, body, action }) => (
  <div style={{
    display:"flex", flexDirection:"column", alignItems:"center",
    justifyContent:"center", padding:"48px 24px", textAlign:"center", gap: 12,
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
      position:"fixed", bottom: 24, right: 24, zIndex: 999,
      background: type === "error" ? `${C.red}20` : `${C.signal}18`,
      border: `1px solid ${type === "error" ? C.red : C.signal}`,
      borderRadius: 10, padding: "12px 18px",
      fontSize: 13.5, color: type === "error" ? C.red : C.signal,
      maxWidth: 340,
    }}>
      {type === "success" ? "✓ " : "✕ "}{msg}
    </div>
  );
};

// ═══════════════════════════════════════════════
// OPPORTUNITY FEED
// The #1 moat feature — "Here are 147 companies
// that became good prospects today"
// ═══════════════════════════════════════════════
export function OpportunityFeedView({ onToast }) {
  const { get, post } = useApi();
  const [feed,       setFeed]       = useState([]);
  const [summary,    setSummary]    = useState({});
  const [loading,    setLoading]    = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [acting,     setActing]     = useState(null);
  const [sourceFilter, setSourceFilter] = useState("all");
  const [minScore,   setMinScore]   = useState(60);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      get(`/api/opportunities/feed?min_score=${minScore}&limit=50`),
      get("/api/opportunities/signals/summary"),
    ]).then(([f, s]) => {
      setFeed(f.opportunities || []);
      setSummary(s);
    }).finally(() => setLoading(false));
  }, [minScore]);

  useEffect(() => { load(); }, [minScore]);

  const refresh = async () => {
    setRefreshing(true);
    await post("/api/opportunities/refresh", {});
    onToast("Feed refreshing — ready in ~30 seconds");
    setTimeout(load, 30000);
    setRefreshing(false);
  };

  const act = async (oppId, action, opp) => {
    setActing(oppId);
    const res = await post("/api/opportunities/action", {
      opportunity_id: oppId,
      action,
    });
    if (res.action === "added") {
      onToast(`${opp.email || opp.company} added to leads`);
    } else if (res.action === "dismissed") {
      setFeed(prev => prev.filter(o => o.id !== oppId));
    } else {
      onToast(res.action);
    }
    setActing(null);
  };

  const sourceColors = {
    olvrix:          C.signal,
    olvrix_widgets:  C.ember,
    resonaforge:     C.purple,
    threatfade:      C.red,
    reconos:         C.amber,
    apollo:          "#60A5FA",
    default:         C.mist,
  };

  const sourceLabels = {
    olvrix:          "Olvrix CRM",
    olvrix_widgets:  "Olvrix Widgets",
    resonaforge:     "ResonaForge",
    threatfade:      "ThreatFade",
    reconos:         "ReconOS",
    apollo:          "Apollo",
  };

  const filteredFeed = sourceFilter === "all"
    ? feed
    : feed.filter(o => o.source === sourceFilter);

  return (
    <div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      {/* Header */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ ...S.label, marginBottom: 6 }}>Signal intelligence</div>
          <h1 style={{ margin:0, fontSize:22, fontWeight:800, fontFamily:"'Syne', sans-serif", letterSpacing:"-0.03em" }}>
            Opportunity Feed
          </h1>
          <div style={{ color: C.mist, fontSize: 13, marginTop: 4 }}>
            {summary.total || 0} prospects discovered · {summary.hot || 0} hot leads
          </div>
        </div>
        <button style={S.btn()} onClick={refresh} disabled={refreshing}>
          {refreshing ? "Refreshing..." : "↺ Refresh feed"}
        </button>
      </div>

      {/* Signal source summary */}
      <div style={{ display:"flex", gap: 10, marginBottom: 20, flexWrap:"wrap" }}>
        <button
          style={{
            ...S.btn("ghost"),
            background: sourceFilter === "all" ? `${C.signal}15` : "transparent",
            color: sourceFilter === "all" ? C.signal : C.mist,
            borderColor: sourceFilter === "all" ? `${C.signal}40` : C.wire,
          }}
          onClick={() => setSourceFilter("all")}
        >
          All sources ({summary.total || 0})
        </button>
        {Object.entries(summary.by_source || {}).map(([src, count]) => (
          <button key={src}
            style={{
              ...S.btn("ghost"),
              background: sourceFilter === src ? `${sourceColors[src] || C.mist}15` : "transparent",
              color: sourceFilter === src ? (sourceColors[src] || C.mist) : C.mist,
              borderColor: sourceFilter === src ? `${sourceColors[src] || C.mist}40` : C.wire,
            }}
            onClick={() => setSourceFilter(src)}
          >
            {sourceLabels[src] || src} ({count})
          </button>
        ))}
      </div>

      {/* Score filter */}
      <div style={{ ...S.card, marginBottom: 20, padding:"14px 18px" }}>
        <div style={{ display:"flex", alignItems:"center", gap: 16 }}>
          <div style={{ ...S.label }}>Min score</div>
          <input
            type="range" min="40" max="90" step="5"
            value={minScore}
            onChange={e => setMinScore(Number(e.target.value))}
            style={{ flex: 1, accentColor: C.signal }}
          />
          <span style={{
            ...S.mono, color: C.signal, fontWeight: 700, fontSize: 15, minWidth: 30,
          }}>{minScore}</span>
        </div>
        <div style={{ fontSize: 11.5, color: C.mist, marginTop: 6 }}>
          Higher score = stronger buying signal. Hot leads (85+) from Olvrix Widgets are the warmest.
        </div>
      </div>

      {/* Feed */}
      {loading ? <Loader /> : filteredFeed.length === 0 ? (
        <EmptyState
          icon="🎯"
          title="No opportunities yet"
          body="Connect your Olvrix account and ResonaForge to start receiving signals. The feed refreshes every 30 minutes."
          action={<button style={S.btn()} onClick={refresh}>Refresh now</button>}
        />
      ) : (
        <div style={{ display:"flex", flexDirection:"column", gap: 12 }}>
          {filteredFeed.map(opp => {
            const srcColor = sourceColors[opp.source] || C.mist;
            return (
              <div key={opp.id} style={{
                ...S.card,
                borderColor: opp.is_hot ? `${C.ember}50` : C.wire,
                background: opp.is_hot
                  ? `linear-gradient(135deg, ${C.ember}06, ${C.obs})`
                  : C.obs,
              }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", gap: 12 }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    {/* Source + score */}
                    <div style={{ display:"flex", alignItems:"center", gap: 8, marginBottom: 8 }}>
                      <Badge color={srcColor}>{opp.source_label || opp.source}</Badge>
                      {opp.is_hot && <Badge color={C.ember}>🔥 Hot lead</Badge>}
                      <span style={{
                        ...S.mono, fontSize: 11, color: C.mist,
                      }}>
                        Signal score: <span style={{ color: opp.score >= 85 ? C.ember : C.signal, fontWeight: 700 }}>
                          {opp.score}
                        </span>
                      </span>
                    </div>

                    {/* Contact info */}
                    <div style={{ marginBottom: 6 }}>
                      {(opp.first_name || opp.last_name) && (
                        <span style={{ fontWeight: 600, fontSize: 14, marginRight: 8 }}>
                          {opp.first_name} {opp.last_name}
                        </span>
                      )}
                      {opp.title && (
                        <span style={{ fontSize: 12, color: C.mist }}>{opp.title}</span>
                      )}
                    </div>
                    <div style={{ display:"flex", alignItems:"center", gap: 10, marginBottom: 8 }}>
                      {opp.company && (
                        <span style={{ fontWeight: 600, fontSize: 13.5 }}>{opp.company}</span>
                      )}
                      {opp.domain && (
                        <span style={{ ...S.mono, fontSize: 11, color: C.signal }}>{opp.domain}</span>
                      )}
                    </div>
                    {opp.email && (
                      <div style={{ ...S.mono, fontSize: 11.5, color: C.mist, marginBottom: 8 }}>
                        {opp.email}
                      </div>
                    )}

                    {/* Signal detail */}
                    {opp.signal_data && (
                      <div style={{
                        fontSize: 12, color: C.mist, lineHeight: 1.55,
                        padding: "6px 10px",
                        background: C.slate, borderRadius: 6,
                        borderLeft: `2px solid ${srcColor}`,
                        marginBottom: opp.suggested_first_line ? 8 : 0,
                      }}>
                        {opp.source === "threatfade" && (
                          <>Security gap: <span style={{ color: C.amber }}>{opp.signal_data.gap_type?.replace(/_/g," ")}</span> ({opp.signal_data.severity})</>
                        )}
                        {opp.source === "reconos" && (
                          <>Signal: <span style={{ color: C.amber }}>{opp.signal_data.signal_type?.replace(/_/g," ")}</span> — {opp.signal_data.signal_detail}</>
                        )}
                        {opp.source === "resonaforge" && (
                          <>Engaged with: <span style={{ color: C.purple }}>{opp.signal_data.post_title}</span> ({opp.signal_data.engagement_count}x)</>
                        )}
                        {opp.source === "olvrix_widgets" && (
                          <>Widget: <span style={{ color: C.ember }}>{opp.widget_type}</span> on {opp.page_url}</>
                        )}
                        {opp.source === "olvrix" && "From Olvrix CRM contact database"}
                        {opp.source === "apollo" && `${opp.signal_data.seniority || ""} ${opp.signal_data.headline || "Job signal"}`}
                      </div>
                    )}

                    {/* AI-suggested first line */}
                    {opp.suggested_first_line && (
                      <div style={{
                        fontSize: 12, color: C.snow, fontStyle: "italic",
                        padding: "8px 12px", background: `${C.signal}08`,
                        borderRadius: 6, border: `1px solid ${C.signal}20`,
                      }}>
                        💬 "{opp.suggested_first_line}"
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div style={{ display:"flex", flexDirection:"column", gap: 8, flexShrink: 0 }}>
                    <button
                      style={S.btn("sm")}
                      onClick={() => act(opp.id, "add_to_campaign", opp)}
                      disabled={acting === opp.id}
                    >
                      {acting === opp.id ? "..." : "+ Add to leads"}
                    </button>
                    <button
                      style={S.btn("ghost")}
                      onClick={() => act(opp.id, "dismiss", opp)}
                      disabled={acting === opp.id}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// LEARNING ENGINE DASHBOARD
// ═══════════════════════════════════════════════
export function LearningView({ onToast }) {
  const { get, post } = useApi();
  const [insights,       setInsights]       = useState(null);
  const [recommendations,setRecommendations]= useState(null);
  const [graphStats,     setGraphStats]     = useState(null);
  const [loading,        setLoading]        = useState(true);
  const [optimizing,     setOptimizing]     = useState(false);

  useEffect(() => {
    Promise.all([
      get("/api/learning/insights"),
      get("/api/learning/recommendations"),
      get("/api/graphify/stats"),
    ]).then(([i, r, g]) => {
      setInsights(i);
      setRecommendations(r);
      setGraphStats(g);
    }).finally(() => setLoading(false));
  }, []);

  const runOptimization = async () => {
    setOptimizing(true);
    await post("/api/learning/optimize/run", {});
    onToast("Optimization running — insights updated in ~60 seconds");
    setTimeout(() => {
      get("/api/learning/insights").then(setInsights);
      setOptimizing(false);
    }, 60000);
  };

  if (loading) return <Loader />;

  const stage    = insights?.learning_stage || {};
  const bestTimes = insights?.best_send_times || [];
  const bestSubs  = insights?.best_subjects || [];
  const products  = insights?.product_performance || [];
  const recs      = recommendations || {};
  const gs        = graphStats || {};

  return (
    <div>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ ...S.label, marginBottom: 6 }}>AI Intelligence</div>
          <h1 style={{ margin:0, fontSize:22, fontWeight:800, fontFamily:"'Syne', sans-serif", letterSpacing:"-0.03em" }}>
            Learning Engine
          </h1>
          <div style={{ color: C.mist, fontSize: 13, marginTop: 4 }}>
            {insights?.data_points || 0} signals processed · {stage.label || "Bootstrap"}
          </div>
        </div>
        <button style={S.btn()} onClick={runOptimization} disabled={optimizing}>
          {optimizing ? "Optimizing..." : "Run optimization"}
        </button>
      </div>

      {/* Learning stage */}
      <div style={{
        ...S.card, marginBottom: 16,
        background: `linear-gradient(135deg, ${C.signal}06, ${C.obs})`,
        border: `1px solid ${C.signal}30`,
      }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom: 14 }}>
          <div>
            <div style={{ ...S.label, marginBottom: 6 }}>Learning stage</div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>{stage.label || "Bootstrap"}</div>
            <div style={{ fontSize: 13, color: C.mist, marginTop: 4, lineHeight: 1.5 }}>
              {stage.message}
            </div>
          </div>
          <div style={{
            ...S.mono, fontSize: 28, fontWeight: 800, color: C.signal, lineHeight: 1,
          }}>
            {stage.pct || 0}%
          </div>
        </div>
        <div style={{ height: 5, background: C.wire, borderRadius: 3 }}>
          <div style={{
            height:"100%", width:`${stage.pct || 0}%`,
            background: C.signal, borderRadius: 3,
            transition: "width 1s ease",
          }} />
        </div>
      </div>

      {/* AI Summary */}
      {insights?.ai_summary && (
        <div style={{
          ...S.card, marginBottom: 16,
          borderLeft: `3px solid ${C.signal}`,
        }}>
          <div style={{ ...S.label, marginBottom: 8 }}>AI insight</div>
          <div style={{ fontSize: 14, color: C.snow, lineHeight: 1.65 }}>
            {insights.ai_summary}
          </div>
        </div>
      )}

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap: 16, marginBottom: 16 }}>
        {/* Best send times */}
        <div style={S.card}>
          <h3 style={S.sectionTitle}>Best send times</h3>
          {bestTimes.length === 0 ? (
            <div style={{ fontSize: 13, color: C.mist }}>
              Send campaigns to build timing data.
            </div>
          ) : bestTimes.map((t, i) => (
            <div key={i} style={{
              display:"flex", justifyContent:"space-between", alignItems:"center",
              padding:"8px 0", borderBottom:`1px solid ${C.wire}`,
            }}>
              <span style={{ fontSize: 13 }}>{t.label}</span>
              <span style={{ ...S.mono, color: C.signal, fontWeight: 700 }}>
                {t.replies} replies
              </span>
            </div>
          ))}
          <div style={{ marginTop: 12, fontSize: 12, color: C.mist }}>
            Default: {recs.send_time}
          </div>
        </div>

        {/* Product performance */}
        <div style={S.card}>
          <h3 style={S.sectionTitle}>Product performance</h3>
          {products.length === 0 ? (
            <div style={{ fontSize: 13, color: C.mist }}>
              Launch campaigns per product to compare performance.
            </div>
          ) : products.map((p, i) => (
            <div key={i} style={{
              display:"flex", justifyContent:"space-between", alignItems:"center",
              padding:"8px 0", borderBottom:`1px solid ${C.wire}`,
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{p.product}</div>
                <div style={{ fontSize: 11, color: C.mist }}>{p.total_sent} sent</div>
              </div>
              <span style={{
                ...S.mono, fontWeight: 800, fontSize: 16,
                color: p.avg_reply_rate >= 5 ? C.signal : p.avg_reply_rate >= 3 ? C.amber : C.mist,
              }}>
                {p.avg_reply_rate}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      <div style={{ ...S.card, marginBottom: 16 }}>
        <h3 style={S.sectionTitle}>
          {recs.data_powered ? "Data-powered recommendations" : "Default recommendations"}
        </h3>
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap: 10 }}>
          {[
            { label:"Send window", value: recs.send_time },
            { label:"Sequence length", value: `${recs.sequence_length} emails` },
            { label:"Bounce target", value: recs.bounce_target },
            { label:"Daily volume", value: recs.optimal_volume },
          ].map((r, i) => (
            <div key={i} style={{
              padding:"12px 14px", background: C.slate, borderRadius: 8,
            }}>
              <div style={{ ...S.label, marginBottom: 4 }}>{r.label}</div>
              <div style={{ fontSize: 13.5, fontWeight: 600 }}>{r.value}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Graphify cost stats */}
      {gs.cost && (
        <div style={S.card}>
          <h3 style={S.sectionTitle}>Graphify cost savings</h3>
          <div style={{ display:"flex", gap: 20, flexWrap:"wrap", marginBottom: 16 }}>
            {[
              { label:"Without Graphify", value:`$${gs.cost.without_graphify}`, color: C.red },
              { label:"With Graphify",    value:`$${gs.cost.with_graphify}`,    color: C.signal },
              { label:"Saved this month", value:`$${gs.cost.saved_usd}`,        color: C.signal },
              { label:"Savings",          value:`${gs.cost.savings_pct}%`,      color: C.signal },
            ].map((s, i) => (
              <div key={i} style={{ textAlign:"center", minWidth: 100 }}>
                <div style={{ ...S.label, marginBottom: 4 }}>{s.label}</div>
                <div style={{
                  ...S.mono, fontSize: 22, fontWeight: 800, color: s.color,
                }}>{s.value}</div>
              </div>
            ))}
          </div>
          <div style={{ display:"flex", gap: 8 }}>
            <div style={{
              flex: 1, padding:"8px 12px", background: C.slate, borderRadius: 6,
              fontSize: 11.5, color: C.mist, textAlign:"center",
            }}>
              Exact cache hits: <span style={{ color: C.signal, fontWeight: 700 }}>
                {gs.hit_rate?.exact || 0}%
              </span>
            </div>
            <div style={{
              flex: 1, padding:"8px 12px", background: C.slate, borderRadius: 6,
              fontSize: 11.5, color: C.mist, textAlign:"center",
            }}>
              Semantic hits: <span style={{ color: C.signal, fontWeight: 700 }}>
                {gs.hit_rate?.semantic || 0}%
              </span>
            </div>
            <div style={{
              flex: 1, padding:"8px 12px", background: C.slate, borderRadius: 6,
              fontSize: 11.5, color: C.mist, textAlign:"center",
            }}>
              Full generation: <span style={{ color: C.amber, fontWeight: 700 }}>
                {gs.hit_rate?.miss || 0}%
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// A/B TESTING VIEW
// ═══════════════════════════════════════════════
export function ABTestingView({ onToast }) {
  const { get, post } = useApi();
  const [tests,     setTests]     = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [creating,  setCreating]  = useState(false);
  const [showCreate,setShowCreate]= useState(false);
  const [spintax,   setSpintax]   = useState("");
  const [spintaxResult, setSpintaxResult] = useState(null);
  const [form, setForm] = useState({
    campaign_id: "",
    test_type:   "subject",
    variant_a:   "",
    variant_b:   "",
    split:       50,
  });

  useEffect(() => {
    get("/api/testing/ab")
      .then(d => setTests(d.tests || []))
      .finally(() => setLoading(false));
  }, []);

  const createTest = async () => {
    if (!form.variant_a || !form.variant_b) {
      onToast("Fill in both variants", "error");
      return;
    }
    setCreating(true);
    const res = await post("/api/testing/ab/create", {
      campaign_id: parseInt(form.campaign_id) || null,
      test_type:   form.test_type,
      variants: [
        { label: "A", value: form.variant_a },
        { label: "B", value: form.variant_b },
      ],
      split_pct:  [form.split, 100 - form.split],
      min_sample: 100,
    });
    if (res.test_id) {
      onToast("A/B test created");
      setShowCreate(false);
      const d = await get("/api/testing/ab");
      setTests(d.tests || []);
    } else {
      onToast(res.detail || "Failed to create test", "error");
    }
    setCreating(false);
  };

  const previewSpintax = async () => {
    if (!spintax.trim()) return;
    const res = await post("/api/testing/spintax/preview", {
      template:   spintax,
      variations: 5,
    });
    setSpintaxResult(res);
  };

  const statusColor = s =>
    s === "running" ? C.signal : s === "complete" ? C.mist : C.amber;

  return (
    <div>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom: 24 }}>
        <div>
          <div style={{ ...S.label, marginBottom: 6 }}>Testing</div>
          <h1 style={{ margin:0, fontSize:22, fontWeight:800, fontFamily:"'Syne', sans-serif", letterSpacing:"-0.03em" }}>
            A/B Testing + Spintax
          </h1>
        </div>
        <button style={S.btn()} onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "Cancel" : "+ New A/B test"}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div style={{ ...S.card, marginBottom: 20 }}>
          <h3 style={{ ...S.sectionTitle, marginBottom: 16 }}>New A/B test</h3>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap: 12, marginBottom: 14 }}>
            <div>
              <div style={{ ...S.label, marginBottom: 6 }}>Test type</div>
              <select style={S.input} value={form.test_type}
                onChange={e => setForm({...form, test_type: e.target.value})}>
                <option value="subject">Subject line</option>
                <option value="first_line">First line / opener</option>
                <option value="cta">Call to action</option>
                <option value="send_time">Send time</option>
              </select>
            </div>
            <div>
              <div style={{ ...S.label, marginBottom: 6 }}>Campaign ID (optional)</div>
              <input style={S.input} placeholder="Leave blank for all"
                value={form.campaign_id}
                onChange={e => setForm({...form, campaign_id: e.target.value})} />
            </div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ ...S.label, marginBottom: 6 }}>Variant A</div>
            <input style={S.input} placeholder="Your email infrastructure has a gap"
              value={form.variant_a}
              onChange={e => setForm({...form, variant_a: e.target.value})} />
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ ...S.label, marginBottom: 6 }}>Variant B</div>
            <input style={S.input} placeholder="Quick question about {company}'s DMARC"
              value={form.variant_b}
              onChange={e => setForm({...form, variant_b: e.target.value})} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <div style={{ display:"flex", justifyContent:"space-between", fontSize:12, marginBottom: 6 }}>
              <span style={{ color: C.mist }}>Split</span>
              <span style={{ ...S.mono }}>A: {form.split}% · B: {100 - form.split}%</span>
            </div>
            <input type="range" min="30" max="70" step="5"
              value={form.split}
              onChange={e => setForm({...form, split: Number(e.target.value)})}
              style={{ width:"100%", accentColor: C.signal }} />
          </div>
          <button style={S.btn()} onClick={createTest} disabled={creating}>
            {creating ? "Creating..." : "Create A/B test"}
          </button>
        </div>
      )}

      {/* Active tests */}
      {loading ? <Loader /> : (
        <div style={{ marginBottom: 20 }}>
          <h3 style={{ ...S.sectionTitle }}>Active tests</h3>
          {tests.length === 0 ? (
            <EmptyState
              icon="🧪"
              title="No A/B tests yet"
              body="Create your first test to start optimizing. Need at least 100 sends per variant for statistical significance."
              action={<button style={S.btn()} onClick={() => setShowCreate(true)}>Create first test</button>}
            />
          ) : tests.map(t => (
            <div key={t.id} style={{ ...S.card, marginBottom: 10 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                <div>
                  <div style={{ display:"flex", alignItems:"center", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 600, fontSize: 13.5 }}>
                      {t.test_type.replace(/_/g," ").toUpperCase()} test #{t.id}
                    </span>
                    <Badge color={statusColor(t.status)}>{t.status}</Badge>
                    {t.winner && <Badge color={C.signal}>Winner: {t.winner}</Badge>}
                  </div>
                  <div style={{ fontSize: 12, color: C.mist }}>
                    Started {new Date(t.started_at).toLocaleDateString()}
                    {t.campaign_id && ` · Campaign #${t.campaign_id}`}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Spintax section */}
      <div style={{ ...S.card }}>
        <h3 style={{ ...S.sectionTitle }}>Spintax — Phrase Rotation</h3>
        <div style={{ fontSize: 13, color: C.mist, marginBottom: 16, lineHeight: 1.6 }}>
          Use <code style={{ ...S.mono, background: C.slate, padding:"1px 6px", borderRadius: 4 }}>
            {"{"}option1|option2|option3{"}"}
          </code> syntax to rotate phrases. Each prospect gets a unique variation — prevents spam fingerprinting.
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ ...S.label, marginBottom: 6 }}>Template</div>
          <textarea
            style={{ ...S.input, height: 80, resize:"vertical" }}
            placeholder="{Hi|Hey|Hello} {{first_name}}, noticed {your team|the team} at {{company}} is {growing fast|expanding quickly}..."
            value={spintax}
            onChange={e => setSpintax(e.target.value)}
          />
        </div>
        <button style={S.btn("ghost")} onClick={previewSpintax}>
          Preview variations
        </button>

        {spintaxResult && (
          <div style={{ marginTop: 16 }}>
            <div style={{ display:"flex", justifyContent:"space-between", marginBottom: 10 }}>
              <div style={{ ...S.label }}>Variations</div>
              <span style={{
                fontSize: 12, color: spintaxResult.diversity_score >= 70 ? C.signal : C.amber,
              }}>
                Diversity: {spintaxResult.diversity_score}%
              </span>
            </div>
            {(spintaxResult.variations || []).map((v, i) => (
              <div key={i} style={{
                padding:"10px 12px", marginBottom: 8,
                background: C.slate, borderRadius: 8,
                fontSize: 13, color: C.snow, lineHeight: 1.5,
                borderLeft: `2px solid ${C.signal}`,
              }}>
                {v}
              </div>
            ))}
            <div style={{ fontSize: 12, color: C.mist, marginTop: 8 }}>
              {spintaxResult.tip}
            </div>
          </div>
        )}

        {/* Spintax templates */}
        <hr style={S.divider} />
        <div style={{ ...S.label, marginBottom: 10 }}>Quick templates</div>
        <div style={{ display:"flex", flexWrap:"wrap", gap: 8 }}>
          {[
            "{Quick question|Brief thought|One thing} about {{company}}",
            "{Hi|Hey|Hello} {{first_name}},",
            "{Worth a quick chat?|Open to 15 minutes?|Relevant to explore?}",
            "{Best|Cheers|Thanks} — Lloyd",
          ].map((t, i) => (
            <button key={i}
              style={{ ...S.btn("ghost"), fontSize: 11.5 }}
              onClick={() => setSpintax(t)}
            >
              {t.substring(0, 30)}...
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
