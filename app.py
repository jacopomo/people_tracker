import streamlit as st
from database import supabase
from sidebar import tag_manager, system_tools
from tabs import dashboard, directory, analytics

st.set_page_config(page_title="Relationship Tracker", layout="wide")

# Mapping of Levels to Descriptions
INTENSITY_LEVELS = {
    4: "Full Day (Deep connection/Event)",
    3: "In Person (Coffee, meeting, hangout)",
    2: "Phone/Video Call",
    1: "Text/Messaging only"
}

# --- AUTO-UPDATE SCORES ON STARTUP ---
# This ensures that as time passes, the scores decay automatically 
# without needing a manual "Recalculate" click.
if 'scores_refreshed' not in st.session_state:
    try:
        st.session_state['scores_refreshed'] = True
    except Exception as e:
        st.sidebar.warning("Note: Quick score sync pending.")

# --- SIDEBAR ---
with st.sidebar:
    selected_filter_tag, all_tags_df = tag_manager.render(supabase)
    system_tools.render(supabase)

# --- MAIN NAVIGATION ---
main_tab1, main_tab2, main_tab3 = st.tabs(["📊 Dashboard", "📇 Directory", "📈 Analytics"])
with main_tab1:
    dashboard.render(supabase, all_tags_df)

with main_tab2:
    directory.render(supabase, selected_filter_tag, all_tags_df, INTENSITY_LEVELS)

with main_tab3:
    analytics.render(supabase, selected_filter_tag)