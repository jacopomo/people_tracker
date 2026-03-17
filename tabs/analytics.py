import streamlit as st
import pandas as pd
from datetime import date, timedelta
from scoring import get_score_history
import calendar

def render(supabase, selected_filter_tag):
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
        start_date, end_date = date(year, 1, 1), date(year, 12, 31)
    elif view_option == "Specific Month":
        year = col_year.number_input("Year", min_value=2020, max_value=2030, value=today.year, key="month_year")
        month_name = col_month.selectbox("Month", list(calendar.month_name)[1:])
        month_idx = list(calendar.month_name).index(month_name)
        start_date = date(year, month_idx, 1)
        last_day = calendar.monthrange(year, month_idx)[1]
        end_date = date(year, month_idx, last_day)

    # --- 2. GET PEOPLE DATA FROM SUPABASE ---
    if selected_filter_tag != "All":
        # Get people who have the selected tag
        response = supabase.table("person_tags") \
            .select("people(id, first_name, last_name, score), tags!inner(tag_name)") \
            .eq("tags.tag_name", selected_filter_tag) \
            .execute()
        
        data = []
        for row in response.data:
            p = row['people']
            data.append({
                "id": p['id'], 
                "name": f"{p['first_name']} {p['last_name']}",
                "score": p['score']
            })
        people_to_track = pd.DataFrame(data)
    else:
        # Get all people
        response = supabase.table("people").select("id, first_name, last_name, score").execute()
        data = [{"id": r['id'], "name": f"{r['first_name']} {r['last_name']}", "score": r['score']} for r in response.data]
        people_to_track = pd.DataFrame(data)

    if people_to_track.empty:
        st.info("No connections found.")
        return

    # Filter the list by the top scores (the user-selected limit)
    limit = st.selectbox("Show top current relationships:", [5, 10, 20, "All"])
    
    if limit != "All":
        top_people = people_to_track.sort_values("score", ascending=False).head(int(limit))
    else:
        top_people = people_to_track

    # --- 3. GENERATE & FILTER HISTORY ---
    all_histories = []
    
    # We use a progress bar because reconstructing history via Cloud API takes a moment
    progress_bar = st.progress(0)
    for i, (_, person) in enumerate(top_people.iterrows()):
        # Pass 'supabase' client to the history generator
        hist = get_score_history(supabase, person['id'], person['name'])
        
        if not hist.empty:
            if start_date:
                hist = hist[hist['Date'] >= start_date]
            if end_date:
                hist = hist[hist['Date'] <= end_date]
            all_histories.append(hist)
        
        progress_bar.progress((i + 1) / len(top_people))
    
    progress_bar.empty()

    # --- 4. PLOTTING ---
    if all_histories:
        full_df = pd.concat(all_histories)
        # Pivot for the chart (Date as X, Person as Legend, Score as Y)
        chart_data = full_df.pivot(index="Date", columns="Person", values="Score").ffill().fillna(0)
        
        st.line_chart(chart_data)
    else:
        st.info("No encounter history available for this time range.")