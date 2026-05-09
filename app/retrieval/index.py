"""TF-IDF catalog index construction."""

from __future__ import annotations

from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer

from app.catalog.models import CatalogAssessment


def catalog_document(record: CatalogAssessment) -> str:
    return " ".join(
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
