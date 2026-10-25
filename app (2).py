import streamlit as st
import pandas as pd
import numpy as np
import time
import csv
import os
import base64
from datetime import date, datetime, timedelta
import plotly.graph_objects as go

#Page settings
st.set_page_config(page_title="KHWEZI MINING", page_icon=":pick:", layout="wide")

BASE = os.path.dirname(os.path.abspath(__file__))   # data files live next to this program

# =====================================================================
# SHARED HELPERS (written once, used by the dashboard, alerts logic and analysis)
# =====================================================================
# ------------------------------ CONSTANTS ------------------------------
FILES = {k: os.path.join(BASE, v) for k, v in {
    "workers": "workers.csv", "incidents": "incidents.csv", "equipment": "equipment.csv",
    "maintenance_log": "maintenance_log.csv", "risks": "risks.csv"}.items()}
USERS_FILE = os.path.join(BASE, "users.csv")
DEMO_USERS = ("username,password,role\nLesiba,123,Administrator\nNatey,123,Mine Engineer\nSafetyUser,2468,Safety Officer\n"
              "MaintenanceUser,123,Maintenance Engineer\nManagerUser,123,Manager\nInnocent,123,Administrator\n"
              "Thato,123,Mine Engineer\nReesegofetse,123,Safety Officer\nTyler,123,Maintenance Engineer\n"
              "Fortunate,123,Manager\n")

DEPTS = ["Community Relations", "Electrical Engineering", "Emergency Response", "Environmental Management",
         "Finance & Commercial", "Fixed Plant Maintenance", "Geology & Exploration", "Geotechnical Engineering",
         "Grade Control", "Human Resources & Payroll", "Mine Engineering", "Mine Surveying",
         "Mining Operations (Production)", "Mobile Equipment Maintenance", "Occupational Health & Safety",
         "Processing / Metallurgy", "Security", "Supply Chain & Logistics"]
INC_TYPES = ["Fall of ground", "Slip / trip / fall", "Vehicle / equipment collision", "Equipment failure",
             "Fire / explosion", "Electrical", "Struck by object", "Hazardous substance exposure",
             "Machinery entanglement", "Other"]
EQ_TYPES = ["Haul Truck", "Loader", "Excavator", "Drilling Machine", "Bulldozer", "Scraper Winch", "Crusher", "Conveyor"]
# Assumed owner of each equipment type; only used to link equipment downtime to departments in the analysis.
EQ_DEPT = {"Haul Truck": "Mobile Equipment Maintenance", "Loader": "Mobile Equipment Maintenance",
           "Excavator": "Mobile Equipment Maintenance", "Bulldozer": "Mobile Equipment Maintenance",
           "Crusher": "Fixed Plant Maintenance", "Conveyor": "Fixed Plant Maintenance",
           "Drilling Machine": "Mining Operations (Production)", "Scraper Winch": "Mining Operations (Production)"}
MAINT_STATUS = ["Operational", "Due for Maintenance", "Overdue", "Under Maintenance"]
PART = ["Good", "Worn", "Faulty"]
EQ_COLS = ["Equipment ID", "Equipment Type", "Manufacturer", "Operating Hours", "Temperature (C)",
           "Vibration (mm/s)", "Fuel Consumption (L/h)", "Brake Status", "Tyre Status", "Engine Status",
           "Maintenance Status", "Downtime (hours)", "Last Maintenance", "Next Maintenance Due", "Alert Count"]
NUM_COLS = ["Operating Hours", "Temperature (C)", "Vibration (mm/s)", "Fuel Consumption (L/h)",
            "Downtime (hours)", "Alert Count"]
# Educational prototype thresholds only - NOT manufacturer or mine safety limits
LIMITS = {"Temperature": (80, 100, "°C"), "Vibration": (5, 8, "mm/s")}
RISK_CLASSES = [(4, "Low"), (9, "Medium"), (16, "High"), (25, "Critical")]
NORMAL_MSG = "NORMAL: Equipment operating within defined monitoring limits."

# Colour palette (Palette 2: Sophisticated & Precision)
BG, SURFACE, HEAD, GREEN, GREEN_HOVER = "#1A1D21", "#23272D", "#F0F3F7", "#1E5631", "#2E8B57"
BORDER, FOCUS, TEXT, BAR = "#607D8B", "#3F51B5", "#9E9E9E", "#3F51B5"
SEV_COLORS = {"Low": "#6cbf6c", "Medium": "#f2cf4a", "High": "#f09a3e", "Critical": "#d9534f"}
COND_COLORS = {"Normal": "#6cbf6c", "Warning": "#f2cf4a", "Critical": "#d9534f"}
TAG_COLORS = {"Critical": "#f8c9c9", "High": "#fcd9b6", "Warning": "#fde7b0", "Medium": "#fff4c2",
              "Low": "#d9f2d9", "Normal": "#d9f2d9"}
TAG_COLUMNS = ("Level", "Condition", "Classification", "Risk Level", "Severity")

# ------------------------------ STYLE ------------------------------
st.markdown("""
<style>
:root{--bg:#1A1D21;--surf:#23272D;--head:#F0F3F7;--green:#1E5631;--green-hv:#2E8B57;--border:#607D8B;--focus:#3F51B5;--text:#9E9E9E;color-scheme:dark;}
.stApp,[data-testid="stHeader"]{background:var(--bg);}
.stApp p,.stApp li,.stApp label,[data-testid="stCaptionContainer"]{color:var(--text);}
h1,h2,h3,h4{color:var(--head)!important;}
.block-container{padding-top:1.4rem;max-width:1400px;}
.banner{background:var(--surf);padding:18px 26px;border-radius:8px;border-bottom:4px solid var(--green-hv);margin-bottom:14px;}
.banner h1{margin:0;padding:0;font-size:1.9rem;letter-spacing:.05em;}
.banner p{margin:2px 0 0;}
[data-testid="stSidebar"]{background:var(--surf);}
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{background:var(--green);border:none;border-radius:6px;padding:.45rem 1.3rem;}
.stButton>button p,.stFormSubmitButton>button p,.stDownloadButton>button p{color:var(--head)!important;font-weight:700;}
.stButton>button:hover,.stFormSubmitButton>button:hover,.stDownloadButton>button:hover{background:var(--green-hv);}
div[data-baseweb="input"],div[data-baseweb="textarea"],div[data-baseweb="select"]>div{border:1px solid var(--border)!important;border-radius:6px;}
div[data-baseweb="input"]:focus-within,div[data-baseweb="textarea"]:focus-within,div[data-baseweb="select"]>div:focus-within{border-color:var(--focus)!important;box-shadow:0 0 0 2px rgba(63,81,181,.35);}
button[data-baseweb="tab"][aria-selected="true"] p{color:var(--head)!important;font-weight:700;}
div[data-baseweb="tab-highlight"]{background:var(--green-hv)!important;}
[data-testid="stMetric"]{background:var(--surf);border:1px solid var(--border);border-left:5px solid var(--green-hv);border-radius:8px;padding:10px 14px;}
[data-testid="stMetricValue"]{color:var(--head);}
.risk-badge{color:var(--bg);font-weight:700;font-size:1.05rem;padding:12px 16px;border-radius:8px;margin:6px 0;}
</style>
""", unsafe_allow_html=True)

S = st.session_state
STRETCH = {"width": "stretch"} if tuple(int(x) for x in st.__version__.split(".")[:2]) >= (1, 50) \
    else {"use_container_width": True}

# ------------------------------ DATA ------------------------------
for _key, _path in FILES.items():
    if _key not in S:   # load saved data once per session
        S[_key] = pd.read_csv(_path, keep_default_na=False).to_dict("records") if os.path.exists(_path) else []
S.setdefault("logged_in", False)
S.setdefault("role", "")

def save(key):
    pd.DataFrame(S[key]).to_csv(FILES[key], index=False)

# ------------------------------ LOGIC HELPERS ------------------------------

def level(v, warn, crit):
    return "Critical" if v > crit else "Warning" if v >= warn else "Normal"

def overall(temp, vib):
    levels = [level(temp, *LIMITS["Temperature"][:2]), level(vib, *LIMITS["Vibration"][:2])]
    return "Critical" if "Critical" in levels else "Warning" if "Warning" in levels else "Normal"

def condition_alerts(eq_id, temp, vib):
    out = []
    for name, val in (("Temperature", temp), ("Vibration", vib)):
        warn, crit, unit = LIMITS[name]
        lvl = level(val, warn, crit)
        if lvl == "Normal":
            continue
        is_crit = lvl == "Critical"
        out.append({"Level": lvl, "ID Type": "Equipment ID", "ID": eq_id, "Parameter": name, "Value": f"{val} {unit}",
                    "Status": "Above Critical Threshold" if is_crit else "Approaching Critical Threshold",
                    "Message": (f"CRITICAL: Equipment {name.lower()} exceeds predefined threshold. Inspection required"
                                if is_crit else f"WARNING: Equipment {name.lower()} approaching predefined threshold."),
                    "Action": ("Inspect equipment and initiate appropriate maintenance/safety procedures."
                               if is_crit else "Monitor closely and schedule an inspection.")})
    return out

def equipment_df():
    """Equipment as a DataFrame with calculated Availability (%) and Condition."""
    df = pd.DataFrame(S["equipment"], columns=EQ_COLS)
    if df.empty:
        return df
    df[NUM_COLS] = df[NUM_COLS].apply(pd.to_numeric, errors="coerce").fillna(0)
    total = (df["Operating Hours"] + df["Downtime (hours)"]).replace(0, float("nan"))
    df["Availability (%)"] = (df["Operating Hours"] / total * 100).round(1).fillna(0)   # Op / (Op + Down) x 100
    df["Condition"] = [overall(t, v) for t, v in zip(df["Temperature (C)"], df["Vibration (mm/s)"])]
    return df

FLAGS = ["Overdue", "Due", "Under Maintenance", "Excessive Downtime", "Repeated Alerts", "Low Availability"]

