import streamlit as st
import pandas as pd

def render(supabase):
    st.title("🏷️ Tag Manager")
    
    # Fetch all tags from Supabase
    response = supabase.table("tags").select("*").execute()
    all_tags_df = pd.DataFrame(response.data)

    # A. Filter by Tag
    st.subheader("Filter People")
    tag_list = ["All"]
    if not all_tags_df.empty:
        tag_list += all_tags_df["tag_name"].tolist()
        
    selected_filter_tag = st.selectbox(
        "View everyone tagged as:", 
        tag_list
    )

    st.divider()

    # B. Create new tag
    st.subheader("Create Tag")
    new_tag = st.text_input("Tag name", placeholder="e.g. Family")
    if st.button("Add Tag", use_container_width=True):
        if new_tag.strip():
            # In Supabase, if a Unique constraint is hit, it raises an Exception
            try:
                supabase.table("tags").insert({"tag_name": new_tag.strip()}).execute()
                st.success(f"Tag '{new_tag}' created!")
                st.rerun()
            except Exception:
                st.error("Tag already exists or connection error!")

    st.divider()

    # C. Global Tag Cleanup
    if not all_tags_df.empty:
        st.subheader("Delete Tag")
        tag_to_delete = st.selectbox("Select tag to wipe permanently", all_tags_df["tag_name"])
        if st.button("Delete Everywhere", type="primary", use_container_width=True):
            target_id = all_tags_df[all_tags_df["tag_name"] == tag_to_delete]["id"].values[0]
            
            # Note: If you set up 'ON DELETE CASCADE' in your Supabase SQL, 
            # deleting from 'tags' will automatically clean up 'person_tags'.
            supabase.table("tags").delete().eq("id", int(target_id)).execute()
            st.rerun()
    
    # D. Leaderboard
    st.divider()
    st.subheader("🏆 Top Relationships")
    
    # Fetch top 5 people by score
    lb_response = supabase.table("people") \
        .select("first_name, last_name, score") \
        .order("score", desc=True) \
        .limit(5) \
        .execute()
    
    if lb_response.data:
        # Format names for display
        lb_data = []
        for row in lb_response.data:
            lb_data.append({
                "Name": f"{row['first_name']} {row['last_name']}",
                "Score": round(row['score'], 2)
            })
        
        leaderboard_df = pd.DataFrame(lb_data)
        st.dataframe(leaderboard_df, hide_index=True, use_container_width=True)
        
    return selected_filter_tag, all_tags_df