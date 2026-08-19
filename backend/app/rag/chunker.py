"""Markdown frontmatter parsing + header-aware chunking.

No YAML dependency - our frontmatter is flat `key: value` pairs, a hand
rolled parser is a few lines and one less thing to install.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

WORDS_PER_CHUNK = 350  # ~ 512 tokens at ~0.7 tokens/word for this prose
OVERLAP_WORDS = 60

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
HEADER_RE = re.compile(r"^(#{1,3})\s+(.*)$", re.MULTILINE)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    category: str
    section: str
    order: int
    text: str
    metadata: dict = field(default_factory=dict)


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    fm_block, body = m.group(1), m.group(2)
    meta: dict = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"')
    return meta, body


def split_sections(body: str) -> list[tuple[str, str]]:
    """Split markdown body into (header_title, section_text) using ## / ###
    headers. Content before the first header (e.g. a banner blockquote) is
    kept under the document's own top-level "# Title" header if present, or
    an "Overview" section otherwise."""
    matches = list(HEADER_RE.finditer(body))
    if not matches:
        return [("Overview", body.strip())]

    sections: list[tuple[str, str]] = []
    # Leading text before first header (banners, etc.) attaches to first section.
    lead = body[: matches[0].start()].strip()

    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        text = body[start:end].strip()
        if level == 1:
            # Document title header - treat its intro text as "Overview".
            if text:
                sections.append(("Overview", (lead + "\n\n" + text).strip() if lead else text))
                lead = ""
            continue
        if lead and not sections:
            text = f"{lead}\n\n{text}"
            lead = ""
        if text:
            sections.append((title, text))

    return sections or [("Overview", body.strip())]


def _word_chunks(text: str) -> list[str]:
    words = text.split()
    if len(words) <= WORDS_PER_CHUNK:
        return [text]
    chunks = []
    step = WORDS_PER_CHUNK - OVERLAP_WORDS
    for start in range(0, len(words), step):
        piece = words[start : start + WORDS_PER_CHUNK]
        if not piece:
            break
        chunks.append(" ".join(piece))
        if start + WORDS_PER_CHUNK >= len(words):
            break
    return chunks


def chunk_document(doc_id: str, raw_text: str) -> list[Chunk]:
    meta, body = parse_frontmatter(raw_text)
    title = meta.get("title", doc_id)
    category = meta.get("category", "reference")

    chunks: list[Chunk] = []
    order = 0
    for section_title, section_text in split_sections(body):
        for piece in _word_chunks(section_text):
            if not piece.strip():
                continue
            slug = re.sub(r"[^a-z0-9]+", "-", section_title.lower()).strip("-")
            chunk_id = f"{doc_id}::{slug}::{order}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    title=title,
                    category=category,
                    section=section_title,
                    order=order,
                    text=piece,
                    metadata=meta,
                )
            )
            order += 1
    return chunks