def add_flags(df, window=14, min_avail=85, max_down=500, repeats=3):
    today = pd.Timestamp(date.today())
    nxt = pd.to_datetime(df["Next Maintenance Due"], errors="coerce")
    ms = df["Maintenance Status"]
    df["Under Maintenance"] = ms == "Under Maintenance"
    df["Overdue"] = ((nxt < today) | (ms == "Overdue")) & ~df["Under Maintenance"]
    df["Due"] = ((nxt <= today + pd.Timedelta(days=window)) | (ms == "Due for Maintenance")) \
        & ~df["Under Maintenance"] & ~df["Overdue"]
    df["Excessive Downtime"] = df["Downtime (hours)"] >= max_down
    df["Repeated Alerts"] = df["Alert Count"] >= repeats
    df["Low Availability"] = df["Availability (%)"] < min_avail
    df["Flag Count"] = df[FLAGS].sum(axis=1)
    df["Flags"] = df[FLAGS].apply(lambda r: ", ".join(c for c in FLAGS if r[c]), axis=1)
    return df

def generate_alerts(pages):
    """Build every active alert the role is allowed to see; `pages` is the role's page list."""
    out = []

    def add(lvl, cat, id_type, id_, param, value, status, action):
        out.append({"Level": lvl, "Category": cat, "ID Type": id_type, "ID": id_, "Parameter": param,
                    "Value": value, "Status": status, "Action": action})

    if "Equipment Data" in pages:
        df = equipment_df()
        if not df.empty:
            for _, r in df.iterrows():
                for a in condition_alerts(r["Equipment ID"], r["Temperature (C)"], r["Vibration (mm/s)"]):
                    cat = "High equipment temperature" if a["Parameter"] == "Temperature" else "High equipment vibration"
                    add(a["Level"], cat, "Equipment ID", a["ID"], a["Parameter"], a["Value"], a["Status"], a["Action"])
            df = add_flags(df)
            for _, r in df.iterrows():
                if r["Overdue"]:
                    add("Critical", "Overdue maintenance", "Equipment ID", r["Equipment ID"], "Maintenance",
                        f"Due {r['Next Maintenance Due']}", "Overdue Maintenance", "Schedule maintenance immediately.")
                if r["Excessive Downtime"]:
                    add("Warning", "Excessive equipment downtime", "Equipment ID", r["Equipment ID"], "Downtime",
                        f"{r['Downtime (hours)']:.0f} hours", "Above Downtime Limit (500 h)",
                        "Investigate causes of downtime and review maintenance plan.")
    if "Worker Safety Data" in pages:
        for w in S["workers"]:
            wid = w["Worker's ID"]
            if w["PPE"] == "No":
                add("Critical", "Low PPE compliance", "Worker ID", wid, "PPE", "Not wearing full PPE", "Non-compliant",
                    "Stop work until full PPE is worn and record corrective action.")
            if int(w["Fatigue Level"]) >= 8:
                add("Warning", "High fatigue level", "Worker ID", wid, "Fatigue", f"{w['Fatigue Level']}/10",
                    "Above Fatigue Limit (8)", "Rest the worker or reassign duties.")
            if w["Risk Level"] == "High":
                add("Warning", "High-risk safety observation", "Worker ID", wid, "Worker Risk Level", "High",
                    "High-Risk Worker", "Investigate the safety observation and take action.")
    if "Safety Incidents" in pages:
        for i in S["incidents"]:
            if i["Status"] != "Closed" and i["Severity"] in ("Critical", "High"):
                crit = i["Severity"] == "Critical"
                add("Critical" if crit else "Warning", "Critical safety incident" if crit else "High-severity safety incident",
                    "Incident ID", i["Incident ID"], "Severity", i["Severity"], f"Status: {i['Status']}",
                    "Attend immediately and complete the investigation.")
    if "Risk Assessment" in pages:
        for r in S["risks"]:
            if r["Classification"] in ("High", "Critical"):
                add("Critical" if r["Classification"] == "Critical" else "Warning", "High-risk assessment", "Risk ID",
                    r["Risk ID"], "Risk Score", f"{r['Risk Score']} ({r['Classification']})",
                    "Requires Management Attention", "Implement additional controls and review the risk.")
    out.sort(key=lambda a: a["Level"] != "Critical")
    return out


# ------------------------------ DISPLAY HELPERS ------------------------------

def show_table(df):
    """Interactive table; Level / Condition / Severity style columns are colour coded."""
    df = df.copy()
    for c in df.columns:   # a column that mixes numbers and text is shown as text
        if df[c].map(type).nunique() > 1:
            df[c] = df[c].astype(str)
    for c in df.select_dtypes("datetime").columns:
        df[c] = df[c].dt.strftime("%Y-%m-%d")
    cols = [c for c in TAG_COLUMNS if c in df.columns]
    data = df.style.apply(lambda s: [f"background-color: {TAG_COLORS.get(str(v), '')}; color: {BG}" for v in s],
                          subset=cols) if cols else df
    st.dataframe(data, hide_index=True, **STRETCH)

def filter_df(df, cols, key):
    """Multiselect filters laid out in 3 columns; returns the filtered DataFrame."""
    layout = st.columns(3)
    for i, c in enumerate(cols):
        sel = layout[i % 3].multiselect(c, sorted(df[c].astype(str).unique()), key=f"{key}_{c}")
        if sel:
            df = df[df[c].astype(str).isin(sel)]
    return df

def search_df(df, text):
    if text.strip() and not df.empty:
        df = df[df.astype(str).apply(lambda c: c.str.contains(text.strip(), case=False, regex=False)).any(axis=1)]
    return df

def style_fig(fig, title, height=320):
    fig.update_layout(title=dict(text=title, font=dict(size=15, color=HEAD)), height=height,
                      margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=SURFACE,
                      font=dict(color=TEXT), showlegend=False)
    fig.update_xaxes(gridcolor="#33383F")
    fig.update_yaxes(gridcolor="#33383F")
    st.plotly_chart(fig, **STRETCH)

def bar_chart(data, title, colors=None, horizontal=False, lines=(), height=320):
    """Bar chart from {label: value}; lines = [(value, colour, name)] draws threshold lines."""
    data = dict(data)
    if not data:
        st.info("No data yet.")
        return
    labels, vals = [str(k) for k in data], [float(v) for v in data.values()]
    marker = [(colors or {}).get(k, BAR) for k in data]
    fig = go.Figure(go.Bar(x=vals if horizontal else labels, y=labels if horizontal else vals, marker_color=marker,
                           orientation="h" if horizontal else "v", text=[f"{v:g}" for v in vals], textposition="outside",
                           cliponaxis=False))
    for v, colour, name in lines:
        kw = dict(line_dash="dash", line_color=colour, annotation_text=name, annotation_font_color=colour)
        fig.add_vline(x=v, **kw) if horizontal else fig.add_hline(y=v, **kw)
    value_axis = fig.update_xaxes if horizontal else fig.update_yaxes
    if all(v == int(v) for v in vals) and max(vals) <= 10:
        value_axis(dtick=1)
    if horizontal:
        fig.update_yaxes(autorange="reversed")
    elif len(labels) > 4:
        fig.update_xaxes(tickangle=-30)
    style_fig(fig, title, height)

def line_chart(series, title, height=320):
    fig = go.Figure(go.Scatter(x=[str(i) for i in series.index], y=series.values, mode="lines+markers",
                               line=dict(color=BAR), marker=dict(color=GREEN_HOVER, size=8)))
    fig.update_yaxes(rangemode="tozero", dtick=1 if series.max() <= 10 else None)
    style_fig(fig, title, height)

def stacked_chart(table, title, height=320):
    """Stacked bars from a crosstab (rows = categories, columns = severity)."""
    fig = go.Figure([go.Bar(name=c, x=[str(i) for i in table.index], y=table[c], marker_color=SEV_COLORS.get(c, BAR))
                     for c in table.columns])
    fig.update_layout(barmode="stack")
    style_fig(fig, title, height)

def by_id(eq, col):
    return dict(zip(eq["Equipment ID"], eq[col])) if len(eq) else {}

@st.cache_data
def login_background():
    """The login picture (logo + mine at sunrise) as base64; empty text if login_bg.jpeg is missing."""
    path = os.path.join(BASE, "login_bg.jpeg")
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# ------------------------------ PART (i) DASHBOARD ------------------------------
def page_dashboard(pages):
    st.header("Dashboard")
    w, inc, eq, rk = pd.DataFrame(S["workers"]), pd.DataFrame(S["incidents"]), equipment_df(), pd.DataFrame(S["risks"])
    alerts = generate_alerts(pages)
    cond = eq["Condition"].value_counts() if len(eq) else pd.Series(dtype=int)
    pct = lambda x: f"{x * 100:.0f}%"
    kpis = {"Total workers": len(w), "Total safety incidents": len(inc),
            "Near misses": int(pd.to_numeric(w["Near Misses"]).sum()) if len(w) else 0,
            "High-risk observations": int((w["Risk Level"] == "High").sum()) if len(w) else 0,
            "PPE compliance": pct((w["PPE"] == "Yes").mean()) if len(w) else "-",
            "Total equipment": len(eq),
            "Equipment available": int((eq["Maintenance Status"] == "Operational").sum()) if len(eq) else 0,
            "Equipment under maintenance": int((eq["Maintenance Status"] == "Under Maintenance").sum()) if len(eq) else 0,
            "Equipment alerts": int(len(eq) - cond.get("Normal", 0)),
            "Avg equipment availability": f"{eq['Availability (%)'].mean():.1f}%" if len(eq) else "-",
            "Critical equipment alerts": int(cond.get("Critical", 0)),
            "High / Critical incidents": int(inc["Severity"].isin(["High", "Critical"]).sum()) if len(inc) else 0,
            "Active critical alerts": sum(a["Level"] == "Critical" for a in alerts),
            "High / Critical risks": int(rk["Classification"].isin(["High", "Critical"]).sum()) if len(rk) else 0,
            "Equipment operating normally": pct(cond.get("Normal", 0) / len(eq)) if len(eq) else "-"}
    items = list(kpis.items())
    for i in range(0, len(items), 5):
        for col, (name, val) in zip(st.columns(5), items[i:i + 5]):
            col.metric(name, val)

    c1, c2, c3 = st.columns(3)
    with c1:
        sev = inc["Severity"].value_counts() if len(inc) else {}
        bar_chart({k: int(sev.get(k, 0)) for k in SEV_COLORS}, "Incidents by severity", colors=SEV_COLORS)
    with c2:
        bar_chart({k: int(cond.get(k, 0)) for k in COND_COLORS}, "Equipment condition", colors=COND_COLORS)
    with c3:
        bar_chart(by_id(eq, "Availability (%)"), "Availability by equipment (%)", horizontal=True,
                  lines=[(85, "#d9534f", "Min 85%")])

    st.subheader("Top active alerts")
    if alerts:
        show_table(pd.DataFrame(alerts[:8], columns=["Level", "Category", "ID", "Parameter", "Value", "Status"]))
        st.caption("Open the Alerts section for all alerts and recommended actions.")
    else:
        st.success("No active alerts.")

