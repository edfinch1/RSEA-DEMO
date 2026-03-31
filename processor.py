"""
RSEA Supplier Catalog — Extraction Processor (Hardened v2)
"""

import os
import io
import time
import pdfplumber
import instructor
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError
from schema import (
    SupplierCatalog,
    ProductItem,
    DocumentClassification,
    DocumentType,
)
from typing import List, Optional, Tuple


# ── Constants ─────────────────────────────────────────────────────────────────

MAX_CHARS_PER_CHUNK = 12_000  # ~3k tokens — safe for GPT-4o context window
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2
MAX_PAGES = 50  # Safety cap — reject absurdly large PDFs


# ── System Prompts ────────────────────────────────────────────────────────────

CLASSIFY_PROMPT = """You are a document classification agent for RSEA Safety, 
Australia's largest safety equipment retailer.

Your job is to quickly classify an uploaded document so we know how to process it.

Classification rules:
- "supplier_catalog": Contains a LIST of products with PRICES (price lists, catalogs, quotes)
- "invoice": A billing document for specific orders
- "technical_manual": Instruction manuals, spec sheets, engineering docs WITHOUT pricing
- "compliance_report": Safety certifications, audit reports, test results
- "general_document": Anything else (letters, contracts, memos)

Be generous with "supplier_catalog" — if the document has ANY product-price data, 
classify it as a catalog. We'd rather extract something than reject a valid document.

Set is_extractable = true if there are product items with prices we can extract.
"""

EXTRACT_PROMPT = """You are an expert data extraction agent for RSEA Safety, 
Australia's largest safety equipment retailer.

Your job is to extract EVERY product line item from a supplier document.

EXTRACTION RULES:
1. Extract ALL items — do not skip rows even if formatting is messy or columns 
   dont align properly.
2. Prices are in AUD unless stated otherwise. Strip dollar signs ($), commas, 
   and 'ex GST' / 'inc GST' annotations. Return the raw numeric price.
3. If a SKU/part number is not visible, return an empty string — NEVER invent one.
4. Infer the category from section headings, groupings, or product descriptions.
5. If the supplier name appears (header, footer, watermark), capture it.
6. Handle multi-page documents — every page matters.
7. For compliance certifications (AS/NZS, CE, ISO, EN standards), capture them 
   in the compliance_certs field.
8. Set your confidence (0.0–1.0) for each item:
   - 0.9+ = clearly readable, unambiguous data
   - 0.7–0.9 = readable but some inference needed
   - 0.5–0.7 = partially readable, significant inference
   - <0.5 = guessing — flag for human review
9. Look for GST indicators. If the document says "all prices ex-GST" or similar,
   set gst_note on the catalog and gst_inclusive=false on items.
10. If you see unit-of-measure info (each, pair, box, carton), capture it.

IMPORTANT: It is better to extract a row with low confidence than to skip it.
The human reviewer will catch errors — but they can't review what you don't extract.
"""


# ── Client Setup ──────────────────────────────────────────────────────────────

def _get_client() -> instructor.Instructor:
    """
    Create an instructor-wrapped OpenAI client.
    Raises a clear error if the API key is missing.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. "
            "Add it to your .env or Railway environment variables."
        )
    return instructor.from_openai(OpenAI(api_key=api_key))


# ── PDF Text Extraction ──────────────────────────────────────────────────────

def extract_text_from_pdf(pdf_file) -> str:
    """
    Read all text from a PDF using pdfplumber.
    Accepts a Streamlit UploadedFile or any file-like object.
    """
    text_pages: List[str] = []

    if hasattr(pdf_file, "seek"):
        pdf_file.seek(0)

    pdf_bytes = pdf_file.read()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if len(pdf.pages) > MAX_PAGES:
            raise ValueError(
                f"This PDF has {len(pdf.pages)} pages (max {MAX_PAGES}). "
                "Please upload a smaller document or a specific section."
            )

        for i, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                text_pages.append(f"--- Page {i} ---\n{page_text}")

    if not text_pages:
        raise ValueError(
            "Could not extract any text from this PDF. "
            "The file may be scanned/image-only. "
            "Try a PDF that contains selectable text."
        )

    return "\n\n".join(text_pages)


# ── Text Chunking ─────────────────────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> List[str]:
    """
    Split large documents into chunks that fit comfortably in GPT-4o's
    context window.  Splits on page boundaries ('--- Page') to avoid
    cutting rows in half.
    """
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    current_chunk = ""

    # Split on page markers
    pages = text.split("--- Page ")
    for page in pages:
        if not page.strip():
            continue

        page_with_marker = f"--- Page {page}"

        if len(current_chunk) + len(page_with_marker) > max_chars and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = ""

        current_chunk += page_with_marker

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks if chunks else [text]


# ── API Call with Retry ───────────────────────────────────────────────────────

def _api_call_with_retry(client, messages, response_model, system_prompt, max_retries=MAX_RETRIES):
    """
    Wraps the instructor API call with retry logic for rate limits,
    timeouts, and connection errors.  Prevents demo crashes.
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            result = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=4096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages,
                ],
                response_model=response_model,
            )
            return result

        except RateLimitError as e:
            last_error = e
            wait = RETRY_DELAY_SECONDS * attempt
            time.sleep(wait)

        except (APITimeoutError, APIConnectionError) as e:
            last_error = e
            wait = RETRY_DELAY_SECONDS * attempt
            time.sleep(wait)

        except Exception as e:
            # For unexpected errors, don't retry — surface immediately
            raise RuntimeError(
                f"API call failed: {type(e).__name__}: {e}"
            ) from e

    raise RuntimeError(
        f"API call failed after {max_retries} retries. "
        f"Last error: {type(last_error).__name__}: {last_error}"
    )


