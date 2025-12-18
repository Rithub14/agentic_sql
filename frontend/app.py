import os
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_QUERY_URL = f"{API_BASE_URL}/api/query"
API_TEST_URL = f"{API_BASE_URL}/api/test-connection"

st.set_page_config(page_title="Agentic SQL Explorer", layout="wide")

st.title("🧠 Agentic SQL Explorer")
st.caption("Natural Language → SQL → Results → Visualization (Multi-Agent)")

# -----------------------
# Helpers
# -----------------------


def assemble_url(db_type: str, host: str, port: str, user: str, password: str, database: str) -> str:
    if db_type == "sqlite":
        return f"sqlite:///{database}"

    safe_user = quote_plus(user) if user else ""
    safe_pass = quote_plus(password) if password else ""
    auth = f"{safe_user}:{safe_pass}@" if safe_user or safe_pass else ""
    port_part = f":{port}" if port else ""
    return f"{db_type}://{auth}{host}{port_part}/{database}"


# -----------------------
# Session State Init
# -----------------------

if "api_response" not in st.session_state:
    st.session_state.api_response = None

if "force_render_chart" not in st.session_state:
    st.session_state.force_render_chart = False

# -----------------------
# User Input (structured DB form)
# -----------------------

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

col1, col2 = st.columns(2)
with col1:
    host = st.text_input("Host", value="localhost" if db_type != "sqlite" else "", key="db_host")
with col2:
    port = st.text_input("Port", value="5432" if db_type == "postgresql" else "3306" if db_type == "mysql" else "", key="db_port")

col3, col4 = st.columns(2)
with col3:
    username = st.text_input("Username", value="", key="db_user")
with col4:
    password = st.text_input("Password", type="password", value="", key="db_password")

database = st.text_input(
    "Database name (or SQLite file path)",
    value="",
    placeholder="sampledb or /path/to/file.db",
    key="db_name",
)

db_url = assemble_url(db_type, host, port, username, password, database)

chart_type = st.selectbox(
    "Optional: Choose a visualization",
    options=["None", "bar", "line", "pie"],
    key="chart_type",
)

test_clicked = st.button("Test connection", key="test_connection")
submit = st.button("Run Query", key="run_query", disabled=not question or not db_url)

# -----------------------
# API Call (ONLY HERE)
# -----------------------

if test_clicked and db_url:
    with st.spinner("Testing connection..."):
        resp = requests.post(API_TEST_URL, json={"database_url": db_url})
    if resp.status_code == 200 and resp.json().get("ok"):
        st.success("Connection successful.")
    else:
        st.error(f"Connection failed: {resp.json().get('message') if resp.ok else resp.text}")

if submit:
    payload = {
        "question": question,
        "chart": None if chart_type == "None" else chart_type,
        "database_url": db_url,
    }

    with st.spinner("Running agentic pipeline..."):
        response = requests.post(API_QUERY_URL, json=payload)

    if response.status_code != 200:
        st.error("Backend error occurred")
        st.session_state.api_response = None
    else:
        st.session_state.api_response = response.json()
        st.session_state.force_render_chart = False  # reset

# -----------------------
# Render Results (ALWAYS)
# -----------------------

if st.session_state.api_response:
    data = st.session_state.api_response

    # SQL
    st.subheader("Generated SQL")
    st.code(data["sql"], language="sql")

    results = data["results"]

    if results:
        df = pd.DataFrame(results)

        st.subheader("Query Results")
        st.dataframe(df, use_container_width=True)

        viz = data["visualization"]

        # -----------------------
        # Visualization
        # -----------------------

        should_render = viz.get("render") or st.session_state.force_render_chart

        if should_render:
            st.subheader("Visualization")

            x = viz["spec"]["x"]
            y = viz["spec"]["y"]

            if viz["chart"] == "bar":
                fig = px.bar(df, x=x, y=y)
            elif viz["chart"] == "line":
                fig = px.line(df, x=x, y=y)
            elif viz["chart"] == "pie":
                fig = px.pie(df, names=x, values=y)
            else:
                fig = None

            if fig:
                st.plotly_chart(fig, use_container_width=True)

        elif viz.get("suggest"):
            st.info(viz["message"])

            if st.button(f"Generate {viz['chart']} chart"):
                st.session_state.force_render_chart = True

    else:
        st.warning("No results returned")
