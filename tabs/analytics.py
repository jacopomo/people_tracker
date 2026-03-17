import streamlit as st
import pandas as pd
from datetime import date, timedelta
from scoring import get_score_history
import calendar

def render(conn, selected_filter_tag):
    st.header("📈 Score Evolution")

    # --- 1. SET UP DATE FILTERS ---
    col_view, col_year, col_month = st.columns([2, 1, 1])
    
    with col_view:
        view_option = st.selectbox(
            "Time Range", 
            ["All Time", "Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 365 Days", "Specific Year", "Specific Month"]
        )

    # Logic to determine Start and End dates
    today = date.today()
    start_date = None
    end_date = today

    if view_option == "Last 7 Days":
        start_date = today - timedelta(days=7)
    elif view_option == "Last 30 Days":
        start_date = today - timedelta(days=30)
    elif view_option == "Last 90 Days":
        start_date = today - timedelta(days=90)
    elif view_option == "Last 365 Days":
        start_date = today - timedelta(days=365)
    elif view_option == "Specific Year":
        year = col_year.number_input("Year", min_value=2020, max_value=2030, value=today.year)
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
    elif view_option == "Specific Month":
        year = col_year.number_input("Year", min_value=2020, max_value=2030, value=today.year, key="month_year")
        month_name = col_month.selectbox("Month", list(calendar.month_name)[1:])
        month_idx = list(calendar.month_name).index(month_name)
        start_date = date(year, month_idx, 1)
        last_day = calendar.monthrange(year, month_idx)[1]
        end_date = date(year, month_idx, last_day)

    # --- 2. GET PEOPLE DATA ---
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

    limit = st.selectbox("Show top current relationships:", [5, 10, 20, "All"])
    num_limit = len(people_to_track) if limit == "All" else limit
    
    ids = people_to_track['id'].tolist()
    placeholders = ','.join('?' for _ in ids)
    top_people = pd.read_sql(f"SELECT id, first_name || ' ' || last_name as name FROM people WHERE id IN ({placeholders}) ORDER BY score DESC LIMIT ?", 
                             conn, params=(*ids, num_limit))

    # --- 3. GENERATE & FILTER HISTORY ---
    all_histories = []
    for _, person in top_people.iterrows():
        # get_score_history calculates from the VERY BEGINNING to maintain 'Burn' accuracy
        hist = get_score_history(conn, person['id'], person['name'])
        
        if not hist.empty:
            # Now we slice the data based on our UI filters
            if start_date:
                hist = hist[hist['Date'] >= start_date]
            if end_date:
                hist = hist[hist['Date'] <= end_date]
            
            all_histories.append(hist)

    # --- 4. PLOTTING ---
    if all_histories:
        full_df = pd.concat(all_histories)
        # Ensure we have a continuous index for the chart
        chart_data = full_df.pivot(index="Date", columns="Person", values="Score").ffill().fillna(0)
        
        st.line_chart(chart_data)
    else:
        st.info("No encounter history available for this time range.")