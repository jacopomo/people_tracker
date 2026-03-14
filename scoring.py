import sqlite3

# --- ALGORITHM CONFIGURATION ---
# Edit these numbers to change how the points are calculated
SCORING_WEIGHTS = {
    4: 2.0,   # Full Day / Deep Connection
    3: 1.0,   # In Person
    2: 0.75,  # Phone/Video
    1: 0.25   # Text/Messaging
}

def update_person_score(conn, person_id):
    """
    Recalculates the total score for a person based on all their encounters.
    Expects an active sqlite3 connection and the person's ID.
    """
    cursor = conn.execute("SELECT intensity FROM encounters WHERE person_id = ?", (person_id,))
    encounters = cursor.fetchall()
    
    new_score = 0.0
    for (intensity,) in encounters:
        new_score += SCORING_WEIGHTS.get(intensity, 0.0)
    
    conn.execute("UPDATE people SET score = ? WHERE id = ?", (new_score, person_id))
    conn.commit()
    return new_score

def recalculate_all(conn):
    """Updates every single person in the database."""
    cursor = conn.execute("SELECT id FROM people")
    all_ids = cursor.fetchall()
    for (pid,) in all_ids:
        update_person_score(conn, pid)