# ── Document Classification ──────────────────────────────────────────────────

def classify_document(text: str) -> DocumentClassification:
    """
    Quick, cheap classification pass.
    Uses only the first ~2000 chars to minimise tokens.
    """
    client = _get_client()

    # Only send a preview — classification doesn't need the full document
    preview = text[:2000]
    if len(text) > 2000:
        # Also grab a snippet from the middle for better classification
        mid = len(text) // 2
        preview += "\n\n[... middle of document ...]\n\n" + text[mid:mid + 1000]

    classification = _api_call_with_retry(
        client=client,
        messages=[
            {
                "role": "user",
                "content": (
                    "Classify this document and determine if it contains "
                    "extractable product/pricing data.\n\n"
                    f"{preview}"
                ),
            }
        ],
        response_model=DocumentClassification,
        system_prompt=CLASSIFY_PROMPT,
    )

    return classification


# ── Validation ────────────────────────────────────────────────────────────────

def validate_catalog(catalog: SupplierCatalog) -> SupplierCatalog:
    """
    Post-extraction validation.
    Flags items with suspicious data.
    """
    for item in catalog.items:
        flags: List[str] = []

        # Price validation
        if item.price <= 0:
            flags.append("Data Error: Price is $0 or negative")
        elif item.price > 50_000:
            flags.append("Review: Unusually high price")

        # SKU validation
        if not item.sku or item.sku.strip() == "":
            flags.append("Missing SKU")

        # Name validation
        if not item.name or item.name.strip() == "":
            flags.append("Missing product name")

        # Confidence validation
        if item.confidence is not None and item.confidence < 0.5:
            flags.append("Low AI confidence")

        if flags:
            item.flag = " | ".join(flags)

    return catalog


# ── Main Extraction Pipeline ─────────────────────────────────────────────────

def extract_catalog_data(
    pdf_file,
    skip_classification: bool = False,
) -> Tuple[DocumentClassification, Optional[SupplierCatalog]]:
    """
    End-to-end pipeline:
    1. Extract text from PDF
    2. Classify the document (catch non-catalogs early)
    3. Chunk large documents
    4. Send each chunk to GPT-4o for structured extraction
    5. Merge chunk results
    6. Validate

    Returns (classification, catalog_or_none).
    If the document isn't extractable, catalog will be None.
    """
    # ── Step 1: Get raw text ──────────────────────────────────────────────
    raw_text = extract_text_from_pdf(pdf_file)

    # ── Step 2: Classify ──────────────────────────────────────────────────
    classification = classify_document(raw_text)

    if not classification.is_extractable and not skip_classification:
        # Document isn't a catalog — return early with no catalog
        return classification, None

    # ── Step 3: Chunk text for large documents ────────────────────────────
    chunks = chunk_text(raw_text)
    client = _get_client()

    # ── Step 4: Extract from each chunk ───────────────────────────────────
    all_items: List[ProductItem] = []
    supplier_name = "Unknown Supplier"
    document_date = None
    currency = "AUD"
    gst_note = None

    for i, chunk in enumerate(chunks):
        chunk_label = f"(chunk {i + 1}/{len(chunks)})" if len(chunks) > 1 else ""

        catalog_chunk = _api_call_with_retry(
            client=client,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Extract all product items from this supplier document "
                        f"{chunk_label}.\n\n{chunk}"
                    ),
                }
            ],
            response_model=SupplierCatalog,
            system_prompt=EXTRACT_PROMPT,
        )

        all_items.extend(catalog_chunk.items)

        # Keep the best metadata from any chunk
        if catalog_chunk.supplier_name != "Unknown Supplier":
            supplier_name = catalog_chunk.supplier_name
        if catalog_chunk.document_date:
            document_date = catalog_chunk.document_date
        if catalog_chunk.currency != "AUD":
            currency = catalog_chunk.currency
        if catalog_chunk.gst_note:
            gst_note = catalog_chunk.gst_note

        # Rate limit courtesy between chunks
        if i < len(chunks) - 1:
            time.sleep(0.5)

    # ── Step 5: Merge into a single catalog ───────────────────────────────
    merged_catalog = SupplierCatalog(
        supplier_name=supplier_name,
        document_date=document_date,
        currency=currency,
        gst_note=gst_note,
        items=all_items,
    )

    # ── Step 6: Validate ──────────────────────────────────────────────────
    merged_catalog = validate_catalog(merged_catalog)

    return classification, merged_catalog
