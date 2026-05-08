import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import os
import html as html_module
from dotenv import load_dotenv

load_dotenv(override=True)

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8000")

st.set_page_config(
    page_title="TubePulse · YouTube Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS injection (single call, no nesting issues) ─────────────────────
CSS = """
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
html, body, [class*="css"], .stApp {
    background: #fdfdfd !important;
    color: #1e293b !important;
    font-family: 'Inter', sans-serif !important;
}
h1, h2, h3, .stHeading {
    font-family: 'Outfit', sans-serif !important;
}
#MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
    visibility: hidden !important;
    display: none !important;
}
section[data-testid="stSidebar"] {
    background-color: #fff5f5 !important;
    border-right: 1px solid #fee2e2 !important;
}
.stButton > button {
    background: linear-gradient(135deg, #FF0000 0%, #CC0000 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.6rem 1.5rem !important;
    font-weight: 700 !important;
    font-family: 'Outfit', sans-serif !important;
    letter-spacing: 0.5px !important;
    box-shadow: 0 4px 15px rgba(255, 0, 0, 0.2) !important;
    transition: all 0.3s ease !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(255, 0, 0, 0.3) !important;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────
def fmt_num(n):
    try:
        v = float(n)
    except (TypeError, ValueError):
        return "0"
    if abs(v) >= 1_000_000:
        return f"{v/1_000_000:.2f}M"
    if abs(v) >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{v:,.0f}"


def fmt_money(n):
    try:
        return f"${float(n):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def card(label, value, delta=None, delta_label="vs start", color="#FF0000", money=False):
    delta_part = ""
    if delta is not None:
        sign = "+" if delta >= 0 else ""
        bg   = "#dcfce7" if delta >= 0 else "#fee2e2"
        tc   = "#15803d" if delta >= 0 else "#b91c1c"
        txt  = fmt_money(delta) if money else fmt_num(delta)
        delta_part = (
            '<div style="margin-top:12px;display:flex;align-items:center;gap:8px;">'
            f'<span style="background:{bg};color:{tc};padding:4px 12px;border-radius:20px;'
            f'font-size:13px;font-weight:700;">{sign}{txt}</span>'
            f'<span style="color:#64748b;font-size:12px;font-weight:500;">{delta_label}</span>'
            '</div>'
        )

    html = (
        f'<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;'
        f'border-top:5px solid {color};'
        'padding:20px 24px;box-shadow:0 4px 18px rgba(0,0,0,.08);height:100%;'
        'transition:transform 0.2s ease;">'
        '<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1px;color:#64748b;margin-bottom:10px;">{label}</div>'
        f'<div style="font-size:32px;font-weight:800;color:#111111;line-height:1;font-family:Outfit,sans-serif;">{value}</div>'
        + delta_part +
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

def style_plotly(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,1)",
        font=dict(color="#64748b", family="Inter"),
        xaxis=dict(gridcolor="#f1f5f9", linecolor="#e2e8f0"),
        yaxis=dict(gridcolor="#f1f5f9", linecolor="#e2e8f0"),
        legend=dict(font=dict(color="#111")),
        margin=dict(l=10, r=10, t=40, b=10),
        hoverlabel=dict(bgcolor="#fff", bordercolor="#e2e8f0", font=dict(color="#111")),
    )
    return fig


def add_today_line(fig, last_dt, y_min, y_max):
    """Draw 'Today' as a Scatter trace instead of add_vline (avoids int+str TypeError)."""
    if last_dt is None:
        return fig
    fig.add_trace(go.Scatter(
        x=[last_dt, last_dt], y=[y_min, y_max],
        mode="lines", name="Today",
        line=dict(color="#64748b", dash="dot", width=1.5),
        showlegend=False,
    ))
    fig.add_annotation(
        x=last_dt, y=y_max, text=" Today",
        showarrow=False, font=dict(color="#64748b", size=11), xanchor="left",
    )
    return fig


# ── Header ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:14px;padding:4px 0 20px 0;
            border-bottom:2px solid #e2e8f0;margin-bottom:28px;">
    <div style="width:42px;height:42px;border-radius:10px;background:#e00;
                display:flex;align-items:center;justify-content:center;
                color:#fff;font-size:22px;box-shadow:0 4px 12px rgba(220,0,0,.35);">▶</div>
    <div>
        <div style="font-size:22px;font-weight:800;letter-spacing:-.5px;color:#111;">
            Tube<span style="color:#e00;">Pulse</span>
        </div>
        <div style="font-size:12px;color:#64748b;font-weight:600;">
            Growth · Forecast · Revenue
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎯 Run Analysis")
    channel_file = st.file_uploader("Channel Data (CSV)", type=["csv"])
    video_file = st.file_uploader("Video Data (CSV) — Optional", type=["csv"])
    st.divider()
    cpm_input = st.number_input("Estimated CPM ($)", min_value=0.1, value=5.0, step=0.5)
    forecast_period_input = st.selectbox(
        "Forecast Period",
        options=[30, 90, 180, 365],
        index=0,
        format_func=lambda x: f"{x} Days",
    )
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("⚡ Analyze Now", type="primary", use_container_width=True)
    
    st.divider()
    st.markdown("### ⚙️ Pipeline Management")
    if st.button("🔄 Retrain All Models", use_container_width=True):
        with st.spinner("Retraining full ML pipeline..."):
            try:
                res = requests.post(f"{FASTAPI_URL}/retrain", timeout=300)
                if res.status_code == 200:
                    st.success("✅ Models retrained & saved!")
                else:
                    st.error("Failed to retrain pipeline.")
            except Exception as e:
                st.error(f"Error: {e}")


# ── Landing page (no file uploaded yet) ──────────────────────────────────
if channel_file is None:
    if analyze_btn:
        st.warning("⚠️ Please upload your Channel Data CSV in the sidebar first.")
    st.markdown("""
    <div style="text-align:center;padding:60px 0 40px;">
        <div style="display:inline-block;background:rgba(220,0,0,.08);color:#e00;
                    padding:8px 24px;border-radius:999px;font-size:16px;
                    font-weight:700;letter-spacing:1px;margin-bottom:24px;">
            CREATOR INTELLIGENCE PLATFORM
        </div>
        <h1 style="font-size:clamp(36px,5vw,60px);font-weight:800;
                   line-height:1.1;letter-spacing:-1.5px;color:#111;margin:0;">
            Forecasting the Future of<br>
            <span style="color:#e00;">YouTube Growth.</span>
        </h1>
        <p style="font-size:20px;color:#64748b;max-width:650px;
                  margin:20px auto 0;line-height:1.7;">
            Turn your analytics into subscriber forecasts, revenue projections,
            and smart growth strategies.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        card("📈 Subscriber Forecast", "Prophet ML Engine")
    with c2:
        card("💰 Revenue Projection", "CPM × Views Model")
    with c3:
        card("🤖 AI Strategy", "Google Gemini")
    st.stop()

# File uploaded but analyze not clicked yet — show a prompt
if not analyze_btn:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;">
        <div style="font-size:48px;margin-bottom:20px;">📂</div>
        <h2 style="color:#111;font-size:26px;font-weight:800;margin:0 0 12px;">File ready!</h2>
        <p style="color:#64748b;font-size:16px;">
            Your CSV is uploaded. Set your CPM and forecast period,<br>
            then click <b style="color:#e00;">⚡ Analyze Now</b> in the sidebar.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Run Analysis ─────────────────────────────────────────────────────────
if analyze_btn:
    with st.spinner("🔮 Analyzing data and generating AI insights..."):
        try:
            files = {"channel_file": (channel_file.name, channel_file.getvalue(), "text/csv")}
            if video_file:
                files["video_file"] = (video_file.name, video_file.getvalue(), "text/csv")

            response = requests.post(
                f"{FASTAPI_URL}/analyze",
                files=files,
                data={"cpm": cpm_input, "forecast_periods": forecast_period_input},
                timeout=300,
            )

            if response.status_code != 200:
                st.error(f"Backend error {response.status_code}: {response.text}")
                st.stop()

            result = response.json()
            if result.get("status") != "success":
                st.error(f"Analysis failed: {result.get('message', 'Unknown error')}")
                st.stop()

            # Store in session state for persistence
            d = result["data"]
            
            # 1. Process Channel Features
            cf = pd.DataFrame(d["channel_features"])
            cf["date"] = pd.to_datetime(cf["date"])
            cf = cf.sort_values("date")
            
            # 2. Process Forecasts
            s_fc = pd.DataFrame(d["forecasts"]["subscribers"])
            if not s_fc.empty:
                s_fc["ds"] = pd.to_datetime(s_fc["ds"])
                s_fc = s_fc.sort_values("ds")
                
            v_fc = pd.DataFrame(d["forecasts"]["total_views"])
            if not v_fc.empty:
                v_fc["ds"] = pd.to_datetime(v_fc["ds"])
                v_fc = v_fc.sort_values("ds")
            
            st.session_state.analysis_data = {
                "channel_features": cf,
                "sub_fc": s_fc,
                "view_fc": v_fc,
                "projected_revenue": float(d["forecasts"].get("projected_revenue", 0)),
                "weekend_analysis": d.get("weekend_analysis") or {},
                "genai_insights": d.get("genai_insights", ""),
                "rule_insights": d.get("rule_insights", []),
                "accuracy_metrics": d.get("accuracy_metrics", {}),
                "last_forecast_period": forecast_period_input,
                "last_cpm": cpm_input
            }

        except requests.exceptions.ConnectionError:
            st.error(f"❌ Cannot connect to backend at **{FASTAPI_URL}**. Is `uvicorn src.api:app --reload` running?")
            st.stop()
        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.stop()

# ── Load from Session State ───────────────────────────────────────────
if "analysis_data" not in st.session_state:
    st.stop()

ad = st.session_state.analysis_data
channel_features = ad["channel_features"]
sub_fc = ad["sub_fc"]
view_fc = ad["view_fc"]
projected_revenue = ad["projected_revenue"]
weekend_analysis = ad["weekend_analysis"]
genai_insights = ad["genai_insights"]
rule_insights = ad["rule_insights"]
active_forecast_period = ad["last_forecast_period"]
active_cpm = ad["last_cpm"]


# ── Derived metrics ────────────────────────────────────────────────────
# ── Derived metrics ────────────────────────────────────────────────────
latest = channel_features.iloc[-1] if not channel_features.empty else None
first  = channel_features.iloc[0]  if not channel_features.empty else None

def safe_float(row, col):
    if row is None: return 0.0
    try: return float(row.get(col, 0) or 0)
    except: return 0.0

current_subs  = safe_float(latest, "subscribers")
start_subs    = safe_float(first,  "subscribers")
sub_increase  = current_subs - start_subs

current_views = safe_float(latest, "total_views")
start_views   = safe_float(first,  "total_views")
view_increase = current_views - start_views

total_revenue = float(channel_features["revenue"].sum()) if "revenue" in channel_features.columns else 0.0

# Ensure we are taking the absolute last value of the forecast
final_total_subs_pred  = float(sub_fc["yhat"].iloc[-1])  if not sub_fc.empty  else current_subs
final_total_views_pred = float(view_fc["yhat"].iloc[-1]) if not view_fc.empty else current_views

# Calculate the NET growth over the forecast period
net_sub_growth  = final_total_subs_pred - current_subs
net_view_growth = final_total_views_pred - current_views

start_date = str(first.get("date", "—"))[:10] if first is not None else "—"
end_date   = str(latest.get("date", "—"))[:10] if latest is not None else "—"
weekend_diff = float(weekend_analysis.get("weekend_view_diff_pct", 0))


# ── Executive Summary ─────────────────────────────────────────────────
st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
    <h2 style="margin:0;font-size:20px;font-weight:800;color:#111;">Executive Summary</h2>
    <span style="background:#f1f5f9;padding:4px 14px;border-radius:20px;
                 font-size:12px;font-weight:600;color:#475569;">
        {start_date} → {end_date}
    </span>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    card("Current Subscribers", fmt_num(current_subs), delta=sub_increase, delta_label="since start")
with c2:
    card("Total Views", fmt_num(current_views), delta=view_increase, delta_label="since start")
with c3:
    card("Historical Revenue", fmt_money(total_revenue))
with c4:
    card("Weekend vs Weekday", f"{weekend_diff:+.1f}%")

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)


