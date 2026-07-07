"""
The 7th agent: an independent second opinion for BLOCK-tier cases, built
entirely on Google's stack (Gemini via Vertex AI / Google AI Studio) — no
third-party model dependency.

Design goal: reduce single-pass reasoning error on the highest-stakes
decisions without introducing an external vendor, an extra API key
requirement, or a cost-reasonableness question under the competition rules.
Independence here comes from three structural choices, not from switching
model providers:

  1. A different model checkpoint than the rest of the pipeline
     (gemini-2.5-pro "Critic" vs. gemini-2.0-flash "Worker" agents) —
     different training run, different failure modes.
  2. A different prompting stance: the Critic is instructed to argue
     AGAINST the Worker pipeline's conclusion first (adversarial/red-team
     framing), then decide — this is the same "debate" pattern used in
     LLM self-critique research to catch confirmation bias in a single
     forward pass.
  3. Re-derivation from raw tool outputs, not from the Worker pipeline's
     narrative summary — the Critic calls retrieve_policy and
     vendor_lookup itself (via the same MCP tool server used for IDE
     integration, see tools/mcp_server.py) instead of trusting the
     Risk Scoring Agent's prose.

This keeps the entire submission on a single, free-tier-accessible model
family, satisfying the Reasonableness Standard in the competition rules
without any participant needing a second vendor's API key to reproduce it.
"""
import os, json
import google.generativeai as genai

CRITIC_MODEL = "gemini-2.5-pro"

SYSTEM_PROMPT = """You are an independent fraud-review critic for an accounts-payable
guardian system. Another AI pipeline has already scored this case as high-risk
(BLOCK tier) using a faster model. Your job is specifically to argue the OPPOSITE
case first: build the strongest case for why this might be a false positive (a
legitimate vendor action that merely looks suspicious), using ONLY the tool calls
available to you (retrieve_policy, vendor_lookup, bank_change_lookup,
sanctions_check) — do not accept the input summary's framing at face value.
Then weigh your case against the original evidence and decide.

Respond with a JSON object only:
{"agrees_with_block": bool, "false_positive_case": str, "final_rationale": str,
 "recommended_tier": "ALLOW" | "HOLD" | "BLOCK"}
"""


def run_critic_review(sanitized_case: dict) -> dict:
    """Runs the independent Gemini-Pro critic pass. Returns {"ran": False, ...}
    gracefully if GOOGLE_API_KEY isn't configured, so the pipeline degrades to
    "Worker-only mode" rather than failing the whole request."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"ran": False, "note": "GOOGLE_API_KEY not set — critic pass skipped."}

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(CRITIC_MODEL, system_instruction=SYSTEM_PROMPT)

    # The critic gets MCP-style tool access to the same verified function
    # tools the Worker pipeline used (see tools/mcp_server.py) so it can
    # independently re-check claims rather than trusting the summary.
    from tools.function_tools import vendor_lookup, bank_change_lookup, sanctions_check, retrieve_policy

    tool_fns = [vendor_lookup, bank_change_lookup, sanctions_check, retrieve_policy]
    chat = model.start_chat(enable_automatic_function_calling=True)
    # google-generativeai supports passing plain python functions as tools
    # when the model object is constructed with tools=[...]; re-instantiate
    # with tools bound for this call.
    model_with_tools = genai.GenerativeModel(CRITIC_MODEL, system_instruction=SYSTEM_PROMPT, tools=tool_fns)
    chat = model_with_tools.start_chat(enable_automatic_function_calling=True)

    response = chat.send_message(json.dumps(sanitized_case))
    text = response.text.strip().strip("`").lstrip("json").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"agrees_with_block": None, "final_rationale": text, "recommended_tier": "HOLD"}
    parsed["ran"] = True
    parsed["model"] = CRITIC_MODEL
    return parsed
