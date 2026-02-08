# Enhanced Cognee - Multi-Language Support Guide

**Version:** 1.0.0
**Date:** 2026-02-06
**Sprint:** 9 - Multi-Language & Polish

---

## Overview

Enhanced Cognee now supports **28 languages** with automatic language detection, multi-language search, and cross-language functionality. This guide explains how to use these features.

---

## Supported Languages

Enhanced Cognee supports the following 28 languages:

| Code | Language | Native Name |
|------|----------|-------------|
| en | English | English |
| es | Spanish | Espanol |
| fr | French | Francais |
| de | German | Deutsch |
| zh-cn | Chinese (Simplified) | 中文 |
| zh-tw | Chinese (Traditional) | 中文 |
| ja | Japanese | 日本語 |
| ko | Korean | 한국어 |
| ru | Russian | Русский |
| ar | Arabic | العربية |
| pt | Portuguese | Portugues |
| it | Italian | Italiano |
| nl | Dutch | Nederlands |
| pl | Polish | Polski |
| sv | Swedish | Svenska |
| da | Danish | Dansk |
| no | Norwegian | Norsk |
| fi | Finnish | Suomi |
| el | Greek | Ελληνικά |
| cs | Czech | Cestina |
| hu | Hungarian | Magyar |
| ro | Romanian | Romana |
| bg | Bulgarian | Български |
| sk | Slovak | Slovencina |
| hr | Croatian | Hrvatski |
| sr | Serbian | Српски |
| sl | Slovenian | Slovenski |
| lt | Lithuanian | Lietuviu |
| lv | Latvian | Latviski |

---

## MCP Tools

### 1. detect_language

Detect the language of any text.

**Parameters:**
- `text` (string): Text to analyze

**Returns:**
- Language code (e.g., 'en', 'es', 'fr')
- Language name
- Confidence score (0.0 to 1.0)
- Whether the language is supported

**Example:**
```python
# Detect language of text
result = await detect_language("Bonjour, comment allez-vous?")
# Returns: French (fr) with 0.90 confidence
```

**Usage via MCP:**
```
Call MCP tool: detect_language
Parameters:
  text: "Bonjour, comment allez-vous?"
```

### 2. get_supported_languages

Get a complete list of all 28 supported languages.

**Parameters:** None

**Returns:**
- Complete list of supported languages with codes and names

**Usage via MCP:**
```
Call MCP tool: get_supported_languages
```

### 3. search_by_language

Search memories with language filtering.

**Parameters:**
- `query` (string): Search query text
- `language` (string): Language code to filter by (e.g., 'en', 'es')
- `user_id` (string): User identifier (default: 'default')
- `agent_id` (string): Agent identifier (default: 'claude-code')
- `limit` (integer): Maximum results (default: 10)

**Returns:**
- Search results filtered by language

**Example:**
```python
# Search only Spanish memories
results = await search_by_language(
    query="trading strategy",
    language="es",
    limit=10
)
```

**Usage via MCP:**
```
Call MCP tool: search_by_language
Parameters:
  query: "trading strategy"
  language: "es"
  limit: 10
```

### 4. get_language_distribution

Get statistics on language distribution across memories.

**Parameters:**
- `user_id` (string): User identifier (default: 'default')
- `agent_id` (string): Agent identifier (default: 'claude-code')

**Returns:**
- Language distribution with counts and percentages

**Example:**
```python
# Get language stats
stats = await get_language_distribution()
# Returns:
# English: 150 memories (75.0%)
# Spanish: 30 memories (15.0%)
# French: 20 memories (10.0%)
```

**Usage via MCP:**
```
Call MCP tool: get_language_distribution
```

### 5. cross_language_search

Search memories in any language with relevance boosting.

Automatically detects query language and boosts results in the same language.

**Parameters:**
- `query` (string): Search query text (language auto-detected)
- `user_id` (string): User identifier (default: 'default')
- `agent_id` (string): Agent identifier (default: 'claude-code')
- `limit` (integer): Maximum results (default: 10)

**Returns:**
- Ranked search results with language match indicators

**Example:**
```python
# Search with English query
results = await cross_language_search(
    query="risk management strategy"
)
# Prioritizes English memories, but includes other languages
```

**Usage via MCP:**
```
Call MCP tool: cross_language_search
Parameters:
  query: "risk management strategy"
  limit: 10
```

### 6. get_search_facets

Get faceted search options for advanced filtering.

**Returns:**
- Faceted counts for:
  - Language
  - Memory type
  - Category

**Example:**
```python
# Get search facets
facets = await get_search_facets()
# Returns:
# LANGUAGE:
#   English: 150
#   Spanish: 30
#   French: 20
# MEMORY_TYPE:
#   feature: 80
#   bugfix: 60
#   decision: 60
# CATEGORY:
#   trading: 100
#   development: 100
```

**Usage via MCP:**
```
Call MCP tool: get_search_facets
```

---

## Automatic Language Detection

All memories are automatically analyzed for language when added.

### How It Works

1. **Text Analysis:** When you add a memory, the system analyzes the text
2. **Language Detection:** Uses langdetect library for accurate detection
3. **Metadata Storage:** Language code and confidence stored in metadata
4. **Search Enhancement:** Enables language-aware search

