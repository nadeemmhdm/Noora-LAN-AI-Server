import re
import math
from typing import List, Dict, Any, Optional
from collections import Counter
from backend.database import (
    insert_knowledge_document, insert_knowledge_chunks,
    get_all_knowledge_documents, get_knowledge_document,
    get_chunks_by_document, delete_knowledge_document,
    get_all_knowledge_chunks_with_doc_info, log_system_event
)

# Common stop words for keyword extraction
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "did", "do", "does", "doing", "don", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once",
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where", "which",
    "while", "who", "whom", "why", "will", "with", "you", "your", "yours", "yourself"
}

def extract_keywords(text: str, max_keywords: int = 12) -> str:
    """Extracts top non-stopword alphanumeric keywords from text."""
    words = re.findall(r"\b[a-zA-Z0-9_\-\.]{3,}\b", text.lower())
    filtered = [w for w in words if w not in STOP_WORDS and not w.isdigit()]
    counts = Counter(filtered)
    top_words = [w for w, _ in counts.most_common(max_keywords)]
    return ", ".join(top_words)

def parse_markdown_into_sections(markdown_text: str) -> List[Dict[str, str]]:
    """
    Splits markdown document into semantic sections based on headers (#, ##, ###).
    Returns list of dicts: {'title': str, 'content': str}.
    """
    lines = markdown_text.splitlines()
    sections = []
    current_title = "Overview"
    current_lines = []

    for line in lines:
        header_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if header_match:
            # Save previous section if it has content
            if current_lines:
                sec_text = "\n".join(current_lines).strip()
                if sec_text:
                    sections.append({
                        "title": current_title,
                        "content": sec_text
                    })
                current_lines = []
            current_title = header_match.group(2).strip()
        else:
            current_lines.append(line)

    if current_lines:
        sec_text = "\n".join(current_lines).strip()
        if sec_text:
            sections.append({
                "title": current_title,
                "content": sec_text
            })

    return sections

