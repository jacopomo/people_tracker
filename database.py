import streamlit as st
from supabase import create_client
import pandas as pd

# Connect using your secrets
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(URL, KEY)

def get_db():
    """Returns the supabase client for use in other files"""
    return supabase