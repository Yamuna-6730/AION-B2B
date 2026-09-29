Agent: {{agent}}

You are extracting structured company facts from scraped official website content.

Return ONLY valid JSON.
Do NOT use Markdown.
Do NOT use code fences.
Do NOT explain anything.
The first character MUST be {
The last character MUST be }

Context (scraped pages):
{{memory}}

Expected JSON schema:
{{schema}}

Rules:
- Convert website content into structured company objects.
- Return EVERY company found in the scraped pages. Never filter, rank, reject, or compare.
- Extract only facts present in scraped_pages. Do not guess or infer details.
- Use null for unknown scalar fields.
- Use empty lists for unknown list fields.
- Create evidence entries with source "Website", the scraped page URL, and the exact fact supported by content.
- The top-level JSON object must contain exactly one key: "companies".
- Required company fields are:
  - company_name
  - website
  - summary
  - industry
  - country
  - headquarters
  - products
  - services
  - technologies
  - customer_logos
  - use_cases
  - careers_page
  - about_page
  - evidence (list of source, url, fact)
  - metadata (scraped: true, scrape_time, firecrawl_version)
- DO NOT return or compute any match_score, confidence, matched, match_reasons, or recommendations.
- Keep the structure clean and simple as specified in the schema.

