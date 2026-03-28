import glob
import os
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_QUERY_URL = f"{API_BASE_URL}/api/query"
API_TEST_URL = f"{API_BASE_URL}/api/test-connection"

REQUEST_TIMEOUT = 60  # seconds

st.set_page_config(page_title="Agentic SQL Explorer", layout="wide")
st.title("Agentic SQL Explorer")
st.caption("Natural Language → SQL → Results → Visualization (Multi-Agent)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assemble_url(db_type: str, host: str, port: str, user: str, password: str, database: str) -> str:
    if db_type == "sqlite":
        return f"sqlite:///{database}"
    safe_user = quote_plus(user) if user else ""
    safe_pass = quote_plus(password) if password else ""
    auth = f"{safe_user}:{safe_pass}@" if safe_user or safe_pass else ""
    port_part = f":{port}" if port else ""
    return f"{db_type}://{auth}{host}{port_part}/{database}"


_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_SQLITE_DIR = os.path.join(_PROJECT_ROOT, "sample_dbs", "sqlite")


def _find_sqlite_databases() -> list[str]:
    """Return .db / .sqlite / .sqlite3 files from sample_dbs/sqlite/, relative to project root."""
    found = []
    for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
        found.extend(glob.glob(os.path.join(_SQLITE_DIR, pattern)))
    return sorted(os.path.relpath(f, _PROJECT_ROOT) for f in found)


def _render_chart(df: pd.DataFrame, spec: dict) -> None:
    """Render a Plotly chart from a visualization spec. Handles all supported chart types."""
    chart = spec.get("chart")
    x = spec.get("x")
    y_cols: list = spec.get("y") or []
    color = spec.get("color")
    title = spec.get("title", "")
    barmode = spec.get("barmode")

    # Guard: required columns must exist in the dataframe
    needed = ([x] if x else []) + y_cols + ([color] if color else [])
    missing = [c for c in needed if c and c not in df.columns]
    if missing:
        st.warning(f"Cannot render chart — column(s) not found in results: {', '.join(missing)}")
        return

    common = dict(title=title, template="plotly_white")

    if chart == "bar":
        y_arg = y_cols if len(y_cols) > 1 else y_cols[0]
        fig = px.bar(df, x=x, y=y_arg, color=color,
                     barmode=barmode or "group", **common)

    elif chart == "bar_h":
        fig = px.bar(df.sort_values(y_cols[0], ascending=True),
                     x=y_cols[0], y=x, orientation="h", color=color, **common)

    elif chart == "line":
        y_arg = y_cols if len(y_cols) > 1 else y_cols[0]
        fig = px.line(df, x=x, y=y_arg, color=color, markers=True, **common)

    elif chart == "scatter":
        fig = px.scatter(df, x=x, y=y_cols[0], color=color,
                         hover_data=df.columns.tolist(), **common)

    elif chart == "histogram":
        fig = px.histogram(df, x=x, color=color, **common)

    elif chart == "pie":
        fig = px.pie(df, names=x, values=y_cols[0], **common)
        fig.update_traces(textposition="inside", textinfo="percent+label")

    else:
        st.info(f"Chart type '{chart}' is not supported yet.")
        return

    fig.update_layout(
        xaxis_title=x.replace("_", " ").title() if x else None,
        yaxis_title=y_cols[0].replace("_", " ").title() if y_cols else None,
        legend_title_text=color.replace("_", " ").title() if color else None,
        margin=dict(t=50, l=0, r=0, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

st.session_state.setdefault("api_response", None)
st.session_state.setdefault("force_render_chart", False)
st.session_state.setdefault("query_history", [])  # list of {question, sql, row_count}


# ---------------------------------------------------------------------------
# Input form
# ---------------------------------------------------------------------------

question = st.text_input(
    "Ask a question about your database",
    placeholder="e.g. Show total sales per country",
    key="question_input",
)

db_type = st.selectbox(
    "Database type",
    options=["postgresql", "mysql", "sqlite"],
    key="db_type",
)

if db_type != "sqlite":
    col1, col2 = st.columns(2)
    with col1:
        host = st.text_input("Host", value="localhost", key="db_host")
    with col2:
        default_port = "5432" if db_type == "postgresql" else "3306"
        port = st.text_input("Port", value=default_port, key="db_port")

    col3, col4 = st.columns(2)
    with col3:
        username = st.text_input("Username", value="", key="db_user")
    with col4:
        password = st.text_input("Password", type="password", value="", key="db_password")
else:
    host = port = username = password = ""

_CUSTOM = "Custom path..."

if db_type == "sqlite":
    _db_files = _find_sqlite_databases()
    _options = _db_files + [_CUSTOM] if _db_files else [_CUSTOM]
    _selected = st.selectbox(
        "SQLite database file",
        options=_options,
        help="Place .db / .sqlite files in sample_dbs/sqlite/ to have them appear here automatically.",
        key="db_name_select",
    )
    if _selected == _CUSTOM or not _db_files:
        database = st.text_input(
            "SQLite file path",
            value="",
            placeholder="/path/to/file.db",
            key="db_name_custom",
        )
    else:
        database = _selected
        st.caption(f"`{os.path.join(_PROJECT_ROOT, _selected)}`")
else:
    database = st.text_input(
        "Database name",
        value="",
        placeholder="sampledb",
        key="db_name",
    )

db_url = assemble_url(db_type, host, port, username, password, database)

chart_type = st.selectbox(
    "Optional: Force a visualization type",
    options=["None", "bar", "bar_h", "line", "scatter", "histogram", "pie"],
    help="Leave as None to let the agent auto-select the best chart.",
    key="chart_type",
)

test_clicked = st.button("Test connection", key="test_connection")
submit = st.button("Run Query", key="run_query", disabled=not question or not db_url)


# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------

if test_clicked and db_url:
    with st.spinner("Testing connection..."):
        try:
            resp = requests.post(API_TEST_URL, json={"database_url": db_url}, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200 and resp.json().get("ok"):
                st.success("Connection successful.")
            else:
                msg = resp.json().get("message", resp.text) if resp.ok else resp.text
                st.error(f"Connection failed: {msg}")
        except requests.exceptions.Timeout:
            st.error("Connection test timed out. Is the API server running?")
        except requests.exceptions.ConnectionError:
            st.error("Could not reach the API server. Is it running?")


# ---------------------------------------------------------------------------
# Run query
# ---------------------------------------------------------------------------

if submit:
    payload = {
        "question": question,
        "chart": None if chart_type == "None" else chart_type,
        "database_url": db_url,
    }

    with st.spinner("Running agentic pipeline..."):
        try:
            response = requests.post(API_QUERY_URL, json=payload, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout:
            st.error("The query timed out. Try a simpler question or check your database.")
            response = None
        except requests.exceptions.ConnectionError:
            st.error("Could not reach the API server. Is it running?")
            response = None

    if response is not None:
        if response.status_code == 422:
            # Validation error — show the message from the API
            st.error(f"Query blocked: {response.json().get('detail', 'Invalid SQL')}")
            st.session_state.api_response = None
        elif response.status_code != 200:
            detail = response.json().get("detail", "") if response.headers.get("content-type", "").startswith("application/json") else ""
            st.error(f"Backend error. {detail}")
            st.session_state.api_response = None
        else:
            data = response.json()
            st.session_state.api_response = data
            st.session_state.force_render_chart = False

            # Append to query history (keep last 10)
            st.session_state.query_history.insert(0, {
                "question": question,
                "sql": data.get("sql", ""),
                "row_count": len(data.get("results", [])),
            })
            st.session_state.query_history = st.session_state.query_history[:10]


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

if st.session_state.api_response:
    data = st.session_state.api_response

    st.subheader("Generated SQL")
    st.code(data["sql"], language="sql")

    results = data.get("results", [])

    if results:
        df = pd.DataFrame(results)

        st.subheader(f"Query Results ({len(df):,} rows)")
        st.dataframe(df, use_container_width=True)

        # CSV export
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download as CSV",
            data=csv_bytes,
            file_name="query_results.csv",
            mime="text/csv",
        )

        viz = data.get("visualization", {})
        spec = viz.get("spec") or {}
        should_render = viz.get("render") or st.session_state.force_render_chart

        if should_render and spec:
            st.subheader("Visualization")
            _render_chart(df, spec)

        elif viz.get("suggest") and spec:
            st.info(viz["message"])
            if st.button(f"Generate {viz['chart'].replace('_', ' ')} chart"):
                st.session_state.force_render_chart = True
                st.rerun()

    else:
        st.warning("No results returned.")


# ---------------------------------------------------------------------------
# Query history sidebar
# ---------------------------------------------------------------------------

if st.session_state.query_history:
    with st.sidebar:
        st.header("Query History")
        for i, entry in enumerate(st.session_state.query_history):
            with st.expander(f"{i + 1}. {entry['question'][:60]}"):
                st.caption(f"{entry['row_count']} rows")
                st.code(entry["sql"], language="sql")
