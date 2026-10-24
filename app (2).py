import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import csv, os, sys, subprocess, base64
from datetime import date, datetime, timedelta
from streamlit.runtime import exists

# ------------------------------ START-UP ------------------------------
BASE = os.path.dirname(os.path.abspath(__file__))   # data files live next to this program
THEME = {"base": "dark", "primaryColor": "#2E8B57", "backgroundColor": "#1A1D21",
         "secondaryBackgroundColor": "#23272D", "textColor": "#9E9E9E"}


def write_theme_config():
    """Save the colour theme to .streamlit/config.toml (once) so Streamlit's own widgets use it too."""
    path = os.path.join(BASE, ".streamlit", "config.toml")
    try:
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write("[theme]\n" + "".join(f'{k} = "{v}"\n' for k, v in THEME.items()))
    except OSError:
        pass   # the CSS below still applies the colours


write_theme_config()
if not exists():   # started with "python app.py": launch it through Streamlit instead
    subprocess.run([sys.executable, "-m", "streamlit", "run", __file__])
    sys.exit()

st.set_page_config(page_title="KHWEZI MINING", page_icon=":pick:", layout="wide")

# ------------------------------ CONSTANTS ------------------------------
FILES = {k: os.path.join(BASE, v) for k, v in {
    "workers": "workers.csv", "incidents": "incidents.csv", "equipment": "equipment.csv",
    "maintenance_log": "maintenance_log.csv", "risks": "risks.csv"}.items()}
USERS_FILE = os.path.join(BASE, "users.csv")
DEMO_USERS = ("username,password,role\nadmin,admin123,Administrator\nsafety,safety123,Safety Officer\n"
              "engineer,engineer123,Mine Engineer\nmaintenance,maint123,Maintenance Engineer\n"
              "manager,manager123,Manager\n")
ROLE_ALIASES = {"Maintenance Manager": "Maintenance Engineer", "Mining Engineer": "Mine Engineer"}

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

# PART (a): which pages each role may open (Table 1 of the brief).
# FIX: one dictionary replaces the five repeated if/elif page lists; page names must match the PAGE_FUNCS names exactly.
ALL = ["Dashboard", "Alerts", "Worker Safety Data", "Equipment Data", "Maintenance Data", "Safety Incidents",
       "Risk Assessment", "Data Analysis", "General Reports"]
PAGES = {"Administrator": ALL + ["Manage Users"],
         "Safety Officer": ["Dashboard", "Alerts", "Worker Safety Data", "Safety Incidents", "Risk Assessment",
                            "Data Analysis", "General Reports"],
         "Mine Engineer": ALL,
         "Maintenance Engineer": ["Dashboard", "Alerts", "Equipment Data", "Maintenance Data", "Data Analysis",
                                  "General Reports"],
         "Manager": ALL}

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


def load_users():
    """PART (a): reads users.csv into a dictionary (her original loop)."""
    if not os.path.exists(USERS_FILE):   # FIX: create a demo file instead of crashing when users.csv is missing
        with open(USERS_FILE, "w", newline="") as f:
            f.write(DEMO_USERS)
        S["demo_users"] = True
    users = {}   # {"admin": {"password": "admin123", "role": "Administrator"}}
    with open(USERS_FILE, mode="r", newline="") as file:   # newline="" handles line endings on every operating system
        reader = csv.DictReader(file)   # every row becomes a dictionary {username: ..., password: ..., role: ...}
        for row in reader:
            file_username = row["username"].strip()
            file_password = row["password"].strip()
            file_role = row["role"].strip()
            if file_username != "":   # skip empty rows
                users[file_username] = {"password": file_password, "role": file_role}
    return users


# ------------------------------ LOGIC HELPERS ------------------------------
def first_error(checks):
    """Return the message of the first failed check, or None."""
    return next((msg for failed, msg in checks if failed), None)


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


def find_eq(eq_id):
    return next((r for r in S["equipment"] if r["Equipment ID"] == eq_id), None)


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


def sample_equipment():
    d = lambda n: str(date.today() + timedelta(days=n))
    rows = [("TRK-012", "Haul Truck", "Caterpillar", 4200, 92, 9.2, 85, "Good", "Worn", "Good", "Overdue", 520, -120, -10, 4),
            ("TRK-014", "Haul Truck", "Komatsu", 5100, 74, 3.8, 80, "Good", "Good", "Good", "Operational", 140, -30, 60, 0),
            ("LDR-003", "Loader", "Volvo", 3300, 85, 4.1, 55, "Good", "Good", "Good", "Due for Maintenance", 210, -80, 7, 2),
            ("EXC-001", "Excavator", "Hitachi", 6000, 102, 6.5, 95, "Good", "Good", "Faulty", "Under Maintenance", 900, -5, 25, 5),
            ("DRL-007", "Drilling Machine", "Epiroc", 2800, 70, 2.9, 40, "Good", "Good", "Good", "Operational", 90, -20, 70, 0),
            ("BDZ-002", "Bulldozer", "Caterpillar", 3900, 78, 5.4, 70, "Worn", "Good", "Good", "Operational", 330, -45, 40, 3),
            ("CRS-001", "Crusher", "Metso", 7000, 88, 7.1, 0, "Good", "Good", "Good", "Due for Maintenance", 600, -85, 3, 3),
            ("CNV-004", "Conveyor", "Sandvik", 7600, 60, 2.2, 0, "Good", "Good", "Good", "Operational", 60, -15, 90, 0)]
    return [dict(zip(EQ_COLS, r[:12] + (d(r[12]), d(r[13]), r[14]))) for r in rows]


