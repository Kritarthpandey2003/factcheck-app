import streamlit as st
import PyPDF2
import requests
from duckduckgo_search import DDGS
import time
import json
import os

st.set_page_config(page_title="Fact-Check Agent", page_icon="🔍", layout="wide")

st.title("🔍 Automated Fact-Checking Agent")
st.markdown("Upload a document, and this AI agent will extract claims (stats, dates, figures), search the live web, and verify their accuracy.")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Enter your Google Gemini API Key:", type="password")
    st.markdown("[Get an API key here](https://aistudio.google.com/app/apikey)")
    selected_model = st.selectbox("Select Model:", ["gemini-1.5-flash", "gemini-1.5-pro"])

def call_gemini_api(prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1/models/{selected_model}:generateContent?key={api_key.strip()}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        res_json = response.json()
        try:
            res_text = res_json['candidates'][0]['content']['parts'][0]['text']
            # Clean JSON
            if "```json" in res_text: res_text = res_text.split("```json")[1].split("```")[0]
            elif "```" in res_text: res_text = res_text.split("```")[1].split("```")[0]
            return res_text.strip()
        except:
            return None
    else:
        st.error(f"API Error {response.status_code}: {response.text}")
        return None

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def extract_claims(text, api_key):
    prompt = f"""
    Extract specific, verifiable claims from this text as a JSON array of strings. 
    Focus on stats, dates, and figures.
    Text: {text}
    """
    res_text = call_gemini_api(prompt, api_key)
    if res_text:
        try:
            return json.loads(res_text)
        except:
            return []
    return []

def search_web(query):
    results_text = ""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            for res in results:
                results_text += f"Source: {res['title']}\nSnippet: {res['body']}\n\n"
    except:
        results_text = "Could not fetch live search results."
    return results_text

def verify_claim(claim, api_key):
    search_context = search_web(claim)
    prompt = f"""
    Verify this claim based ONLY on these search results: "{claim}"
    Results: {search_context}
    Return JSON: {{"status": "Verified/Inaccurate/False", "explanation": "...", "real_fact": "..."}}
    """
    res_text = call_gemini_api(prompt, api_key)
    if res_text:
        try:
            return json.loads(res_text)
        except:
            pass
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
                st.info("No claims found or API error. Try waiting 60s.")
            else:
                st.success(f"Extracted {len(claims)} claims. Verifying...")
                st.markdown("### 📊 Fact-Check Summary")
                col1, col2, col3, col4 = st.columns(4)
                m_total = col1.empty(); m_v = col2.empty(); m_i = col3.empty(); m_f = col4.empty()
                m_total.metric("Total", len(claims)); m_v.metric("✅ Verified", 0); m_i.metric("⚠️ Inaccurate", 0); m_f.metric("❌ False", 0)
                v_c = 0; i_c = 0; f_c = 0
                for i, claim in enumerate(claims):
                    with st.status(f"Verifying {i+1}...", expanded=False) as status:
                        res = verify_claim(claim, api_key)
                        s = res.get("status", "Error")
                        if s == "Verified": v_c += 1; m_v.metric("✅ Verified", v_c); st.success("✅ Verified")
                        elif s == "Inaccurate": i_c += 1; m_i.metric("⚠️ Inaccurate", i_c); st.warning("⚠️ Inaccurate")
                        elif s == "False": f_c += 1; m_f.metric("❌ False", f_c); st.error("❌ False")
                        st.write(f"**Claim:** {claim}")
                        st.write(f"**Explanation:** {res.get('explanation')}")
                        st.write(f"**Real Fact:** {res.get('real_fact')}")
                        status.update(label=f"Done: {claim[:30]}...", state="complete")
