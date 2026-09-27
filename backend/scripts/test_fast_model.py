"""
Sanity-check script for Nemotron Fast (nvidia/Nemotron-3_5-Lightning).
Sends 5 distinct code snippets (some with obvious a11y issues, some clean) to call_nemotron_fast
and prints the model's evaluations, token usage, and cumulative cost.
"""
import asyncio
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.services.llm_client import (
    call_nemotron_fast,
    get_total_cost_so_far,
    get_token_usage_stats,
    reset_cost_tracker,
)

SAMPLE_SNIPPETS = [
    {
        "id": "1",
        "name": "Image without alt attribute",
        "expected": "VIOLATION (Missing alternative text on informative image)",
        "code": '<img src="/images/hero-banner.png" className="w-full h-auto" />',
    },
    {
        "id": "2",
        "name": "Icon button with aria-label",
        "expected": "CLEAN (Properly labeled button with aria-hidden icon)",
        "code": '<button type="button" aria-label="Close dialog" onClick={handleClose}><span aria-hidden="true">&times;</span></button>',
    },
    {
        "id": "3",
        "name": "Form input without associated label",
        "expected": "VIOLATION (Missing accessible label; placeholder does not suffice)",
        "code": '<input type="email" placeholder="name@company.com" id="user-email" />',
    },
    {
        "id": "4",
        "name": "Semantic navigation landmark",
        "expected": "CLEAN (Accessible landmark with descriptive label and list items)",
        "code": '<nav aria-label="Main Navigation">\n  <ul>\n    <li><a href="/dashboard">Dashboard</a></li>\n    <li><a href="/settings">Settings</a></li>\n  </ul>\n</nav>',
    },
    {
        "id": "5",
        "name": "Clickable div without button semantics or keyboard support",
        "expected": "VIOLATION (Non-semantic interactive element without role or keyboard listeners)",
        "code": '<div className="custom-submit-btn" onClick={submitForm}>Submit Feedback</div>',
    },
]

SYSTEM_PROMPT = """You are an automated Web Accessibility (WCAG 2.2 AA) code scanner.
Analyze the provided code snippet.
Determine whether there is an accessibility violation.
Respond with a JSON object containing:
- "has_violation": boolean
- "violation_type": string (e.g. "image-alt", "input-label", "aria-roles", or "none")
- "severity": "critical" | "serious" | "moderate" | "minor" | "none"
- "explanation": string (brief, 1-2 sentences explaining why or why not)
- "recommendation": string (actionable advice or fix)
"""

async def run_sanity_checks():
    reset_cost_tracker()
    print("=" * 80)
    print("NEMOTRON FAST (Nemotron-3_5-Lightning) ACCESSIBILITY SANITY CHECK")
    print("=" * 80)

    for item in SAMPLE_SNIPPETS:
        print(f"\n--- [Test {item['id']}/5] {item['name']} ---")
        print(f"Code Snippet:\n  {item['code']}")
        print(f"Expected Assessment: {item['expected']}")

        user_prompt = f"Inspect this UI code snippet for accessibility issues:\n\n```jsx\n{item['code']}\n```"

        try:
            response = await call_nemotron_fast(
                prompt=user_prompt,
                system_prompt=SYSTEM_PROMPT,
                max_tokens=1000,
                response_format="json",
            )
            print("\nModel Evaluation (JSON):")
            print(response.strip())
        except Exception as e:
            print(f"Error calling Nemotron Fast: {e}")

    stats = get_token_usage_stats()
    print("\n" + "=" * 80)
    print("RUN SUMMARY & COST BREAKDOWN")
    print("=" * 80)
    print(f"Total API Calls:         {stats['total_calls']}")
    print(f"Total Input Tokens:      {stats['total_input_tokens']}")
    print(f"Total Output Tokens:     {stats['total_output_tokens']}")
    print(f"Total Tokens:            {stats['total_tokens']}")
    print(f"Total Estimated Spend:   ${stats['total_cost_usd']:.6f} USD")
    print(f"Average Cost Per Snippet: ${(stats['total_cost_usd'] / max(1, stats['total_calls'])):.6f} USD")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_sanity_checks())
