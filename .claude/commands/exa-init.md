# Exa Search API Reference

> **Canonical reference:** https://exa.ai/docs/reference/search-api-guide-for-coding-agents
> If anything below looks outdated or contradicts real API behavior, fetch that URL — it is the source of truth for search types, parameters, and response shape.
> Fetched 2026-06-07.

## Search Types & Use Cases

Six search variants:

- **`auto`** (default): "Balance of speed and quality" — recommended for most queries
- **`fast`**: ~450ms latency; "Optimized search models with good relevance"
- **`instant`**: ~250ms; "Real-time apps (chat, voice, autocomplete)"
- **`deep-lite`**: ~4s; "Lightweight synthesis; cheaper than full `deep`"
- **`deep`**: 4-15s; "Multi-step planning with structured outputs"
- **`deep-reasoning`**: 12-40s; "Maximum reasoning capability per step"

> Start with `auto` unless you have a specific latency or synthesis requirement.

---

## Core Parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `query` | string | Required | Natural language search query. Supports long, semantically rich descriptions |
| `type` | string | `auto` | Search method variant |
| `stream` | boolean | false | Returns `text/event-stream` with OpenAI-compatible chat completion chunks |
| `numResults` | integer | 10 | Range: 1-100 |
| `category` | string | — | `company`, `people`, `research paper`, `news`, `personal site`, `financial report` |
| `userLocation` | string | — | Two-letter ISO country code |
| `includeDomains` | string[] | — | Max 1200 domains |
| `excludeDomains` | string[] | — | Max 1200 domains |
| `startPublishedDate` | string | — | ISO 8601 format |
| `endPublishedDate` | string | — | ISO 8601 format |
| `moderation` | boolean | false | Filter unsafe content from results |
| `additionalQueries` | string[] | — | Extra query variations for deep-search variants |
| `systemPrompt` | string | — | Instructions guiding synthesized output |
| `outputSchema` | object | — | JSON schema for synthesized `output.content` |
| `compliance` | string | — | Enterprise-only; set to `"hipaa"` for HIPAA mode |

### Nested Contents Parameters

All content retrieval options nest under `contents`:

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `contents.text` | boolean/object | — | Return full page text as markdown |
| `contents.highlights` | boolean/object | — | Return key excerpts relevant to query |
| `contents.summary` | boolean/object | — | Return LLM-generated summary |
| `contents.livecrawlTimeout` | integer | 10000ms | Timeout for livecrawling |
| `contents.maxAgeHours` | integer | — | `0`=always livecrawl, `-1`=never, omit for default |
| `contents.subpages` | integer | 0 | Number of subpages to crawl |
| `contents.subpageTarget` | string/string[] | — | Keywords to prioritize in subpage selection |
| `contents.extras.links` | integer | 0 | URLs to extract per page |
| `contents.extras.imageLinks` | integer | 0 | Image URLs to extract per page |

### Text Object Options

When using `contents.text` as an object:

| Option | Type | Default | Purpose |
|--------|------|---------|---------|
| `maxCharacters` | integer | — | Character limit for returned text |
| `includeHtmlTags` | boolean | false | Preserve HTML tags in output |
| `verbosity` | string | `compact` | Values: `compact`, `standard`, `full` |
| `includeSections` | string[] | — | Allowed: `header`, `navigation`, `banner`, `body`, `sidebar`, `footer`, `metadata` |
| `excludeSections` | string[] | — | Same section options as include |

### Highlights Object Options

> Prefer `highlights: true` for the highest-quality default.

| Option | Type | Default | Purpose |
|--------|------|---------|---------|
| `query` | string | — | Custom query that guides which highlights are returned |
| `maxCharacters` | integer | — | Cap on total highlight characters per URL |

### Summary Object Options

| Option | Type | Default | Purpose |
|--------|------|---------|---------|
| `query` | string | — | Custom summary query |
| `schema` | object | — | JSON Schema for structured output |

---

## Token Efficiency Guidance

| Mode | Best For |
|------|----------|
| `text` | Deep analysis, when you need full context, broad research |
| `highlights` | Factual questions, specific lookups, multi-step agent workflows |
| `summary` | Quick overviews, structured extraction, tighter output size control |

> Use `highlights` for agent workflows. When building multi-step agents that make repeated search calls, `highlights` provide the most relevant excerpts without flooding context windows.

For real-time needs: set `contents.maxAgeHours: 0` to force livecrawl, knowing that this may increase latency.

---

## Category Restrictions

