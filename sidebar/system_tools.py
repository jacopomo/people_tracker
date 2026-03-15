import streamlit as st
import pandas as pd
from scoring import recalculate_all

def render(conn):
    st.divider()
    st.subheader("⚙️ System Tools")
    
    col1, col2 = st.columns(2)
    
    if col1.button("🔄 Recalculate"):
        recalculate_all(conn)
        st.success("Scores updated!")
        st.rerun()

    if col2.button("🧹 Clean Dataset"):
        duplicates_query = """
        SELECT TRIM(LOWER(first_name)) as clean_first, 
               TRIM(LOWER(last_name)) as clean_last, 
               COUNT(*) as count 
        FROM people 
        GROUP BY clean_first, clean_last 
        HAVING count > 1
        """
        dupes = pd.read_sql(duplicates_query, conn)
        
        if dupes.empty:
            st.info("No duplicates found.")
        else:
            for _, row in dupes.iterrows():
                ids_df = pd.read_sql(
                    """SELECT id FROM people 
                       WHERE TRIM(LOWER(first_name)) = ? 
                       AND TRIM(LOWER(last_name)) = ? 
                       ORDER BY id ASC""", 
                    conn, params=(row['clean_first'], row['clean_last'])
                )
                
                ids = ids_df['id'].tolist()
                primary_id = ids[0]
                duplicate_ids = ids[1:]
                
                for dup_id in duplicate_ids:
                    conn.execute("UPDATE encounters SET person_id = ? WHERE person_id = ?", (int(primary_id), int(dup_id)))
                    conn.execute("UPDATE OR IGNORE person_tags SET person_id = ? WHERE person_id = ?", (int(primary_id), int(dup_id)))
                    conn.execute("DELETE FROM people WHERE id = ?", (int(dup_id),))
                    conn.execute("DELETE FROM person_tags WHERE person_id = ?", (int(dup_id),))

                conn.execute(f"""
                    DELETE FROM encounters 
                    WHERE person_id = {primary_id} 
                    AND id NOT IN (
                        SELECT id FROM (
                            SELECT id, MAX(intensity) 
                            FROM encounters 
                            WHERE person_id = {primary_id} 
                            GROUP BY date
                        )
                    )
                """)
            
            conn.commit()
            recalculate_all(conn)
            st.success(f"Merged {len(dupes)} sets of duplicates!")
            st.rerun()