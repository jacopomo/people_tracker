import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
from scoring import update_person_score, recalculate_all
from sidebar import tag_manager, system_tools
from tabs import dashboard, directory, analytics

# 1. Database Connection & Schema Setup
conn = sqlite3.connect("people.db", check_same_thread=False)

# Load schema from file
try:
    with open('schema.sql', 'r') as f:
        schema = f.read()
        conn.executescript(schema)
    conn.commit()
except Exception as e:
    st.error(f"Error loading schema.sql: {e}")

# Mapping of Levels to Descriptions
INTENSITY_LEVELS = {
    4: "Full Day (Deep connection/Event)",
    3: "In Person (Coffee, meeting, hangout)",
    2: "Phone/Video Call",
    1: "Text/Messaging only"
}

st.set_page_config(page_title="People Tracker Pro", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    selected_filter_tag, all_tags_df = tag_manager.render(conn)
    system_tools.render(conn)

# --- MAIN NAVIGATION ---
main_tab1, main_tab2, main_tab3 = st.tabs(["📊 Dashboard", "📇 Directory", "📈 Analytics"])
with main_tab1:
    dashboard.render(conn, all_tags_df)

with main_tab2:
    directory.render(conn, selected_filter_tag, all_tags_df, INTENSITY_LEVELS)

with main_tab3:
    analytics.render(conn, selected_filter_tag)