def classify_risk(score):
    """RiskScore = Likelihood x Consequence: 1-4 Low, 5-9 Medium, 10-16 High, 17-25 Critical."""
    return next(name for limit, name in RISK_CLASSES if score <= limit)


def generate_alerts(role):
    """Build every active alert the role is allowed to see (based on the role's page access)."""
    pages, out = PAGES.get(role, []), []

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
def alert_text(level_, id_type, id_, param, value, status, action):
    """Alert in the style of Figure 1 of the project brief."""
    line = "=" * 53
    return (f"{line}\nMINING MONITORING ALERT\n{line}\n[{level_.upper()}]\n{id_type}: {id_}\nParameter: {param}\n"
            f"Value: {value}\nStatus: {status}\nRecommended Action:\n {action}\n{line}")


def show_alert(a):
    st.code(alert_text(a["Level"], a["ID Type"], a["ID"], a["Parameter"], a["Value"], a["Status"], a["Action"]),
            language=None)


def show_condition_alerts(alerts):
    if not alerts:
        st.info(NORMAL_MSG)
    for a in alerts:
        st.write(a["Message"])
        show_alert(a)


def notify(kind, payload):
    """Queue a message that is shown after the next rerun (so the page also shows the new data)."""
    S.setdefault("flash", []).append((kind, payload))


def show_flash():
    for kind, payload in S.pop("flash", []):
        if kind == "condition":
            show_condition_alerts(payload)
        else:
            getattr(st, kind)(payload)


def fkey(name):
    """Form/widget key that changes when reset_form() is called, which clears the form."""
    return f"{name}_{S.get('ver_' + name, 0)}"


def reset_form(name):
    S["ver_" + name] = S.get("ver_" + name, 0) + 1


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


# ------------------------------ PAGES ------------------------------
def page_dashboard():
    st.header("Dashboard")
    w, inc, eq, rk = pd.DataFrame(S["workers"]), pd.DataFrame(S["incidents"]), equipment_df(), pd.DataFrame(S["risks"])
    alerts = generate_alerts(S["role"])
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


def page_alerts():
    st.header("Alerts and Notifications")
    alerts = generate_alerts(S["role"])
    if not alerts:
        st.success("There are no active alerts.")
        return
    crit = sum(a["Level"] == "Critical" for a in alerts)
    m = st.columns(3)
    m[0].metric("Active alerts", len(alerts))
    m[1].metric("Critical", crit)
    m[2].metric("Warning", len(alerts) - crit)

    df = pd.DataFrame(alerts)
    f1, f2 = st.columns(2)
    levels = f1.multiselect("Level", sorted(df["Level"].unique()))
    cats = f2.multiselect("Category", sorted(df["Category"].unique()))
    shown = [a for a in alerts if (not levels or a["Level"] in levels) and (not cats or a["Category"] in cats)]
    show_table(pd.DataFrame(shown, columns=["Level", "Category", "ID Type", "ID", "Parameter", "Value", "Status"]))
    if shown:
        labels = [f"[{a['Level'].upper()}] {a['ID']} - {a['Category']}" for a in shown]
        pick = st.selectbox("Select an alert to see the full notification and recommended action", labels)
        show_alert(shown[labels.index(pick)])