# ── Revenue Hero ───────────────────────────────────────────────────────
st.markdown(f"""
<div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;
            padding:32px 36px;box-shadow:0 4px 20px rgba(0,0,0,.04);
            margin-bottom:28px;position:relative;overflow:hidden;">
    <div style="position:absolute;top:-60px;right:-60px;width:240px;height:240px;
                border-radius:50%;background:radial-gradient(circle,rgba(220,0,0,.06),transparent 70%);"></div>
    <div style="font-size:13px;font-weight:700;color:#e00;text-transform:uppercase;
                letter-spacing:1px;margin-bottom:10px;">
        💰 Projected Revenue · Next {forecast_period_input} Days
    </div>
    <div style="font-size:52px;font-weight:800;color:#111;letter-spacing:-2px;line-height:1;">
        {fmt_money(projected_revenue)}
    </div>
    <div style="color:#64748b;font-size:14px;margin-top:10px;">
        Based on CPM of <b>${cpm_input:.2f}</b> applied to forecasted views.
    </div>
    <div style="display:flex;gap:16px;margin-top:20px;flex-wrap:wrap;">
        <div style="background:#f8f9fc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 20px;">
            <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;
                        letter-spacing:.8px;margin-bottom:4px;">Historical Revenue</div>
            <div style="font-size:22px;font-weight:800;color:#111;">{fmt_money(total_revenue)}</div>
        </div>
        <div style="background:#f8f9fc;border:1px solid #e2e8f0;border-radius:10px;padding:14px 20px;">
            <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;
                        letter-spacing:.8px;margin-bottom:4px;">Total Lifetime Projected</div>
            <div style="font-size:22px;font-weight:800;color:#e00;">{fmt_money(total_revenue + projected_revenue)}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Forecast Summary ───────────────────────────────────────────────────
st.markdown(f"""
<h2 style="font-size:20px;font-weight:800;color:#111;margin:0 0 16px 0;">
    Forecast · <span style="color:#e00;">{active_forecast_period} Days</span>
</h2>
""", unsafe_allow_html=True)

fc1, fc2, fc3 = st.columns(3)
with fc1:
    card("Total Subscribers", fmt_num(final_total_subs_pred), delta=net_sub_growth, delta_label="growth vs today")
with fc2:
    card("Total Views", fmt_num(final_total_views_pred), delta=net_view_growth, delta_label="growth vs today")
with fc3:
    card("Projected Revenue", fmt_money(projected_revenue), delta=projected_revenue, delta_label="next period", money=True)
    
st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
acc_metrics = ad.get("accuracy_metrics", {})
if acc_metrics:
    m1, m2, m3 = st.columns(3)
    with m1:
        acc = acc_metrics.get("subscribers", {}).get("accuracy", 0)
        card("Subscriber Model Accuracy", f"{acc}%", color="#27ae60")
    with m2:
        mae = acc_metrics.get("total_views", {}).get("mae", 0)
        card("View Forecast Error (MAE)", fmt_num(mae), color="#f39c12")
    with m3:
        mape = acc_metrics.get("total_views", {}).get("mape", 0)
        card("View Error Rate (MAPE)", f"{mape}%", color="#f39c12")

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)


# ── AI Insights + Alerts ───────────────────────────────────────────────
st.markdown("<h2 style='font-size:20px;font-weight:800;color:#111;margin:0 0 12px 0;'>🔔 System Alerts</h2>", unsafe_allow_html=True)
rule_insights = d.get("rule_insights", [])

alerts_html = ""
if not rule_insights:
    alerts_html = "<div style='color:#64748b;font-size:14px;padding:8px 0;'>No active alerts. Everything looks good!</div>"
else:
    for alert in rule_insights:
        if "⚠️" in alert:
            bg, border, tc, ico = "#fffbeb", "#fde68a", "#b45309", "⚠️"
        elif "✅" in alert:
            bg, border, tc, ico = "#f0fdf4", "#bbf7d0", "#15803d", "✅"
        else:
            bg, border, tc, ico = "#f0f9ff", "#bae6fd", "#0369a1", "ℹ️"
        clean = alert.replace("⚠️", "").replace("✅", "").strip()
        alerts_html += f"""
        <div style="background:{bg};border:1px solid {border};color:{tc};
                    border-radius:8px;padding:12px 14px;margin-bottom:10px;
                    font-size:13px;display:flex;gap:10px;align-items:flex-start;">
            <span>{ico}</span><span>{clean}</span>
        </div>"""

st.markdown(f"""
<div style="background:#fff;border:1px solid #e2e8f0;border-radius:14px;padding:20px;
            box-shadow:0 2px 12px rgba(0,0,0,.04);margin-bottom:28px;">{alerts_html}</div>
""", unsafe_allow_html=True)

st.markdown("<h2 style='font-size:22px;font-weight:800;color:#0f172a;margin:0 0 16px 0;'>✨ AI Strategic Insights</h2>",
            unsafe_allow_html=True)
ai_text = d.get("genai_insights", "No AI insights available.")

# Combine the styled div and markdown text into a single block to fix rendering
st.markdown(f"""
<div style="background:#ffffff;border:1px solid #e2e8f0;border-left:6px solid #FF0000;
            border-radius:16px;padding:32px;box-shadow:0 10px 15px -3px rgba(0,0,0,0.05);
            margin-bottom:28px; line-height:1.7; color:#334155;">
{ai_text}
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)


