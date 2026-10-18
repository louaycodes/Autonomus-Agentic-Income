import pytest
from src.cluster.engine_a_transformer import Transformer

def test_extract_tags():
    text = "Recherche expert DevOps pour migration Kubernetes sur AWS et mise en conformité RGPD"
    tags = Transformer.extract_tags(text)
    assert "cloud" in tags
    assert "security" in tags

def test_parse_budget():
    assert Transformer.parse_budget("Budget alloué : 75 000 € HT") == 75000.0
    assert Transformer.parse_budget("Enveloppe estimée à 120000 EUR") == 120000.0
    assert Transformer.parse_budget("Sans budget spécifié") is None

def test_transform_opportunity():
    raw = {
        "title": "Développement Application Web SaaS",
        "description": "Prestation d'ingénierie backend Python FastAPI avec budget de 40 000 euros.",
        "deadline": "2026-12-31"
    }
    transformed = Transformer.transform_opportunity(raw, "test_source")
    assert transformed["opp_id"] is not None
    assert transformed["budget_eur"] == 40000.0
    assert transformed["category"] in ["software", "cloud"]
    assert transformed["deadline"] == "2026-12-31"
