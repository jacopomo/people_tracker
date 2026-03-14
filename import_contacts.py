import pandas as pd
import sqlite3

df = pd.read_csv("contacts.csv")

conn = sqlite3.connect("people.db")

people = df[["First Name", "Last Name"]].dropna()

people.columns = ["first_name", "last_name"]

people.to_sql("people", conn, if_exists="append", index=False)

conn.close()