import pandas as pd
from datetime import datetime, date, timedelta

SCORING_WEIGHTS = {
    4: 2.0,   # Full Day
    3: 1.0,   # In Person
    2: 0.5,   # Phone/Video
    1: 0.25   # Text/Messaging
}

def calculate_decayed_score(encounters_df, target_date=None):
    """Calculates score where decay PERMANENTLY reduces the total."""
    if encounters_df.empty:
        return 0.0
    
    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()

    df = encounters_df.copy()
    # Supabase returns dates as strings, ensure they are date objects
    df['date_obj'] = pd.to_datetime(df['date']).dt.date
    relevant_encs = df[df['date_obj'] <= target_date].sort_values('date_obj')

    if relevant_encs.empty:
        return 0.0

    current_score = 0.0
    first_date = relevant_encs.iloc[0]['date_obj']
    
    iter_date = first_date
    days_since_last = 0
    enc_map = relevant_encs.groupby('date_obj')['intensity'].max().to_dict()

    while iter_date <= target_date:
        if iter_date in enc_map:
            current_score += SCORING_WEIGHTS.get(int(enc_map[iter_date]), 0.0)
            days_since_last = 0
        else:
            days_since_last += 1

        if days_since_last > 7:
            if days_since_last <= 14:
                daily_loss = 0.1
            elif days_since_last <= 30:
                daily_loss = 0.25 
            else:
                daily_loss = 1
            
            current_score -= daily_loss

        current_score = max(current_score, 0.0)
        iter_date += timedelta(days=1)

    return round(current_score, 2)
def update_person_score(supabase, person_id):
    try:
        response = supabase.table("encounters") \
            .select("date, intensity") \
            .eq("person_id", person_id) \
            .execute()
        
        # If no encounters, score is 0. Avoid the heavy calculation.
        if not response.data:
            supabase.table("people").update({"score": 0.0}).eq("id", person_id).execute()
            return 0.0

        enc_df = pd.DataFrame(response.data)
        new_score = calculate_decayed_score(enc_df)
        
        supabase.table("people").update({"score": new_score}).eq("id", person_id).execute()
        return new_score
    except Exception as e:
        print(f"Error updating score for {person_id}: {e}")
        return 0.0

def recalculate_all(supabase):
    """Loops through all people in Supabase and refreshes their scores."""
    response = supabase.table("people").select("id").execute()
    for row in response.data:
        update_person_score(supabase, row['id'])

def get_score_history(supabase, person_id, name):
    """Reconstructs the daily score history for analytics from Supabase."""
    response = supabase.table("encounters") \
        .select("date, intensity") \
        .eq("person_id", person_id) \
        .order("date", desc=False) \
        .execute()
    
    enc_df = pd.DataFrame(response.data)
    
    if enc_df.empty:
        return pd.DataFrame()
    
    enc_df['date'] = pd.to_datetime(enc_df['date']).dt.date
    start_date = enc_df['date'].min()
    end_date = date.today()
    
    history = []
    current_day = start_date
    
    while current_day <= end_date:
        daily_score = calculate_decayed_score(enc_df, target_date=current_day)
        history.append({
            "Date": current_day,
            "Score": daily_score,
            "Person": name
        })
        current_day += timedelta(days=1)
    
    return pd.DataFrame(history)