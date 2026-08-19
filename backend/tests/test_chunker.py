from app.rag.chunker import chunk_document, parse_frontmatter, split_sections

SAMPLE_DOC = """---
doc_id: sample-doc
title: Sample Document
category: reference
---

> A banner line.

# Sample Document

Intro text under the title.

## Section One

Body of section one.

## Section Two

Body of section two.
"""


def test_parse_frontmatter_extracts_metadata():
    meta, body = parse_frontmatter(SAMPLE_DOC)
    assert meta["doc_id"] == "sample-doc"
    assert meta["title"] == "Sample Document"
    assert meta["category"] == "reference"
    assert "Section One" in body


def test_parse_frontmatter_handles_missing_frontmatter():
    meta, body = parse_frontmatter("# No frontmatter\n\nJust text.")
    assert meta == {}
    assert "Just text" in body


def test_split_sections_finds_headers():
    _, body = parse_frontmatter(SAMPLE_DOC)
    sections = split_sections(body)
    titles = [t for t, _ in sections]
    assert "Section One" in titles
    assert "Section Two" in titles


def test_chunk_document_produces_unique_chunk_ids():
    chunks = chunk_document("sample-doc", SAMPLE_DOC)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert len(chunks) >= 2


def test_chunk_document_carries_metadata():
    chunks = chunk_document("sample-doc", SAMPLE_DOC)
    assert all(c.doc_id == "sample-doc" for c in chunks)
    assert all(c.category == "reference" for c in chunks)


def test_long_section_is_split_into_multiple_chunks():
    long_body = "---\ndoc_id: long-doc\ntitle: Long\ncategory: reference\n---\n\n## Only Section\n\n" + ("word " * 1000)
    chunks = chunk_document("long-doc", long_body)
    assert len(chunks) > 1
