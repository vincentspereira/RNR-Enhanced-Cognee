# LLM Prompt Templates for Enhanced Cognee

This directory contains comprehensive prompt templates for all LLM-powered operations in Enhanced Cognee.

## Available Templates

### 1. summarization.txt
**Purpose:** Generate concise summaries of long-form memories while preserving critical information.

**Use Cases:**
- Monthly memory summarization (old memories)
- Category-based summarization
- Large memory optimization

**Key Features:**
- Preserves facts, names, dates, numbers
- Maintains context and purpose
- Removes redundancy
- Structured JSON output with key points, entities, action items
- Few-shot examples for different content types

**Output Schema:**
```json
{
  "summary": "string",
  "key_points": ["string"],
  "entities": {"people": [], "organizations": [], "systems": []},
  "action_items": ["string"],
  "tags": ["string"],
  "confidence_score": 0.95,
  "original_length": 2500,
  "summary_length": 350
}
```

---

### 2. deduplication.txt
**Purpose:** Detect duplicate, near-duplicate, or distinct memories for intelligent merging.

**Use Cases:**
- Weekly automated deduplication
- Manual duplicate checking
- Memory merge recommendations

**Key Features:**
- Categorizes: exact, near, related, or distinct
- Similarity scoring (0.0-1.0)
- Merge recommendations with strategies
- Entity overlap analysis
- Temporal progression detection

**Output Schema:**
```json
{
  "are_duplicates": true,
  "duplicate_type": "exact|near|related|distinct",
  "similarity_score": 0.92,
  "confidence": 0.95,
  "reasoning": "explanation",
  "key_differences": ["string"],
  "key_similarities": ["string"],
  "merge_recommendation": "keep_both|merge|keep_newer",
  "merged_content": "string (if merge)"
}
```

---

### 3. extraction.txt
**Purpose:** Extract entities and relationships to build knowledge graph.

**Use Cases:**
- Automatic entity extraction
- Knowledge graph construction
- Semantic search enhancement
- Relationship mapping

**Key Features:**
- 10 entity categories (people, orgs, systems, files, technologies, etc.)
- Relationship extraction
- Context and metadata
- Confidence scoring
- Few-shot examples for different content types

**Output Schema:**
```json
{
  "entities": {
    "people": [{"name": "string", "confidence": 0.95}],
    "organizations": [{"name": "string", "confidence": 0.98}],
    "systems": [{"name": "string", "confidence": 0.99}],
    "technologies": [{"name": "string", "confidence": 0.97}],
    "files": [{"name": "string", "confidence": 0.96}],
    "dates": [{"text": "string", "confidence": 0.99}],
    "concepts": [{"name": "string", "confidence": 0.92}]
  },
  "relationships": [
    {"source": "string", "target": "string", "type": "uses", "confidence": 0.95}
  ]
}
```

---

### 4. intent_detection.txt
**Purpose:** Detect user intent when updating existing memories.

**Use Cases:**
- Smart memory updates
- Automatic merge vs replace decisions
- Version control logic
- Change tracking

**Key Features:**
- 8 intent categories (correction, enhancement, update, refactoring, merge, replacement, clarification, abstraction)
- Contradiction detection
- Addition/removal tracking
- Recommended actions (replace, merge, keep_both, version)
- Temporal analysis

**Output Schema:**
```json
{
  "intent": "correction|enhancement|update|refactoring|...",
  "confidence": 0.92,
  "reasoning": "explanation",
  "contradictions": [{"old_statement": "string", "new_statement": "string"}],
  "additions": ["string"],
  "removals": ["string"],
  "recommendations": {
    "action": "replace|merge|keep_both",
    "explanation": "why"
  }
}
```

---

### 5. quality_check.txt
**Purpose:** Assess memory quality for curation and improvement.

**Use Cases:**
- Automatic quality assessment
- Memory curation
- Enhancement recommendations
- Low-quality memory detection

**Key Features:**
- 6 quality dimensions (clarity, completeness, accuracy, actionability, value, timeliness)
- 0-10 scoring with detailed reasoning
- Strengths and weaknesses analysis
- Improvement suggestions
- Issue detection (critical, high, medium, low)
- Recommendations (keep, enhance, summarize, expand, delete)

**Output Schema:**
```json
{
  "overall_quality": {
    "score": 8.2,
    "rating": "high",
    "confidence": 0.90
  },
  "dimension_scores": {
    "clarity": {"score": 9, "reasoning": "explanation"},
    "completeness": {"score": 7, "reasoning": "explanation"},
    "accuracy": {"score": 8, "reasoning": "explanation"},
    "actionability": {"score": 6, "reasoning": "explanation"},
    "value": {"score": 9, "reasoning": "explanation"},
    "timeliness": {"score": 10, "reasoning": "explanation"}
  },
  "strengths": ["string"],
  "weaknesses": ["string"],
  "improvement_suggestions": ["string"],
  "issues": [
    {"severity": "low|medium|high|critical", "type": "string", "description": "string"}
  ],
  "recommendations": {
    "should_keep": true,
    "should_summarize": false,
    "should_expand": true,
    "action": "keep_as_is|keep_and_enhance|request_enhancement|..."
  }
}
```

