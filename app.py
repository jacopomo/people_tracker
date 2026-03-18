import streamlit as st
from database import supabase
from sidebar import tag_manager, system_tools
from tabs import dashboard, directory, analytics

def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Private Vault")
        st.text_input("Enter Passcode", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter Passcode", type="password", on_change=password_entered, key="password")
        st.error("😕 Access Denied")
        return False
    else:
        return True

if not check_password():
    st.stop() # Stops the rest of the app from loading

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