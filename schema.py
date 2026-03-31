"""
RSEA Supplier Catalog — Pydantic Schema (Hardened v2)
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


# ── Document Classification ───────────────────────────────────────────────────

class DocumentType(str, Enum):
    """What kind of document did the user upload?"""
    SUPPLIER_CATALOG = "supplier_catalog"
    TECHNICAL_MANUAL = "technical_manual"
    INVOICE = "invoice"
    COMPLIANCE_REPORT = "compliance_report"
    GENERAL_DOCUMENT = "general_document"
    UNKNOWN = "unknown"


class DocumentClassification(BaseModel):
    """
    First-pass classification — runs BEFORE extraction to catch non-catalogs.
    This is cheap (small prompt, small response) and saves us from
    wasting tokens on a 15-page mech engineering manual.
    """
    doc_type: DocumentType = Field(
        description="The type of document detected."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score 0.0–1.0 for the classification."
    )
    summary: str = Field(
        description="One-sentence summary of what this document appears to be."
    )
    is_extractable: bool = Field(
        description=(
            "True if this document contains product/pricing data that can be "
            "extracted into a catalog format. False for instruction manuals, "
            "technical specs without pricing, etc."
        )
    )
    recommendation: str = Field(
        description=(
            "What to tell the user. E.g. 'This is a supplier price list — "
            "ready for extraction.' or 'This appears to be a technical manual "
            "without pricing data.'"
        )
    )


# ── Product Item ──────────────────────────────────────────────────────────────

class ProductItem(BaseModel):
    """
    A single product line item extracted from a supplier catalog.

    CRITICAL DESIGN: 'sku' and 'category' default to empty strings,
    all bonus fields are Optional[str] = None.  This means:
    - GPT fills them in when the data exists → impressive demo
    - GPT skips them when the data doesn't exist → no crash
    """

    # ── Core fields (always attempted) ────────────────────────────────────
    sku: str = Field(
        default="",
        description="Product SKU / part number. Empty string if not found."
    )
    name: str = Field(
        default="",
        description="Product name or description."
    )
    price: float = Field(
        default=0.0,
        description="Unit price in AUD. Strip $, commas, GST annotations."
    )
    category: str = Field(
        default="Uncategorised",
        description="Product category or group. Infer from context if needed."
    )

    # ── Bonus fields (Optional — extracted when present, None when not) ───
    description: Optional[str] = Field(
        default=None,
        description="Extended product description or specifications."
    )
    unit_of_measure: Optional[str] = Field(
        default=None,
        description="e.g. 'Each', 'Pair', 'Box of 100', 'Carton'."
    )
    moq: Optional[int] = Field(
        default=None,
        description="Minimum Order Quantity if listed."
    )
    compliance_certs: Optional[str] = Field(
        default=None,
        description=(
            "Compliance / certification codes found near this item. "
            "e.g. 'AS/NZS 1337.1', 'CE EN 166', 'ISO 13485'."
        )
    )
    gst_inclusive: Optional[bool] = Field(
        default=None,
        description="True if the price includes GST, False if ex-GST, None if unclear."
    )

    # ── System fields (set by validation, NOT by AI) ──────────────────────
    flag: Optional[str] = Field(
        default=None,
        description="Validation flag set by the system — not extracted by AI."
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="AI's confidence that this row was extracted correctly (0.0–1.0)."
    )


# ── Supplier Catalog ─────────────────────────────────────────────────────────

class SupplierCatalog(BaseModel):
    """
    The full extraction result.  Every field has a safe default so
    even a partial extraction produces a usable object.
    """

    supplier_name: str = Field(
        default="Unknown Supplier",
        description="Supplier / vendor name if it appears in the document."
    )
    document_date: Optional[str] = Field(
        default=None,
        description="Date on the catalog/price list if visible (any format)."
    )
    currency: str = Field(
        default="AUD",
        description="Currency code. Default AUD for Australian suppliers."
    )
    gst_note: Optional[str] = Field(
        default=None,
        description="Any global GST note, e.g. 'All prices ex-GST'."
    )
    items: List[ProductItem] = Field(
        default_factory=list,
        description="All product line items found in the catalog."
    )
