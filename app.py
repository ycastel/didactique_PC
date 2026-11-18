import streamlit as st
import requests

st.title("Test Diagnostic Mistral")
txt = st.text_area("Consigne :", "Justifier la présence d'ions chlorure.")

if st.button("Tester"):
    st.write("1. Bouton cliqué !")
    cle = st.secrets["MISTRAL_API_KEY"].strip()
    st.write("2. Clé lue (début) :", cle[:4] + "...")
    url = "https://" + "api.mistral.ai" + "/v1/chat/completions"
    headers = {"Authorization": "Bearer " + cle, "Content-Type": "application/json"}
    body = {"model": "mistral-small-latest", "messages": [{"role": "user", "content": "Explique les implicites de : " + txt}]}
    rep = requests.post(url, headers=headers, json=body)
    st.write("3. Code réponse :", rep.status_code)
    st.write(rep.text)