| Category | Supports Date Filters | Supports excludeDomains | Supports includeDomains |
|----------|----------------------|------------------------|-------------------------|
| `company` | ❌ | ❌ | ✅ |
| `people` | ❌ | ❌ | ✅ (LinkedIn only) |
| `research paper` | ✅ | ✅ | ✅ |
| `news` | ✅ | ✅ | ✅ |
| `personal site` | ✅ | ✅ | ✅ |
| `financial report` | ✅ | ✅ | ✅ |

---

## Output Schema

For any search type, use `outputSchema` to control the shape of `output.content`:

- Text: `{"type": "text", "description": "..."}`
- Structured: `{"type": "object", "properties": {...}, "required": [...]}`

Constraints: max nesting depth 2, max total properties 10.

> Do NOT include citation fields in your schema — `/search` returns grounding data automatically in `output.grounding`.

---

## Response Schema

```json
{
  "requestId": "string",
  "searchType": "string",
  "results": [
    {
      "title": "string",
      "url": "string",
      "id": "string",
      "publishedDate": "ISO 8601 or null",
      "author": "string or null",
      "image": "string",
      "favicon": "string",
      "text": "string (if requested)",
      "highlights": ["string"],
      "highlightScores": [0.46],
      "summary": "string (if requested)",
      "subpages": [],
      "extras": {
        "links": ["https://..."]
      }
    }
  ],
  "output": {
    "content": "string or object (deep search only)",
    "grounding": [
      {
        "field": "string",
        "citations": [{"url": "string", "title": "string"}],
        "confidence": "high|medium|low"
      }
    ]
  },
  "costDollars": {
    "total": 0.007
  }
}
```

### Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `requestId` | string | Unique request identifier |
| `searchType` | string | Which search type was used (for `auto` queries) |
| `results` | array | List of result objects |
| `results[].title` | string | Page title |
| `results[].url` | string | Page URL |
| `results[].id` | string | Document ID (same as URL). Use with `/contents` endpoint |
| `results[].publishedDate` | string/null | Estimated publication date (YYYY-MM-DD format) |
| `results[].author` | string/null | Author if available |
| `results[].image` | string | Associated image URL if available |
| `results[].favicon` | string | Favicon URL for the domain |
| `results[].text` | string | Full page text (if `contents.text` requested) |
| `results[].highlights` | string[] | Key excerpts (if `contents.highlights` requested) |
| `results[].highlightScores` | float[] | Cosine similarity scores for each highlight |
| `results[].summary` | string | LLM summary (if `contents.summary` requested) |
| `results[].subpages` | array | Nested results from subpage crawling |
| `results[].extras.links` | string[] | Extracted links from the page |
| `output` | object | Synthesized output object (when `outputSchema` provided) |
| `output.content` | string/object | String by default, object when `outputSchema` provided |
| `output.grounding` | array | Field-level citations and confidence labels |
| `costDollars.total` | float | Total dollar cost for the request |

---

## Streaming Response

When `stream: true`, `/search` returns `text/event-stream` instead of a JSON body. Each `data:` frame contains an OpenAI-compatible `chat.completion.chunk` payload.

```json
{
  "object": "chat.completion.chunk",
  "choices": [
    {
      "index": 0,
      "delta": {
        "role": "assistant",
        "content": "..."
      },
      "finish_reason": null
    }
  ]
}
```

---

## Latency Characteristics

Base latencies by type:

| Type | Latency | Use Case |
|------|---------|----------|
| `instant` | ~250ms | Real-time apps |
| `fast` | ~450ms | Good speed/relevance balance |
| `auto` | ~1s | Default; router picks variant |
| `deep-lite` | 4s | Lightweight synthesis |
| `deep` | 4-15s | Multi-step planning |
| `deep-reasoning` | 12-40s | Maximum reasoning |

Modifiers that stack on top:
- `outputSchema` present: adds synthesis latency to any type
- `contents.maxAgeHours: 720`: returns cached version much faster

---

## Python SDK

```bash
pip install exa-py
```

```python
from exa_py import Exa
exa = Exa(api_key="YOUR_API_KEY")
result = exa.search("latest developments in LLMs", contents={"highlights": True})
```

**Python naming convention:** snake_case for all parameters.
- `numResults` → `num_results`
- `maxAgeHours` → `max_age_hours`
- `outputSchema` → `output_schema`
- Nested dictionaries also use snake_case: `contents={"text": {"max_characters": 4000}}`

---

## JavaScript/TypeScript SDK

```bash
npm install exa-js
```

```javascript
import Exa from "exa-js";
const exa = new Exa("YOUR_API_KEY");
const result = await exa.search("latest developments in LLMs", {
  contents: { highlights: true },
});
```