# =====================================================================
# PART (b) WORKER HEALTH AND SAFETY MONITORING  -  written by Group Member 1
# Her original logic is kept: same fields, same risk rules, same messages.
# Every change is marked "FIX:" so it is easy to explain in the interview.
# =====================================================================
def page_workers():
    st.header("Worker Health and Safety Monitoring")
    st.write("Record the worker's safety data and look for potential health and safety risks.")
    st.subheader("Record Worker Information")

    # --- input fields (same order as the original code) ---
    worker_id = st.text_input("Worker's ID")
    department = st.selectbox("Select Department", [""] + DEPTS)   # FIX: shared DEPTS list instead of a long list typed inside the page
    job_role = st.text_input("Job Role")
    shift = st.selectbox("Select Shift", ["Day Shift", "Night Shift"])
    ppe = st.selectbox("Is the worker wearing full PPE?", ["", "Yes", "No"])
    training = st.selectbox("Has the worker received and completed safety training?", ["", "Yes", "No"])
    fatigue = st.number_input("Worker's Fatigue Level (1-10)", min_value=1, max_value=10, value=1, step=1)   # FIX: whole numbers only
    observation = st.text_area("Safety Observation(s)", placeholder="Enter any safety observations or concerns regarding the worker's health and safety.")
    near_misses = st.number_input("Number of near misses reported by the worker", min_value=0, step=1)
    previous_incidents = st.number_input("Number of previous incidents involving the worker", min_value=0, step=1)

    if st.button("Record Worker Data"):
        # FIX: one list of checks replaces the long if/elif chain; the first failed check is shown.
        # FIX: PPE and training were never checked before, so an empty answer was accepted.
        # FIX: a worker ID that already exists is rejected (same idea as her incident ID check).
        error = first_error([
            (worker_id.strip() == "", "Please enter the Worker's ID."),
            (worker_id.strip() in [str(w["Worker's ID"]) for w in S["workers"]], "This Worker's ID already exists."),
            (department == "", "Please select the Worker's Department."),
            (job_role.strip() == "", "Please enter the Worker's Job Role."),
            (ppe == "", "Please state whether the worker is wearing full PPE."),
            (training == "", "Please state whether the worker has completed safety training."),
            (observation.strip() == "", "Please enter any safety observations or concerns regarding the worker's health and safety. If there are none, please enter 'None'.")])
        if error:
            st.error(error)
        else:
            # Worker's risk level (her original rules, unchanged)
            if ppe == "No" or training == "No" or fatigue >= 8 or near_misses >= 3 or previous_incidents >= 2:
                risk_level = "High"
            elif fatigue >= 5:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            # Save the worker's information (keys match the columns of workers.csv)
            worker_data = {"Worker's ID": worker_id.strip(), "Department": department, "Job Role": job_role.strip(),
                           "Shift": shift, "PPE": ppe, "Training": training, "Fatigue Level": int(fatigue),
                           "Safety Observation(s)": observation.strip(), "Near Misses": int(near_misses),
                           "Previous Incidents": int(previous_incidents), "Risk Level": risk_level}
            S["workers"].append(worker_data)
            save("workers")   # FIX: write to workers.csv so the data is not lost when the page is refreshed
            st.success("Worker safety data submitted successfully!")
            if risk_level == "High":
                st.warning("The worker's risk level is HIGH. Please investigate immediately and take action to address the safety concerns.")

    st.subheader("Recorded Worker's Data")
    if len(S["workers"]) > 0:
        show_table(pd.DataFrame(S["workers"]))   # FIX: shared table (colour-coded risk level, no deprecated use_container_width)
        st.write("Total workers recorded:", len(S["workers"]))
    else:
        st.info("Workers' data has not yet been recorded!")


