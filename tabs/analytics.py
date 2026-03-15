# tabs/analytics.py
import streamlit as st
import pandas as pd
from scoring import get_score_history

def render(conn, selected_filter_tag):
    st.header("📈 Score Evolution")

    # Filter logic
    if selected_filter_tag != "All":
        query = """SELECT p.id, p.first_name || ' ' || p.last_name as name FROM people p
                   JOIN person_tags pt ON p.id = pt.person_id
                   JOIN tags t ON pt.tag_id = t.id WHERE t.tag_name = ?"""
        people_to_track = pd.read_sql(query, conn, params=(selected_filter_tag,))
    else:
        people_to_track = pd.read_sql("SELECT id, first_name || ' ' || last_name as name FROM people", conn)

    if people_to_track.empty:
        st.info("No connections found.")
        return

    # Top N selection
    limit = st.selectbox("Show top:", [5, 10, 20, "All"])
    num_limit = len(people_to_track) if limit == "All" else limit
    
    # Get top people by current score
    ids = people_to_track['id'].tolist()
    placeholders = ','.join('?' for _ in ids)
    top_people = pd.read_sql(f"SELECT id, first_name || ' ' || last_name as name FROM people WHERE id IN ({placeholders}) ORDER BY score DESC LIMIT ?", 
                             conn, params=(*ids, num_limit))

    all_histories = []
    for _, person in top_people.iterrows():
        hist = get_score_history(conn, person['id'], person['name'])
        all_histories.append(hist)

    if all_histories:
        full_df = pd.concat(all_histories)
        chart_data = full_df.pivot(index="Date", columns="Person", values="Score").ffill().fillna(0)
        st.line_chart(chart_data)