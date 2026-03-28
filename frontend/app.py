import glob
import io
import json
import os
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_QUERY_URL = f"{API_BASE_URL}/api/query"
API_TEST_URL = f"{API_BASE_URL}/api/test-connection"
API_SCHEMA_URL = f"{API_BASE_URL}/api/schema"
API_SUGGESTIONS_URL = f"{API_BASE_URL}/api/suggestions"

REQUEST_TIMEOUT = 60  # seconds

st.set_page_config(page_title="Agentic SQL Explorer", layout="wide")


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
    found = []
    for pattern in ("*.db", "*.sqlite", "*.sqlite3"):
        found.extend(glob.glob(os.path.join(_SQLITE_DIR, pattern)))
    return sorted(os.path.relpath(f, _PROJECT_ROOT) for f in found)


def _render_chart(df: pd.DataFrame, spec: dict) -> None:
    chart = spec.get("chart")
    x = spec.get("x")
    y_cols: list = spec.get("y") or []
    color = spec.get("color")
    title = spec.get("title", "")
    barmode = spec.get("barmode")

    needed = ([x] if x else []) + y_cols + ([color] if color else [])
    missing = [c for c in needed if c and c not in df.columns]
    if missing:
        st.warning(f"Cannot render chart — column(s) not found: {', '.join(missing)}")
        return

    common = dict(title=title, template="plotly_white")

    if chart == "bar":
        y_arg = y_cols if len(y_cols) > 1 else y_cols[0]
        fig = px.bar(df, x=x, y=y_arg, color=color, barmode=barmode or "group", **common)
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


