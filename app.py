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

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def extract_claims(text, api_key):
    genai.configure(api_key=api_key)
    
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
    
    # Try modern models first
    for model_name in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            res_text = response.text.strip()
            # Clean up potential markdown formatting
            if res_text.startswith("```json"):
                res_text = res_text[7:]
            if res_text.startswith("```"):
                res_text = res_text[3:]
            if res_text.endswith("```"):
                res_text = res_text[:-3]
                
            claims = json.loads(res_text.strip())
            return claims
        except Exception as e:
            continue # Try next model
            
    st.error("The Gemini API is currently unavailable or your key is still activating. Please wait 1 minute and try again.")
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
    
    # Try multiple models in case of 404 errors
    for model_name in ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]:
        try:
            model = genai.GenerativeModel(model_name)
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
        except Exception:
            continue
            
    return {"status": "Error", "explanation": "No compatible Gemini model found.", "real_fact": "N/A"}


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
                    
                    st.markdown("### 📊 Fact-Check Summary")
                    col1, col2, col3, col4 = st.columns(4)
                    metric_total = col1.empty()
                    metric_verified = col2.empty()
                    metric_inaccurate = col3.empty()
                    metric_false = col4.empty()
                    
                    metric_total.metric("Total Claims", len(claims))
                    metric_verified.metric("✅ Verified", 0)
                    metric_inaccurate.metric("⚠️ Inaccurate", 0)
                    metric_false.metric("❌ False", 0)
                    
                    v_count = 0
                    i_count = 0
                    f_count = 0
                    
                    st.markdown("### 🔍 Detailed Analysis")
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
                                v_count += 1
                                metric_verified.metric("✅ Verified", v_count)
                            elif status_val == "Inaccurate":
                                st.warning(f"⚠️ Status: {status_val}")
                                status.update(label=f"⚠️ {claim[:50]}...", state="complete")
                                i_count += 1
                                metric_inaccurate.metric("⚠️ Inaccurate", i_count)
                            elif status_val == "False":
                                st.error(f"❌ Status: {status_val}")
                                status.update(label=f"❌ {claim[:50]}...", state="complete")
                                f_count += 1
                                metric_false.metric("❌ False", f_count)
                            else:
                                st.info(f"❓ Status: {status_val}")
                                status.update(label=f"❓ {claim[:50]}...", state="complete")
                                
                            st.write(f"**Explanation:** {verification.get('explanation', 'N/A')}")
                            st.write(f"**The Real Fact:** {verification.get('real_fact', 'N/A')}")