### Example

```python
# Add memory - language auto-detected
await add_memory(
    content="La estrategia de trading es rentable",
    agent_id="trading-bot"
)

# Metadata automatically includes:
# {
#   "language": "es",
#   "language_name": "Spanish",
#   "language_confidence": 0.90
# }
```

---

## Cross-Language Search

Cross-language search allows you to find memories regardless of language, with smart ranking.

### How It Works

1. **Query Language Detection:** Automatically detects your query language
2. **Relevance Scoring:**
   - Same language as query: **1.0x** boost
   - Different supported language: **0.7x** boost
   - Unsupported language: **0.5x** boost
3. **Ranked Results:** Returns memories sorted by relevance

### Example

```python
# English query searches all memories
results = await cross_language_search(
    query="momentum strategy"
)

# Results:
# 1. [SAME] English: "Momentum trading strategy..."
# 2. [SAME] English: "Strategy for momentum..."
# 3. [DIFF] Spanish: "Estrategia de momento..."
# 4. [DIFF] French: "Strategie de momentum..."
```

---

## Language Filtering

You can filter search results by specific languages.

### Use Cases

- **Single Language Projects:** Only search memories in your project's language
- **Multilingual Teams:** Find memories in specific team languages
- **Translation Work:** Compare memories across languages

### Example

```python
# Only search Spanish memories
spanish_results = await search_by_language(
    query="estrategia",
    language="es"
)

# Only search French memories
french_results = await search_by_language(
    query="strategie",
    language="fr"
)
```

---

## Best Practices

### 1. Consistent Language Use

For best results, use consistent language within memories:

```python
# GOOD: Consistent Spanish
await add_memory(
    content="La estrategia de trading usa indicadores tecnicos",
    agent_id="spanish-bot"
)

# AVOID: Mixed languages
await add_memory(
    content="La trading strategy usa technical indicators",
    agent_id="mixed-bot"
)
```

### 2. Query in Target Language

For language-specific search, query in that language:

```python
# Spanish query for Spanish memories
await search_by_language(
    query="estrategia de momento",  # Spanish keywords
    language="es"
)
```

### 3. Use Cross-Language for Discovery

Use cross-language search when you want to find related concepts across languages:

```python
# Find all momentum-related content
await cross_language_search(
    query="momentum strategy"
)
# Returns results from all languages
```

---

## Performance

### Query Performance

Target performance: **<50ms** for language-filtered queries

**Optimizations:**
- Language-specific database indexes
- Efficient language detection algorithm
- Cached metadata for fast filtering

### Benchmarks

| Operation | Performance |
|-----------|-------------|
| Language detection | <5ms |
| Language-filtered search | <50ms |
| Cross-language search | <100ms |
| Language distribution | <30ms |

---

## Troubleshooting

### Issue: Language Detection Incorrect

**Problem:** Language is detected incorrectly

**Solutions:**
1. Ensure text is long enough (>10 characters)
2. Use consistent language within text
3. Mixed languages may confuse detection

### Issue: No Results in Language

**Problem:** search_by_language returns no results

**Solutions:**
1. Check language code is correct (use get_supported_languages)
2. Verify memories exist in that language
3. Try cross_language_search instead

### Issue: Low Confidence Scores

**Problem:** Language detection has low confidence

**Solutions:**
1. Provide more text for analysis
2. Avoid mixed-language content
3. Use consistent vocabulary

---

## Migration Guide

### Existing Memories

Existing memories without language metadata will:
1. Default to English ('en')
2. Have confidence score of 0.0
3. Still be searchable via cross_language_search

### Re-Detect Languages

To update existing memories with language detection:

```python
# Get all memories
memories = await get_memories(limit=1000)

# Re-detect language for each
for memory in memories:
    lang, conf = language_detector.detect_language(memory['content'])

    # Update metadata
    await update_memory(
        memory_id=memory['id'],
        content=memory['content'],
        metadata={
            **memory.get('metadata', {}),
            'language': lang,
            'language_confidence': conf
        }
    )
```

---

## API Reference

### Python API

```python
from src.language_detector import language_detector
from src.multi_language_search import multi_language_search

# Detect language
lang_code, confidence = language_detector.detect_language(text)
lang_name = language_detector.get_language_name(lang_code)

# Multi-language search
filtered = multi_language_search.search_by_language(
    memories=memories,
    language='es'
)

# Cross-language search
ranked = multi_language_search.cross_language_search(
    query="search text",
    memories=memories
)

# Language distribution
distribution = multi_language_search.get_language_distribution(memories)
```

### MCP Tools

All features are available via MCP tools for Claude Code integration.

---

## Future Enhancements

**Planned Features:**
- Translation support for cross-language queries
- Language-specific embeddings
- Multilingual knowledge graph queries
- Language preference settings per agent
- Automatic translation of summaries

---

## Support

For issues or questions about multi-language features:
1. Check this guide first
2. Review troubleshooting section
3. Check GitHub Issues
4. Create new issue with details

---

**Generated:** 2026-02-06
**Enhanced Cognee Team**
**Sprint:** 9 - Multi-Language & Polish
**Status:** Multi-Language Support COMPLETE
