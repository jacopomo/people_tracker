import streamlit as st
import pandas as pd
from datetime import date
from scoring import update_person_score

def render(conn, selected_filter_tag, all_tags_df, intensity_levels):
    st.title("📇 People Directory")

    # 1. Search Logic
    if selected_filter_tag != "All":
        query = """
        SELECT p.id, p.first_name, p.last_name FROM people p
        JOIN person_tags pt ON p.id = pt.person_id
        JOIN tags t ON pt.tag_id = t.id
        WHERE t.tag_name = ?
        """
        df = pd.read_sql(query, conn, params=(selected_filter_tag,))
    else:
        search = st.text_input("Search for a person by name...", placeholder="Start typing...")
        query = "SELECT id, first_name, last_name FROM people WHERE first_name LIKE ? OR last_name LIKE ?"
        df = pd.read_sql(query, conn, params=(f"%{search}%", f"%{search}%"))

    if df.empty:
        st.warning("No one found. Try a different search or tag.")
        return

    # 2. Person Selection
    df["display_name"] = df["first_name"] + " " + df["last_name"]
    person_id = st.selectbox(
        "Select person", 
        options=df["id"], 
        format_func=lambda x: df[df["id"] == x]["display_name"].iloc[0]
    )
    
    # 3. Profile Header
    person_data = pd.read_sql("SELECT score FROM people WHERE id = ?", conn, params=(int(person_id),)).iloc[0]
    st.metric(label="Relationship Score", value=f"{person_data['score']:.2f} pts")

    # 4. Interaction Tabs
    tab_log, tab_tags, tab_hist = st.tabs(["🕒 Log New", "🏷️ Manage Tags", "🗑️ History & Delete"])

    with tab_log:
        st.subheader("Log New Encounter")
        enc_date = st.date_input("Date", date.today())
        intensity_choice = st.radio(
            "Encounter Intensity",
            options=list(intensity_levels.keys()),
            format_func=lambda x: intensity_levels[x],
            index=1,
            horizontal=True,
            key=f"int_{person_id}"
        )

        if st.button("Save Encounter", width="stretch"):
            conn.execute(
                "INSERT INTO encounters (person_id, date, intensity) VALUES (?, ?, ?)",
                (int(person_id), str(enc_date), intensity_choice)
            )
            conn.commit()
            update_person_score(conn, person_id)
            st.success("Encounter logged!")
            st.rerun()

    with tab_tags:
        st.subheader("Current Tags")
        current_tags_df = pd.read_sql("""
            SELECT t.id, t.tag_name FROM tags t 
            JOIN person_tags pt ON t.id = pt.tag_id 
            WHERE pt.person_id = ?""", conn, params=(int(person_id),))

        if not current_tags_df.empty:
            for _, row in current_tags_df.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"🏷️ {row['tag_name']}")
                if c2.button("Remove", key=f"del_tag_{person_id}_{row['id']}"):
                    conn.execute("DELETE FROM person_tags WHERE person_id = ? AND tag_id = ?", (int(person_id), int(row['id'])))
                    conn.commit()
                    st.rerun()
        
        st.divider()
        assigned_names = current_tags_df["tag_name"].tolist() if not current_tags_df.empty else []
        available_tags = all_tags_df[~all_tags_df["tag_name"].isin(assigned_names)]
        
        if not available_tags.empty:
            tag_to_add = st.selectbox("Choose a tag to add", available_tags["tag_name"])
            if st.button("Assign Tag"):
                t_id = available_tags[available_tags["tag_name"] == tag_to_add]["id"].values[0]
                conn.execute("INSERT INTO person_tags (person_id, tag_id) VALUES (?, ?)", (int(person_id), int(t_id)))
                conn.commit()
                st.rerun()

    with tab_hist:
        st.subheader("Manage Encounters")
        full_hist = pd.read_sql(
            "SELECT id, date, intensity FROM encounters WHERE person_id = ? ORDER BY date DESC", 
            conn, params=(int(person_id),)
        )
        
        if not full_hist.empty:
            for _, row in full_hist.iterrows():
                col_i, col_d = st.columns([4, 1])
                col_i.write(f"**{row['date']}** — Intensity: {row['intensity']}")
                if col_d.button("Delete", key=f"enc_del_{row['id']}", type="secondary"):
                    conn.execute("DELETE FROM encounters WHERE id = ?", (int(row['id']),))
                    conn.commit()
                    update_person_score(conn, person_id)
                    st.rerun()
        else:
            st.info("No history found.")