# ------------------------------ (j) INTERACTIVE DATA ANALYSIS ------------------------------
QUESTIONS = {}   # category -> {question text: function}
SOURCE_NAMES = {"inc": "incident", "w": "worker", "eq": "equipment", "rk": "risk assessment"}

def question(category, text, needs=()):
    """Register an analysis question; `needs` lists the data sets that must contain records."""
    def register(fn):
        def run(d):
            missing = [SOURCE_NAMES[n] for n in needs if d[n].empty]
            if missing:
                st.info(f"No {' or '.join(missing)} records are available for this question yet.")
            else:
                fn(d)
        QUESTIONS.setdefault(category, {})[text] = run
        return fn
    return register

def answer(msg):
    st.info("**Answer:** " + msg)

def leaders(counts):
    top = counts[counts == counts.max()]
    return ", ".join(map(str, top.index)), counts.max()


def most_incidents(d, col, what, horizontal=True):
    counts = d["inc"][col].astype(str).str.strip().value_counts()
    names, n = leaders(counts)
    answer(f"The {what} with the most incidents: **{names}** ({n} incident{'s' if n != 1 else ''}).")
    bar_chart(counts.to_dict(), f"Incidents by {what}", horizontal=horizontal)

def eq_extreme(d, col, what, unit="", highest=True, lines=()):
    s = d["eq"].set_index("Equipment ID")[col]
    val = s.max() if highest else s.min()
    answer(f"{what}: **{', '.join(s[s == val].index)}** ({val:g}{unit}).")
    bar_chart(s.sort_values(ascending=not highest).to_dict(), col, horizontal=True, lines=lines)

def equipment_table(df, cols=("Equipment ID", "Equipment Type", "Availability (%)", "Downtime (hours)", "Alert Count",
                              "Next Maintenance Due", "Maintenance Status", "Flags")):
    show_table(df[[c for c in cols if c in df.columns]])

def dept_risk(d):
    """Safety risk index per department = high-risk workers + high/critical incidents + high/critical risks."""
    parts = {}
    if not d["w"].empty and "Department" in d["w"]:
        parts["High-risk workers"] = d["w"][d["w"]["Risk Level"] == "High"].groupby("Department").size()
    if not d["inc"].empty and "Department" in d["inc"]:
        parts["High/Critical incidents"] = d["inc"][d["inc"]["Severity"].isin(["High", "Critical"])].groupby("Department").size()
    if not d["rk"].empty and "Department" in d["rk"]:
        parts["High/Critical risks"] = d["rk"][d["rk"]["Classification"].isin(["High", "Critical"])].groupby("Department").size()
    if not parts:
        return pd.DataFrame(columns=["Safety risk index"])
    df = pd.DataFrame(parts).fillna(0).astype(int)
    df["Safety risk index"] = df.sum(axis=1)
    return df.sort_values("Safety risk index", ascending=False)

def dept_table(d):
    t = dept_risk(d)
    if not d["eq"].empty:
        down = d["eq"].assign(Department=d["eq"]["Equipment Type"].map(EQ_DEPT)).groupby("Department")["Downtime (hours)"].sum()
        t = t.join(down.rename("Equipment downtime (h)"), how="outer").fillna(0)
    return t

# ---- Health and Safety ----
HS = "Health and Safety"

@question(HS, "How many safety incidents occurred during the selected period?")
def q_incident_count(d):
    answer(f"**{len(d['inc'])}** safety incident(s) between {d['start']} and {d['end']}.")
    if len(d["inc"]):
        line_chart(d["inc"]["Date"].dt.strftime("%Y-%m").value_counts().sort_index(), "Incidents per month")

@question(HS, "Which department has the highest number of incidents?", ("inc",))
def q_dept_incidents(d):
    most_incidents(d, "Department", "department")

@question(HS, "Which shift records the most incidents?", ("inc",))
def q_shift_incidents(d):
    most_incidents(d, "Shift", "shift", horizontal=False)

@question(HS, "What percentage of workers comply with PPE requirements?", ("w",))
def q_ppe(d):
    w = d["w"]
    pct = (w["PPE"] == "Yes").mean() * 100
    answer(f"**{pct:.0f}%** of workers wear full PPE ({int((w['PPE'] == 'Yes').sum())} of {len(w)}).")
    bar_chart(w["PPE"].value_counts().to_dict(), "Workers by PPE status", colors={"Yes": "#6cbf6c", "No": "#d9534f"})
    if (w["PPE"] == "No").any():
        st.markdown("**Non-compliant workers**")
        show_table(w[w["PPE"] == "No"][["Worker's ID", "Department", "Job Role", "Shift", "Risk Level"]])

@question(HS, "How many near misses have been recorded?", ("w",))
def q_near_misses(d):
    nm = pd.to_numeric(d["w"]["Near Misses"])
    answer(f"**{int(nm.sum())}** near miss(es) recorded across {len(d['w'])} workers.")
    by_dept = d["w"].assign(**{"Near Misses": nm}).groupby("Department")["Near Misses"].sum()
    bar_chart(by_dept[by_dept > 0].sort_values(ascending=False).to_dict(), "Near misses by department", horizontal=True)

@question(HS, "Which incident types occur most frequently?", ("inc",))
def q_incident_types(d):
    most_incidents(d, "Incident Type", "incident type")

@question(HS, "How many incidents are classified as high or critical?", ("inc",))
def q_high_critical(d):
    hc = d["inc"][d["inc"]["Severity"].isin(["High", "Critical"])]
    answer(f"**{len(hc)}** of {len(d['inc'])} incidents ({len(hc) / len(d['inc']) * 100:.0f}%) are High or Critical; "
           f"**{int((hc['Status'] != 'Closed').sum())}** of them are still open.")
    bar_chart(d["inc"]["Severity"].value_counts().reindex(list(SEV_COLORS)).fillna(0).to_dict(), "Incidents by severity",
              colors=SEV_COLORS)
    if len(hc):
        show_table(hc[["Incident ID", "Date", "Department", "Incident Type", "Severity", "Status"]])

@question(HS, "Which departments have the highest safety risk?")
def q_dept_risk(d):
    t = dept_risk(d)
    if t.empty:
        return st.info("No worker, incident or risk records are available for this question yet.")
    names, n = leaders(t["Safety risk index"])
    answer(f"Highest safety risk: **{names}** (index {n}).")
    st.caption("Safety risk index = high-risk workers + high/critical incidents + high/critical risk assessments.")
    bar_chart(t["Safety risk index"].head(10).to_dict(), "Safety risk index by department", horizontal=True)
    show_table(t.reset_index(names="Department"))

@question(HS, "Is there an observable difference in incidents between day and night shifts?", ("inc",))
def q_day_night(d):
    inc = d["inc"]
    c = inc["Shift"].value_counts()
    day, night = int(c.get("Day Shift", 0)), int(c.get("Night Shift", 0))
    if day == night:
        answer(f"No difference in the number of incidents: day shift and night shift both have **{day}**.")
    else:
        more, less = ("Night", "Day") if night > day else ("Day", "Night")
        low = min(day, night)
        extra = f" ({(abs(night - day) / low * 100):.0f}% more)" if low else ""
        answer(f"**{more} shift** has more incidents: night = **{night}**, day = **{day}**{extra} than {less.lower()} shift.")
    stacked_chart(pd.crosstab(inc["Shift"], inc["Severity"]).reindex(columns=list(SEV_COLORS)).dropna(axis=1, how="all"),
                  "Incidents by shift and severity")

@question(HS, "Which safety conditions require immediate attention?")
def q_attention(d):
    urgent = [a for a in d["alerts"] if a["ID Type"] != "Equipment ID" and a["Level"] == "Critical"]
    if not urgent:
        return st.success("No critical safety conditions are currently active.")
    answer(f"**{len(urgent)}** critical safety condition(s) need immediate attention.")
    show_table(pd.DataFrame(urgent)[["Level", "Category", "ID Type", "ID", "Value", "Action"]])

# ---- Equipment ----
EQ = "Equipment"

@question(EQ, "Which equipment has the highest downtime?", ("eq",))
def q_eq_downtime(d):
    eq_extreme(d, "Downtime (hours)", "Highest downtime", " h", True, [(500, "#d9534f", "Limit 500 h")])

@question(EQ, "Which equipment has the lowest availability?", ("eq",))
def q_eq_availability(d):
    eq_extreme(d, "Availability (%)", "Lowest availability", "%", False, [(85, "#d9534f", "Min 85%")])

@question(EQ, "Which equipment has the highest vibration?", ("eq",))
def q_eq_vibration(d):
    eq_extreme(d, "Vibration (mm/s)", "Highest vibration", " mm/s", True,
               [(5, "#e0a800", "Warning 5"), (8, "#d9534f", "Critical 8")])

@question(EQ, "Which equipment has the highest operating temperature?", ("eq",))
def q_eq_temperature(d):
    eq_extreme(d, "Temperature (C)", "Highest temperature", " °C", True,
               [(80, "#e0a800", "Warning 80"), (100, "#d9534f", "Critical 100")])

@question(EQ, "Which equipment has generated the most alerts?", ("eq",))
def q_eq_alerts(d):
    eq_extreme(d, "Alert Count", "Most alerts recorded", " alert(s)", True)

@question(EQ, "Which equipment requires maintenance?", ("eq",))
def q_eq_maintenance(d):
    df = d["eqf"][d["eqf"][["Overdue", "Due", "Under Maintenance"]].any(axis=1)]
    answer(f"**{len(df)}** equipment item(s) are due, overdue or under maintenance: **{', '.join(df['Equipment ID']) or 'none'}**.")
    equipment_table(df)

@question(EQ, "Which equipment is overdue for maintenance?", ("eq",))
def q_eq_overdue(d):
    df = d["eqf"][d["eqf"]["Overdue"]]
    answer(f"**{len(df)}** equipment item(s) overdue: **{', '.join(df['Equipment ID']) or 'none'}**.")
    equipment_table(df)

