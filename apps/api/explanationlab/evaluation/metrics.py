"""Automated text-level diagnostics (§8.1).

**These are diagnostic signals, not measures of understanding.** Every metric
here is deterministic, cheap and explainable — a researcher can check any number
by hand, which is the point. Nothing in the platform ranks a condition by these.

Specifically, and deliberately: readability indices are reported because the
brief asks for them, with a standing caveat attached to the payload. The
literature is clear that they were fitted to surface features and are not
validated comprehension measures (Docs/RESEARCH_FOUNDATIONS.md §2). Optimising
them produces choppy text that scores well and teaches no better.
"""

from __future__ import annotations

import re
from collections import Counter

METRICS_VERSION = "1.0"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])[\s\n]+")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)

# Indirection and padding phrases. Sourced from the complaint categories
# documented in Docs/RESEARCH_FOUNDATIONS.md §1.1 — this list is an operational
# restatement of what readers actually objected to, not a general style opinion.
_INDIRECTION_PHRASES = (
    "it is worth noting",
    "it is important to note",
    "it is the case that",
    "the operative consideration",
    "it bears mentioning",
    "one might consider",
    "it should be emphasised",
    "it should be emphasized",
    "in some sense",
    "at a high level",
    "fundamentally speaking",
    "it turns out that",
    "the key insight here is",
    "this is not merely",
    "not so much",
    "the more productive altitude",
    "load-bearing",
    "in other words",
    "that is to say",
    "needless to say",
    "as previously mentioned",
)

# Suffixes typical of nominalised, latinate register — the "dense" style readers
# reported struggling with.
_NOMINALISATION_SUFFIXES = ("tion", "sion", "ment", "ance", "ence", "ity", "ness", "ism")

# Hedges, tracked for fidelity work rather than as a quality signal.
_HEDGES = (
    "may",
    "might",
    "could",
    "often",
    "sometimes",
    "usually",
    "typically",
    "generally",
    "approximately",
    "roughly",
    "tends",
    "likely",
)

# Causal/explanatory connectives: a crude proxy for whether mechanism is being
# explained rather than facts asserted.
_CAUSAL_MARKERS = (
    "because",
    "therefore",
    "so that",
    "which means",
    "as a result",
    "consequently",
    "this is why",
    "the reason",
    "leads to",
    "causes",
    "due to",
    "in order to",
    "hence",
    "thus",
    "follows that",
)

_SEQUENCE_MARKERS = ("first", "second", "third", "next", "then", "finally", "step", "once")

# Words whose referent is often left dangling — the "vague references" complaint.
_DANGLING_STARTERS = ("this ", "that ", "these ", "those ", "it ", "they ", "such ")

_COMMON_WORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "is", "are", "was", "were",
    "be", "been", "being", "to", "of", "in", "on", "at", "for", "with", "from",
    "by", "as", "that", "this", "these", "those", "it", "its", "you", "your",
    "we", "our", "they", "their", "he", "she", "not", "no", "do", "does", "did",
    "can", "could", "will", "would", "should", "may", "might", "must", "have",
    "has", "had", "there", "here", "when", "where", "which", "who", "what", "how",
    "why", "all", "any", "each", "more", "most", "other", "some", "such", "only",
    "same", "so", "than", "too", "very", "just", "also", "into", "over", "after",
    "before", "while", "because", "about", "up", "down", "out", "one", "two",
}


def _strip_code(text: str) -> str:
    return _CODE_FENCE_RE.sub(" ", text)


def _syllables(word: str) -> int:
    """Approximate English syllable count. Good enough for a surface index."""
    word = word.lower().strip("'-")
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    count = len(re.findall(r"[aeiouy]{1,2}", word))
    return max(1, count)


def _sentences(text: str) -> list[str]:
    plain = _strip_code(text)
    plain = _HEADING_RE.sub(lambda m: m.group(2) + ".", plain)
    parts = [s.strip() for s in _SENTENCE_SPLIT.split(plain) if s.strip()]
    return parts


