# streamlit_app.py
from http import HTTPStatus

import requests
import streamlit as st

st.title("Hello FastAPI via Streamlit")

# API URL (adjust host/port if running in Docker)
api_url = "http://api.eduagent:8000/hello"

if st.button("Say Hello"):
    try:
        response = requests.get(api_url)
        if response.status_code == HTTPStatus.OK:
            data = response.json()
            st.success(data)
        else:
            st.error(f"API returned status {response.status_code}")
    except Exception as e:
        st.error(f"Error calling API: {e}")
