"""Domain knowledge: clause keywords, risk weights, and benchmark language.

Centralised so the MCP tools, agents, and report layer share one source of
truth. Weights are taken verbatim from SRS Appendix B.
"""
from __future__ import annotations

from .models import ClauseType

# Keyword/anchor terms used to locate each clause type in raw contract text.
CLAUSE_KEYWORDS: dict[ClauseType, list[str]] = {
    ClauseType.TERMINATION: ["terminat", "notice period", "for cause", "end this agreement", "expiration"],
    ClauseType.LIABILITY_CAP: ["liabilit", "limitation of liability", "aggregate liability", "in no event"],
    ClauseType.INDEMNIFICATION: ["indemnif", "hold harmless", "defend", "indemnit"],
    ClauseType.IP_OWNERSHIP: ["intellectual property", "work product", "ownership", "assigns all right", "copyright", "patent"],
    ClauseType.NON_COMPETE: ["non-compete", "noncompete", "compete", "restrictive covenant", "solicit"],
    ClauseType.CONFIDENTIALITY: ["confidential", "non-disclosure", "proprietary information", "trade secret"],
    ClauseType.PAYMENT_TERMS: ["payment", "invoice", "fees", "late fee", "net 30", "net 60", "penalt"],
    ClauseType.GOVERNING_LAW: ["governing law", "governed by", "laws of", "jurisdiction"],
    ClauseType.DISPUTE_RESOLUTION: ["arbitrat", "mediation", "dispute", "litigation", "venue", "courts of"],
    ClauseType.AUTO_RENEWAL: ["automatically renew", "auto-renew", "renewal term", "evergreen", "unless terminated"],
}

# Overall-risk weighting (SRS Appendix B). Sums to 1.00.
RISK_WEIGHTS: dict[ClauseType, float] = {
    ClauseType.LIABILITY_CAP: 0.20,
    ClauseType.INDEMNIFICATION: 0.20,
    ClauseType.TERMINATION: 0.15,
    ClauseType.IP_OWNERSHIP: 0.15,
    ClauseType.NON_COMPETE: 0.10,
    ClauseType.CONFIDENTIALITY: 0.08,
    ClauseType.AUTO_RENEWAL: 0.05,
    ClauseType.PAYMENT_TERMS: 0.04,
    ClauseType.DISPUTE_RESOLUTION: 0.02,
    ClauseType.GOVERNING_LAW: 0.01,
}

# Phrases that materially increase clause risk (heuristic scoring signal).
HIGH_RISK_SIGNALS: list[str] = [
    "unlimited", "sole discretion", "irrevocable", "perpetual", "without limitation",
    "in no event", "waive", "indemnify and hold harmless", "automatically renew",
    "non-negotiable", "exclusive", "no liability", "as is", "without notice",
    "liquidated damages", "personal guarantee", "any and all", "uncapped",
]
MEDIUM_RISK_SIGNALS: list[str] = [
    "may terminate", "30 days", "60 days", "renewal", "penalty", "late fee",
    "governing law", "arbitration", "material breach", "reasonable efforts",
]

# Standard market language returned by get_industry_benchmark (SRS FR-7).
INDUSTRY_BENCHMARKS: dict[ClauseType, str] = {
    ClauseType.LIABILITY_CAP: "Liability is typically capped at fees paid in the trailing 12 months.",
    ClauseType.INDEMNIFICATION: "Indemnities are usually mutual and limited to third-party IP and confidentiality claims.",
    ClauseType.TERMINATION: "Either party may terminate for convenience on 30 days' written notice.",
    ClauseType.IP_OWNERSHIP: "Each party retains pre-existing IP; deliverables assign to the customer on payment.",
    ClauseType.NON_COMPETE: "Non-competes, where enforceable, are limited to 12 months and a defined geography.",
    ClauseType.CONFIDENTIALITY: "Mutual confidentiality with a 3–5 year survival period is standard.",
    ClauseType.PAYMENT_TERMS: "Net-30 payment terms with interest on late amounts at ~1.5%/month.",
    ClauseType.GOVERNING_LAW: "Governing law commonly follows the customer's or vendor's home jurisdiction.",
    ClauseType.DISPUTE_RESOLUTION: "Good-faith negotiation first, then binding arbitration or courts in the agreed venue.",
    ClauseType.AUTO_RENEWAL: "Auto-renewal with a 30–60 day opt-out window before each renewal term.",
}

# Plain-English legal definitions for lookup_legal_definition (SRS FR-7).
LEGAL_DEFINITIONS: dict[str, str] = {
    "indemnification": "A promise by one party to cover the losses or legal costs of the other party.",
    "liability cap": "A ceiling on the total amount of money one party can be required to pay the other.",
    "force majeure": "Excuses a party from its obligations when extraordinary events beyond its control occur.",
    "governing law": "The jurisdiction whose laws are used to interpret and enforce the contract.",
    "arbitration": "Resolving disputes privately before a neutral arbitrator instead of going to court.",
    "non-compete": "A restriction preventing someone from working for or starting a competing business.",
    "confidentiality": "An obligation to keep certain information secret and not disclose it to others.",
    "auto-renewal": "A clause that renews the contract automatically unless a party opts out in time.",
    "termination for convenience": "The right to end a contract without needing a reason or fault.",
    "intellectual property": "Creations of the mind — inventions, designs, software, and brands — that can be owned.",
}