def _export_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def _run_query(question: str, db_url: str, chart_type: str) -> dict | None:
    """Execute the query pipeline and return the response dict, or None on error."""
    history_payload = [
        {"question": t["question"], "sql": t["sql"]}
        for t in st.session_state.conversation_history[-5:]
    ]
    payload = {
        "question": question,
        "chart": None if chart_type == "None" else chart_type,
        "database_url": db_url,
        "conversation_history": history_payload,
    }
    try:
        response = requests.post(API_QUERY_URL, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        st.error("Query timed out. Try a simpler question or check your database.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Could not reach the API server. Is it running?")
        return None

    if response.status_code == 422:
        st.error(f"Query blocked: {response.json().get('detail', 'Invalid SQL')}")
        return None
    elif response.status_code != 200:
        detail = ""
        if response.headers.get("content-type", "").startswith("application/json"):
            detail = response.json().get("detail", "")
        st.error(f"Backend error. {detail}")
        return None

    return response.json()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

st.session_state.setdefault("api_response", None)
st.session_state.setdefault("force_render_chart", False)
st.session_state.setdefault("query_history", [])
st.session_state.setdefault("conversation_history", [])
st.session_state.setdefault("schema_data", None)
st.session_state.setdefault("suggestions", [])
st.session_state.setdefault("current_page", "Query")
st.session_state.setdefault("auto_run_question", None)

if "question_input" not in st.session_state:
    st.session_state.question_input = ""


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

_PAGES = ["Query", "Schema Explorer"]

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Page",
        options=_PAGES,
        index=_PAGES.index(st.session_state.current_page),
        label_visibility="collapsed",
    )
    # Sync selection back — plain state var, not widget-bound
    st.session_state.current_page = page

    st.divider()
    st.header("Database Connection")

    # Demo DB shortcut — populated from DEMO_DATABASE_URL env var
    _demo_url = os.getenv("DEMO_DATABASE_URL", "")
    if _demo_url:
        if st.button("Use Demo DB (NBA)", use_container_width=True):
            st.session_state["_demo_url_active"] = True
        if st.session_state.get("_demo_url_active"):
            st.success("Demo DB active — scroll down to connect.")

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
            help="Place .db / .sqlite files in sample_dbs/sqlite/ to appear here automatically.",
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

    # Use demo DB URL if active, otherwise assemble from form fields
    if st.session_state.get("_demo_url_active") and _demo_url:
        db_url = _demo_url
    else:
        db_url = assemble_url(db_type, host, port, username, password, database)

    test_clicked = st.button("Test Connection", key="test_connection", use_container_width=True)

    if test_clicked and db_url:
        with st.spinner("Testing..."):
            try:
                resp = requests.post(API_TEST_URL, json={"database_url": db_url}, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200 and resp.json().get("ok"):
                    st.success("Connection successful.")
                else:
                    msg = resp.json().get("message", resp.text) if resp.ok else resp.text
                    st.error(f"Failed: {msg}")
            except requests.exceptions.Timeout:
                st.error("Timed out. Is the API server running?")
            except requests.exceptions.ConnectionError:
                st.error("Cannot reach API server.")

    st.divider()

    st.subheader("Visualization")
    chart_type = st.selectbox(
        "Force chart type",
        options=["None", "bar", "bar_h", "line", "scatter", "histogram", "pie"],
        help="Leave as None to let the agent auto-select.",
        key="chart_type",
    )

    if st.session_state.query_history:
        st.divider()
        st.subheader("Query History")
        for i, entry in enumerate(st.session_state.query_history):
            with st.expander(f"{i + 1}. {entry['question'][:55]}"):
                st.caption(f"{entry['row_count']} rows")
                st.code(entry["sql"], language="sql")


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

st.title("Agentic SQL Explorer")
st.caption("Natural Language → SQL → Results → Visualization (Multi-Agent)")


# ===========================================================================
# Page: Query
# ===========================================================================

if st.session_state.current_page == "Query":

    # If a suggestion was clicked in Schema Explorer, inject it and auto-run
    auto_question = st.session_state.pop("auto_run_question", None)
    if auto_question:
        st.session_state.question_input = auto_question

    question = st.text_input(
        "Ask a question about your database",
        placeholder="e.g. Show total sales per country",
        key="question_input",
    )

    col_run, col_clear = st.columns([3, 1])
    with col_run:
        submit = st.button(
            "Run Query",
            key="run_query",
            disabled=not question or not db_url,
            use_container_width=True,
            type="primary",
        )
    with col_clear:
        if st.session_state.conversation_history:
            if st.button("Clear context", key="clear_conv", use_container_width=True):
                st.session_state.conversation_history = []
                st.rerun()

    if st.session_state.conversation_history:
        with st.expander(
            f"Conversation context — {len(st.session_state.conversation_history)} prior turn(s)",
            expanded=False,
        ):
            st.caption("Previous Q&A pairs sent with your next question for follow-up support.")
            for i, turn in enumerate(st.session_state.conversation_history, 1):
                st.markdown(f"**Turn {i}:** {turn['question']}")
                st.code(turn["sql"], language="sql")

    # Auto-run when redirected from Schema Explorer
    should_run = submit or bool(auto_question and question and db_url)

    if should_run and question and db_url:
        with st.spinner("Running agentic pipeline..."):
            data = _run_query(question, db_url, chart_type)

        if data:
            st.session_state.api_response = data
            st.session_state.force_render_chart = False
            st.session_state.conversation_history.append({
                "question": question,
                "sql": data.get("sql", ""),
            })
            st.session_state.conversation_history = st.session_state.conversation_history[-10:]
            st.session_state.query_history.insert(0, {
                "question": question,
                "sql": data.get("sql", ""),
                "row_count": len(data.get("results", [])),
            })
            st.session_state.query_history = st.session_state.query_history[:10]

    # Display results
    if st.session_state.api_response:
        data = st.session_state.api_response

        st.subheader("Generated SQL")
        st.code(data["sql"], language="sql")

        if data.get("explanation"):
            st.info(f"**What this query does:** {data['explanation']}")

        results = data.get("results", [])

        if results:
            df = pd.DataFrame(results)

            st.subheader(f"Query Results ({len(df):,} rows)")
            st.dataframe(df, use_container_width=True)

            col_csv, col_excel, col_json = st.columns(3)
            with col_csv:
                st.download_button(
                    label="Download CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="results.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with col_excel:
                st.download_button(
                    label="Download Excel",
                    data=_export_excel(df),
                    file_name="results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            with col_json:
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(results, default=str, indent=2).encode("utf-8"),
                    file_name="results.json",
                    mime="application/json",
                    use_container_width=True,
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


# ===========================================================================
# Page: Schema Explorer
# ===========================================================================

elif st.session_state.current_page == "Schema Explorer":

    st.markdown("Inspect your database tables and get suggested questions to get started quickly.")

    explore_clicked = st.button(
        "Explore Schema",
        key="explore_schema",
        disabled=not db_url,
        type="primary",
    )

    if explore_clicked and db_url:
        with st.spinner("Analyzing schema and generating suggestions..."):
            # Fetch schema
            try:
                schema_resp = requests.post(
                    API_SCHEMA_URL, json={"database_url": db_url}, timeout=REQUEST_TIMEOUT
                )
                if schema_resp.status_code == 200:
                    st.session_state.schema_data = schema_resp.json()
                else:
                    try:
                        detail = schema_resp.json().get("detail", schema_resp.text)
                    except Exception:
                        detail = schema_resp.text or f"HTTP {schema_resp.status_code}"
                    st.error(f"Schema fetch failed: {detail}")
                    st.session_state.schema_data = None
            except requests.exceptions.ConnectionError:
                st.error("Could not reach the API server. Check that API_BASE_URL is correct.")
                st.session_state.schema_data = None

            # Fetch suggestions in same spinner
            if st.session_state.schema_data:
                try:
                    sug_resp = requests.post(
                        API_SUGGESTIONS_URL, json={"database_url": db_url}, timeout=REQUEST_TIMEOUT
                    )
                    st.session_state.suggestions = (
                        sug_resp.json().get("suggestions", [])
                        if sug_resp.status_code == 200 else []
                    )
                except Exception:
                    st.session_state.suggestions = []

    if st.session_state.schema_data:
        schema_data = st.session_state.schema_data
        tables = schema_data.get("tables", {})

        # --- Suggested questions (shown first, prominent) ---
        if st.session_state.suggestions:
            st.subheader("Suggested Questions")
            st.caption("Click any question to run it instantly.")
            for suggestion in st.session_state.suggestions:
                if st.button(f"▶  {suggestion}", key=f"sug_{hash(suggestion)}", use_container_width=True):
                    st.session_state.auto_run_question = suggestion
                    st.session_state.current_page = "Query"
                    st.session_state.api_response = None
                    st.rerun()

        st.divider()

        # --- Table details ---
        st.subheader(f"Tables ({len(tables)})")
        for table_name, columns in tables.items():
            with st.expander(f"**{table_name}**  — {len(columns)} columns", expanded=False):
                col_df = pd.DataFrame(
                    [{"column": col, "type": typ} for col, typ in columns.items()]
                )
                st.dataframe(col_df, use_container_width=True, hide_index=True)

    else:
        st.info("Click **Explore Schema** to inspect the connected database.")
