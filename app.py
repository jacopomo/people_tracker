import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
from scoring import update_person_score, recalculate_all

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

# --- SIDEBAR: TAG MANAGEMENT ---
with st.sidebar:
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
    
    # E. System Tools
    st.divider()
    st.subheader("⚙️ System Tools")
    
    col1, col2 = st.columns(2)
    
    if col1.button("🔄 Recalculate"):
        recalculate_all(conn)
        st.success("Scores updated!")
        st.rerun()

    if col2.button("🧹 Clean Dataset"):
        # 1. Find duplicates by normalizing names (Remove spaces, ignore case)
        duplicates_query = """
        SELECT TRIM(LOWER(first_name)) as clean_first, 
               TRIM(LOWER(last_name)) as clean_last, 
               COUNT(*) as count 
        FROM people 
        GROUP BY clean_first, clean_last 
        HAVING count > 1
        """
        dupes = pd.read_sql(duplicates_query, conn)
        
        if dupes.empty:
            st.info("No duplicates found. Check for typos (e.g., Jon vs John).")
        else:
            for _, row in dupes.iterrows():
                # Get all IDs that match this normalized name
                ids_df = pd.read_sql(
                    """SELECT id FROM people 
                       WHERE TRIM(LOWER(first_name)) = ? 
                       AND TRIM(LOWER(last_name)) = ? 
                       ORDER BY id ASC""", 
                    conn, params=(row['clean_first'], row['clean_last'])
                )
                
                ids = ids_df['id'].tolist()
                primary_id = ids[0]
                duplicate_ids = ids[1:]
                
                for dup_id in duplicate_ids:
                    # 2. Move encounters to primary
                    conn.execute("UPDATE encounters SET person_id = ? WHERE person_id = ?", (int(primary_id), int(dup_id)))
                    # 3. Move tags (IGNORE if primary already has that tag)
                    conn.execute("UPDATE OR IGNORE person_tags SET person_id = ? WHERE person_id = ?", (int(primary_id), int(dup_id)))
                    # 4. Wipe the duplicate person
                    conn.execute("DELETE FROM people WHERE id = ?", (int(dup_id),))
                    # 5. Cleanup the tags table for the deleted user
                    conn.execute("DELETE FROM person_tags WHERE person_id = ?", (int(dup_id),))

                # 6. De-duplicate Encounters: If multiple on same day, keep highest intensity
                # We do this specifically for the primary_id we just merged into
                conn.execute(f"""
                    DELETE FROM encounters 
                    WHERE person_id = {primary_id} 
                    AND id NOT IN (
                        SELECT id FROM (
                            SELECT id, MAX(intensity) 
                            FROM encounters 
                            WHERE person_id = {primary_id} 
                            GROUP BY date
                        )
                    )
                """)
            
            conn.commit()
            recalculate_all(conn) # Re-run scoring for the merged history
            st.success(f"Merged {len(dupes)} sets of duplicates!")
            st.rerun()
# --- MAIN NAVIGATION ---
# This creates the top-level tabs for the whole app
main_tab1, main_tab2, main_tab3 = st.tabs(["📊 Dashboard", "📇 Directory", "📈 Analytics"])

with main_tab1:
    st.header("Relationship Dashboard")
    st.write("Welcome back! Here is a summary of your connections.")
    
    # Quick Stat Cards
    c1, c2, c3 = st.columns(3)
    total_people = pd.read_sql("SELECT COUNT(*) FROM people", conn).iloc[0,0]
    total_enc = pd.read_sql("SELECT COUNT(*) FROM encounters", conn).iloc[0,0]
    
    c1.metric("Total Connections", total_people)
    c2.metric("Total Encounters", total_enc)
    c3.metric("Active Tags", len(all_tags_df))

    st.divider()
    st.subheader("Recent Activity")
    recent_query = """
    SELECT p.first_name || ' ' || p.last_name as Name, e.date, e.intensity 
    FROM encounters e JOIN people p ON e.person_id = p.id 
    ORDER BY e.date DESC LIMIT 5
    """
    st.table(pd.read_sql(recent_query, conn))

