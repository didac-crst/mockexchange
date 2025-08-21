# GitHub PR Tools

This folder contains tools for exporting and analyzing GitHub PR comments, specifically designed for integration with LLMs like Cursor.

## Structure

```
scripts/github-pr-tools/
├── README.md                    # This file
├── export_github_pr_comments.sh # Export PR comments to JSON
├── analyze_pr_comments.py       # Analyze comments and generate LLM prompts
└── output/                      # Generated files (JSON + LLM prompts)
    ├── pr_123_comments.json
    └── pr_123_comments_llm_prompt.txt
```

## Usage

### 1. Setup GitHub Token

Create `scripts/.env` with your GitHub token:
```bash
echo "GITHUB_TOKEN=your_github_token_here" > scripts/.env
```

### 2. Export PR Comments

```bash
make export-pr-comments PR=123
```

This exports PR #123 comments to `output/pr_123_comments.json`.

### 3. Analyze Comments

```bash
# Analyze all reviews (complete context)
make analyze-pr-comments PR=123

# Analyze only latest review (recommended - less confusion for LLM)
make analyze-pr-comments-latest PR=123
```

This generates structured LLM prompts:
- `output/pr_123_comments_llm_prompt.txt` (all reviews)
- `output/pr_123_comments_latest_review_llm_prompt.txt` (latest review only)

### 4. Use with Cursor

Since Cursor is the LLM, you can:

1. **Copy-paste the prompt** into Cursor's chat
2. **Open the generated file** in Cursor and ask it to analyze
3. **Use Cursor's agent** to process the comments directly

## Manual Usage

```bash
# Export comments
./scripts/github-pr-tools/export_github_pr_comments.sh 123

# Analyze comments
python scripts/github-pr-tools/analyze_pr_comments.py scripts/github-pr-tools/output/pr_123_comments.json
```

## Output Files

- **`pr_123_comments.json`**: Raw GitHub API response with all PR comments
- **`pr_123_comments_llm_prompt.txt`**: Structured prompt with all reviews (complete context)
- **`pr_123_comments_latest_review_llm_prompt.txt`**: Structured prompt with latest review only (recommended for LLM)

## Integration with Cursor

The generated LLM prompts are specifically formatted for Cursor's analysis capabilities. You can:

1. Open the prompt file in Cursor
2. Ask Cursor to analyze the PR comments
3. Get actionable suggestions for code improvements
4. Use Cursor's agent to implement the suggested changes

## Cleanup

To clean up generated files:
```bash
rm -rf scripts/github-pr-tools/output/*
```
