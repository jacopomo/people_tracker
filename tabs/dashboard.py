import streamlit as st
import pandas as pd
from scoring import recalculate_all

def render(supabase, all_tags_df):
    st.header("📊 Relationship Dashboard")
    st.write("Welcome back! Your data is now synced to the cloud.")
    
    # 1. Quick Stat Cards
    c1, c2, c3 = st.columns(3)
    
    # Supabase "count" is very efficient: we use head(0) to just get the metadata
    total_people_res = supabase.table("people").select("*", count="exact").execute()
    total_enc_res = supabase.table("encounters").select("*", count="exact").execute()
    
    total_people = total_people_res.count if total_people_res.count else 0
    total_enc = total_enc_res.count if total_enc_res.count else 0
    
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
                    # Supabase Insert
                    supabase.table("people").insert({
                        "first_name": f_name.strip(),
                        "last_name": l_name.strip(),
                        "score": 0.0
                    }).execute()
                    
                    st.success(f"Created profile for {f_name}!")
                    st.rerun()
                else:
                    st.error("Please provide both names.")

    # 3. Recent Activity Table
    st.subheader("🕒 Recent Activity")
    
    # We fetch the joined data. Supabase lets us pull 'people' data directly 
    # through the foreign key defined in our SQL schema.
    recent_res = supabase.table("encounters") \
        .select("date, intensity, people(first_name, last_name)") \
        .order("date", desc=True) \
        .limit(5) \
        .execute()
    
    if recent_res.data:
        # Format the data for a clean table
        formatted_data = []
        for row in recent_res.data:
            name = f"{row['people']['first_name']} {row['people']['last_name']}"
            
            # Map intensity to labels
            intensity_map = {
                4: '🟢 Full Day',
                3: '🔵 In Person',
                2: '🟡 Phone/Video',
                1: '⚪ Text/Chat'
            }
            
            formatted_data.append({
                "Name": name,
                "Date": row['date'],
                "Type": intensity_map.get(row['intensity'], "Unknown")
            })
            
        recent_df = pd.DataFrame(formatted_data)
        st.table(recent_df)
    else:
        st.info("No activity logged yet.")