def chunk_section_content(section_title: str, text: str, max_chunk_words: int = 250) -> List[Dict[str, Any]]:
    """
    Splits long section text into readable semantic chunks.
    Ensures chunks don't exceed max_chunk_words while keeping paragraphs together.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk_paragraphs = []
    current_word_count = 0

    for para in paragraphs:
        para_clean = para.strip()
        if not para_clean:
            continue
        words = para_clean.split()
        para_word_count = len(words)

        if current_word_count + para_word_count > max_chunk_words and current_chunk_paragraphs:
            chunk_text = "\n\n".join(current_chunk_paragraphs)
            chunks.append({
                "section_title": section_title,
                "content": chunk_text,
                "keywords": extract_keywords(chunk_text)
            })
            current_chunk_paragraphs = [para_clean]
            current_word_count = para_word_count
        else:
            current_chunk_paragraphs.append(para_clean)
            current_word_count += para_word_count

    if current_chunk_paragraphs:
        chunk_text = "\n\n".join(current_chunk_paragraphs)
        chunks.append({
            "section_title": section_title,
            "content": chunk_text,
            "keywords": extract_keywords(chunk_text)
        })

    return chunks

def analyze_and_train_markdown(filename: str, raw_content: str) -> Dict[str, Any]:
    """
    Main training function:
    1. Analyzes markdown structure, headers, and topics.
    2. Generates an executive summary.
    3. Breaks document into searchable semantic chunks.
    4. Persists the trained memory into SQLite database.
    """
    if not raw_content or not raw_content.strip():
        raise ValueError("Uploaded markdown document is empty.")

    clean_content = raw_content.strip()
    file_size_bytes = len(clean_content.encode("utf-8"))
    total_words = len(re.findall(r"\b\w+\b", clean_content))

    # Detect title from first heading or filename
    title_match = re.search(r"^#\s+(.+)$", clean_content, re.MULTILINE)
    if title_match:
        doc_title = title_match.group(1).strip()
    else:
        # Fallback to sanitized filename
        doc_title = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()

    # Parse into sections
    sections = parse_markdown_into_sections(clean_content)
    if not sections:
        sections = [{"title": "General", "content": clean_content}]

    # Chunk sections
    all_chunks = []
    section_titles = []
    for sec in sections:
        sec_title = sec["title"]
        section_titles.append(sec_title)
        sec_chunks = chunk_section_content(sec_title, sec["content"])
        all_chunks.extend(sec_chunks)

    if not all_chunks:
        all_chunks = [{
            "section_title": doc_title,
            "content": clean_content[:1500],
            "keywords": extract_keywords(clean_content[:1500])
        }]

    # Generate document summary
    key_topics = ", ".join(section_titles[:6])
    summary = f"Document '{doc_title}' covers key sections: {key_topics}. Contains {len(all_chunks)} semantic knowledge chunks ({total_words} words)."

    # Store in database
    doc_id = insert_knowledge_document(
        filename=filename,
        title=doc_title,
        summary=summary,
        word_count=total_words,
        chunk_count=len(all_chunks),
        file_size_bytes=file_size_bytes
    )
    insert_knowledge_chunks(doc_id, all_chunks)

    log_system_event(
        "INFO", "KNOWLEDGE",
        f"AI trained on document '{filename}' (ID: {doc_id}): {len(all_chunks)} chunks memorized ({total_words} words)."
    )

    return {
        "id": doc_id,
        "doc_id": doc_id,
        "filename": filename,
        "title": doc_title,
        "summary": summary,
        "word_count": total_words,
        "chunk_count": len(all_chunks),
        "file_size_bytes": file_size_bytes,
        "sections": section_titles
    }

def tokenize_query(query: str) -> List[str]:
    """Tokenizes and filters query terms for retrieval."""
    words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", query.lower())
    return [w for w in words if w not in STOP_WORDS]

def search_knowledge_memory(query: str, top_k: int = 3, min_score: float = 1.0) -> List[Dict[str, Any]]:
    """
    Sub-millisecond BM25-based semantic retrieval engine.
    Finds the most relevant trained knowledge chunks from memory to answer the user query.
    """
    tokens = tokenize_query(query)
    if not tokens:
        return []

    chunks = get_all_knowledge_chunks_with_doc_info()
    if not chunks:
        return []

    num_docs = len(chunks)
    avg_len = sum(len(c["content"].split()) for c in chunks) / max(1, num_docs)

    # Document frequencies
    df = Counter()
    chunk_words_list = []
    for c in chunks:
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", (c["content"] + " " + (c["keywords"] or "")).lower())
        unique_words = set(words)
        for t in tokens:
            if t in unique_words:
                df[t] += 1
        chunk_words_list.append(Counter(words))

    # BM25 Scoring parameters
    k1 = 1.2
    b = 0.75

    scored_chunks = []
    for idx, c in enumerate(chunks):
        tf_dict = chunk_words_list[idx]
        doc_len = sum(tf_dict.values())
        score = 0.0

        section_lower = (c.get("section_title") or "").lower()
        title_lower = (c.get("doc_title") or "").lower()

        for t in tokens:
            n_t = df.get(t, 0)
            if n_t == 0:
                continue
            # Standard BM25 IDF
            idf = math.log(1.0 + (num_docs - n_t + 0.5) / (n_t + 0.5))
            f = tf_dict.get(t, 0)
            denom = f + k1 * (1.0 - b + b * (doc_len / max(1.0, avg_len)))
            bm25 = idf * ((f * (k1 + 1.0)) / max(0.001, denom))
            score += bm25

            # Boost if token appears in section title or document title
            if t in section_lower:
                score += 2.5
            if t in title_lower:
                score += 1.5

        if score >= min_score:
            scored_chunks.append({
                "chunk_id": c["id"],
                "doc_id": c["doc_id"],
                "doc_title": c["doc_title"],
                "filename": c["filename"],
                "section_title": c["section_title"],
                "content": c["content"],
                "score": round(score, 2)
            })

    # Sort descending by score
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]

def format_knowledge_context(chunks: List[Dict[str, Any]]) -> str:
    """Formats retrieved memory chunks into clear system context for the neural model."""
    if not chunks:
        return ""

    lines = [
        "[AI TRAINED KNOWLEDGE MEMORY]",
        "The following verified information was learned from user-uploaded training documents. Prioritize this trained knowledge when answering the question:",
        ""
    ]

    for idx, c in enumerate(chunks, 1):
        doc_name = c.get("doc_title") or c.get("filename") or "Trained Doc"
        sec_name = c.get("section_title") or "General"
        content = c.get("content", "").strip()
        lines.append(f"--- Learned Memory {idx}: {doc_name} (Section: {sec_name}) ---")
        lines.append(content)
        lines.append("")

    lines.append("Instructions: Use the learned facts above directly to answer the user's question accurately. If the document specifies answers, policies, or procedures, follow them precisely.")
    return "\n".join(lines)

def format_collapsible_memory_markdown(memory_sources: List[Dict[str, Any]]) -> str:
    """Formats retrieved memory chunks into an interactive collapsible HTML+Markdown block."""
    if not memory_sources:
        return ""
    count = len(memory_sources)
    lines = [
        "",
        '<details class="noora-memory-accordion mt-3 p-3 rounded-xl bg-slate-950 border border-violet-500/30 text-xs" open>',
        f'<summary class="cursor-pointer font-semibold text-violet-400 hover:text-violet-300 flex items-center gap-1.5 select-none">🧠 <strong>Learned AI Memory</strong> ({count} document citations used)</summary>',
        '<div class="mt-2.5 space-y-2 text-slate-300 pl-2 border-l-2 border-violet-500/40">',
        ""
    ]
    for idx, m in enumerate(memory_sources, 1):
        doc_name = m.get("doc_title") or m.get("filename") or "Trained Document"
        sec = m.get("section_title") or "General"
        snippet = m.get("content", "").strip()[:180].replace("\n", " ")
        lines.append(f"{idx}. **{doc_name}** — *{sec}*")
        if snippet:
            lines.append(f"   > {snippet}...")

    lines.extend(["", "</div>", "</details>", ""])
    return "\n".join(lines)
