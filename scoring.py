import sqlite3
import pandas as pd

SCORING_WEIGHTS = {
    4: 2.0,   # Full Day
    3: 1.0,   # In Person
    2: 0.75,  # Phone/Video
    1: 0.25   # Text/Messaging
}

def calculate_score_from_encounters(encounters_df):
    """Logic to sum scores. Easy to add decay logic here later."""
    if encounters_df.empty:
        return 0.0
    return encounters_df['intensity'].map(SCORING_WEIGHTS).sum()

def update_person_score(conn, person_id):
    query = "SELECT intensity FROM encounters WHERE person_id = ?"
    enc_df = pd.read_sql(query, conn, params=(int(person_id),))
    new_score = calculate_score_from_encounters(enc_df)
    
    conn.execute("UPDATE people SET score = ? WHERE id = ?", (new_score, int(person_id)))
    conn.commit()
    return new_score

def recalculate_all(conn):
    cursor = conn.execute("SELECT id FROM people")
    for (pid,) in cursor.fetchall():
        update_person_score(conn, pid)

def get_score_history(conn, person_id, name):
    """Reconstructs score over time for the analytics tab."""
    query = "SELECT date, intensity FROM encounters WHERE person_id = ? ORDER BY date ASC"
    df = pd.read_sql(query, conn, params=(int(person_id),))
    if df.empty:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    history = []
    running_score = 0
    
    for _, row in df.iterrows():
        running_score += SCORING_WEIGHTS.get(row['intensity'], 0)
        history.append({"Date": row['date'], "Score": running_score, "Person": name})
    
    return pd.DataFrame(history)