def compute_metrics(text: str, *, factual_checklist: list[str] | None = None) -> dict:
    """Return the full diagnostic payload for one explanation."""
    body = _strip_code(text)
    sentences = _sentences(text)
    words = _WORD_RE.findall(body)
    lowered_words = [w.lower() for w in words]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]

    word_count = len(words)
    sentence_count = len(sentences)
    syllable_total = sum(_syllables(w) for w in words)

    sentence_lengths = [len(_WORD_RE.findall(s)) for s in sentences]
    long_sentences = [n for n in sentence_lengths if n > 30]

    # --- readability (surface only) ---
    if word_count and sentence_count:
        words_per_sentence = word_count / sentence_count
        syllables_per_word = syllable_total / word_count
        flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
        fk_grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59
        complex_words = sum(1 for w in words if _syllables(w) >= 3)
        gunning_fog = 0.4 * (words_per_sentence + 100 * (complex_words / word_count))
    else:
        words_per_sentence = syllables_per_word = 0.0
        flesch = fk_grade = gunning_fog = 0.0
        complex_words = 0

    # --- repetition ---
    content_words = [w for w in lowered_words if w not in _COMMON_WORDS and len(w) > 3]
    word_freq = Counter(content_words)
    trigrams = Counter(
        " ".join(lowered_words[i : i + 3]) for i in range(max(0, len(lowered_words) - 2))
    )
    repeated_trigrams = {k: v for k, v in trigrams.items() if v > 1}

    # --- jargon (heuristic) ---
    jargon_candidates = sorted(
        {
            w.lower()
            for w in words
            if len(w) >= 10
            and w.lower() not in _COMMON_WORDS
            and any(w.lower().endswith(s) for s in _NOMINALISATION_SUFFIXES)
        }
    )
    nominalisations = sum(
        1 for w in lowered_words if len(w) > 6 and any(w.endswith(s) for s in _NOMINALISATION_SUFFIXES)
    )

    lowered_text = body.lower()
    indirection_hits = [p for p in _INDIRECTION_PHRASES if p in lowered_text]

    # --- terminology introduction order ---
    term_intro = _terminology_introduction(body, jargon_candidates)

    # --- potentially unresolved references ---
    dangling = []
    for idx, sentence in enumerate(sentences):
        low = sentence.lower().lstrip("*-# ")
        for starter in _DANGLING_STARTERS:
            if low.startswith(starter):
                following = low[len(starter) :].split()
                # "This cache" is fine; bare "This is" is the problem case.
                if not following or following[0] in {"is", "are", "was", "were", "means", "can", "will"}:
                    dangling.append({"sentence_index": idx, "excerpt": sentence[:140]})
                break

    # --- structure ---
    headings = [{"level": len(m.group(1)), "text": m.group(2).strip()} for m in _HEADING_RE.finditer(text)]
    heading_levels = [h["level"] for h in headings]

    # --- explanation step / mechanism coverage ---
    causal_hits = {m: lowered_text.count(m) for m in _CAUSAL_MARKERS if m in lowered_text}
    sequence_hits = {m: lowered_text.count(m) for m in _SEQUENCE_MARKERS if m in lowered_text}

    # --- concept coverage against the reviewed checklist ---
    coverage = _checklist_coverage(lowered_text, factual_checklist or [])

    return {
        "metrics_version": METRICS_VERSION,
        "surface": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": len(paragraphs),
            "avg_sentence_words": round(words_per_sentence, 2),
            "max_sentence_words": max(sentence_lengths) if sentence_lengths else 0,
            "long_sentence_count": len(long_sentences),
            "long_sentence_share": round(len(long_sentences) / sentence_count, 4)
            if sentence_count
            else 0,
            "avg_paragraph_words": round(word_count / len(paragraphs), 2) if paragraphs else 0,
            "max_paragraph_words": max((len(_WORD_RE.findall(p)) for p in paragraphs), default=0),
            "avg_syllables_per_word": round(syllables_per_word, 3),
            "complex_word_share": round(complex_words / word_count, 4) if word_count else 0,
            "type_token_ratio": round(len(set(lowered_words)) / word_count, 4) if word_count else 0,
        },
        "readability": {
            "flesch_reading_ease": round(flesch, 2),
            "flesch_kincaid_grade": round(fk_grade, 2),
            "gunning_fog": round(gunning_fog, 2),
            "caveat": (
                "Readability indices are surface diagnostics fitted to word and sentence "
                "length. They are NOT validated measures of comprehension and must not be "
                "used to rank explanations."
            ),
        },
        "repetition": {
            "repeated_trigram_count": len(repeated_trigrams),
            "top_repeated_trigrams": sorted(
                repeated_trigrams.items(), key=lambda kv: -kv[1]
            )[:10],
            "most_frequent_content_words": word_freq.most_common(10),
        },
        "jargon": {
            "candidate_count": len(jargon_candidates),
            "candidates": jargon_candidates[:40],
            "nominalisation_count": nominalisations,
            "nominalisation_density": round(nominalisations / word_count, 4) if word_count else 0,
            "indirection_phrase_count": len(indirection_hits),
            "indirection_phrases": indirection_hits,
            "method": (
                "Heuristic: long nominalised words plus a phrase list derived from the "
                "documented reader complaints. Not a curated domain glossary."
            ),
        },
        "terminology_introduction": term_intro,
        "unresolved_references": {
            "count": len(dangling),
            "examples": dangling[:10],
            "method": "Sentences opening with a bare demonstrative or pronoun.",
        },
        "structure": {
            "heading_count": len(headings),
            "max_heading_depth": max(heading_levels) if heading_levels else 0,
            "heading_levels_used": sorted(set(heading_levels)),
            "has_skipped_heading_level": _has_skipped_level(heading_levels),
            "list_item_count": len(_LIST_RE.findall(text)),
            "table_row_count": len(_TABLE_ROW_RE.findall(text)),
            "code_block_count": len(_CODE_FENCE_RE.findall(text)),
            "headings": headings[:20],
        },
        "explanation_steps": {
            "causal_marker_total": sum(causal_hits.values()),
            "causal_markers": causal_hits,
            "causal_density_per_100w": round(sum(causal_hits.values()) / word_count * 100, 2)
            if word_count
            else 0,
            "sequence_marker_total": sum(sequence_hits.values()),
            "sequence_markers": sequence_hits,
        },
        "hedging": {
            "hedge_count": sum(lowered_words.count(h) for h in _HEDGES),
            "hedge_density_per_100w": round(
                sum(lowered_words.count(h) for h in _HEDGES) / word_count * 100, 2
            )
            if word_count
            else 0,
        },
        "concept_coverage": coverage,
        "interpretation_warning": (
            "Diagnostic signals only. Shorter sentences do not mean a better explanation; "
            "more headings do not mean clearer structure. Use these to describe a text, "
            "never to rank one."
        ),
    }


