"""Engine A — Deterministic Transformer & Enrichment Pipeline ($0 LLM Cost)."""
import re
import hashlib
from typing import Dict, Any, List, Optional

class Transformer:
    """Extracts, categorizes and normalizes raw B2B opportunities using deterministic rules."""

    TECH_TAGS = {
        "cloud": ["cloud", "aws", "azure", "gcp", "hébergement", "devops", "kubernetes", "docker"],
        "security": ["sécurité", "cyber", "rgpd", "gdpr", "audit", "compliance", "iso 27001", "pentest"],
        "software": ["développement", "application", "saas", "api", "logiciel", "web", "mobile", "frontend", "backend"],
        "ai_data": ["ia", "intelligence artificielle", "machine learning", "data", "analytics", "bi", "llm"],
        "infrastructure": ["réseau", "serveur", "vps", "telecom", "fibre", "matériel"]
    }

    @staticmethod
    def generate_id(source: str, title: str, deadline: Optional[str] = None) -> str:
        unique_str = f"{source}:{title.strip().lower()}:{deadline or ''}"
        return hashlib.sha256(unique_str.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def extract_tags(cls, text: str) -> List[str]:
        text_lower = text.lower()
        matched_tags = set()
        for category, keywords in cls.TECH_TAGS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", text_lower):
                    matched_tags.add(category)
                    break
        if not matched_tags:
            matched_tags.add("general_it")
        return sorted(list(matched_tags))

    @staticmethod
    def parse_budget(text: str) -> Optional[float]:
        # Search for patterns like "50 000 €", "50000 EUR", "120,000 €"
        match = re.search(r"(\d[\d\s,.]*)\s*(?:€|eur|euros?)", text, re.IGNORECASE)
        if match:
            clean_num = match.group(1).replace(" ", "").replace(",", ".")
            try:
                val = float(clean_num)
                if 100 <= val <= 100_000_000:
                    return val
            except ValueError:
                pass
        return None

    @classmethod
    def transform_opportunity(cls, raw_item: Dict[str, Any], source: str) -> Dict[str, Any]:
        title = raw_item.get("title", "").strip()
        description = raw_item.get("description", "").strip()
        full_text = f"{title} {description}"

        opp_id = cls.generate_id(source, title, raw_item.get("deadline"))
        tags = cls.extract_tags(full_text)
        budget = raw_item.get("budget_eur") or cls.parse_budget(full_text)

        # Primary category determination
        category = tags[0] if tags else "it_services"

        return {
            "opp_id": opp_id,
            "title": title,
            "source": source,
            "category": category,
            "budget_eur": budget,
            "deadline": raw_item.get("deadline"),
            "tags": tags,
            "raw_data": raw_item
        }