# =====================================================================
# PART (c) SAFETY INCIDENT DATABASE  -  written by Group Member 1
# The recording form is hers. FIX: the missing fields and the
# view / search / filter / count / trend tabs were added to meet the brief.
# =====================================================================
def page_incidents():
    st.header("Safety Incidents Database")
    st.write("Record and monitor safety incidents that occur at the mine")
    tab_add, tab_view, tab_count = st.tabs(["Record Incident", "View / Search / Filter", "Counts & Trends"])

    with tab_add:
        st.subheader("Record a New Safety Incident")
        incident_id = st.text_input("Incident ID")
        incident_worker_id = st.text_input("Worker ID")
        incident_date = st.date_input("Date of incident", value=date.today())
        incident_time = st.time_input("Time of incident", value=datetime.now().time().replace(microsecond=0))   # FIX: new field (brief)
        shift = st.selectbox("Shift", ["<CHOOSE>", "Day Shift", "Night Shift"])                              # FIX: new field (brief)
        department = st.selectbox("Department", ["<CHOOSE>"] + DEPTS)                                        # FIX: new field (brief)
        location = st.text_input("Location of the incident", placeholder="Where did the incident happen...")   # FIX: one line, not a big text box
        incident_type = st.selectbox("Type of incident", ["<CHOOSE>"] + INC_TYPES)   # FIX: drop-down so incidents can be counted and categorised
        severity = st.selectbox("Incident Severity", ["<CHOOSE>", "Low", "Medium", "High", "Critical"])
        injury = st.selectbox("Did the incident cause injury?", ["<CHOOSE>", "No", "Yes"])
        lost_time = st.selectbox("Lost-time injury?", ["<CHOOSE>", "No", "Yes"])                              # FIX: new field (brief)
        cause = st.text_input("Cause of incident")                                                           # FIX: new field (brief)
        status = st.selectbox("Incident Status", ["Open", "Under Investigation", "Closed"])                  # FIX: new field (brief)
        description = st.text_area("Description of Incident", placeholder="Describe what happened...")
        corrective_action = st.text_area("Corrective Measures Taken", placeholder="Describe actions taken...")

        if st.button("Record Incident"):
            existing_ids = [str(i["Incident ID"]) for i in S["incidents"]]   # FIX: the old loop used the misspelled key "indidents"
            error = first_error([
                (incident_id.strip() == "", "Please enter the Incident ID."),
                (incident_id.strip() in existing_ids, "This Incident ID already exists. Please enter another ID."),
                (incident_worker_id.strip() == "", "Please enter the Worker's ID."),   # FIX: the old code checked worker_id (a variable from the Workers page)
                (shift == "<CHOOSE>", "Please select the shift."),
                (department == "<CHOOSE>", "Please select the department."),
                (location.strip() == "", "Please enter the location."),
                (incident_type == "<CHOOSE>", "Please select the incident type."),
                (severity == "<CHOOSE>", "Please select the severity."),
                (injury == "<CHOOSE>", "Please state whether there was an injury."),
                (lost_time == "<CHOOSE>", "Please state whether it was a lost-time injury."),
                (injury == "No" and lost_time == "Yes", "A lost-time injury requires an injury."),
                (cause.strip() == "", "Please enter the cause of the incident.")])
            if error:
                st.error(error)
            else:
                # keys match the columns of incidents.csv
                incident = {"Incident ID": incident_id.strip(), "Worker ID": incident_worker_id.strip(),
                            "Date": str(incident_date), "Time": incident_time.strftime("%H:%M"), "Shift": shift,
                            "Department": department, "Location": location.strip(), "Incident Type": incident_type,
                            "Severity": severity, "Injury": injury, "Lost-Time Injury": lost_time,
                            "Cause": cause.strip(), "Status": status, "Description": description.strip(),
                            "Corrective Action": corrective_action.strip()}
                S["incidents"].append(incident)
                save("incidents")   # FIX: write to incidents.csv so the data is not lost
                st.success("Safety incident recorded successfully!")
                if severity in ["High", "Critical"]:
                    st.warning("Extreme risk incident recorded. Attend immediately.")
                if injury == "Yes":
                    st.warning("An injury was reported. Respond immediately.")

    df = pd.DataFrame(S["incidents"])   # the table is built after saving, so a new incident shows straight away

    with tab_view:   # FIX: view, search and filter incidents (required by the brief)
        if df.empty:
            st.info("No safety incidents have been recorded yet.")
        else:
            text = st.text_input("Search incidents", placeholder="ID, worker, location, cause, description...")
            view = search_df(filter_df(df, ["Severity", "Shift", "Incident Type", "Status", "Department", "Injury"], "inc"), text)
            show_table(view)
            st.write("Incidents shown:", len(view), "of", len(df))

    with tab_count:   # FIX: count, categorise and trend incidents (required by the brief)
        if df.empty:
            st.info("No safety incidents have been recorded yet.")
        else:
            m = st.columns(4)
            m[0].metric("Total incidents", len(df))
            m[1].metric("High / Critical", int(df["Severity"].isin(["High", "Critical"]).sum()))
            m[2].metric("With injury", int((df["Injury"] == "Yes").sum()))
            m[3].metric("Lost-time injuries", int((df["Lost-Time Injury"] == "Yes").sum()))
            group = st.selectbox("Categorise and count incidents by",
                                 ["Incident Type", "Severity", "Department", "Shift", "Cause", "Status", "Location"])
            counts = df[group].value_counts()
            bar_chart(counts.to_dict(), f"Incidents by {group}", colors=SEV_COLORS, horizontal=True)
            st.write(f"Most frequent {group.lower()}: **{counts.index[0]}** ({counts.iloc[0]} incidents)")
            monthly = st.radio("Trend interval", ["Daily", "Monthly"], horizontal=True) == "Monthly"
            dates = pd.to_datetime(df["Date"], errors="coerce").dropna()
            if len(dates):
                line_chart(dates.dt.strftime("%Y-%m" if monthly else "%Y-%m-%d").value_counts().sort_index(),
                           f"Incidents per {'month' if monthly else 'day'}")


