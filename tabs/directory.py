import streamlit as st
import pandas as pd
from datetime import date
from scoring import update_person_score

def render(supabase, selected_filter_tag, all_tags_df, intensity_levels):
    st.title("📇 People Directory")

    # 1. Search Logic
    if selected_filter_tag != "All":
        # JOIN logic in Supabase: We query the join table and 'select' through the relationship
        response = supabase.table("person_tags") \
            .select("people(id, first_name, last_name), tags!inner(tag_name)") \
            .eq("tags.tag_name", selected_filter_tag) \
            .execute()
        
        # Flatten the nested JSON response into a DataFrame
        data = []
        for row in response.data:
            p = row['people']
            data.append({"id": p['id'], "first_name": p['first_name'], "last_name": p['last_name']})
        df = pd.DataFrame(data)
    else:
        search = st.text_input("Search for a person by name...", placeholder="Start typing...")
        # ILIKE is PostgreSQL's case-insensitive search
        response = supabase.table("people") \
            .select("id, first_name, last_name") \
            .or_(f"first_name.ilike.%{search}%,last_name.ilike.%{search}%") \
            .execute()
        df = pd.DataFrame(response.data)

    if df.empty:
        st.warning("No one found. Try a different search or tag.")
        return

    # 2. Person Selection
    df["display_name"] = df["first_name"] + " " + df["last_name"]
    person_id = st.selectbox(
        "Select person", 
        options=df["id"].tolist(), 
        format_func=lambda x: df[df["id"] == x]["display_name"].iloc[0]
    )
    
    # 3. Profile Header
    person_response = supabase.table("people").select("score").eq("id", person_id).single().execute()
    current_score = person_response.data['score'] if person_response.data else 0.0
    st.metric(label="Relationship Score", value=f"{current_score:.2f} pts")

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

        if st.button("Save Encounter", use_container_width=True):
            supabase.table("encounters").insert({
                "person_id": int(person_id),
                "date": str(enc_date),
                "intensity": int(intensity_choice)
            }).execute()
            
            # Recalculate and update the score in the cloud
            update_person_score(supabase, person_id)
            st.success("Encounter logged!")
            st.rerun()

    with tab_tags:
        st.subheader("Current Tags")
        tag_response = supabase.table("person_tags") \
            .select("tags(id, tag_name)") \
            .eq("person_id", person_id) \
            .execute()
        
        current_tags_data = [row['tags'] for row in tag_response.data]
        current_tags_df = pd.DataFrame(current_tags_data)

        if not current_tags_df.empty:
            for _, row in current_tags_df.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(f"🏷️ {row['tag_name']}")
                if c2.button("Remove", key=f"del_tag_{person_id}_{row['id']}"):
                    supabase.table("person_tags") \
                        .delete() \
                        .eq("person_id", person_id) \
                        .eq("tag_id", row['id']) \
                        .execute()
                    st.rerun()
        
        st.divider()
        assigned_names = current_tags_df["tag_name"].tolist() if not current_tags_df.empty else []
        available_tags = all_tags_df[~all_tags_df["tag_name"].isin(assigned_names)]
        
        if not available_tags.empty:
            tag_to_add = st.selectbox("Choose a tag to add", available_tags["tag_name"])
            if st.button("Assign Tag"):
                t_id = available_tags[available_tags["tag_name"] == tag_to_add]["id"].values[0]
                supabase.table("person_tags").insert({
                    "person_id": int(person_id),
                    "tag_id": int(t_id)
                }).execute()
                st.rerun()

    with tab_hist:
        st.subheader("Manage Encounters")
        hist_response = supabase.table("encounters") \
            .select("id, date, intensity") \
            .eq("person_id", person_id) \
            .order("date", desc=True) \
            .execute()
        full_hist = pd.DataFrame(hist_response.data)
        
        if not full_hist.empty:
            for _, row in full_hist.iterrows():
                col_i, col_d = st.columns([4, 1])
                col_i.write(f"**{row['date']}** — Intensity: {row['intensity']}")
                if col_d.button("Delete", key=f"enc_del_{row['id']}", type="secondary"):
                    supabase.table("encounters").delete().eq("id", row['id']).execute()
                    update_person_score(supabase, person_id)
                    st.rerun()
        else:
            st.info("No history found.")