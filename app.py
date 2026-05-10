import streamlit as st
import PyPDF2
import google.generativeai as genai
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
    selected_model = st.selectbox("Select Gemini Model (Try 'gemini-1.5-flash' first):", 
                                ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro", "gemini-1.0-pro"])
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    
    if st.button("🔍 Debug: List Available Models"):
        if not api_key:
            st.error("Please enter an API key first.")
        else:
            try:
                genai.configure(api_key=api_key.strip(), transport='rest')
                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                st.write("Your available models:")
                st.write(models)
            except Exception as e:
                st.error(f"Error listing models: {e}")

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def extract_claims(text, api_key):
    api_key = api_key.strip()
    genai.configure(api_key=api_key, transport='rest')
    
    prompt = f"""
    You are an expert fact-checker. Read the following text and extract all specific, verifiable claims.
    Focus on: 1. Statistics 2. Dates 3. Financial figures.
    Return output EXACTLY as a valid JSON array of strings.
    Text: {text}
    """
    try:
        model = genai.GenerativeModel(selected_model)
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if "```json" in res_text: res_text = res_text.split("```json")[1].split("```")[0]
        elif "```" in res_text: res_text = res_text.split("```")[1].split("```")[0]
        return json.loads(res_text.strip())
    except Exception as e:
        st.error(f"Error during claim extraction: {e}")
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
    api_key = api_key.strip()
    genai.configure(api_key=api_key, transport='rest')
    
    prompt = f"""
    Verify this claim based ONLY on these search results: "{claim}"
    Results: {search_context}
    Return JSON: {{"status": "Verified/Inaccurate/False", "explanation": "...", "real_fact": "..."}}
    """
    try:
        model = genai.GenerativeModel(selected_model)
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if "```json" in res_text: res_text = res_text.split("```json")[1].split("```")[0]
        elif "```" in res_text: res_text = res_text.split("```")[1].split("```")[0]
        return json.loads(res_text.strip())
    except Exception as e:
        return {"status": "Error", "explanation": str(e), "real_fact": "N/A"}

uploaded_file = st.file_uploader("Upload a PDF document to verify", type=["pdf"])

if uploaded_file is not None:
    if not api_key:
        st.warning("⚠️ Please enter your Gemini API Key in the sidebar.")
    else:
        if st.button("Start Fact-Checking", type="primary"):
            doc_text = extract_text_from_pdf(uploaded_file)
            if not doc_text.strip():
                st.error("Could not extract text.")
            else:
                claims = extract_claims(doc_text, api_key)
                if not claims:
                    st.info("No claims found or API error.")
                else:
                    st.success(f"Extracted {len(claims)} claims. Verifying...")
                    st.markdown("### 📊 Fact-Check Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    m_total = col1.empty(); m_v = col2.empty(); m_i = col3.empty(); m_f = col4.empty()
                    m_total.metric("Total", len(claims)); m_v.metric("✅ Verified", 0); m_i.metric("⚠️ Inaccurate", 0); m_f.metric("❌ False", 0)
                    v_c = 0; i_c = 0; f_c = 0
                    st.markdown("### 🔍 Detailed Analysis")
                    for i, claim in enumerate(claims):
                        with st.status(f"Verifying {i+1}...", expanded=False) as status:
                            st.write(f"**Claim:** {claim}")
                            time.sleep(1)
                            res = verify_claim(claim, api_key)
                            s = res.get("status", "Error")
                            if s == "Verified": v_c += 1; m_v.metric("✅ Verified", v_c); st.success("✅ Verified")
                            elif s == "Inaccurate": i_c += 1; m_i.metric("⚠️ Inaccurate", i_c); st.warning("⚠️ Inaccurate")
                            elif s == "False": f_c += 1; m_f.metric("❌ False", f_c); st.error("❌ False")
                            st.write(f"**Explanation:** {res.get('explanation')}")
                            st.write(f"**Real Fact:** {res.get('real_fact')}")
                            status.update(label=f"Done: {claim[:30]}...", state="complete")