with main_tab2:
    # --- THIS IS YOUR ORIGINAL "MAIN UI" LOGIC ---
    st.title("People Directory")

    # Search Logic
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

    if not df.empty:
        df["display_name"] = df["first_name"] + " " + df["last_name"]
        person_id = st.selectbox("Select person", options=df["id"], format_func=lambda x: df[df["id"] == x]["display_name"].iloc[0])
        
        # FETCH CURRENT SCORE
        person_data = pd.read_sql("SELECT score FROM people WHERE id = ?", conn, params=(int(person_id),)).iloc[0]
        current_score = person_data['score']

        st.metric(label="Relationship Score", value=f"{current_score:.2f} pts")

        # --- QUICK LOOK ---
        st.subheader("Quick Look: Last 5 Encounters")
        quick_history_query = """
        SELECT date, 
               CASE intensity 
                   WHEN 4 THEN '🟢 Full Day'
                   WHEN 3 THEN '🔵 In Person'
                   WHEN 2 THEN '🟡 Phone/Video'
                   WHEN 1 THEN '⚪ Text/Chat'
                   ELSE 'Unknown'
               END as Type
        FROM encounters 
        WHERE person_id = ? 
        ORDER BY date DESC 
        LIMIT 5
        """
        quick_df = pd.read_sql(quick_history_query, conn, params=(int(person_id),))
        if not quick_df.empty:
            st.table(quick_df)
        else:
            st.info("No recent encounters logged.")

        # Your existing sub-tabs for the specific person
        inner_tab1, inner_tab2, inner_tab3 = st.tabs(["🕒 Log New", "🏷️ Manage Tags", "🗑️ History & Delete"])

        with inner_tab1:
            st.subheader("Log New Encounter")
            enc_date = st.date_input("Date", date.today())
            intensity_choice = st.radio(
                "Encounter Intensity",
                options=list(INTENSITY_LEVELS.keys()),
                format_func=lambda x: INTENSITY_LEVELS[x],
                index=1,
                horizontal=True,
                key="int_choice"
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

        with inner_tab2:
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
            assigned_tag_names = current_tags_df["tag_name"].tolist() if not current_tags_df.empty else []
            available_tags = all_tags_df[~all_tags_df["tag_name"].isin(assigned_tag_names)]
            if not available_tags.empty:
                tag_to_add = st.selectbox("Choose a tag to add", available_tags["tag_name"])
                if st.button("Assign Tag"):
                    tag_id = available_tags[available_tags["tag_name"] == tag_to_add]["id"].values[0]
                    conn.execute("INSERT INTO person_tags (person_id, tag_id) VALUES (?, ?)", (int(person_id), int(tag_id)))
                    conn.commit()
                    st.rerun()

        with inner_tab3:
            st.subheader("Manage Encounters")
            full_history_query = """
            SELECT id, date, intensity FROM encounters 
            WHERE person_id = ? ORDER BY date DESC
            """
            full_history = pd.read_sql(full_history_query, conn, params=(int(person_id),))
            
            if not full_history.empty:
                for _, row in full_history.iterrows():
                    col_info, col_del = st.columns([4, 1])
                    col_info.write(f"**{row['date']}** — Intensity: {row['intensity']}")
                    if col_del.button("Delete", key=f"enc_{row['id']}", type="secondary"):
                        conn.execute("DELETE FROM encounters WHERE id = ?", (int(row['id']),))
                        conn.commit()
                        update_person_score(conn, person_id)
                        st.rerun()
            else:
                st.info("No encounters logged yet.")

with main_tab3:
    st.header("Relationship Analytics")
    st.write("Visualizing your social network health.")
    
    # Simple Chart: Scores over time (if you have score history) or current score distribution
    all_people_scores = pd.read_sql("SELECT first_name, score FROM people WHERE score > 0 ORDER BY score DESC", conn)
    if not all_people_scores.empty:
        st.bar_chart(all_people_scores.set_index("first_name"))
    else:
        st.info("Log more encounters to see analytics!")