# ── Growth Charts ──────────────────────────────────────────────────────
st.markdown("<h2 style='font-size:20px;font-weight:800;color:#111;margin:0 0 16px 0;'>📈 Growth Trajectory</h2>",
            unsafe_allow_html=True)

# Explicitly pull latest from session state to ensure no stale data
cf_plot = st.session_state.analysis_data["channel_features"]
s_fc_plot = st.session_state.analysis_data["sub_fc"]
v_fc_plot = st.session_state.analysis_data["view_fc"]
last_date_plot = cf_plot["date"].iloc[-1] if not cf_plot.empty else None

tab1, tab2 = st.tabs(["👥  Subscribers", "👁️  Total Views"])

with tab1:
    if not cf_plot.empty and "subscribers" in cf_plot.columns:
        # 1. Clean and align forecast
        sub_fc_future = s_fc_plot[s_fc_plot["ds"] > last_date_plot].copy() if last_date_plot is not None else s_fc_plot.copy()
        
        # Integration check: ensure forecast continues from the last historical point
        cur_subs = float(cf_plot["subscribers"].iloc[-1])
        if not sub_fc_future.empty:
             first_f = sub_fc_future["yhat"].iloc[0]
             # FORCE stacking if the forecast is clearly just a daily gain or starting from near-zero
             if first_f < cur_subs * 0.8 or first_f < 500:
                 sub_fc_future["yhat"] = cur_subs + sub_fc_future["yhat"].cumsum()

        # Get values as pure lists to strip any pandas index behavior
        x_hist = cf_plot["date"].dt.strftime('%Y-%m-%d').tolist()
        y_hist = [float(v) for v in cf_plot["subscribers"]]
        
        # 1. Clean and align forecast
        sub_fc_future = s_fc_plot[s_fc_plot["ds"] > last_date_plot].copy() if last_date_plot is not None else s_fc_plot.copy()
        
        # Integration check: ensure forecast continues from the last historical point
        cur_subs = y_hist[-1] if y_hist else 0
        if not sub_fc_future.empty:
             # If the forecast looks like a daily gain (starts small), stack it
             if sub_fc_future["yhat"].iloc[0] < cur_subs * 0.8:
                 sub_fc_future["yhat"] = cur_subs + sub_fc_future["yhat"].cumsum()

        x_fore = sub_fc_future["ds"].dt.strftime('%Y-%m-%d').tolist()
        y_fore = [float(v) for v in sub_fc_future["yhat"]]

        y_all_sub = y_hist + y_fore
        y_min_s, y_max_s = min(y_all_sub), max(y_all_sub)
        yr_s = y_max_s - y_min_s
        yp_min_s = max(0, y_min_s - (yr_s * 0.1))
        yp_max_s = y_max_s + (yr_s * 0.1)
        
        fig_sub = go.Figure()
        fig_sub.add_trace(go.Scatter(
            x=x_hist, y=y_hist,
            name="Historical Total", mode="lines",
            line=dict(color="#e00000", width=3),
            fill="tozeroy", fillcolor="rgba(220,0,0,0.08)",
            hovertemplate="Historical: %{y:,.0f}<extra></extra>"
        ))
        if not sub_fc_future.empty:
            fig_sub.add_trace(go.Scatter(
                x=x_fore, y=y_fore,
                name=f"{active_forecast_period}-Day Forecast", mode="lines",
                line=dict(color="#00c853", width=3, dash="dash"),
                fill="tozeroy", fillcolor="rgba(0,200,83,0.07)",
                hovertemplate="Forecast: %{y:,.0f}<extra></extra>"
            ))
            
        fig_sub = add_today_line(fig_sub, last_date_plot, yp_min_s, yp_max_s)
        fig_sub = style_plotly(fig_sub)
        fig_sub.update_layout(
            title="Subscriber Growth Trajectory",
            hovermode="x unified",
            yaxis=dict(range=[yp_min_s, yp_max_s], tickformat=",")
        )
        st.plotly_chart(fig_sub, use_container_width=True)
    else:
        st.info("Insufficient subscriber data.")