def page_equipment():
    st.header("Equipment Data and Condition Monitoring")
    st.caption("Thresholds are educational prototype values only, not manufacturer or mine safety limits.")
    tab_reg, tab_list, tab_cond, tab_ch = st.tabs(["Register Equipment", "Equipment Database", "Condition Monitoring", "Charts"])

    with tab_reg:
        with st.form(fkey("equipment")):
            c1, c2 = st.columns(2)
            eq_id = c1.text_input("Equipment ID", placeholder="e.g. TRK-012")
            eq_type = c1.selectbox("Equipment Type", ["<CHOOSE>"] + EQ_TYPES)
            maker = c1.text_input("Manufacturer")
            op_hours = c1.number_input("Operating hours", min_value=0.0, step=10.0)
            down = c1.number_input("Downtime (hours)", min_value=0.0, step=1.0)
            fuel = c1.number_input("Fuel consumption (L/h)", min_value=0.0, step=1.0)
            temp = c1.number_input("Temperature (°C)", min_value=-20.0, max_value=300.0, value=60.0)
            vib = c1.number_input("Vibration (mm/s)", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
            brake = c2.selectbox("Brake status", PART)
            tyre = c2.selectbox("Tyre status", PART)
            engine = c2.selectbox("Engine status", PART)
            mstatus = c2.selectbox("Maintenance status", MAINT_STATUS)
            last = c2.date_input("Last maintenance date", value=date.today())
            nxt = c2.date_input("Next maintenance due", value=date.today() + timedelta(days=90))
            submitted = st.form_submit_button("Register Equipment")

        if submitted:
            err = first_error([(not eq_id.strip(), "Please enter the Equipment ID."),
                               (find_eq(eq_id.strip()) is not None, "This Equipment ID already exists."),
                               (eq_type == "<CHOOSE>", "Please select the equipment type."),
                               (not maker.strip(), "Please enter the manufacturer."),
                               (nxt < last, "The next maintenance date cannot be before the last maintenance date.")])
            if err:
                st.error(err)
            else:
                alerts = condition_alerts(eq_id.strip(), temp, vib)
                S["equipment"].append(dict(zip(EQ_COLS, [eq_id.strip(), eq_type, maker.strip(), op_hours, temp, vib, fuel,
                                                         brake, tyre, engine, mstatus, down, str(last), str(nxt),
                                                         len(alerts)])))
                save("equipment")
                notify("success", "Equipment registered successfully!")
                notify("condition", alerts)
                reset_form("equipment")
                st.rerun()

        if not S["equipment"] and st.button("Load sample equipment data"):
            S["equipment"] = sample_equipment()
            save("equipment")
            st.rerun()

    df = equipment_df()

    with tab_list:
        if df.empty:
            st.info("No equipment has been recorded yet.")
        else:
            text = st.text_input("Search equipment", placeholder="ID or manufacturer")
            view = search_df(filter_df(df, ["Equipment Type", "Maintenance Status", "Condition"], "eq"), text)
            show_table(view)
            st.write("Equipment shown:", len(view), "of", len(df))

    with tab_cond:
        if df.empty:
            st.info("No equipment has been recorded yet.")
        else:
            st.table(pd.DataFrame({"Parameter": ["Temperature", "Vibration"], "Normal": ["< 80 °C", "< 5 mm/s"],
                                   "Warning": ["80 - 100 °C", "5 - 8 mm/s"], "Critical": ["> 100 °C", "> 8 mm/s"]}))
            n = df["Condition"].value_counts()
            m = st.columns(4)
            m[0].metric("Normal", int(n.get("Normal", 0)))
            m[1].metric("Warning", int(n.get("Warning", 0)))
            m[2].metric("Critical", int(n.get("Critical", 0)))
            m[3].metric("% operating normally", f"{n.get('Normal', 0) / len(df) * 100:.0f}%")

            with st.form("reading_form"):
                r = st.columns(3)
                rid = r[0].selectbox("Equipment", df["Equipment ID"].tolist())
                new_t = r[1].number_input("New temperature (°C)", min_value=-20.0, max_value=300.0, value=60.0)
                new_v = r[2].number_input("New vibration (mm/s)", min_value=0.0, max_value=100.0, value=2.0, step=0.1)
                if st.form_submit_button("Update Readings"):
                    rec = find_eq(rid)
                    alerts = condition_alerts(rid, new_t, new_v)
                    rec["Temperature (C)"], rec["Vibration (mm/s)"] = new_t, new_v
                    rec["Alert Count"] = int(rec["Alert Count"]) + len(alerts)
                    save("equipment")
                    notify("success", f"Readings for {rid} updated.")
                    notify("condition", alerts)
                    st.rerun()

            rank = {"Critical": 0, "Warning": 1, "Normal": 2}
            show_table(df[["Equipment ID", "Equipment Type", "Temperature (C)", "Vibration (mm/s)", "Condition", "Alert Count"]]
                       .sort_values("Condition", key=lambda s: s.map(rank)))

            all_alerts = [a for _, r in df.iterrows()
                          for a in condition_alerts(r["Equipment ID"], r["Temperature (C)"], r["Vibration (mm/s)"])]
            st.write(f"Critical alerts: **{sum(a['Level'] == 'Critical' for a in all_alerts)}**  |  "
                     f"Warning alerts: **{sum(a['Level'] == 'Warning' for a in all_alerts)}**")
            for a in sorted(all_alerts, key=lambda a: a["Level"] != "Critical"):
                with st.expander(f"[{a['Level'].upper()}] {a['ID']} - {a['Parameter']}"):
                    show_condition_alerts([a])

    with tab_ch:
        if df.empty:
            st.info("No equipment has been recorded yet.")
        else:
            temps, vibs = by_id(df, "Temperature (C)"), by_id(df, "Vibration (mm/s)")
            n = df["Condition"].value_counts()
            c1, c2, c3 = st.columns(3)
            with c1:
                bar_chart(temps, "Temperature (°C)", horizontal=True,
                          lines=[(80, "#e0a800", "Warning 80"), (100, "#d9534f", "Critical 100")],
                          colors={k: COND_COLORS[level(v, *LIMITS["Temperature"][:2])] for k, v in temps.items()})
            with c2:
                bar_chart(vibs, "Vibration (mm/s)", horizontal=True,
                          lines=[(5, "#e0a800", "Warning 5"), (8, "#d9534f", "Critical 8")],
                          colors={k: COND_COLORS[level(v, *LIMITS["Vibration"][:2])] for k, v in vibs.items()})
            with c3:
                bar_chart({k: int(n.get(k, 0)) for k in COND_COLORS}, "Equipment condition", colors=COND_COLORS)


def page_maintenance():
    st.header("Equipment Maintenance Monitoring")
    if not S["equipment"]:
        st.info("No equipment recorded yet. Add equipment (or load the sample data) in Equipment Data first.")
        return
    tab_status, tab_update, tab_log, tab_ch = st.tabs(["Maintenance Status", "Update Maintenance", "Maintenance Log", "Charts"])
    cats = [("Due for maintenance", "Due"), ("Overdue", "Overdue"), ("Under maintenance", "Under Maintenance"),
            ("Excessive downtime", "Excessive Downtime"), ("Repeated alerts", "Repeated Alerts"),
            ("Low availability", "Low Availability")]

    with tab_status:
        with st.expander("Monitoring settings (prototype values)"):
            s = st.columns(4)
            window = s[0].number_input("'Due' window (days)", min_value=1, value=14)
            min_avail = s[1].number_input("Min availability (%)", min_value=0.0, max_value=100.0, value=85.0)
            max_down = s[2].number_input("Excessive downtime (h)", min_value=1.0, value=500.0)
            repeats = s[3].number_input("Repeated alerts (count)", min_value=1, value=3)

        df = add_flags(equipment_df(), window, min_avail, max_down, repeats)
        st.write("Average equipment availability:", f"**{df['Availability (%)'].mean():.1f}%**")
        for i in (0, 3):
            for col, (title, flag) in zip(st.columns(3), cats[i:i + 3]):
                col.metric(title, int(df[flag].sum()))

        show = ["Equipment ID", "Equipment Type", "Availability (%)", "Downtime (hours)", "Alert Count",
                "Next Maintenance Due", "Maintenance Status"]
        st.markdown("**Maintenance priority list** (overdue first, then most flags)")
        pri = df[df["Flag Count"] > 0].sort_values(["Overdue", "Flag Count", "Availability (%)"], ascending=[False, False, True])
        if pri.empty:
            st.success("No equipment currently requires maintenance attention.")
        else:
            show_table(pri[show + ["Flags"]])
        for title, flag in cats:
            with st.expander(f"{title} ({int(df[flag].sum())})"):
                show_table(df[df[flag]][show])

        st.markdown("**Maintenance alerts**")
        for _, r in df.iterrows():
            if r["Overdue"]:
                show_alert({"Level": "Critical", "ID Type": "Equipment ID", "ID": r["Equipment ID"], "Parameter": "Maintenance",
                            "Value": f"Due {r['Next Maintenance Due']}", "Status": "Overdue Maintenance",
                            "Action": "Schedule maintenance immediately."})
            if r["Excessive Downtime"]:
                show_alert({"Level": "Warning", "ID Type": "Equipment ID", "ID": r["Equipment ID"], "Parameter": "Downtime",
                            "Value": f"{r['Downtime (hours)']:.0f} hours", "Status": "Excessive Downtime",
                            "Action": "Investigate causes of downtime and review maintenance plan."})
        if not (df["Overdue"].any() or df["Excessive Downtime"].any()):
            st.success("No maintenance alerts at this time.")

    with tab_update:
        with st.form(fkey("maintenance")):
            u1, u2 = st.columns(2)
            eq = u1.selectbox("Equipment", [e["Equipment ID"] for e in S["equipment"]])
            act = u1.selectbox("Action", ["Start maintenance", "Complete maintenance"])
            mdate = u1.date_input("Date", value=date.today())
            tech = u1.text_input("Technician / Maintenance Engineer")
            interval = u2.number_input("Days until next maintenance (when completing)", min_value=1, value=90)
            added = u2.number_input("Downtime hours to add", min_value=0.0, step=1.0)
            notes = u2.text_area("Notes")
            submitted = st.form_submit_button("Save Maintenance Record")

        if submitted:
            rec = find_eq(eq)
            under = rec["Maintenance Status"] == "Under Maintenance"
            err = first_error([(not tech.strip(), "Please enter the technician's name."),
                               (act == "Start maintenance" and under, "This equipment is already under maintenance."),
                               (act == "Complete maintenance" and not under,
                                "Only equipment under maintenance can be completed. Start maintenance first.")])
            if err:
                st.error(err)
            else:
                rec["Downtime (hours)"] = float(rec["Downtime (hours)"]) + added
                if act == "Start maintenance":
                    rec["Maintenance Status"] = "Under Maintenance"
                else:
                    rec.update({"Maintenance Status": "Operational", "Last Maintenance": str(mdate),
                                "Next Maintenance Due": str(mdate + timedelta(days=int(interval))), "Alert Count": 0})
                S["maintenance_log"].append({"Log ID": f"MNT-{len(S['maintenance_log']) + 1:03d}", "Equipment ID": eq,
                                             "Action": act, "Date": str(mdate), "Technician": tech.strip(),
                                             "Downtime Added (h)": added, "Notes": notes.strip()})
                save("equipment")
                save("maintenance_log")
                notify("success", f"{act} recorded for {eq}.")
                reset_form("maintenance")
                st.rerun()

    with tab_log:
        if S["maintenance_log"]:
            show_table(pd.DataFrame(S["maintenance_log"]))
        else:
            st.info("No maintenance work has been logged yet.")

    with tab_ch:
        c1, c2, c3 = st.columns(3)
        with c1:
            bar_chart(by_id(df, "Availability (%)"), "Availability (%)", horizontal=True,
                      lines=[(min_avail, "#d9534f", f"Min {min_avail:g}%")])
        with c2:
            bar_chart(by_id(df, "Downtime (hours)"), "Downtime (hours)", horizontal=True,
                      lines=[(max_down, "#d9534f", f"Limit {max_down:g} h")])
        with c3:
            bar_chart(by_id(df, "Alert Count"), "Alerts per equipment", horizontal=True)


def page_risk():
    st.header("Risk Assessment")
    tab_add, tab_reg = st.tabs(["Assess Risk", "Risk Register"])

    with tab_add:
        st.caption("Risk Score = Likelihood x Consequence (1-5 scale)   |   1-4 Low   |   5-9 Medium   |   10-16 High   |   17-25 Critical")
        k = lambda name: fkey("risk") + "_" + name
        c1, c2 = st.columns(2)
        risk_id = c1.text_input("Risk ID", key=k("id"))
        hazard = c1.text_input("Hazard description", key=k("hazard"))
        dept = c1.selectbox("Department", ["<CHOOSE>"] + DEPTS, key=k("dept"))
        location = c1.text_input("Location", key=k("loc"))
        rdate = c1.date_input("Date of assessment", value=date.today(), key=k("date"))
        assessor = c1.text_input("Assessed by", key=k("by"))
        like = c2.selectbox("Likelihood (1 = rare ... 5 = almost certain)", [1, 2, 3, 4, 5], key=k("l"))
        cons = c2.selectbox("Consequence (1 = minor ... 5 = catastrophic)", [1, 2, 3, 4, 5], key=k("c"))
        controls = c2.text_area("Existing controls", key=k("ctrl"))
        score = like * cons
        cls = classify_risk(score)
        c2.markdown(f'<div class="risk-badge" style="background:{SEV_COLORS[cls]}">'
                    f'Risk score = {like} x {cons} = {score} &rarr; {cls.upper()}</div>', unsafe_allow_html=True)

        if st.button("Record Risk Assessment"):
            err = first_error([(not risk_id.strip(), "Please enter the Risk ID."),
                               (risk_id.strip() in [str(r["Risk ID"]) for r in S["risks"]], "This Risk ID already exists."),
                               (not hazard.strip(), "Please describe the hazard."),
                               (dept == "<CHOOSE>", "Please select the department."),
                               (not location.strip(), "Please enter the location."),
                               (not assessor.strip(), "Please enter who assessed the risk.")])
            if err:
                st.error(err)
            else:
                S["risks"].append({"Risk ID": risk_id.strip(), "Hazard": hazard.strip(), "Department": dept,
                                   "Location": location.strip(), "Likelihood": like, "Consequence": cons,
                                   "Risk Score": score, "Classification": cls, "Controls": controls.strip(),
                                   "Date": str(rdate), "Assessed By": assessor.strip()})
                save("risks")
                if cls in ("High", "Critical"):
                    notify("warning", f"{cls.upper()} RISK: risk score {score}. Immediate management attention and "
                                      "additional controls are required.")
                else:
                    notify("success", f"Risk score {score}: {cls} risk recorded.")
                reset_form("risk")
                st.rerun()

    with tab_reg:
        df = pd.DataFrame(S["risks"])
        if df.empty:
            st.info("No risk assessments have been recorded yet.")
            return
        counts = df["Classification"].value_counts()
        for col, (_, name) in zip(st.columns(5), RISK_CLASSES + [(0, "Total")]):
            col.metric(name, len(df) if name == "Total" else int(counts.get(name, 0)))
        view = filter_df(df, ["Classification", "Department"], "rk")
        show_table(view.sort_values("Risk Score", ascending=False))

        st.markdown("**Risk matrix** (number of risks; rows = Likelihood, columns = Consequence)")
        grid = pd.DataFrame({c: [int(((df["Likelihood"].astype(int) == l) & (df["Consequence"].astype(int) == c)).sum())
                                 for l in range(5, 0, -1)] for c in range(1, 6)}, index=range(5, 0, -1))
        grid.index.name, grid.columns.name = "Likelihood", "Consequence"
        zone = pd.DataFrame({c: [f"background-color: {SEV_COLORS[classify_risk(l * c)]}; color: {BG}" for l in grid.index]
                             for c in grid.columns}, index=grid.index)
        st.dataframe(grid.style.apply(lambda _: zone, axis=None), **STRETCH)


def page_reports():
    st.header("General Reports")
    sets = [("Worker records", "workers"), ("Incident records", "incidents"), ("Equipment records", "equipment"),
            ("Maintenance log", "maintenance_log"), ("Risk assessments", "risks")]
    for label, key in sets:
        with st.expander(f"{label} ({len(S[key])})"):
            if S[key]:
                df = equipment_df() if key == "equipment" else pd.DataFrame(S[key])
                show_table(df)
                st.download_button(f"Download {label.lower()} (CSV)", df.to_csv(index=False).encode("utf-8"),
                                   file_name=f"{key}_report_{date.today()}.csv", mime="text/csv", key=f"dl_{key}")
            else:
                st.info(f"No {label.lower()} are available.")


def page_users():
    st.header("Manage Users")
    st.write("Users loaded from users.csv:")
    show_table(pd.DataFrame([{"Username": u, "Role": v["role"]} for u, v in load_users().items()]))


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
    if not d["w"].empty:
        parts["High-risk workers"] = d["w"][d["w"]["Risk Level"] == "High"].groupby("Department").size()
    if not d["inc"].empty:
        parts["High/Critical incidents"] = d["inc"][d["inc"]["Severity"].isin(["High", "Critical"])].groupby("Department").size()
    if not d["rk"].empty:
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


def analysis_categories(role):
    pages = PAGES.get(role, [])
    safety = "Safety Incidents" in pages or "Worker Safety Data" in pages
    equip = "Equipment Data" in pages
    return [c for c, ok in ((HS, safety), (EQ, equip), (IN, safety and equip)) if ok]


def page_analysis():
    st.header("Interactive Data Analysis")
    cats = analysis_categories(S["role"])
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
            "eqf": add_flags(eq.copy()) if not eq.empty else eq, "alerts": generate_alerts(S["role"]),
            "start": start, "end": end}
    st.subheader(q)
    QUESTIONS[cat][q](data)


