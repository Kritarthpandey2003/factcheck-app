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
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY") # Fallback to environment variable

def get_model_name():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models:
            if 'flash' in m.lower():
                return m
        for m in models:
            if 'pro' in m.lower():
                return m
        return models[0] if models else 'gemini-pro'
    except Exception:
        return 'gemini-pro'

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def extract_claims(text, api_key):
    genai.configure(api_key=api_key)
    model_name = get_model_name()
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    You are an expert fact-checker. Read the following text and extract all specific, verifiable claims.
    Focus on:
    1. Statistics and percentages
    2. Dates and historical events
    3. Financial and technical figures
    
    Return the output EXACTLY as a valid JSON array of strings. Do not include any markdown formatting or code blocks.
    Example: ["Claim 1", "Claim 2"]
    
    Text:
    {text}
    """
    try:
        response = model.generate_content(prompt)
        # Clean up potential markdown formatting
        res_text = response.text.strip()
        if res_text.startswith("```json"):
            res_text = res_text[7:]
        if res_text.startswith("```"):
            res_text = res_text[3:]
        if res_text.endswith("```"):
            res_text = res_text[:-3]
            
        claims = json.loads(res_text.strip())
        return claims
    except Exception as e:
        st.error(f"Error extracting claims: {e}")
        return []

def search_web(query):
    results_text = ""
    try:
        with DDGS() as ddgs:
            # Get top 3 results
            results = list(ddgs.text(query, max_results=3))
            for res in results:
                results_text += f"Source: {res['title']}\nSnippet: {res['body']}\n\n"
    except Exception as e:
        results_text = "Could not fetch live search results."
    return results_text

def verify_claim(claim, api_key):
    # Search the web based on the claim
    search_context = search_web(claim)
    
    genai.configure(api_key=api_key)
    model_name = get_model_name()
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    You are an expert fact-checker. 
    Evaluate the following claim based ONLY on the provided search results from the live web.
    
    Claim to verify: "{claim}"
    
    Web Search Results:
    {search_context}
    
    You must classify the claim into exactly one of these categories:
    - Verified (Matches data found)
    - Inaccurate (Matches partially, but outdated or slightly wrong)
    - False (Contradicts data found or no evidence exists)
    
    Return the result EXACTLY as a JSON object with three keys:
    "status": "Verified" or "Inaccurate" or "False",
    "explanation": "A short explanation of why",
    "real_fact": "The actual truth based on the search results"
    
    Do not include markdown code blocks.
    """
    
    try:
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if res_text.startswith("```json"):
            res_text = res_text[7:]
        if res_text.startswith("```"):
            res_text = res_text[3:]
        if res_text.endswith("```"):
            res_text = res_text[:-3]
            
        verification = json.loads(res_text.strip())
        return verification
    except Exception as e:
        return {"status": "Error", "explanation": str(e), "real_fact": "N/A"}


uploaded_file = st.file_uploader("Upload a PDF document to verify", type=["pdf"])

if uploaded_file is not None:
    if not api_key:
        st.warning("⚠️ Please enter your Gemini API Key in the sidebar to proceed.")
    else:
        if st.button("Start Fact-Checking", type="primary"):
            with st.spinner("Extracting text from PDF..."):
                doc_text = extract_text_from_pdf(uploaded_file)
            
            if not doc_text.strip():
                st.error("Could not extract any text from the uploaded PDF.")
            else:
                with st.spinner("Analyzing text and extracting claims via Gemini..."):
                    claims = extract_claims(doc_text, api_key)
                
                if not claims:
                    st.info("No verifiable claims (stats, dates, figures) were found in this document.")
                else:
                    st.success(f"Extracted {len(claims)} verifiable claims. Starting live web verification...")
                    
                    # Display results in an expander for each claim
                    for i, claim in enumerate(claims):
                        with st.status(f"Verifying Claim {i+1}: {claim[:50]}...", expanded=False) as status:
                            st.write(f"**Original Claim:** {claim}")
                            st.write("🔍 Searching the live web...")
                            
                            # Add a small sleep to avoid rate limits on DuckDuckGo
                            time.sleep(1) 
                            
                            verification = verify_claim(claim, api_key)
                            
                            status_val = verification.get("status", "Error")
                            if status_val == "Verified":
                                st.success(f"✅ Status: {status_val}")
                                status.update(label=f"✅ {claim[:50]}...", state="complete")
                            elif status_val == "Inaccurate":
                                st.warning(f"⚠️ Status: {status_val}")
                                status.update(label=f"⚠️ {claim[:50]}...", state="complete")
                            elif status_val == "False":
                                st.error(f"❌ Status: {status_val}")
                                status.update(label=f"❌ {claim[:50]}...", state="complete")
                            else:
                                st.info(f"❓ Status: {status_val}")
                                status.update(label=f"❓ {claim[:50]}...", state="complete")
                                
                            st.write(f"**Explanation:** {verification.get('explanation', 'N/A')}")
                            st.write(f"**The Real Fact:** {verification.get('real_fact', 'N/A')}")