with tab2:
    if not cf_plot.empty and "total_views" in cf_plot.columns:
        view_fc_future = v_fc_plot[v_fc_plot["ds"] > last_date_plot].copy() if last_date_plot is not None else v_fc_plot.copy()
        
        # Get values as pure lists
        x_h_v = cf_plot["date"].dt.strftime('%Y-%m-%d').tolist()
        y_h_v = [float(v) for v in cf_plot["total_views"]]
        
        # Integration check for views
        cur_views = y_h_v[-1] if y_h_v else 0
        if not view_fc_future.empty:
             if view_fc_future["yhat"].iloc[0] < cur_views * 0.8:
                 view_fc_future["yhat"] = cur_views + view_fc_future["yhat"].cumsum()

        x_f_v = view_fc_future["ds"].dt.strftime('%Y-%m-%d').tolist()
        y_f_v = [float(v) for v in view_fc_future["yhat"]]

        y_all_v = y_h_v + y_f_v
        y_min_v, y_max_v = min(y_all_v), max(y_all_v)
        yr_v = y_max_v - y_min_v
        yp_min_v = max(0, y_min_v - (yr_v * 0.1))
        yp_max_v = y_max_v + (yr_v * 0.1)
        
        fig_view = go.Figure()
        fig_view.add_trace(go.Scatter(
            x=x_h_v, y=y_h_v,
            name="Historical Views", mode="lines",
            line=dict(color="#111111", width=3),
            fill="tozeroy", fillcolor="rgba(17,17,17,0.06)",
            hovertemplate="Views: %{y:,.0f}<extra></extra>"
        ))
        if not view_fc_future.empty:
            fig_view.add_trace(go.Scatter(
                x=x_f_v, y=y_f_v,
                name=f"{active_forecast_period}-Day Views Forecast", mode="lines",
                line=dict(color="#0090ff", width=3, dash="dash"),
                fill="tozeroy", fillcolor="rgba(0,144,255,0.08)",
                hovertemplate="Forecast: %{y:,.0f}<extra></extra>"
            ))
            
        fig_view = add_today_line(fig_view, last_date_plot, yp_min_v, yp_max_v)
        fig_view = style_plotly(fig_view)
        fig_view.update_layout(
            title="Views Accumulation Forecast",
            hovermode="x unified",
            yaxis=dict(range=[yp_min_v, yp_max_v], tickformat=",")
        )
        st.plotly_chart(fig_view, use_container_width=True)

with st.expander("📊 Data Diagnostic Tool"):
    st.write("If your graphs don't match your cards, check the values below:")
    col_a, col_b = st.columns(2)
    with col_a:
        st.write("**Latest Channel Values:**")
        st.dataframe(cf_plot[['date', 'subscribers', 'total_views']].tail(3))
    with col_b:
        st.write("**Forecast Values:**")
        st.dataframe(s_fc_plot[s_fc_plot["ds"] > last_date_plot].head(3) if not s_fc_plot.empty else "N/A")
    st.info(f"Detected columns: {', '.join(cf_plot.columns.tolist())}")



# ── Footer ─────────────────────────────────────────────────────────────
st.markdown("""
<div style="border-top:1px solid #e2e8f0;margin-top:50px;padding:20px 0;
            text-align:center;color:#94a3b8;font-size:13px;">
    Powered by <b>TubePulse Intelligence</b> · YouTube Red × Neon Edition
</div>
""", unsafe_allow_html=True)