# ------------------------------ LOGIN ------------------------------
# =====================================================================
# PART (a) ACCESS CONTROL - LOGIN  -  written by Group Member 1
# Her flow is kept: read users.csv -> check username and password ->
# store the role in session_state -> rerun so the user's pages appear.
# =====================================================================
@st.cache_data
def login_background():
    """The login picture (logo + mine at sunrise) as base64; empty text if login_bg.jpg is missing."""
    path = os.path.join(BASE, "login_bg.jpg")
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


picture = login_background()
if S["logged_in"] or not picture:   # the logo picture already shows the company name, so the banner is only used without it
    st.markdown('<div class="banner"><h1>KHWEZI MINING</h1><p>Health, Safety and Equipment Monitoring</p></div>',
                unsafe_allow_html=True)

if not S["logged_in"]:
    # Login page style: the picture fills the page and the form sits under the logo. Without the picture, a sunset gradient is used.
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

    users = load_users()   # FIX: creates a demo users.csv if the file is missing instead of crashing
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.form("login"):   # a form lets the Enter key submit the login
            st.header("Login")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                # checks that the username exists and the password matches the one on the same row of the csv
                if username.strip() in users and password == users[username.strip()]["password"]:
                    user_role = users[username.strip()]["role"]   # the role that belongs to the username in the csv
                    S["logged_in"] = True
                    S["role"] = ROLE_ALIASES.get(user_role, user_role)   # FIX: "Maintenance Manager" -> "Maintenance Engineer" (brief)
                    S["greeted"] = False
                    st.rerun()   # restart the script: logged_in is now True, so the login page is skipped
                else:
                    st.error("Incorrect username or password. Enter the correct credentials or contact the system administrator.")
        if S.get("demo_users"):
            st.info("users.csv was not found, so a demo file was created.\n\n"
                    "Try admin / admin123 (also safety123, engineer123, maint123, manager123).")
    st.stop()   # nothing below the login page is shown until the user is logged in
    # FIX: the old code also waited 3 seconds (time.sleep) after login, which only slowed the app down

