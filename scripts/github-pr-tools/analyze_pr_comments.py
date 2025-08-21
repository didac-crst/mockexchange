#!/usr/bin/env python3
"""
Example script showing how to analyze exported PR comments with an LLM.

This script demonstrates how to use the JSON output from:
    make export-pr-comments PR=123

Usage:
    python scripts/github-pr-tools/analyze_pr_comments.py scripts/github-pr-tools/output/pr_123_comments.json
"""

import json
import sys
from pathlib import Path
from typing import Any


def load_pr_comments(file_path: str) -> list[dict[str, Any]]:
    """Load PR comments from JSON file."""
    with open(file_path) as f:
        return json.load(f)


def filter_latest_review(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter comments to only include the latest review."""
    if not comments:
        return comments

    # Group comments by review ID
    reviews: dict[int, list[dict[str, Any]]] = {}
    for comment in comments:
        review_id = comment.get("pull_request_review_id")
        if review_id:
            if review_id not in reviews:
                reviews[review_id] = []
            reviews[review_id].append(comment)

    if not reviews:
        return comments

    # Find the latest review (highest review ID)
    latest_review_id = max(reviews.keys())
    latest_comments = reviews[latest_review_id]

    print(f"📊 Found {len(reviews)} reviews:")
    for review_id, review_comments in reviews.items():
        print(f"   - Review {review_id}: {len(review_comments)} comments")
    print(f"🎯 Using latest review {latest_review_id} with {len(latest_comments)} comments")

    return latest_comments


def analyze_comments(comments: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze PR comments and extract insights."""
    analysis: dict[str, Any] = {
        "total_comments": len(comments),
        "commenters": set[str](),
        "suggestion_types": {
            "refactor": 0,
            "bug": 0,
            "security": 0,
            "performance": 0,
            "documentation": 0,
            "other": 0,
        },
        "files_affected": set[str](),
        "severity_levels": {"high": 0, "medium": 0, "low": 0},
    }

    for comment in comments:
        # Extract commenter
        if "user" in comment and "login" in comment["user"]:
            analysis["commenters"].add(comment["user"]["login"])

        # Extract file path
        if "path" in comment:
            analysis["files_affected"].add(comment["path"])

        # Analyze comment body for suggestion types
        body = comment.get("body", "").lower()

        if "refactor" in body or "suggestion" in body:
            analysis["suggestion_types"]["refactor"] += 1
        elif "bug" in body or "error" in body or "fix" in body:
            analysis["suggestion_types"]["bug"] += 1
        elif "security" in body:
            analysis["suggestion_types"]["security"] += 1
        elif "performance" in body or "slow" in body:
            analysis["suggestion_types"]["performance"] += 1
        elif "documentation" in body or "readme" in body:
            analysis["suggestion_types"]["documentation"] += 1
        else:
            analysis["suggestion_types"]["other"] += 1

        # Analyze severity (simple heuristic)
        if any(word in body for word in ["critical", "security", "bug", "error"]):
            analysis["severity_levels"]["high"] += 1
        elif any(word in body for word in ["warning", "potential", "consider"]):
            analysis["severity_levels"]["medium"] += 1
        else:
            analysis["severity_levels"]["low"] += 1

    # Convert sets to lists for JSON serialization
    analysis["commenters"] = list(analysis["commenters"])
    analysis["files_affected"] = list(analysis["files_affected"])

    return analysis


def generate_llm_prompt(comments: list[dict[str, Any]], analysis: dict[str, Any]) -> str:
    """Generate a prompt for an LLM to analyze the PR comments."""

    prompt = f"""# PR Code Review Analysis

## Summary
- **Total Comments**: {analysis['total_comments']}
- **Commenters**: {', '.join(analysis['commenters'])}
- **Files Affected**: {len(analysis['files_affected'])} files

## Comment Types
- Refactor Suggestions: {analysis['suggestion_types']['refactor']}
- Bug Fixes: {analysis['suggestion_types']['bug']}
- Security Issues: {analysis['suggestion_types']['security']}
- Performance: {analysis['suggestion_types']['performance']}
- Documentation: {analysis['suggestion_types']['documentation']}
- Other: {analysis['suggestion_types']['other']}

## Severity Distribution
- High Priority: {analysis['severity_levels']['high']}
- Medium Priority: {analysis['severity_levels']['medium']}
- Low Priority: {analysis['severity_levels']['low']}

## Detailed Comments

"""

    for i, comment in enumerate(comments, 1):
        prompt += f"""### Comment {i}
**File**: {comment.get('path', 'Unknown')}
**Line**: {comment.get('line', 'Unknown')}
**Author**: {comment.get('user', {}).get('login', 'Unknown')}
**Type**: {comment.get('subject_type', 'Unknown')}

{comment.get('body', 'No body')}

---
"""

    prompt += """
## Your Task
Please analyze these PR comments and provide:

1. **Priority Assessment**: Which comments should be addressed first?
2. **Action Items**: Specific tasks to implement the suggestions
3. **Code Examples**: Show how to implement the suggested changes
4. **Risk Assessment**: Any potential issues with the suggestions
5. **Summary**: Overall quality and completeness of the review

Focus on actionable, specific recommendations.
"""

    return prompt


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_pr_comments.py <comments_json_file> [--latest-only]")
        print(
            "Example: python scripts/github-pr-tools/analyze_pr_comments.py scripts/github-pr-tools/output/pr_123_comments.json"
        )
        print(
            "Example: python scripts/github-pr-tools/analyze_pr_comments.py scripts/github-pr-tools/output/pr_123_comments.json --latest-only"
        )
        sys.exit(1)

    file_path = sys.argv[1]
    latest_only = "--latest-only" in sys.argv

    if not Path(file_path).exists():
        print(f"Error: File {file_path} not found")
        print("First export PR comments with: make export-pr-comments PR=123")
        sys.exit(1)

    try:
        # Load comments
        comments = load_pr_comments(file_path)

        # Filter to latest review if requested
        if latest_only:
            comments = filter_latest_review(comments)
            output_suffix = "_latest_review_llm_prompt.txt"
        else:
            output_suffix = "_llm_prompt.txt"

        # Analyze comments
        analysis = analyze_comments(comments)

        # Generate LLM prompt
        prompt = generate_llm_prompt(comments, analysis)

        # Save prompt to file
        output_file = file_path.replace(".json", output_suffix)
        with open(output_file, "w") as f:
            f.write(prompt)

        print("✅ Analysis complete!")
        print("📊 Summary:")
        print(
            f"   - {analysis['total_comments']} comments from {len(analysis['commenters'])} reviewers"
        )
        print(f"   - {len(analysis['files_affected'])} files affected")
        print(
            f"   - {analysis['suggestion_types']['bug']} bug fixes, {analysis['suggestion_types']['refactor']} refactor suggestions"
        )
        print(f"   - {analysis['severity_levels']['high']} high priority items")
        print("")
        print(f"🤖 LLM prompt saved to: {output_file}")
        if latest_only:
            print("🎯 Using latest review only (less confusion for LLM)")
        else:
            print("📋 Using all reviews (complete context)")
        print("💡 Open the file in Cursor or copy-paste the content into Cursor's chat")

    except Exception as e:
        print(f"Error analyzing comments: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
