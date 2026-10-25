
import streamlit as st
import openai
from openai import OpenAI

print("OpenAI SDK version:", openai.__version__)

try:
    api_key = st.secrets["OPENAI_API_KEY"]
    print("API key loaded:", bool(api_key))

    client = OpenAI(
        api_key=api_key,
        timeout=20,
        max_retries=0
    )

    response = client.models.list()
    print("Connection successful!")
    print("Models returned:", len(response.data))

except Exception as e:
    print("Error type:", type(e).__name__)
    print("Error details:", repr(e))
    print("Underlying cause:", repr(e.__cause__))

    if e.__cause__:
        print("Cause type:", type(e.__cause__).__name__)
