"""Generates a complete multi-tier Fintech & Banking enterprise corpus with text, ASTs, and DuckDB tables."""
import json
from pathlib import Path

DATA_DIR = Path("/run/media/soham/D Drive/botmartz/botmartz-engine/data/sample_industry_fintech")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 1. Complex Policy & Compliance Doc (Text + Deep AST)
compliance_doc = """# Global Fintech Compliance & Risk Underwriting Standards 2026

## 1. Executive Summary & Regulatory Framework
This operational manual governs risk scoring, cross-border remittance limits, AML tiered thresholds, and credit decisioning across North America, EMEA, and APAC corridors. All operations adhere strictly to Basel III liquidity ratios and FATF Travel Rule mandates.

### 1.1 Capital Adequacy & Tier 1 Liquidity Reserves
The institution maintains a Common Equity Tier 1 (CET1) capital ratio of not less than 12.5%, surpassing the regulatory statutory minimum of 8.0%. Stress testing simulating severe liquidity contagion requires daily automated reconciliation across all correspondent clearing nodes.

### 1.2 Remittance KYC Tiers & Verification Mandates
Transactions are dynamically segmented into four verification tiers:
- Tier 1 (Micro-transfers <= $1,000 USD): Automated biometric matching and instant PEP/Sanctions list delta check.
- Tier 2 (Standard transfers $1,001 - $10,000 USD): Proof of address verification, source of funds self-attestation, and automated behavioral velocity analysis.
- Tier 3 (Enhanced Due Diligence $10,001 - $100,000 USD): Full tax documentation review, corporate beneficial ownership registry verification, and manual officer sign-off.
- Tier 4 (Institutional Remittances > $100,000 USD): Real-time cryptographic ledger escrow, AML supervisor dual-key authorization, and correspondent bank pre-notification.

## 2. Dynamic Credit Scoring & Real-Time Fraud Engine
Our proprietary risk scoring engine computes an ensemble score S in [300, 850] combining credit bureau reporting (40%), real-time transaction telemetry (35%), and merchant dispute frequency (25%).

### 2.1 Anomaly Detection & Hard Freeze Latency
When real-time fraud probability P(Fraud) exceeds 0.88, the settlement gateway initiates a microsecond soft-lock on merchant balances. Chargeback loss reserves are calculated as:
Reserve = Max(0.02 * Rolling_30d_GMV, Historical_Peak_Loss * 1.5).
"""

(DATA_DIR / "fintech_compliance_standards_2026.md").write_text(compliance_doc, encoding="utf-8")

# 2. In-depth Tabular Data for KAG DuckDB (remittances + portfolio credit)
transactions = [
    {"tx_id": "TX-10928", "corridor": "US-GB", "amount_usd": 45000.0, "fee_usd": 67.5, "kyc_tier": "Tier 3", "risk_score": 0.12, "status": "SETTLED"},
    {"tx_id": "TX-10929", "corridor": "US-SG", "amount_usd": 120000.0, "fee_usd": 180.0, "kyc_tier": "Tier 4", "risk_score": 0.08, "status": "SETTLED"},
    {"tx_id": "TX-10930", "corridor": "GB-IN", "amount_usd": 8500.0, "fee_usd": 25.5, "kyc_tier": "Tier 2", "risk_score": 0.45, "status": "FLAGGED_REVIEW"},
    {"tx_id": "TX-10931", "corridor": "US-MX", "amount_usd": 950.0, "fee_usd": 4.75, "kyc_tier": "Tier 1", "risk_score": 0.04, "status": "SETTLED"},
    {"tx_id": "TX-10932", "corridor": "EU-JP", "amount_usd": 210000.0, "fee_usd": 315.0, "kyc_tier": "Tier 4", "risk_score": 0.02, "status": "SETTLED"},
    {"tx_id": "TX-10933", "corridor": "US-BR", "amount_usd": 14200.0, "fee_usd": 42.6, "kyc_tier": "Tier 3", "risk_score": 0.72, "status": "FLAGGED_REVIEW"},
    {"tx_id": "TX-10934", "corridor": "SG-IN", "amount_usd": 32000.0, "fee_usd": 48.0, "kyc_tier": "Tier 3", "risk_score": 0.15, "status": "SETTLED"},
    {"tx_id": "TX-10935", "corridor": "US-CA", "amount_usd": 450.0, "fee_usd": 2.25, "kyc_tier": "Tier 1", "risk_score": 0.01, "status": "SETTLED"},
    {"tx_id": "TX-10936", "corridor": "EU-US", "amount_usd": 550000.0, "fee_usd": 825.0, "kyc_tier": "Tier 4", "risk_score": 0.05, "status": "SETTLED"},
    {"tx_id": "TX-10937", "corridor": "US-GB", "amount_usd": 3100.0, "fee_usd": 9.3, "kyc_tier": "Tier 2", "risk_score": 0.28, "status": "SETTLED"}
]

(DATA_DIR / "settled_remittances_sample.json").write_text(json.dumps(transactions, indent=2), encoding="utf-8")
print(f"Created sample fintech industry corpus in {DATA_DIR}")