@question(EQ, "What is the average equipment availability?", ("eq",))
def q_eq_avg_availability(d):
    avg = d["eq"]["Availability (%)"].mean()
    answer(f"Average equipment availability is **{avg:.1f}%** "
           f"({'above' if avg >= 85 else 'below'} the 85% prototype minimum).")
    bar_chart(by_id(d["eq"], "Availability (%)"), "Availability by equipment (%)", horizontal=True,
              lines=[(85, "#d9534f", "Min 85%")])

@question(EQ, "Which equipment type has the highest downtime?", ("eq",))
def q_type_downtime(d):
    t = d["eq"].groupby("Equipment Type")["Downtime (hours)"].sum().sort_values(ascending=False)
    names, n = leaders(t)
    answer(f"Highest total downtime: **{names}** ({n:g} h).")
    bar_chart(t.to_dict(), "Total downtime by equipment type (h)", horizontal=True)

@question(EQ, "Which equipment requires immediate inspection?", ("eq",))
def q_eq_inspection(d):
    df = d["eqf"]
    df = df[(df["Condition"] == "Critical") | df["Overdue"]].assign(
        Reason=lambda x: [", ".join(r for r, on in (("Critical condition", c == "Critical"), ("Overdue maintenance", o))
                                    if on) for c, o in zip(x["Condition"], x["Overdue"])])
    answer(f"**{len(df)}** equipment item(s) need immediate inspection: **{', '.join(df['Equipment ID']) or 'none'}**.")
    show_table(df[["Equipment ID", "Equipment Type", "Temperature (C)", "Vibration (mm/s)", "Condition", "Reason"]])

# ---- Integrated ----
IN = "Integrated Safety and Equipment Analysis"

@question(IN, "Are safety incidents associated with particular shifts?", ("inc",))
def q_shift_association(d):
    inc = d["inc"]
    counts = inc["Shift"].value_counts()
    share = (counts / counts.sum() * 100).round(0).astype(int)
    answer("Share of incidents by shift: " + ", ".join(f"**{k}** {share[k]}% ({counts[k]})" for k in counts.index) + ".")
    if not d["w"].empty:
        workers = d["w"]["Shift"].value_counts()
        rate = (counts / workers.reindex(counts.index)).dropna().round(2)
        if len(rate):
            st.write("Incidents per recorded worker on the shift: " + ", ".join(f"**{k}** {v}" for k, v in rate.items()))
    stacked_chart(pd.crosstab(inc["Shift"], inc["Severity"]).reindex(columns=list(SEV_COLORS)).dropna(axis=1, how="all"),
                  "Incidents by shift and severity")

@question(IN, "Which departments have both high safety risk and high equipment downtime?", ("eq",))
def q_dept_both(d):
    t = dept_table(d)
    if "Safety risk index" not in t or t["Safety risk index"].sum() == 0:
        return st.info("No safety records with a department are available for this question yet.")
    hi_s = (t["Safety risk index"] >= t["Safety risk index"].mean()) & (t["Safety risk index"] > 0)
    hi_d = (t["Equipment downtime (h)"] >= t["Equipment downtime (h)"].mean()) & (t["Equipment downtime (h)"] > 0)
    both = t[hi_s & hi_d]
    answer(f"Departments high on both: **{', '.join(both.index) or 'none'}**.")
    st.caption("High = at or above the average of all departments listed. Equipment downtime is linked to departments "
               "by equipment type (e.g. haul trucks and loaders: Mobile Equipment Maintenance; crushers and conveyors: "
               "Fixed Plant Maintenance; drills and winches: Mining Operations).")
    show_table(t.assign(**{"High on both": (hi_s & hi_d).map({True: "Yes", False: "No"})}).reset_index(names="Department"))

@question(IN, "Which equipment contributes to the greatest number of alerts?", ("eq",))
def q_eq_alert_sources(d):
    ids = pd.Series([a["ID"] for a in d["alerts"] if a["ID Type"] == "Equipment ID"], dtype=str).value_counts()
    if ids.empty:
        return st.success("There are no active equipment alerts.")
    names, n = leaders(ids)
    answer(f"Most active alerts: **{names}** ({n} alert{'s' if n != 1 else ''}: temperature, vibration, overdue maintenance, downtime).")
    bar_chart(ids.to_dict(), "Active alerts per equipment", horizontal=True)

@question(IN, "Which equipment should receive maintenance priority?", ("eq",))
def q_priority(d):
    pri = d["eqf"][d["eqf"]["Flag Count"] > 0].sort_values(["Overdue", "Flag Count", "Availability (%)"],
                                                           ascending=[False, False, True])
    if pri.empty:
        return st.success("No equipment currently requires maintenance attention.")
    answer(f"Maintenance priority order: **{', '.join(pri['Equipment ID'])}** (overdue first, then most flags, then lowest availability).")
    equipment_table(pri)

@question(IN, "What are the most common causes of safety incidents?", ("inc",))
def q_causes(d):
    counts = d["inc"]["Cause"].str.strip().str.capitalize().value_counts()
    names, n = leaders(counts)
    answer(f"Most common cause: **{names}** ({n} incident{'s' if n != 1 else ''}).")
    bar_chart(counts.head(10).to_dict(), "Most common causes", horizontal=True)

@question(IN, "Which safety indicators require management intervention?")
def q_indicators(d):
    w, inc, rk, rows = d["w"], d["inc"], d["rk"], []

    def row(name, value, target, bad):
        rows.append({"Indicator": name, "Value": value, "Target": target, "Level": "Warning" if bad else "Normal",
                     "Management action": "Intervene" if bad else "None"})

    if not w.empty:
        ppe = (w["PPE"] == "Yes").mean() * 100
        row("PPE compliance", f"{ppe:.0f}%", "100%", ppe < 100)
        row("Workers with fatigue 8 or more", int((w["Fatigue Level"].astype(int) >= 8).sum()), "0",
            (w["Fatigue Level"].astype(int) >= 8).any())
        row("Workers without safety training", int((w["Training"] == "No").sum()), "0", (w["Training"] == "No").any())
        row("High-risk workers", int((w["Risk Level"] == "High").sum()), "0", (w["Risk Level"] == "High").any())
    if not inc.empty:
        open_hc = int(((inc["Status"] != "Closed") & inc["Severity"].isin(["High", "Critical"])).sum())
        lti = int((inc["Lost-Time Injury"] == "Yes").sum())
        row("Open High/Critical incidents", open_hc, "0", open_hc > 0)
        row("Lost-time injuries", lti, "0", lti > 0)
    if not rk.empty:
        hc = int(rk["Classification"].isin(["High", "Critical"]).sum())
        row("High/Critical risk assessments", hc, "0", hc > 0)
    if not rows:
        return st.info("No worker, incident or risk records are available for this question yet.")
    df = pd.DataFrame(rows)
    answer(f"**{int((df['Level'] == 'Warning').sum())}** of {len(df)} safety indicators need management intervention.")
    show_table(df)

@question(IN, "What percentage of monitored equipment is operating normally?", ("eq",))
def q_normal(d):
    n = d["eq"]["Condition"].value_counts()
    answer(f"**{n.get('Normal', 0) / len(d['eq']) * 100:.0f}%** of monitored equipment is operating normally "
           f"({int(n.get('Normal', 0))} of {len(d['eq'])}).")
    bar_chart({k: int(n.get(k, 0)) for k in COND_COLORS}, "Equipment condition", colors=COND_COLORS)

@question(IN, "How many critical alerts are currently active?")
def q_critical_alerts(d):
    crit = [a for a in d["alerts"] if a["Level"] == "Critical"]
    answer(f"**{len(crit)}** critical alert(s) are active out of {len(d['alerts'])} active alerts.")
    if crit:
        show_table(pd.DataFrame(crit)[["Level", "Category", "ID Type", "ID", "Value", "Status"]])

@question(IN, "Which areas of the operation require the greatest attention?")
def q_areas(d):
    t = dept_table(d)
    if t.empty:
        return st.info("No safety or equipment records are available for this question yet.")
    if not d["inc"].empty:
        loc = d["inc"]["Location"].astype(str).str.strip().value_counts()
        names, n = leaders(loc)
        answer(f"Location with the most incidents: **{names}** ({n}).")
        bar_chart(loc.head(8).to_dict(), "Incidents by location", horizontal=True)
    if "Safety risk index" in t and t["Safety risk index"].sum() > 0:
        names, n = leaders(t["Safety risk index"])
        st.write(f"Department with the highest safety risk: **{names}** (index {n}).")
    st.markdown("**Departments**")
    show_table(t.reset_index(names="Department"))

@question(IN, "What recommendations can be generated from the monitoring results?")
def q_recommendations(d):
    w, inc, rk, eqf, rec = d["w"], d["inc"], d["rk"], d["eqf"], []
    crit = sum(a["Level"] == "Critical" for a in d["alerts"])
    if crit:
        rec.append(f"Resolve the **{crit}** active critical alert(s) first (see the Alerts section).")
    if not w.empty:
        if (w["PPE"] == "No").any():
            rec.append(f"Enforce PPE: **{int((w['PPE'] == 'No').sum())}** worker(s) are not wearing full PPE.")
        if (w["Training"] == "No").any():
            rec.append(f"Complete safety training for **{int((w['Training'] == 'No').sum())}** worker(s).")
        if (w["Fatigue Level"].astype(int) >= 8).any():
            rec.append("Rest or reassign workers reporting fatigue of 8 or more.")
    if not inc.empty:
        open_hc = inc[(inc["Status"] != "Closed") & inc["Severity"].isin(["High", "Critical"])]
        if len(open_hc):
            rec.append(f"Close out the **{len(open_hc)}** open High/Critical incident(s): {', '.join(open_hc['Incident ID'])}.")
        shifts = inc["Shift"].value_counts()
        if len(shifts) > 1 and shifts.iloc[0] > shifts.iloc[1]:
            rec.append(f"Review supervision and controls on **{shifts.index[0]}**, which has the most incidents.")
    if not rk.empty and rk["Classification"].isin(["High", "Critical"]).any():
        rec.append("Implement additional controls for the High/Critical risk assessments.")
    if not eqf.empty:
        for flag, text in (("Overdue", "Schedule overdue maintenance immediately for"),
                           ("Excessive Downtime", "Investigate excessive downtime of"),
                           ("Low Availability", "Improve availability of")):
            ids = eqf.loc[eqf[flag], "Equipment ID"].tolist()
            if ids:
                rec.append(f"{text}: **{', '.join(ids)}**.")
        crit_eq = eqf.loc[eqf["Condition"] == "Critical", "Equipment ID"].tolist()
        if crit_eq:
            rec.append(f"Inspect equipment in critical condition: **{', '.join(crit_eq)}**.")
    if not rec:
        return st.success("No intervention is required based on the current records.")
    st.markdown("\n".join(f"- {r}" for r in rec))

