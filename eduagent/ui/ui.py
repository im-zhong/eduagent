# streamlit_app.py
import streamlit as st
import requests

st.title("Hello FastAPI via Streamlit")

# API URL (adjust host/port if running in Docker)
api_url = "http://eduagent-api:8000/hello"

if st.button("Say Hello"):
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            st.success(data)
        else:
            st.error(f"API returned status {response.status_code}")
    except Exception as e:
        st.error(f"Error calling API: {e}")
