import streamlit as st
import pandas as pd
from scoring import recalculate_all

def render(supabase):
    st.divider()
    st.subheader("⚙️ System Tools")
    
    col1, col2 = st.columns(2)
    
    # --- 1. RECALCULATE ---
    if col1.button("🔄 Recalculate", use_container_width=True):
        with st.spinner("Syncing scores..."):
            recalculate_all(supabase)
            st.success("Scores updated!")
            st.rerun()

    # --- 2. CLEAN DATASET (Merge Duplicates) ---
    if col2.button("🧹 Clean Data", use_container_width=True):
        # We fetch the list of people to find duplicates in Python
        # (Postgres TRIM/LOWER is possible, but this is safer for a small-ish DB)
        response = supabase.table("people").select("id, first_name, last_name").execute()
        all_people = pd.DataFrame(response.data)

        if all_people.empty:
            st.info("Database is empty.")
            return

        # Identify duplicates by cleaning strings in Pandas
        all_people['clean_f'] = all_people['first_name'].str.strip().str.lower()
        all_people['clean_l'] = all_people['last_name'].str.strip().str.lower()
        
        # Group to find sets with more than 1 ID
        grouped = all_people.groupby(['clean_f', 'clean_l'])['id'].apply(list).reset_index()
        dupes = grouped[grouped['id'].map(len) > 1]

        if dupes.empty:
            st.info("No duplicates found.")
        else:
            for _, row in dupes.iterrows():
                ids = sorted(row['id']) # Keep the oldest ID (smallest number)
                primary_id = ids[0]
                duplicate_ids = ids[1:]
                
                for dup_id in duplicate_ids:
                    # 1. Move encounters to the primary person
                    supabase.table("encounters").update({"person_id": primary_id}).eq("person_id", dup_id).execute()
                    
                    # 2. Move tags (We use a try/except because person_tags might already exist for primary)
                    tag_res = supabase.table("person_tags").select("tag_id").eq("person_id", dup_id).execute()
                    for tag_row in tag_res.data:
                        try:
                            supabase.table("person_tags").insert({"person_id": primary_id, "tag_id": tag_row['tag_id']}).execute()
                        except:
                            pass # Tag already exists on primary, ignore it
                    
                    # 3. Delete the duplicate person (Cascading will handle their old person_tags)
                    supabase.table("people").delete().eq("id", dup_id).execute()

            # Final Step: Clean up redundant encounters (same person, same day)
            # We refresh the whole score set after the merge
            recalculate_all(supabase)
            st.success(f"Merged {len(dupes)} duplicate sets!")
            st.rerun()