**JavaScript naming convention:** camelCase for all parameters (same as JSON/cURL).

---

## cURL

```bash
curl -X POST "https://api.exa.ai/search" \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"query": "latest developments in LLMs", "contents": {"highlights": true}}'
```

---

## Complete Request Examples

### Basic Search with Highlights

```json
{
  "query": "recent breakthroughs in quantum computing",
  "type": "auto",
  "numResults": 5,
  "contents": {
    "highlights": true
  }
}
```

### Domain-Filtered News Search

```json
{
  "query": "AI regulation policy updates",
  "type": "auto",
  "category": "news",
  "numResults": 10,
  "includeDomains": ["reuters.com", "nytimes.com", "bbc.com"],
  "startPublishedDate": "2025-01-01",
  "contents": {
    "highlights": true
  }
}
```

### Deep Search with Structured Output

```json
{
  "query": "compare the latest frontier AI model releases",
  "type": "deep",
  "systemPrompt": "Prefer official sources and avoid duplicate results",
  "outputSchema": {
    "type": "object",
    "required": ["models"],
    "properties": {
      "models": {
        "type": "array",
        "items": {
          "type": "object",
          "required": ["name", "notable_claims"],
          "properties": {
            "name": { "type": "string" },
            "notable_claims": { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    }
  }
}
```

### Company Research

```json
{
  "query": "agtech companies in the US that have raised series A",
  "type": "auto",
  "category": "company",
  "numResults": 10,
  "contents": {
    "highlights": true
  }
}
```

---

## Common Mistakes & Corrections

| ❌ Wrong | ✅ Correct |
|---------|-----------|
| `useAutoprompt: true` | Remove entirely; deprecated and non-functional |
| `includeUrls` / `excludeUrls` | Use `includeDomains` / `excludeDomains` instead |
| `text: true` (top-level) | Nest: `"contents": {"text": true}` |
| `summary: true` (top-level) | Nest: `"contents": {"summary": true}` |
| `highlights: {...}` (top-level) | Nest: `"contents": {"highlights": {...}}` |
| `numSentences` | Deprecated; use `highlights: true` |
| `highlightsPerUrl` | Deprecated; use `highlights: true` |
| `tokensNum` | Remove; use `contents.text.maxCharacters` instead |
| `livecrawl: "always"` | Use `contents.maxAgeHours: 0` instead |
| `excludeDomains` with `category: "company"` or `"people"` | Remove; unsupported for these categories |

---

## Patterns & Best Practices

1. **Highlights for agents:** Use `highlights` over `text` for agent workflows. Highlights return 10x fewer tokens with the most relevant excerpts.
2. **Auto is default:** `auto` is almost always the right `type`. Only use `fast`/`instant` when latency matters more than quality.
3. **Livecrawl overhead:** `maxAgeHours: 0` forces livecrawl on every result. This increases latency. Omit `maxAgeHours` for the default.
4. **Category limits:** `category: "company"` and `category: "people"` disable many filters. Date filters and `excludeDomains` return 400 errors.
5. **Schema everywhere:** `outputSchema` works with every search type. When you need more reasoning depth, prefer `deep-lite`, `deep`, or `deep-reasoning`.
6. **Separate controls:** `systemPrompt` controls behavior, `outputSchema` controls shape.
7. **Streaming mode:** `stream: true` switches `/search` to SSE mode. Expect OpenAI-compatible chat completion chunks.
8. **Combine modes:** You can request `text`, `highlights`, and `summary` in the same call.

---

## Troubleshooting

**Results too slow?**
1. Use `type: "fast"` or `type: "instant"`
2. Reduce `numResults`
3. Skip contents if you only need URLs

**No results?**
1. Remove filters (date, domain restrictions)
2. Simplify query
3. Try `type: "auto"` — has fallback mechanisms

---

## Error Handling

| HTTP Status | Meaning |
|-------------|---------|
| 400 | Bad request — invalid parameters, unsupported filter for category |
| 401 | Invalid or missing API key |
| 422 | Validation error — check parameter types and constraints |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

Error response format:

```json
{
  "error": "Error message describing the issue"
}
```

---

## Resources

- **Docs:** https://exa.ai/docs
- **Dashboard:** https://dashboard.exa.ai
- **API Status:** https://status.exa.ai
- **API Keys:** https://dashboard.exa.ai/api-keys
- **Full Documentation Index:** https://exa.ai/docs/llms.txt
- **Endpoint:** `POST https://api.exa.ai/search`
- **Authentication:** Pass API key via `x-api-key` header
