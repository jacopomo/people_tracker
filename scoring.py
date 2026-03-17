import pandas as pd
from datetime import datetime, date, timedelta

SCORING_WEIGHTS = {
    4: 2.0,   # Full Day
    3: 1.0,   # In Person
    2: 0.5,  # Phone/Video
    1: 0.25   # Text/Messaging
}

def calculate_decayed_score(encounters_df, target_date=None):
    """
    Calculates score where decay PERMANENTLY reduces the total.
    """
    if encounters_df.empty:
        return 0.0
    
    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()

    # Get all encounters up to the target date
    df = encounters_df.copy()
    df['date_obj'] = pd.to_datetime(df['date']).dt.date
    relevant_encs = df[df['date_obj'] <= target_date].sort_values('date_obj')

    if relevant_encs.empty:
        return 0.0

    current_score = 0.0
    first_date = relevant_encs.iloc[0]['date_obj']
    
    # We simulate day-by-day to ensure decay is 'permanent'
    # and resets correctly on encounter days
    iter_date = first_date
    days_since_last = 0
    
    # Create a dictionary for quick lookup of encounter points by date
    enc_map = relevant_encs.groupby('date_obj')['intensity'].max().to_dict()

    while iter_date <= target_date:
        # 1. Add points if an encounter happened today
        if iter_date in enc_map:
            current_score += SCORING_WEIGHTS.get(int(enc_map[iter_date]), 0.0)
            days_since_last = 0
        else:
            days_since_last += 1

        # 2. Apply the 'Burn' (Subtraction)
        # Only start burning after 7 days of silence
        if days_since_last > 7:
            if days_since_last <= 14:
                daily_loss =  0.1
            elif days_since_last <= 30:
                daily_loss = 0.25 
            else:
                daily_loss = 1
            
            # Subtract the loss from the running total
            current_score -= daily_loss

        # Prevent score from going negative
        current_score = max(current_score, 0.0)
        iter_date += timedelta(days=1)

    return round(current_score, 2)
def update_person_score(conn, person_id):
    query = "SELECT date, intensity FROM encounters WHERE person_id = ?"
    enc_df = pd.read_sql(query, conn, params=(int(person_id),))
    new_score = calculate_decayed_score(enc_df)
    
    conn.execute("UPDATE people SET score = ? WHERE id = ?", (new_score, int(person_id)))
    conn.commit()
    return new_score

def recalculate_all(conn):
    cursor = conn.execute("SELECT id FROM people")
    for (pid,) in cursor.fetchall():
        update_person_score(conn, pid)

def get_score_history(conn, person_id, name):
    """Reconstructs the daily score history for analytics."""
    query = "SELECT date, intensity FROM encounters WHERE person_id = ? ORDER BY date ASC"
    enc_df = pd.read_sql(query, conn, params=(int(person_id),))
    
    if enc_df.empty:
        return pd.DataFrame()
    
    # Convert dates
    enc_df['date'] = pd.to_datetime(enc_df['date']).dt.date
    
    start_date = enc_df['date'].min()
    end_date = date.today()
    
    history = []
    current_day = start_date
    
    # Iterate through every day from first meeting until today
    while current_day <= end_date:
        # Calculate score for THIS specific day
        daily_score = calculate_decayed_score(enc_df, target_date=current_day)
        
        history.append({
            "Date": current_day,
            "Score": daily_score,
            "Person": name
        })
        current_day += timedelta(days=1)
    
    return pd.DataFrame(history)