---

## Usage Examples

### Using a Template

```python
from pathlib import Path

# Load template
template_path = Path("src/llm/prompts/summarization.txt")
with open(template_path, 'r') as f:
    prompt_template = f.read()

# Format with actual data
prompt = prompt_template.format(
    content=memory_content,
    memory_id=memory_id,
    agent_id=agent_id,
    category=category,
    tags=tags,
    created_at=created_at,
    target_ratio=0.3,
    original_length=len(memory_content),
    target_length=int(len(memory_content) * 0.3)
)

# Call LLM
response = await llm_client.call(prompt)
result = json.loads(response)
```

### With Error Handling

```python
async def summarize_memory(memory_content: str, memory_id: str) -> dict:
    """Summarize a memory using LLM."""
    try:
        # Load and format template
        template = load_prompt_template("summarization.txt")
        prompt = template.format(
            content=memory_content,
            memory_id=memory_id,
            # ... other parameters
        )

        # Call LLM with timeout
        response = await asyncio.wait_for(
            llm_client.call(prompt),
            timeout=30.0
        )

        # Parse and validate response
        result = json.loads(response)
        validate_summary_result(result)

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from LLM: {e}")
        return {"error": "Failed to parse LLM response"}

    except asyncio.TimeoutError:
        logger.error("LLM call timed out")
        return {"error": "LLM timeout"}
```

---

## Template Structure

Each template follows this structure:

1. **System Prompt** - Role and behavior definition
2. **Guidelines** - Detailed instructions for the task
3. **Output Format** - JSON schema specification
4. **Few-Shot Examples** - 3-8 comprehensive examples
5. **User Prompt Template** - Format string with placeholders
6. **Edge Cases** - Special scenarios handling
7. **Quality Indicators** - Self-evaluation criteria

---

## Best Practices

### When Creating New Templates

1. **Be Specific** - Clearly define the task and expected output
2. **Provide Examples** - Include 5+ few-shot examples covering edge cases
3. **Use JSON Output** - Structured output is easier to parse and validate
4. **Include Confidence Scores** - Help assess result reliability
5. **Handle Edge Cases** - Document how to handle unusual inputs
6. **Add Quality Checks** - Include self-evaluation criteria

### When Using Templates

1. **Validate Placeholders** - Ensure all {variables} are provided
2. **Set Timeouts** - LLM calls can hang, use timeouts
3. **Parse Carefully** - Validate JSON structure before using
4. **Log Failures** - Track LLM failures for debugging
5. **Cache Results** - Cache LLM responses when appropriate
6. **Monitor Costs** - Track token usage and costs

---

## Template Maintenance

### Version Control
- All templates are version-controlled in this directory
- Document changes in commit messages
- Update template version when making breaking changes

### Testing
- Test templates with real data before deploying
- Validate output schema matches expectations
- Check for edge cases
- Monitor LLM performance and accuracy

### Optimization
- Monitor prompt length (longer prompts = more cost)
- Balance detail vs brevity
- Consider token limits for different models
- A/B test template variations

---

## Model Compatibility

These templates are designed for:
- **Primary:** Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)
- **Compatible:** Claude 3 Opus, Claude 3 Haiku
- **Adaptable:** GPT-4, GPT-4 Turbo (may require minor adjustments)

### Model-Specific Notes

**Claude 3.5 Sonnet:**
- Optimal performance
- Follows JSON schema well
- Good with few-shot learning

**GPT-4:**
- May need temperature adjustment (0.3-0.7)
- Ensure JSON format is enforced
- Consider using function calling for structured output

---

## Performance Metrics

Track these metrics for each template:

- **Success Rate:** % of calls returning valid JSON
- **Accuracy:** Human-validated accuracy score
- **Latency:** Average response time
- **Token Usage:** Average input/output tokens
- **Cost:** Average cost per call
- **Confidence Calibration:** How well confidence scores match actual accuracy

---

## Troubleshooting

### Common Issues

**Invalid JSON Response:**
- Increase emphasis on JSON format in system prompt
- Use JSON mode if available (GPT-4)
- Add JSON schema validation in prompt
- Implement retry logic

**Low Confidence Scores:**
- Provide more context in user prompt
- Adjust few-shot examples
- Clarify task in system prompt
- Consider if task is too ambiguous

**High Latency:**
- Shorten prompt (remove unnecessary examples)
- Reduce context length
- Use faster model (Haiku vs Sonnet)
- Implement caching

**Poor Quality Output:**
- Add more few-shot examples
- Improve prompt clarity
- Adjust temperature (lower = more deterministic)
- Consider if task is appropriate for LLM

---

## Contributing

When adding new templates:

1. Follow the established structure
2. Include comprehensive examples
3. Document use cases clearly
4. Add to this README
5. Test with real data
6. Update any related code

---

**Last Updated:** 2026-02-06
**Version:** 1.0.0
**Maintained By:** Enhanced Cognee Team
