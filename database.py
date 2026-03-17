import streamlit as st
from supabase import create_client

URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)