# ------------------------------ NAVIGATION ------------------------------
# PART (a): role-based navigation - each role only sees the pages listed for it in PAGES
role = S["role"]
st.sidebar.title("Khwezi Mining")
st.sidebar.write("Logged in as:", role)
selected = st.sidebar.radio("Select a section", PAGES.get(role, ["Dashboard"]))
if st.sidebar.button("Logout"):
    S.update(logged_in=False, role="")
    st.rerun()

if not S.get("greeted"):   # one summary of the active alerts straight after login
    S["greeted"] = True
    active = generate_alerts(role)
    if active:
        n = sum(a["Level"] == "Critical" for a in active)
        st.toast(f"You have {n} critical and {len(active) - n} warning alert(s). Open the Alerts section for details.")

PAGE_FUNCS = {"Dashboard": page_dashboard, "Alerts": page_alerts, "Worker Safety Data": page_workers,
              "Equipment Data": page_equipment, "Maintenance Data": page_maintenance,
              "Safety Incidents": page_incidents, "Risk Assessment": page_risk, "Data Analysis": page_analysis,
              "General Reports": page_reports, "Manage Users": page_users}

st.write(f"Hello, {role}! Welcome to the Khwezi Mining Health, Safety and Equipment Monitoring System.")
show_flash()
PAGE_FUNCS[selected]()
st.caption("Educational prototype - thresholds are not manufacturer or mine safety limits.")
