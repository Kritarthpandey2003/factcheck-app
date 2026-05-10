import streamlit as st
import PyPDF2
import requests
from duckduckgo_search import DDGS
import json
import os
import time

st.set_page_config(page_title="Fact-Check Agent", page_icon="🔍", layout="wide")

st.title("🔍 Automated Fact-Checking Agent")
st.markdown("Upload a document, and this AI agent will extract claims, search the web, and verify accuracy.")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Enter your Google Gemini API Key:", type="password")
    st.markdown("[Get an API key here](https://aistudio.google.com/app/apikey)")
    if st.button("📋 List My Available Models"):
        if api_key:
            r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key.strip()}")
            if r.status_code == 200:
                models = [m['name'] for m in r.json().get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
                st.success("Your models:")
                for m in models:
                    st.code(m)
            else:
                st.error(f"Error: {r.text}")
        else:
            st.warning("Enter API key first!")

def call_gemini_api(prompt, api_key):
    api_key = api_key.strip()
    last_res = "No models reached."
    for version in ["v1beta", "v1"]:
        for model in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
            url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={api_key}"
            headers = {'Content-Type': 'application/json'}
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    res_json = response.json()
                    res_text = res_json['candidates'][0]['content']['parts'][0]['text']
                    if "```json" in res_text: res_text = res_text.split("```json")[1].split("```")[0]
                    elif "```" in res_text: res_text = res_text.split("```")[1].split("```")[0]
                    return res_text.strip()
                else:
                    last_res = f"Error {response.status_code}: {response.text}"
                    time.sleep(1)
            except Exception as e:
                last_res = str(e)
                time.sleep(1)
                continue
    st.session_state['last_error'] = last_res
    return None

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text(): text += page.extract_text() + "\n"
    return text

def extract_claims(text, api_key):
    prompt = f"Extract verifiable claims from this text as a JSON array of strings: {text}"
    res_text = call_gemini_api(prompt, api_key)
    if res_text:
        try: return json.loads(res_text)
        except: return []
    return []

def search_web(query):
    results_text = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            for res in results: results_text += f"Snippet: {res['body']}\n\n"
    except: results_text = "No results."
    return results_text

def verify_claim(claim, api_key):
    search_context = search_web(claim)
    prompt = f"Verify claim: {claim}\nContext: {search_context}\nReturn JSON: {{\"status\": \"Verified/Inaccurate/False\", \"explanation\": \"...\", \"real_fact\": \"...\"}}"
    res_text = call_gemini_api(prompt, api_key)
    if res_text:
        try: return json.loads(res_text)
        except: pass
    return {"status": "Error", "explanation": "API response error", "real_fact": "N/A"}

uploaded_file = st.file_uploader("Upload a PDF document to verify", type=["pdf"])

if uploaded_file is not None:
    if not api_key:
        st.warning("⚠️ Please enter your Gemini API Key in the sidebar.")
    else:
        if st.button("Start Fact-Checking", type="primary"):
            doc_text = extract_text_from_pdf(uploaded_file)
            claims = extract_claims(doc_text, api_key)
            if not claims:
                st.info("Still searching for a compatible model... please wait 10 seconds and try one more time.")
                if 'last_error' in st.session_state:
                    st.error(f"Last Error: {st.session_state['last_error']}")
            else:
                st.success(f"Connection Successful! Verifying {len(claims)} claims...")
                col1, col2, col3, col4 = st.columns(4)
                m_total = col1.empty(); m_v = col2.empty(); m_i = col3.empty(); m_f = col4.empty()
                m_total.metric("Total", len(claims)); m_v.metric("✅ Verified", 0); m_i.metric("⚠️ Inaccurate", 0); m_f.metric("❌ False", 0)
                v_c, i_c, f_c = 0, 0, 0
                for i, claim in enumerate(claims):
                    with st.status(f"Verifying {i+1}...", expanded=False) as status:
                        res = verify_claim(claim, api_key)
                        s = res.get("status", "Error")
                        if s == "Verified": v_c += 1; m_v.metric("✅ Verified", v_c); st.success("✅ Verified")
                        elif s == "Inaccurate": i_c += 1; m_i.metric("⚠️ Inaccurate", i_c); st.warning("⚠️ Inaccurate")
                        elif s == "False": f_c += 1; m_f.metric("❌ False", f_c); st.error("❌ False")
                        st.write(f"**Claim:** {claim}"); st.write(f"**Explanation:** {res.get('explanation')}"); st.write(f"**Real Fact:** {res.get('real_fact')}")
                        status.update(label=f"Done: {claim[:30]}...", state="complete")