def analysis_categories(pages):
    safety = "Safety Incidents" in pages or "Worker Safety Data" in pages
    equip = "Equipment Data" in pages
    return [c for c, ok in ((HS, safety), (EQ, equip), (IN, safety and equip)) if ok]

def page_analysis(pages):
    st.header("Interactive Data Analysis")
    cats = analysis_categories(pages)
    c1, c2 = st.columns([1, 2])
    cat = c1.selectbox("Question category", cats)
    q = c2.selectbox("Question", list(QUESTIONS[cat]))

    inc = pd.DataFrame(S["incidents"])
    dates = pd.to_datetime(inc["Date"], errors="coerce").dropna() if not inc.empty else pd.Series(dtype="datetime64[ns]")
    d1, d2 = st.columns(2)
    start = d1.date_input("Period from (incidents)", value=dates.min().date() if len(dates) else date.today() - timedelta(days=30))
    end = d2.date_input("Period to (incidents)", value=max(dates.max().date(), date.today()) if len(dates) else date.today())

    if not inc.empty:
        inc["Date"] = pd.to_datetime(inc["Date"], errors="coerce")
        inc = inc[(inc["Date"] >= pd.Timestamp(start)) & (inc["Date"] <= pd.Timestamp(end))]
    eq = equipment_df()
    data = {"w": pd.DataFrame(S["workers"]), "inc": inc, "eq": eq, "rk": pd.DataFrame(S["risks"]),
            "eqf": add_flags(eq.copy()) if not eq.empty else eq, "alerts": generate_alerts(pages),
            "start": start, "end": end}
    st.subheader(q)
    QUESTIONS[cat][q](data)


# =====================================================================
# MAIN PROGRAM - the group's elif-chain style is kept (no function def for pages a to h).
# Lines marked "FIX:" are the only changes made to the members' code.
# =====================================================================
picture = login_background()   # the login picture (empty text if login_bg.jpeg is missing)

#initializing the state session before logging in.
# (the data is already loaded from the csv files above, so the lists below only matter if a csv file is missing)
if "logged_in" not in st.session_state:  #log in screen
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state["role"] = ""
    
if "workers" not in st.session_state:
    st.session_state["workers"] = []     #store workers records

if "incidents" not in st.session_state:
    st.session_state["incidents"] = []

if "risks" not in st.session_state:
    st.session_state["risks"] = []              # risk assessment records (g)

if "maintenance_log" not in st.session_state:
    st.session_state["maintenance_log"] = []    # maintenance work records (f)

# Load equipment here too, so Maintenance Data and Alerts work even if Equipment Data was not opened first
equipment_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "equipment.csv")
if "equipment" not in st.session_state:
    try:
        saved = pd.read_csv(equipment_file, keep_default_na=False, dtype=str)
        st.session_state["equipment"] = saved.to_dict("records")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        st.session_state["equipment"] = []

#Page title
# FIX: hidden on the login page when the logo picture is shown (the picture already shows the company name)
if st.session_state["logged_in"] or not picture:
    st.title("KHWEZI MINING")
    st.subheader("Health, Safety and Equipment Monitoring")

# Read users from the CSV file
users = {} #{"Lesiba": ["123","admin"]}

if not os.path.exists(USERS_FILE):   # FIX: create a users.csv instead of crashing when the file is missing
    with open(USERS_FILE, "w", newline="") as f:
        f.write(DEMO_USERS)

with open(USERS_FILE, mode="r", newline="") as file:   # open the users.csv file in read mode, with newline="" to handle line endings correctly across different operating systems.
    reader = csv.DictReader(file)      #values of the csv must be read as a dictinary {username: Lesiba , password: 123, role: admin}]}

    for row in reader:    #reading the user names from the csv and adding them in the dictionary
        file_username = row["username"].strip()
        file_password = row["password"].strip()
        file_role = row["role"].strip()

        if file_username != "":
            users[file_username] = {"password":file_password, "role":file_role}  #converts the csv into a dictionary

#Login page

