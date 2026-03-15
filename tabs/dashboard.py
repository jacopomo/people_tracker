import streamlit as st
import pandas as pd
from scoring import recalculate_all

def render(conn, all_tags_df):
    st.header("📊 Relationship Dashboard")
    st.write("Welcome back! Here is a summary of your connections.")
    
    # 1. Quick Stat Cards
    c1, c2, c3 = st.columns(3)
    total_people = pd.read_sql("SELECT COUNT(*) FROM people", conn).iloc[0,0]
    total_enc = pd.read_sql("SELECT COUNT(*) FROM encounters", conn).iloc[0,0]
    
    c1.metric("Total Connections", total_people)
    c2.metric("Total Encounters", total_enc)
    c3.metric("Active Tags", len(all_tags_df))

    st.divider()

    # 2. Add New Person Form
    with st.expander("➕ Add New Connection"):
        with st.form("new_person_form"):
            col_f, col_l = st.columns(2)
            f_name = col_f.text_input("First Name")
            l_name = col_l.text_input("Last Name")
            submitted = st.form_submit_button("Create Profile")
            
            if submitted:
                if f_name.strip() and l_name.strip():
                    conn.execute(
                        "INSERT INTO people (first_name, last_name, score) VALUES (?, ?, 0)",
                        (f_name.strip(), l_name.strip())
                    )
                    conn.commit()
                    st.success(f"Created profile for {f_name}!")
                    st.rerun()
                else:
                    st.error("Please provide both names.")

    # 3. Recent Activity Table
    st.subheader("🕒 Recent Activity")
    recent_query = """
    SELECT p.first_name || ' ' || p.last_name as Name, e.date, 
           CASE e.intensity 
               WHEN 4 THEN '🟢 Full Day'
               WHEN 3 THEN '🔵 In Person'
               WHEN 2 THEN '🟡 Phone/Video'
               WHEN 1 THEN '⚪ Text/Chat'
           END as Type
    FROM encounters e JOIN people p ON e.person_id = p.id 
    ORDER BY e.date DESC LIMIT 5
    """
    recent_df = pd.read_sql(recent_query, conn)
    if not recent_df.empty:
        st.table(recent_df)
    else:
        st.info("No activity logged yet.")