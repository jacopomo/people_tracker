import streamlit as st
import pandas as pd
import sqlite3

def render(conn):
    st.title("🏷️ Tag Manager")
    
    all_tags_df = pd.read_sql("SELECT * FROM tags", conn)

    # A. Filter by Tag
    st.subheader("Filter People")
    selected_filter_tag = st.selectbox(
        "View everyone tagged as:", 
        ["All"] + all_tags_df["tag_name"].tolist()
    )

    st.divider()

    # B. Create new tag
    st.subheader("Create Tag")
    new_tag = st.text_input("Tag name", placeholder="e.g. Family")
    if st.button("Add Tag"):
        if new_tag.strip():
            try:
                conn.execute("INSERT INTO tags (tag_name) VALUES (?)", (new_tag.strip(),))
                conn.commit()
                st.success(f"Tag '{new_tag}' created!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("Tag already exists!")

    st.divider()

    # C. Global Tag Cleanup
    if not all_tags_df.empty:
        st.subheader("Delete Tag")
        tag_to_delete = st.selectbox("Select tag to wipe permanently", all_tags_df["tag_name"])
        if st.button("Delete Everywhere", type="primary"):
            target_id = all_tags_df[all_tags_df["tag_name"] == tag_to_delete]["id"].values[0]
            conn.execute("DELETE FROM person_tags WHERE tag_id = ?", (int(target_id),))
            conn.execute("DELETE FROM tags WHERE id = ?", (int(target_id),))
            conn.commit()
            st.rerun()
    
    # D. Leaderboard
    st.divider()
    st.subheader("🏆 Top Relationships")
    leaderboard_df = pd.read_sql(
        "SELECT first_name || ' ' || last_name as Name, score FROM people ORDER BY score DESC LIMIT 5", 
        conn
    )
    if not leaderboard_df.empty:
        st.dataframe(leaderboard_df, hide_index=True, width="stretch")
        
    return selected_filter_tag, all_tags_df