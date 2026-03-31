"""
RSEA Supplier Catalog — Streamlit Demo (Hardened v2)
"""

import streamlit as st
import pandas as pd
from processor import extract_catalog_data
from schema import DocumentType

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RSEA · Supplier Catalog Extractor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom Styles ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Header bar */
    .rsea-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .rsea-header h1 {
        color: #ffffff;
        margin: 0;
        font-size: 1.6rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .rsea-header .badge {
        background: rgba(0, 200, 150, 0.15);
        color: #00c896;
        padding: 0.35rem 0.85rem;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        border: 1px solid rgba(0, 200, 150, 0.3);
    }

    /* Stat cards */
    .stat-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fc 100%);
        border: 1px solid #e8ecf1;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .stat-card .number {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        line-height: 1.1;
    }
    .stat-card .label {
        font-size: 0.78rem;
        color: #6c7a8d;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 0.3rem;
    }

    /* Classification banner */
    .classify-banner {
        border-radius: 10px;
        padding: 1rem 1.4rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }
    .classify-banner.catalog {
        background: linear-gradient(135deg, #e8fdf5 0%, #f0fdf4 100%);
        border: 1px solid #86efac;
    }
    .classify-banner.non-catalog {
        background: linear-gradient(135deg, #fef3c7 0%, #fffbeb 100%);
        border: 1px solid #fcd34d;
    }
    .classify-banner .icon { font-size: 1.5rem; }
    .classify-banner .text { flex: 1; }
    .classify-banner .text strong { display: block; margin-bottom: 0.15rem; }
    .classify-banner .text small { color: #6c7a8d; }
    .classify-confidence {
        font-size: 0.85rem;
        font-weight: 600;
        padding: 0.25rem 0.7rem;
        border-radius: 16px;
        white-space: nowrap;
    }
    .confidence-high { background: #dcfce7; color: #166534; }
    .confidence-med  { background: #fef9c3; color: #854d0e; }
    .confidence-low  { background: #fee2e2; color: #991b1b; }

    /* Flag rows */
    .flag-row {
        background: #fff8f0;
        border-left: 4px solid #ff9f43;
        padding: 0.7rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.5rem;
        font-size: 0.88rem;
    }
    .flag-row.error {
        background: #fff0f0;
        border-left-color: #ff6b6b;
    }
    .flag-row.low-confidence {
        background: #fef3c7;
        border-left-color: #f59e0b;
    }

    /* Upload zone */
    [data-testid="stFileUploader"] {
        border: 2px dashed #cbd5e1;
        border-radius: 12px;
        padding: 1rem;
        transition: border-color 0.2s;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: #0f3460;
    }

    /* Success box */
    .success-box {
        background: linear-gradient(135deg, #e8fdf5 0%, #f0fdf4 100%);
        border: 1px solid #86efac;
        border-radius: 10px;
        padding: 1rem 1.4rem;
        margin-bottom: 1rem;
    }

    /* Metadata pills */
    .meta-pills {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }
    .meta-pill {
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 0.3rem 0.8rem;
        font-size: 0.8rem;
        color: #475569;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="rsea-header">
        <h1>🛡️ &nbsp;RSEA · Supplier Catalog Extractor</h1>
        <span class="badge">AI-Powered · Demo v2</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "Upload any supplier document — the AI will classify it, extract product data "
    "into a validated table, and flag anything that needs review."
)

# ── File Upload ───────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "📄  Drop a Supplier Document (PDF)",
    type=["pdf"],
    help="Accepts any PDF — catalogs, price lists, or even technical manuals. The AI will tell you what it found.",
)

if uploaded_file is not None:

    # ── Processing ────────────────────────────────────────────────────────
    with st.spinner("🔍  Step 1/2: Classifying document…"):
        try:
            classification, catalog = extract_catalog_data(uploaded_file)
        except ValueError as e:
            st.error(f"📄  **PDF Error:** {e}")
            st.stop()
        except EnvironmentError as e:
            st.error(f"🔑  **Config Error:** {e}")
            st.stop()
        except RuntimeError as e:
            st.error(f"🌐  **API Error:** {e}")
            st.info("💡 This usually means the API is rate-limited or temporarily unavailable. Try again in a few seconds.")
            st.stop()
        except Exception as e:
            st.error(f"❌  **Unexpected Error:** {type(e).__name__}: {e}")
            st.stop()

    # ── Classification Banner ─────────────────────────────────────────────
    doc_type_labels = {
        DocumentType.SUPPLIER_CATALOG: ("📦", "Supplier Catalog"),
        DocumentType.TECHNICAL_MANUAL: ("📘", "Technical Manual"),
        DocumentType.INVOICE: ("🧾", "Invoice"),
        DocumentType.COMPLIANCE_REPORT: ("✅", "Compliance Report"),
        DocumentType.GENERAL_DOCUMENT: ("📄", "General Document"),
        DocumentType.UNKNOWN: ("❓", "Unknown Document"),
    }

    icon, label = doc_type_labels.get(
        classification.doc_type, ("❓", "Unknown")
    )

    conf_class = (
        "confidence-high" if classification.confidence >= 0.8
        else "confidence-med" if classification.confidence >= 0.5
        else "confidence-low"
    )
    banner_class = "catalog" if classification.is_extractable else "non-catalog"

    st.markdown(
        f"""
        <div class="classify-banner {banner_class}">
            <span class="icon">{icon}</span>
            <div class="text">
                <strong>Detected: {label}</strong>
                <small>{classification.recommendation}</small>
            </div>
            <span class="classify-confidence {conf_class}">
                {classification.confidence:.0%} confident
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Non-extractable document ──────────────────────────────────────────
    if catalog is None:
        st.warning(
            f"**This document doesn't appear to contain extractable product/pricing data.**\n\n"
            f"*{classification.summary}*\n\n"
            f"If you believe this is a supplier catalog, you can force extraction below."
        )

        if st.button("⚡  Force Extraction Anyway", type="secondary"):
            with st.spinner("🔍  Forcing extraction…"):
                try:
                    uploaded_file.seek(0)
                    _, catalog = extract_catalog_data(
                        uploaded_file, skip_classification=True
                    )
                except Exception as e:
                    st.error(f"❌  Extraction failed: {e}")
                    st.stop()

            if catalog and catalog.items:
                st.success(f"Found {len(catalog.items)} items (forced extraction).")
            else:
                st.info("The AI couldn't find any product items in this document.")
                st.stop()
        else:
            st.stop()

    # ── Convert to DataFrame ──────────────────────────────────────────────
    if catalog and catalog.items:
        rows = []
        for item in catalog.items:
            row = {
                "SKU": item.sku or "—",
                "Product Name": item.name or "—",
                "Price (AUD)": item.price,
                "Category": item.category or "—",
                "Confidence": item.confidence,
            }

            # Bonus columns — only add if ANY item has data
            row["UOM"] = item.unit_of_measure or ""
            row["MOQ"] = item.moq if item.moq else ""
            row["Compliance"] = item.compliance_certs or ""
            row["GST Inc."] = (
                "Yes" if item.gst_inclusive is True
                else "No" if item.gst_inclusive is False
                else ""
            )
            row["Flag"] = item.flag or "✅"

            rows.append(row)

        df = pd.DataFrame(rows)

        # Drop bonus columns if all values are empty (cleaner table)
        for col in ["UOM", "MOQ", "Compliance", "GST Inc."]:
            if df[col].replace("", pd.NA).isna().all():
                df = df.drop(columns=[col])

        # ── Catalog Metadata ──────────────────────────────────────────────
        pills = []
        pills.append(f"🏢 {catalog.supplier_name}")
        pills.append(f"💰 {catalog.currency}")
        if catalog.document_date:
            pills.append(f"📅 {catalog.document_date}")
        if catalog.gst_note:
            pills.append(f"🧾 {catalog.gst_note}")

        pills_html = "".join(
            f'<span class="meta-pill">{p}</span>' for p in pills
        )
        st.markdown(f'<div class="meta-pills">{pills_html}</div>', unsafe_allow_html=True)

        # ── Stats Row ─────────────────────────────────────────────────────
        total_items = len(df)
        flagged_items = len(df[df["Flag"] != "✅"])
        avg_price = df["Price (AUD)"].mean() if total_items > 0 else 0

        # Average confidence
        conf_values = df["Confidence"].dropna()
        avg_conf = conf_values.mean() if len(conf_values) > 0 else None

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                f'<div class="stat-card"><div class="number">{total_items}</div>'
                f'<div class="label">Products</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="stat-card"><div class="number">{flagged_items}</div>'
                f'<div class="label">Flagged</div></div>',
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f'<div class="stat-card"><div class="number">${avg_price:,.2f}</div>'
                f'<div class="label">Avg Price</div></div>',
                unsafe_allow_html=True,
            )
        with col4:
            if avg_conf is not None:
                conf_pct = f"{avg_conf:.0%}"
            else:
                conf_pct = "N/A"
            st.markdown(
                f'<div class="stat-card"><div class="number">{conf_pct}</div>'
                f'<div class="label">Avg Confidence</div></div>',
                unsafe_allow_html=True,
            )

        # ── Data Table ────────────────────────────────────────────────────
        st.markdown("### 📋  Extracted Catalog")

        # Build column config dynamically
        col_config = {
            "Price (AUD)": st.column_config.NumberColumn(format="$%.2f"),
            "Flag": st.column_config.TextColumn(width="medium"),
        }
        if "Confidence" in df.columns:
            col_config["Confidence"] = st.column_config.ProgressColumn(
                min_value=0.0,
                max_value=1.0,
                format="%.0%%",
            )

        st.dataframe(
            df,
            use_container_width=True,
            height=min(420, 40 + len(df) * 35),
            column_config=col_config,
        )

        # ── Review Flags ──────────────────────────────────────────────────
        flagged_df = df[df["Flag"] != "✅"]
        if not flagged_df.empty:
            st.markdown("### ⚠️  Review Flags")
            st.caption(
                "These items need manual review before importing."
            )
            for _, row in flagged_df.iterrows():
                flag_text = row["Flag"]
                if "Data Error" in flag_text:
                    css_class = "flag-row error"
                elif "Low AI confidence" in flag_text:
                    css_class = "flag-row low-confidence"
                else:
                    css_class = "flag-row"
                st.markdown(
                    f'<div class="{css_class}">'
                    f'<strong>{row["SKU"]}</strong> · {row["Product Name"]} '
                    f'→ {flag_text}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.success("🎉  No flags — all items passed validation!")

        # ── Export CSV ────────────────────────────────────────────────────
        st.markdown("---")
        csv_data = df.to_csv(index=False).encode("utf-8")
        supplier_slug = catalog.supplier_name.replace(" ", "_").replace("/", "-")
        st.download_button(
            label="📥  Export to CSV (Inventory Upload)",
            data=csv_data,
            file_name=f"{supplier_slug}_catalog.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True,
        )

    else:
        st.info("No product items were found in this document.")

else:
    # ── Empty state ───────────────────────────────────────────────────────
    st.markdown("---")
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown("#### How it works")
        st.markdown(
            """
            1. **Upload** — Drop any supplier PDF  
            2. **Classify** — AI detects document type instantly  
            3. **Extract** — Pulls every product, even from messy layouts  
            4. **Validate** — Flags missing SKUs, bad prices, low confidence  
            5. **Export** — Download a clean CSV for your inventory system  
            """
        )
    with col_right:
        st.markdown("#### Built to handle anything")
        st.markdown(
            """
            - 📦 **Supplier catalogs** → Full extraction + validation  
            - 📘 **Technical manuals** → Gracefully detected, won't crash  
            - 🧾 **Invoices** → Identified and flagged  
            - 🔄 **Multi-page docs** → Chunked and processed in sections  
            - ⚡ **Rate limited** → Auto-retries if the API is busy  
            """
        )
