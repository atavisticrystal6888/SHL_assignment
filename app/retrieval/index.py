"""TF-IDF catalog index construction."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer

from app.catalog.models import CatalogAssessment


RETRIEVAL_NORMALIZATIONS = {
    "behaviour": "behavior",
    "centre": "center",
    "judgement": "judgment",
    "organisation": "organization",
    "programme": "program",
}


def normalize_retrieval_text(text: str) -> str:
    normalized = text.lower()
    for source, target in RETRIEVAL_NORMALIZATIONS.items():
        normalized = normalized.replace(source, target)
    return normalized


def catalog_document(record: CatalogAssessment) -> str:
    return normalize_retrieval_text(
        " ".join(
            [
                record.name,
                record.test_type,
                " ".join(record.categories),
                record.description,
                record.duration,
                " ".join(record.job_levels),
                " ".join(record.languages),
            ]
        )
    )


@dataclass(frozen=True)
class CatalogIndex:
    records: list[CatalogAssessment]
    vectorizer: TfidfVectorizer
    matrix: object


def build_catalog_index(records: list[CatalogAssessment]) -> CatalogIndex:
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    documents = [catalog_document(record) for record in records]
    matrix = vectorizer.fit_transform(documents if documents else ["empty catalog"])
    return CatalogIndex(records=records, vectorizer=vectorizer, matrix=matrix)