if not st.session_state["logged_in"]:
    # FIX: login page style - the logo picture fills the page and the form sits under the logo
    background = (f"url(data:image/jpeg;base64,{picture}) center top/cover no-repeat" if picture else
                  "radial-gradient(circle at 72% 58%,#ffd98a 0,#f59a45 4%,transparent 28%),"
                  "linear-gradient(#1c2a44 0,#6b5577 35%,#e8894a 57%,#2a2420 57.2%,#1A1D21 100%)")
    push_down = "calc(max(54.5vw,100vh)*.68)" if picture else "1.4rem"   # keeps the form just below the logo on any screen
    st.markdown("""<style>
    .stApp{background:BACKGROUND;}
    [data-testid="stHeader"]{background:transparent;}
    .block-container{padding-top:PUSHDOWN;}
    [data-testid="stForm"]{background:rgba(26,29,33,.68);backdrop-filter:blur(8px);border:1px solid rgba(240,243,247,.25);}
    [data-testid="stVerticalBlock"]{gap:.6rem;}
    </style>""".replace("BACKGROUND", background).replace("PUSHDOWN", push_down), unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.form("login"):   # FIX: a form lets the Enter key submit the login
            st.header("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_clicked = st.form_submit_button("Login")

        if login_clicked:
            # FIX: the username is not case-sensitive ("innocent" works for "Innocent"); the password still is
            match = next((u for u in users if u.lower() == username.strip().lower()), None)
            if match and password == users[match]["password"]:   #this checks if the user name and the password are correct
                user_role = users[match]["role"]   #this gets the role that belongs to the username on the csv
            else:
                st.error("Incorrect username or password. Enter the correct credentials or contact the system administrator.")
                st.stop()

            st.session_state["logged_in"] = True
            st.session_state["role"] = user_role #####if the username and the password are on the same row in the csv
                                                 ##### the login will take me to the page of the user's role as shown on the file

            # FIX: the spinner and the two time.sleep() waits (3 seconds in total) were removed - they only slowed the login
            st.rerun()     # Restarts the script with the new session state(logged_in=True and role assigned), 
                            # allowing access to the application after login,
                            # Meaning everything under the first if statements won't happen because the opposite is true)

   


##After login, display the appropriate page based on the user's role

else:

    role= st.session_state["role"]
    st.sidebar.title("Khwezi Mining")
    st.sidebar.write("Logged in as:", role)

    # FIX: the logout button was inside page_analysis, so it only worked on one page. It now sits in the sidebar for every page.
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["role"] = ""
        st.rerun()



## navigator for each role
# FIX: "Data Analysis" (part j) was added to every list.

    if role == "Administrator":
        page = ["<CHOOSE>", "Dashboard", "Worker Safety Data", "Equipment Data", "Maintenance Data", "Manage Users", "Safety Incidents", "Risk Assessment", "Alerts", "Data Analysis", "General Reports"]

    elif role == "Safety Officer":
        page = ["<CHOOSE>", "Dashboard", "Worker Safety Data", "Safety Incidents", "Risk Assessment", "Alerts", "Data Analysis", "General Reports"]

    elif role == "Mine Engineer":
        page = ["<CHOOSE>", "Dashboard", "Worker Safety Data", "Equipment Data", "Maintenance Data", "Safety Incidents", "Risk Assessment", "Alerts", "Data Analysis", "General Reports"]

    elif role == "Maintenance Engineer": # FIX: was "Maintenance Manager", which does not match users.csv, so these users got the full "else" list below
        page = ["<CHOOSE>", "Dashboard", "Equipment Data", "Maintenance Data", "Alerts", "Data Analysis", "General Reports"] 

    else:
        page = ["<CHOOSE>", "Dashboard", "Worker Safety Data", "Equipment Data", "Maintenance Data", "Safety Incidents", "Risk Assessment", "Alerts", "Data Analysis", "General Reports"]

    selected_page = st.sidebar.selectbox("Select a section", page, index=0)  #might be bad!!!!!!!!!!!

    st.write(" Hello!, ", role, "! Welcome to the Khwezi Mining Health, Safety and Equipment Monitoring System.")

### THE DASHBOARD

    if selected_page == "Dashboard":
        # FIX: the full dashboard (part i) replaces the 3-metric starter. It already shows workers, incidents and
        # High/Critical incidents (the old check counted only "High").
        page_dashboard(page)

    ###Worker Safety Data

    elif selected_page == "Worker Safety Data":
        st.header("Worker Health and Safety Monitoring")
        st.write("Record the worker's safety data and look for potential health and safety risks.")
        st.subheader("Record Worker Information")
        worker_id = st.text_input("Worker's ID")
        department = st.selectbox("Select Department", ["", "Community Relations", "Electrical Engineering", "Emergency Response", "Environmental Management", "Finance & Commercial", "Fixed Plant Maintenance", "Geology & Exploration", "Geotechnical Engineering", "Grade Control", "Human Resources & Payroll", "Mine Engineering", "Mine Surveying", "Mining Operations (Production)", "Mobile Equipment Maintenance", "Occupational Health & Safety", "Processing / Metallurgy", "Security", "Supply Chain & Logistics"])
        job_role = st.text_input("Job Role")
        shift = st.selectbox("Select Shift", ["", "Day Shift", "Night Shift"])
        ppe = st.selectbox("Is the worker wearing full PPE?", ["", "Yes", "No"])
        training = st.selectbox("Has the worker recieved and completed safety training?", ["", "Yes", "No"])
        fatigue = st.number_input("Worker's Fatigue Level (1-10)", min_value=1, max_value=10)  ########Check this line again!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        observation = st.text_area("Safety Observation(s)", placeholder="Enter any safety observations or concerns regarding the worker's health and safety.")
        near_misses = st.number_input("Number of near misses reported by the worker", min_value=0, step=1)
        previous_incidents = st.number_input("Number of previous incidents involving the worker", min_value=0, step=1)

        if st.button("Record Worker Data"):
            if worker_id.strip() == "":    #if worker_id is empty or only contains whitespace, show error message
                st.error("Please enter the Worker's ID.")
            elif worker_id.strip() in [str(w["Worker's ID"]) for w in st.session_state["workers"]]:   # FIX: reject a Worker's ID that already exists
                st.error("This Worker's ID already exists.")
            elif job_role.strip() == "":     #if job role is empty or only contains whitespace, show error message
                st.error("Please enter the Worker's Job Role.")
            elif department.strip() == "":     #if department is empty or only contains whitespace, show error message
                st.error("Please select the Worker's Department.")
            elif shift == "":                  # FIX: shift, PPE and training were never checked, so an empty answer was accepted
                st.error("Please select the shift.")
            elif ppe == "":
                st.error("Please state whether the worker is wearing full PPE.")
            elif training == "":
                st.error("Please state whether the worker has completed safety training.")
            elif observation.strip() == "":   #if worker's observations is empty or only contains whitespace, show error message
                st.error("Please enter any safety observations or concerns regarding the worker's health and safety. If there are none, please enter 'None'.")
            else:
            # Worker's risk level

                if (ppe == "No" or training == "No" or fatigue >= 8 or near_misses >= 3 or previous_incidents >= 2):
                    risk_level = "High"
                elif fatigue >= 5:
                    risk_level = "Medium"
                else:
                    risk_level = "Low"

#Save worker's information
                worker_data = {"Worker's ID": worker_id.strip(), "Department": department, "Job Role": job_role, "Shift": shift, "PPE": ppe, "Training": training, "Fatigue Level": int(fatigue), "Safety Observation(s)": observation, "Near Misses": int(near_misses), "Previous Incidents": int(previous_incidents), "Risk Level": risk_level}

                st.session_state["workers"].append(worker_data)
                save("workers")   # FIX: write to workers.csv so the record is not lost when the page is refreshed
                st.success("Worker safety data submitted successfully!")

                if risk_level == "High":
                    st.warning("The worker's risk level is HIGH. Please investigate immediately and take action to address the safety concerns.")
        st.subheader("Recorded Worker's Data")

        if len(st.session_state["workers"]) > 0:
            st.dataframe(st.session_state["workers"], **STRETCH)   #if the length of the workers list is greater than 0, 
                                                    #then the data should be displayed in a table format using the st.dataframe() function. 
                                                    #The dataframe will show all the recorded worker information stored in the session state.
            st.write("Total workers recorded:", len(st.session_state["workers"]))
        else:
            st.info("workers' data has not yet been recorded!")

    #part C

    elif selected_page == "Safety Incidents":
        st.header("Safety Incidents Database")
        st.write("Record and monitor safety incidents that occur at the mine")
        st.subheader("Record a New Safety Incident")
        incident_id = st.text_input("Incident ID")
        incident_worker_id = st.text_input("Worker ID")
        incident_date = st.date_input("Date of incident", value=date.today())
        # FIX: Time, Shift, Department, Lost-time injury, Cause and Status were added (all required by the brief)
        incident_time = st.time_input("Time of incident", value=datetime.now().time().replace(microsecond=0))
        incident_shift = st.selectbox("Shift", ["<CHOOSE>", "Day Shift", "Night Shift"])
        incident_department = st.selectbox("Department", ["<CHOOSE>"] + DEPTS)
        location = st.text_input("Location of the incident", placeholder= "Where did the incident happen...")   # FIX: one line instead of a big text box
        incident_type = st.selectbox("Type of incident", ["<CHOOSE>"] + INC_TYPES)   # FIX: drop-down, so incidents can be counted and categorised
        severity = st.selectbox("Incident Severity", ["<CHOOSE>", "Low", "Medium", "High", "Critical"])
        injury = st.selectbox(" Did the incident cause injury?", ["<CHOOSE>", "No", "Yes"])
        lost_time = st.selectbox("Lost-time injury?", ["<CHOOSE>", "No", "Yes"])
        cause = st.text_input("Cause of incident")
        incident_status = st.selectbox("Incident Status", ["Open", "Under Investigation", "Closed"])
        description = st.text_area("Description of Incident", placeholder= "Describe what happened...")
        corrective_action = st.text_area("Corrective Measures Taken", placeholder = "Describe actions taken...")

        if st.button("Record Incident"):
            if incident_id.strip() == "":
                st.error("Please enter incident ID.")
            
            elif incident_worker_id.strip()=="":
                st.error("Please input the Worker's ID.")

            # FIX: checks for the new fields (the old code accepted "<CHOOSE>" as an answer)
            elif incident_shift == "<CHOOSE>":
                st.error("Please select the shift.")
            elif incident_department == "<CHOOSE>":
                st.error("Please select the department.")
            elif location.strip() == "":
                st.error("Please enter the location.")
            elif incident_type == "<CHOOSE>":
                st.error("Please select the incident type.")
            elif severity == "<CHOOSE>":
                st.error("Please select the severity.")
            elif injury == "<CHOOSE>":
                st.error("Please state whether there was an injury.")
            elif lost_time == "<CHOOSE>":
                st.error("Please state whether it was a lost-time injury.")
            elif injury == "No" and lost_time == "Yes":
                st.error("A lost-time injury requires an injury.")
            elif cause.strip() == "":
                st.error("Please enter the cause of the incident.")
            
            else:

                duplicate = False
                for incident in st.session_state["incidents"]:
                    if incident["Incident ID"] == incident_id.strip():
                        duplicate = True
                        break

                if duplicate: 
                    st.error("This Incident already exists. Please enter another ID.")
                else:
                    # the keys match the columns of incidents.csv
                    incident = {"Incident ID": incident_id.strip(), "Worker ID": incident_worker_id.strip(), "Date": str(incident_date), "Time": incident_time.strftime("%H:%M"), "Shift": incident_shift, "Department": incident_department, "Location": location.strip(), "Incident Type": incident_type, "Severity": severity, "Injury": injury, "Lost-Time Injury": lost_time, "Cause": cause.strip(), "Status": incident_status, "Description": description.strip(), "Corrective Action": corrective_action.strip()}

                    st.session_state["incidents"].append(incident)
                    save("incidents")   # FIX: write to incidents.csv so the record is not lost when the page is refreshed
                    st.success("Safety incident recorded successfully!") 

                    if severity in ["High", "Critical"]:
                        st.warning("Extreme risk incident recorded. Attend immediately")
                    
                    if injury == "Yes":
                        st.warning("An injury was reported. Attend respond immediately")

        st.subheader("Recorded Safety Incidents")

        if len(st.session_state["incidents"]) > 0:
            st.dataframe(st.session_state["incidents"], **STRETCH)
            st.write("Total incidents recorded:", len(st.session_state["incidents"]))

            # FIX: search, filter, count and trends (brief part c) were missing. They are added BELOW her table so her lines stay as they were.
            inc_df = pd.DataFrame(st.session_state["incidents"])
            st.subheader("Search, filter and count incidents")
            search_text = st.text_input("Search incidents", placeholder="ID, worker, location, cause, description...")
            inc_view = search_df(filter_df(inc_df, ["Severity", "Shift", "Incident Type", "Status", "Department", "Injury"], "inc"), search_text)
            show_table(inc_view)
            st.write("Incidents shown:", len(inc_view), "of", len(inc_df))

            group = st.selectbox("Categorise and count incidents by", ["Incident Type", "Severity", "Department", "Shift", "Cause", "Status", "Location"])
            counts = inc_df[group].value_counts()
            bar_chart(counts.to_dict(), "Incidents by " + group, colors=SEV_COLORS, horizontal=True)
            st.write("Most frequent " + group.lower() + ":", counts.index[0], "(" + str(counts.iloc[0]) + " incidents)")

            monthly = st.radio("Trend interval", ["Daily", "Monthly"], horizontal=True) == "Monthly"
            dates = pd.to_datetime(inc_df["Date"], errors="coerce").dropna()
            if len(dates) > 0:
                line_chart(dates.dt.strftime("%Y-%m" if monthly else "%Y-%m-%d").value_counts().sort_index(),
                           "Incidents per " + ("month" if monthly else "day"))
        else:
            st.info("No safety incidents have been recorded yet.")


#####PLACEHOLDERS FOR OTHER SECTIONS
                        
    elif selected_page == "Equipment Data":
        st.header("Equipment Database and Condition Monitoring")
        equipment_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "equipment.csv")
        equipment_types = ["Haul Truck", "Loader", "Excavator", "Drilling Machine",
                           "Bulldozer", "Scraper Winch", "Crusher", "Conveyor"]
        part_statuses = ["Good", "Worn", "Faulty"]
        maintenance_statuses = ["Operational", "Due for Maintenance", "Overdue", "Under Maintenance"]
        columns = ["Equipment ID", "Equipment Type", "Manufacturer", "Operating Hours",
                   "Temperature (C)", "Vibration (mm/s)", "Fuel Consumption (L/h)",
                   "Brake Status", "Tyre Status", "Engine Status", "Maintenance Status",
                   "Downtime (hours)", "Last Maintenance", "Next Maintenance Due", "Alert Count"]
        numeric = ["Operating Hours", "Temperature (C)", "Vibration (mm/s)",
                   "Fuel Consumption (L/h)", "Downtime (hours)", "Alert Count"]

        # Accept the column names used in your earlier equipment CSV.
        aliases = {"ID": "Equipment ID", "Type": "Equipment Type",
                   "Operating time": "Operating Hours", "Temperature": "Temperature (C)",
                   "Vibration": "Vibration (mm/s)", "Fuel": "Fuel Consumption (L/h)",
                   "Brakes": "Brake Status", "Tyres": "Tyre Status", "Engine": "Engine Status",
                   "Maintenance": "Maintenance Status", "Downtime": "Downtime (hours)",
                   "Alerts": "Alert Count"}

        # Load saved records once per session.
        if "equipment" not in st.session_state:
            try:
                saved = pd.read_csv(equipment_file, keep_default_na=False, dtype=str)
                st.session_state["equipment"] = saved.to_dict("records")
            except (FileNotFoundError, pd.errors.EmptyDataError):
                st.session_state["equipment"] = []

        data = pd.DataFrame(st.session_state["equipment"])
        for old, new in aliases.items():
            if old in data.columns and new not in data.columns:
                data[new] = data[old]
        if "Operating Hours" not in data.columns and "Hours" in data.columns:
            data["Operating Hours"] = data["Hours"]
        for column in columns:
            if column not in data.columns:
                data[column] = 0 if column in numeric else ""
        data[numeric] = data[numeric].apply(pd.to_numeric, errors="coerce").fillna(0)
        data["Maintenance Status"] = data["Maintenance Status"].replace(
            {"Normal": "Operational", "Due": "Due for Maintenance"})
        st.session_state["equipment"] = data.to_dict("records")

        def save_equipment():
            saved = pd.DataFrame(st.session_state["equipment"])
            for old, new in aliases.items():
                if old in saved.columns:
                    saved[old] = saved[new]
            saved.to_csv(equipment_file, index=False)

        # Example limits: temperature 80/100 C; vibration 5/8 mm/s.
        def reading_status(value, warning, critical):
            if value > critical:
                return "Critical"
            elif value >= warning:
                return "Warning"
            else:
                return "Normal"

        def machine_condition(temp, vibration):
            states = [reading_status(temp, 80, 100), reading_status(vibration, 5, 8)]
            if "Critical" in states:
                return "Critical"
            elif "Warning" in states:
                return "Warning"
            else:
                return "Normal"

        if "equipment_message" in st.session_state:
            st.success(st.session_state.pop("equipment_message"))

        register, records, monitoring, charts = st.tabs(
            ["D: Register", "D: Equipment Records", "E: Monitoring", "E: Charts"])

        # D: Register a machine and save its details.
        with register:
            with st.form("equipment_form", clear_on_submit=True):
                left, right = st.columns(2)
                eq_id = left.text_input("Equipment ID")
                eq_type = left.selectbox("Equipment Type", equipment_types)
                maker = left.text_input("Manufacturer")
                hours = left.number_input("Operating Hours", min_value=0.0)
                downtime = left.number_input("Downtime (hours)", min_value=0.0)
                fuel = left.number_input("Fuel consumption (L/h)", min_value=0.0)
                temp = left.number_input("Temperature (C)", value=60.0)
                vibration = left.number_input("Vibration (mm/s)", min_value=0.0, value=2.0)
                brakes = right.selectbox("Brake Status", part_statuses)
                tyres = right.selectbox("Tyre Status", part_statuses)
                engine = right.selectbox("Engine Status", part_statuses)
                maintenance = right.selectbox("Maintenance Status", maintenance_statuses)
                last = right.date_input("Last Maintenance", value=date.today())
                due = right.date_input("Next Maintenance Due", value=date.today() + timedelta(days=90))
                submitted = st.form_submit_button("Register Equipment")

            if submitted:
                existing_ids = [r["Equipment ID"] for r in st.session_state["equipment"]]
                if not eq_id.strip() or not maker.strip():
                    st.error("Equipment ID and manufacturer are required.")
                elif eq_id.strip() in existing_ids:
                    st.error("This equipment ID already exists.")
                elif due < last:
                    st.error("Next maintenance due cannot be before last maintenance.")
                else:
                    st.session_state["equipment"].append({
                        "Equipment ID": eq_id.strip(), "Equipment Type": eq_type,
                        "Manufacturer": maker.strip(), "Operating Hours": hours,
                        "Temperature (C)": temp, "Vibration (mm/s)": vibration,
                        "Fuel Consumption (L/h)": fuel, "Brake Status": brakes,
                        "Tyre Status": tyres, "Engine Status": engine,
                        "Maintenance Status": maintenance, "Downtime (hours)": downtime,
                        "Last Maintenance": str(last), "Next Maintenance Due": str(due),
                        "Alert Count": int(temp >= 80) + int(vibration >= 5)
                    })
                    save_equipment()
                    st.session_state["equipment_message"] = "Equipment registered successfully."
                    st.rerun()

        data = pd.DataFrame(st.session_state["equipment"], columns=columns)
        if not data.empty:
            data["Condition"] = [machine_condition(t, v)
                                 for t, v in zip(data["Temperature (C)"], data["Vibration (mm/s)"])]

        # D: Search, filter and display saved equipment.
        with records:
            if data.empty:
                st.info("No equipment recorded yet.")
            else:
                search = st.text_input("Search Equipment ID / Manufacturer")
                kind = st.selectbox("Filter Equipment Type", ["All"] + equipment_types)
                view = data.copy()
                if kind != "All":
                    view = view[view["Equipment Type"] == kind]
                if search:
                    mask = (view["Equipment ID"].astype(str).str.contains(search, case=False, regex=False)
                            | view["Manufacturer"].astype(str).str.contains(search, case=False, regex=False))
                    view = view[mask]
                st.dataframe(view, **STRETCH)

        # E: Check and update the selected machine's readings.
        with monitoring:
            st.caption("These monitoring limits are educational example values.")
            if data.empty:
                st.info("Register equipment before checking readings.")
            else:
                st.table(pd.DataFrame({
                    "Parameter": ["Temperature", "Vibration"],
                    "Normal": ["Below 80 C", "Below 5 mm/s"],
                    "Warning": ["80 to 100 C", "5 to 8 mm/s"],
                    "Critical": ["Above 100 C", "Above 8 mm/s"]
                }))
                selected_id = st.selectbox("Select Equipment", data["Equipment ID"].tolist())
                machine = next(r for r in st.session_state["equipment"] if r["Equipment ID"] == selected_id)

                with st.form("reading_form_" + selected_id):
                    new_temp = st.number_input("New Temperature (C)", value=float(machine["Temperature (C)"]))
                    new_vibration = st.number_input("New Vibration (mm/s)", min_value=0.0,
                                                    value=float(machine["Vibration (mm/s)"]))
                    update = st.form_submit_button("Update Readings")

                if update:
                    machine["Temperature (C)"] = new_temp
                    machine["Vibration (mm/s)"] = new_vibration
                    machine["Alert Count"] += int(new_temp >= 80) + int(new_vibration >= 5)
                    save_equipment()
                    st.session_state["equipment_message"] = "Readings updated successfully."
                    st.rerun()

                for name, value, warning, critical, unit in [
                    ("Temperature", machine["Temperature (C)"], 80, 100, "C"),
                    ("Vibration", machine["Vibration (mm/s)"], 5, 8, "mm/s")
                ]:
                    status = reading_status(value, warning, critical)
                    message = f"{selected_id}: {name} = {value:g} {unit} ({status})"
                    if status == "Critical":
                        st.error(message + ". Inspection required.")
                    elif status == "Warning":
                        st.warning(message + ". Monitor closely and arrange an inspection.")
                    else:
                        st.success(message)

                st.dataframe(data[["Equipment ID", "Temperature (C)", "Vibration (mm/s)",
                                   "Condition", "Alert Count"]], **STRETCH)

        # E: Compare readings with the warning and critical limits.
        with charts:
            if data.empty:
                st.info("Register equipment to display charts.")
            else:
                for column, warning, critical in [("Temperature (C)", 80, 100),
                                                   ("Vibration (mm/s)", 5, 8)]:
                    figure = go.Figure(go.Bar(x=data["Equipment ID"], y=data[column]))
                    figure.update_layout(title=column, xaxis_title="Equipment ID", yaxis_title=column)
                    figure.add_hline(y=warning, line_dash="dash", line_color="orange", annotation_text="Warning")
                    figure.add_hline(y=critical, line_dash="dash", line_color="red", annotation_text="Critical")
                    st.plotly_chart(figure, **STRETCH)
                st.bar_chart(data["Condition"].value_counts())

    # f) Equipment Maintenance Monitoring 
    elif selected_page == "Maintenance Data":   # FIX: this line had 3 spaces instead of 4, which stopped the whole app with an IndentationError
        st.header("Equipment Maintenance Monitoring")

        if "maintenance_message" in st.session_state:       # message saved before st.rerun()
            st.success(st.session_state.pop("maintenance_message"))

        if len(st.session_state["equipment"]) == 0:
            st.info("No equipment recorded yet. Register equipment in Equipment Data first.")
        else:
            today = date.today()
            rows = []

            # Check every machine and decide which maintenance categories it falls into
            for r in st.session_state["equipment"]:
                operating = float(r["Operating Hours"] or 0)
                downtime = float(r["Downtime (hours)"] or 0)
                alert_count = float(r["Alert Count"] or 0)
                status = r["Maintenance Status"]
                due_text = str(r["Next Maintenance Due"])       # dates are saved as text like 2026-11-01

                # Availability = Operating Time / (Operating Time + Downtime) x 100
                total = operating + downtime
                availability = round(operating / total * 100, 1) if total > 0 else 0

                under = status == "Under Maintenance"
                overdue = (not under) and (status == "Overdue" or (due_text != "" and due_text < str(today)))
                due = (not under) and (not overdue) and (status == "Due for Maintenance" or (
                      due_text != "" and due_text <= str(today + timedelta(days=14))))

                rows.append({"Equipment ID": r["Equipment ID"], "Availability (%)": availability,
                             "Downtime (hours)": downtime, "Alert Count": alert_count,
                             "Next Maintenance Due": due_text, "Maintenance Status": status,
                             "Due": due, "Overdue": overdue, "Under Maintenance": under,
                             "Excessive Downtime": downtime >= 500,     # 500 hours or more
                             "Repeated Alerts": alert_count >= 3,       # 3 alerts or more
                             "Low Availability": availability < 85})    # below 85 %

            table = pd.DataFrame(rows)
            categories = ["Due", "Overdue", "Under Maintenance", "Excessive Downtime", "Repeated Alerts", "Low Availability"]
            show = ["Equipment ID", "Availability (%)", "Downtime (hours)", "Alert Count",
                    "Next Maintenance Due", "Maintenance Status"]

            status_tab, update_tab, log_tab = st.tabs(["F: Maintenance Status", "F: Update Maintenance", "F: Maintenance Log"])

            with status_tab:
                st.write("Average equipment availability:", round(table["Availability (%)"].mean(), 1), "%")

                counts = st.columns(6)
                for i, name in enumerate(categories):
                    counts[i].metric(name, int(table[name].sum()))

                for name in categories:         # one list of equipment for each category
                    with st.expander(name + " (" + str(int(table[name].sum())) + ")"):
                        st.dataframe(table[table[name]][show], **STRETCH)

                for r in rows:                  # maintenance alerts
                    if r["Overdue"]:
                        st.error(r["Equipment ID"] + ": maintenance is overdue. Schedule maintenance immediately.")
                    if r["Excessive Downtime"]:
                        st.warning(r["Equipment ID"] + ": excessive downtime. Investigate the causes.")

            with update_tab:
                ids = [r["Equipment ID"] for r in st.session_state["equipment"]]
                with st.form("maintenance_form", clear_on_submit=True):
                    eq_choice = st.selectbox("Equipment", ids)
                    action = st.selectbox("Action", ["Start maintenance", "Complete maintenance"])
                    work_date = st.date_input("Date", value=date.today())
                    technician = st.text_input("Technician / Maintenance Engineer")
                    interval = st.number_input("Days until next maintenance (when completing)", min_value=1, value=90)
                    added = st.number_input("Downtime hours to add", min_value=0.0)
                    save_work = st.form_submit_button("Save Maintenance Record")

                if save_work:
                    record = next(r for r in st.session_state["equipment"] if r["Equipment ID"] == eq_choice)
                    if technician.strip() == "":
                        st.error("Please enter the technician's name.")
                    elif action == "Start maintenance" and record["Maintenance Status"] == "Under Maintenance":
                        st.error("This equipment is already under maintenance.")
                    elif action == "Complete maintenance" and record["Maintenance Status"] != "Under Maintenance":
                        st.error("Only equipment under maintenance can be completed. Start maintenance first.")
                    else:
                        record["Downtime (hours)"] = float(record["Downtime (hours)"] or 0) + added
                        if action == "Start maintenance":
                            record["Maintenance Status"] = "Under Maintenance"
                        else:
                            record["Maintenance Status"] = "Operational"
                            record["Last Maintenance"] = str(work_date)
                            record["Next Maintenance Due"] = str(work_date + timedelta(days=int(interval)))
                            record["Alert Count"] = 0

                        st.session_state["maintenance_log"].append({
                            "Log ID": "MNT-" + str(len(st.session_state["maintenance_log"]) + 1).zfill(3),
                            "Equipment ID": eq_choice, "Action": action, "Date": str(work_date),
                            "Technician": technician.strip(), "Downtime Added (h)": added})
                        pd.DataFrame(st.session_state["equipment"]).to_csv(equipment_file, index=False)   # save to csv
                        save("maintenance_log")   # FIX: the log was never saved, so it disappeared on refresh
                        st.session_state["maintenance_message"] = action + " recorded for " + eq_choice + "."
                        st.rerun()

            with log_tab:
                if len(st.session_state["maintenance_log"]) > 0:
                    st.dataframe(st.session_state["maintenance_log"], **STRETCH)
                else:
                    st.info("No maintenance work has been logged yet.")

    # g) Risk Assessment
    elif selected_page == "Risk Assessment":
        st.header("Risk Assessment")
        st.write("Risk Score = Likelihood x Consequence (1-5 scale). 1-4 Low | 5-9 Medium | 10-16 High | 17-25 Critical")

        with st.form("risk_form", clear_on_submit=True):
            risk_id = st.text_input("Risk ID")
            hazard = st.text_input("Hazard description")
            likelihood = st.selectbox("Likelihood (1 = rare ... 5 = almost certain)", [1, 2, 3, 4, 5])
            consequence = st.selectbox("Consequence (1 = minor ... 5 = catastrophic)", [1, 2, 3, 4, 5])
            submitted_risk = st.form_submit_button("Record Risk Assessment")

        if submitted_risk:
            if risk_id.strip() == "":
                st.error("Please enter the Risk ID.")
            elif hazard.strip() == "":
                st.error("Please describe the hazard.")
            elif risk_id.strip() in [r["Risk ID"] for r in st.session_state["risks"]]:
                st.error("This Risk ID already exists. Please enter another ID.")
            else:
                risk_score = likelihood * consequence       # RiskScore = Likelihood x Consequence

                if risk_score <= 4:
                    classification = "Low"
                elif risk_score <= 9:
                    classification = "Medium"
                elif risk_score <= 16:
                    classification = "High"
                else:
                    classification = "Critical"

                st.session_state["risks"].append({"Risk ID": risk_id.strip(), "Hazard": hazard.strip(),
                                                  "Likelihood": likelihood, "Consequence": consequence,
                                                  "Risk Score": risk_score, "Classification": classification})
                save("risks")   # FIX: the risks were never saved, so they disappeared on refresh

                if classification == "Critical":
                    st.error("CRITICAL RISK (score " + str(risk_score) + "). Immediate management attention is required.")
                elif classification == "High":
                    st.warning("HIGH RISK (score " + str(risk_score) + "). Additional controls are required.")
                else:
                    st.success("Risk recorded: score " + str(risk_score) + " (" + classification + ").")

        st.subheader("Recorded Risk Assessments")
        if len(st.session_state["risks"]) > 0:
            st.dataframe(st.session_state["risks"], **STRETCH)
        else:
            st.info("No risk assessments have been recorded yet.")
        
    # h) Alerts and Notifications
    elif selected_page == "Alerts":
        st.header("Alerts and Notifications")

        alerts = []                  # each alert is a dictionary, like the worker and incident records
        today = str(date.today())

        # "page" is the list of sections this role can open, so each role only sees its own alerts
        if "Equipment Data" in page:
            for r in st.session_state["equipment"]:
                downtime = float(r["Downtime (hours)"] or 0)
                due_text = str(r["Next Maintenance Due"])

                # High temperature and high vibration
                for name, value, warning, critical in [("Temperature", float(r["Temperature (C)"] or 0), 80, 100),
                                                       ("Vibration", float(r["Vibration (mm/s)"] or 0), 5, 8)]:
                    if value > critical:
                        alerts.append({"Level": "Critical", "Category": "High equipment " + name.lower(),
                                       "ID": r["Equipment ID"], "Value": str(value),
                                       "Action": "Inspect equipment and start maintenance/safety procedures."})
                    elif value >= warning:
                        alerts.append({"Level": "Warning", "Category": "High equipment " + name.lower(),
                                       "ID": r["Equipment ID"], "Value": str(value),
                                       "Action": "Monitor closely and schedule an inspection."})

                # Overdue maintenance
                overdue = r["Maintenance Status"] == "Overdue" or (due_text != "" and due_text < today)
                if overdue and r["Maintenance Status"] != "Under Maintenance":
                    alerts.append({"Level": "Critical", "Category": "Overdue maintenance", "ID": r["Equipment ID"],
                                   "Value": "Due " + due_text, "Action": "Schedule maintenance immediately."})

                # Excessive downtime
                if downtime >= 500:
                    alerts.append({"Level": "Warning", "Category": "Excessive equipment downtime", "ID": r["Equipment ID"],
                                   "Value": str(downtime) + " hours", "Action": "Investigate causes of downtime."})

        if "Worker Safety Data" in page:
            for w in st.session_state["workers"]:
                if w["PPE"] == "No":
                    alerts.append({"Level": "Critical", "Category": "Low PPE compliance", "ID": w["Worker's ID"],
                                   "Value": "Not wearing full PPE", "Action": "Stop work until full PPE is worn."})
                if int(w["Fatigue Level"]) >= 8:
                    alerts.append({"Level": "Warning", "Category": "High fatigue level", "ID": w["Worker's ID"],
                                   "Value": str(w["Fatigue Level"]) + "/10", "Action": "Rest the worker or reassign duties."})
                if w["Risk Level"] == "High":
                    alerts.append({"Level": "Warning", "Category": "High-risk safety observation", "ID": w["Worker's ID"],
                                   "Value": "High", "Action": "Investigate the safety observation."})

        if "Safety Incidents" in page:
            for i in st.session_state["incidents"]:
                if i["Severity"] in ["High", "Critical"]:
                    alerts.append({"Level": "Critical" if i["Severity"] == "Critical" else "Warning",
                                   "Category": "Critical safety incident" if i["Severity"] == "Critical" else "High-severity safety incident",
                                   "ID": i["Incident ID"], "Value": i["Severity"],
                                   "Action": "Attend immediately and complete the investigation."})

        if "Risk Assessment" in page:
            for k in st.session_state["risks"]:
                if k["Classification"] in ["High", "Critical"]:
                    alerts.append({"Level": "Critical" if k["Classification"] == "Critical" else "Warning",
                                   "Category": "High-risk assessment", "ID": k["Risk ID"],
                                   "Value": "Score " + str(k["Risk Score"]), "Action": "Implement additional controls."})

        alerts.sort(key=lambda a: a["Level"] != "Critical")      # critical alerts first

        if len(alerts) == 0:
            st.success("There are no active alerts.")
        else:
            critical = len([a for a in alerts if a["Level"] == "Critical"])
            st.write("Active alerts:", len(alerts), "| Critical:", critical, "| Warning:", len(alerts) - critical)
            st.dataframe(alerts, **STRETCH)

            # Full notification in the format of Figure 1 in the brief
            number = st.selectbox("Select an alert to see the full notification", range(len(alerts)),
                                  format_func=lambda n: str(alerts[n]["ID"]) + " - " + alerts[n]["Category"])
            a = alerts[number]
            line = "=" * 53
            st.code(line + "\nMINING MONITORING ALERT\n" + line + "\n[" + a["Level"].upper() + "]\nID: " + str(a["ID"])
                    + "\nIssue: " + a["Category"] + "\nValue: " + str(a["Value"])
                    + "\nRecommended Action:\n " + a["Action"] + "\n" + line)


    elif selected_page == "General Reports":
        st.header("General Reports")
        st.write("Worker records:", len(st.session_state["workers"]))
        st.write("Incident records:", len(st.session_state["incidents"]))

        if st.button("Show Worker Records"):
            if st.session_state["workers"]:
                st.dataframe(st.session_state["workers"])
            else:
                st.info("No worker records are available.")

        if st.button("Show Incident Records"):
            if st.session_state["incidents"]:
                st.dataframe(st.session_state["incidents"])
            else:
                st.info("No incident records are available.")
        
    elif selected_page == "Manage Users":
        st.header("Manage Users")
        st.write("Users loaded from users.csv:")
        user_list=[]

        for username_from_file in users:
            user_list.append({"Username": username_from_file, "Role": users[username_from_file]["role"]})
        
        st.dataframe(user_list, **STRETCH)

    # j) Interactive Data Analysis (the questions and charts are in the analysis section above)
    elif selected_page == "Data Analysis":
        page_analysis(page)