def _has_skipped_level(levels: list[int]) -> bool:
    """True if the heading hierarchy jumps a level (e.g. H1 straight to H3).

    A skipped level means the visual hierarchy does not match the conceptual
    one, which is the "formatting that does not reveal structure" complaint.
    """
    if not levels:
        return False
    previous = levels[0]
    for level in levels[1:]:
        if level > previous + 1:
            return True
        previous = level
    return False


def _terminology_introduction(text: str, terms: list[str]) -> dict:
    """Is each candidate term explained near its first use?

    Crude but checkable: look for a definitional cue within ~200 characters of
    first occurrence.
    """
    lowered = text.lower()
    cues = (" is ", " are ", " means ", " refers to ", " — ", " – ", ", i.e.", "(", " called ", ": ")
    rows = []
    for term in terms[:40]:
        pos = lowered.find(term)
        if pos == -1:
            continue
        window = lowered[pos : pos + 200]
        rows.append(
            {
                "term": term,
                "first_char_offset": pos,
                "defined_near_first_use": any(c in window for c in cues),
            }
        )
    defined = sum(1 for r in rows if r["defined_near_first_use"])
    return {
        "terms_checked": len(rows),
        "defined_near_first_use": defined,
        "undefined_share": round(1 - defined / len(rows), 4) if rows else None,
        "terms": rows,
        "method": "Definitional cue within 200 characters of first use.",
    }


def _checklist_coverage(lowered_text: str, checklist: list[str]) -> dict:
    """Keyword overlap against the reviewed factual checklist.

    Lexical, so a paraphrase scores as a miss. Treated as a prompt for human
    review, not as a correctness measure.
    """
    if not checklist:
        return {
            "checklist_size": 0,
            "items": [],
            "covered": 0,
            "coverage_ratio": None,
            "method": "No reviewed checklist for this question.",
        }

    items = []
    for claim in checklist:
        keywords = [
            w.lower()
            for w in _WORD_RE.findall(claim)
            if w.lower() not in _COMMON_WORDS and len(w) > 3
        ]
        if not keywords:
            items.append({"claim": claim, "matched_keywords": 0, "keyword_count": 0, "likely_present": False})
            continue
        matched = sum(1 for k in keywords if k in lowered_text)
        items.append(
            {
                "claim": claim,
                "matched_keywords": matched,
                "keyword_count": len(keywords),
                "match_ratio": round(matched / len(keywords), 3),
                "likely_present": matched / len(keywords) >= 0.6,
            }
        )
    covered = sum(1 for i in items if i["likely_present"])
    return {
        "checklist_size": len(checklist),
        "items": items,
        "covered": covered,
        "coverage_ratio": round(covered / len(checklist), 3) if checklist else None,
        "method": (
            "Lexical keyword overlap. A correct paraphrase will register as a miss, so "
            "treat low coverage as a prompt for human review, not as evidence of omission."
        ),
    }
