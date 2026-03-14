import pandas as pd
import sqlite3

# 1. Database Connection
conn = sqlite3.connect("people.db", check_same_thread=False)

# 2. Safety Check: Create tables if they don't exist
# This prevents the "no such table" error
conn.executescript("""
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    notes TEXT,
    UNIQUE(first_name, last_name)
);

CREATE TABLE IF NOT EXISTS encounters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,
    date TEXT,
    context TEXT,
    FOREIGN KEY (person_id) REFERENCES people(id)
);
""")
conn.commit()
# 1. Ensure the table has a UNIQUE constraint
conn.execute("""
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    notes TEXT,
    UNIQUE(first_name, last_name)
);
""")

# 2. Load and clean your CSV
df = pd.read_csv("contacts.csv")
people = df[["First Name", "Last Name"]].dropna()
people.columns = ["first_name", "last_name"]

# 3. Create a TEMPORARY table to hold the new data
people.to_sql("temp_people", conn, if_exists="replace", index=False)

# 4. Use SQL to move data from 'temp' to 'people' only if it's new
# "INSERT OR IGNORE" is the magic command here
conn.execute("""
INSERT OR IGNORE INTO people (first_name, last_name)
SELECT first_name, last_name FROM temp_people;
""")

# 5. Clean up the temp table and close
conn.execute("DROP TABLE temp_people;")
conn.commit()
conn.close()

print("Database updated! Duplicates were ignored.")