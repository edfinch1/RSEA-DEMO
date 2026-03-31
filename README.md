# 🛡️ RSEA Supplier Catalog Extractor — MVP

AI-powered extraction of product data from messy supplier PDF price lists.  
Built for [RSEA Safety](https://www.rsea.com.au/) as a proof-of-concept.

## Stack
- **Frontend:** Streamlit
- **AI Engine:** GPT-4o via `instructor`
- **PDF Parsing:** pdfplumber
- **Hosting:** Railway

## Setup
1. `pip install -r requirements.txt`
2. `export OPENAI_API_KEY="your-key"`
3. `streamlit run app.py`
