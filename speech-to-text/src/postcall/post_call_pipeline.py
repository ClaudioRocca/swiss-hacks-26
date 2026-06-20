"""
================================================================================
RM INTELLIGENCE PLATFORM  -  POST-CALL INTELLIGENCE PIPELINE
SwissHack / Julius Bär Challenge
================================================================================

Questo modulo contiene l'intera pipeline post-call.

FLUSSO GENERALE:
    1. La call finisce -> abbiamo la trascrizione (stringa)
    2. Il backend interroga il database SQL -> estrae i dati del cliente
    3. Costruiamo UN prompt grande con: trascrizione + dati cliente + news
    4. UNA chiamata a GPT-4o -> restituisce un JSON completo per tutti i widget
    5. (separato) La Financial API recupera le news per i topic estratti
    6. (separato, on-demand) Generazione della proposal quando l'RM clicca

NOTA IMPORTANTE:
    GPT-4o NON accede al database da solo. Noi prepariamo tutti i dati PRIMA
    e glieli passiamo come testo dentro al prompt. Lui ragiona solo su ciò
    che riceve.
================================================================================
"""

import json
from openai import OpenAI

client = OpenAI(api_key="TUA_API_KEY")  # <-- inserire la chiave reale


# =============================================================================
# STEP 1 - RECUPERO DATI DEL CLIENTE DAL DATABASE
# =============================================================================
# Questa funzione è uno SCHELETRO. Va adattata alle vostre query SQL reali.
# L'obiettivo è restituire un dizionario Python pulito con tutto ciò che serve.

def get_client_context(client_id: str, db_connection) -> dict:
    """
    Interroga il database e restituisce un dizionario con lo storico del cliente.
    Adattate le query alla vostra struttura SQL reale.
    """
    cursor = db_connection.cursor()

    # --- Profilo da onboarding ---
    cursor.execute(
        "SELECT risk_profile, investment_goals, preferences "
        "FROM clients WHERE id = %s", (client_id,)
    )
    profile = cursor.fetchone()

    # --- Portafoglio attuale (posizioni e pesi) ---
    cursor.execute(
        "SELECT asset_class, region, weight_pct "
        "FROM portfolio WHERE client_id = %s", (client_id,)
    )
    portfolio = cursor.fetchall()

    # --- Storico delle call precedenti (concern e topic emersi) ---
    cursor.execute(
        "SELECT call_date, summary, concerns "
        "FROM call_history WHERE client_id = %s "
        "ORDER BY call_date DESC LIMIT 5", (client_id,)
    )
    past_calls = cursor.fetchall()

    # --- Transazioni recenti ---
    cursor.execute(
        "SELECT date, action, asset, amount "
        "FROM transactions WHERE client_id = %s "
        "ORDER BY date DESC LIMIT 10", (client_id,)
    )
    transactions = cursor.fetchall()

    return {
        "profile": profile,
        "portfolio": portfolio,
        "past_calls": past_calls,
        "transactions": transactions,
    }


# =============================================================================
# STEP 2 - COSTRUZIONE DEL CONTESTO COME TESTO
# =============================================================================
# GPT-4o legge testo, non oggetti Python. Convertiamo il contesto in testo
# leggibile e ordinato. Più è chiaro, meglio il modello ragiona.

def build_context_text(ctx: dict) -> str:
    """Trasforma il dizionario del database in testo leggibile per il prompt."""
    lines = []

    lines.append("=== PROFILO CLIENTE (da onboarding) ===")
    lines.append(str(ctx["profile"]))

    lines.append("\n=== PORTAFOGLIO ATTUALE ===")
    for pos in ctx["portfolio"]:
        lines.append(f"- {pos}")

    lines.append("\n=== STORICO CALL PRECEDENTI ===")
    for call in ctx["past_calls"]:
        lines.append(f"- {call}")

    lines.append("\n=== TRANSAZIONI RECENTI ===")
    for tx in ctx["transactions"]:
        lines.append(f"- {tx}")

    return "\n".join(lines)


# =============================================================================
# STEP 3 - IL PROMPT PRINCIPALE (il "cervello" dell'analisi)
# =============================================================================
# Qui è dove avviene tutta la magia. Ogni widget corrisponde a una chiave del
# JSON. Modificate questo prompt per migliorare/cambiare il comportamento.

SYSTEM_PROMPT = """
You are a senior financial intelligence analyst at Julius Bär, a Swiss private
wealth management bank serving High Net Worth Individuals (HNWI).

You receive:
  1. The transcript of a call between a Relationship Manager (RM) and a client.
  2. The client's historical context (profile, portfolio, past calls, transactions).

Your job is to produce a SINGLE structured JSON object that powers a post-call
intelligence dashboard. Analyze the conversation IN COMBINATION with the client's
history and produce the following fields.

Always reason about the CLIENT's words, not the RM's.

Produce EXACTLY this JSON structure:

{
  "summary": "3 to 5 line factual summary of the most important points",

  "sentiment": {
    "overall_mood": "calm | concerned | distressed",
    "mood_trajectory": {
      "start": "calm | concerned | distressed",
      "end": "calm | concerned | distressed",
      "turning_point": "what shifted the client's mood, or null"
    },
    "topics": [
      {
        "topic": "short label",
        "emotion_level": "calm | concerned | distressed",
        "attribution": "julius_bar | market | personal_family",
        "quote": "exact client sentence",
        "confidence": "high | medium | low"
      }
    ]
  },

  "action_items": [
    {
      "action": "concrete next step for the RM",
      "urgency": "high | medium | low",
      "deadline_hint": "timeframe if mentioned, else null"
    }
  ],

  "financial_topics": ["clean list of financial concepts mentioned, for the news API"],

  "latent_needs": [
    {
      "need": "implicit need the client did NOT explicitly ask for",
      "signal": "what in the text suggests this"
    }
  ],

  "profile_updates": ["facts the RM should update in the client profile"],

  "portfolio_alignment": [
    {
      "topic": "what the client expressed",
      "current_exposure": "the relevant current portfolio position",
      "misalignment": "high | medium | low | none",
      "explanation": "why aligned or misaligned"
    }
  ],

  "recurring_concerns": [
    {
      "concern": "topic that also appeared in past calls",
      "times_mentioned": "how many calls including this one",
      "status": "resolved | unresolved",
      "severity": "critical | watch | minor"
    }
  ],

  "behavioural_drift": {
    "declared_profile": "the risk profile from onboarding",
    "observed_behaviour": "what recent calls/this call suggest",
    "drift_detected": true,
    "drift_description": "explanation, or null if no drift"
  },

  "opportunity_delta": [
    {
      "client_interest": "something the client expressed interest in",
      "matched_opportunity": "a market opportunity that matches it",
      "rationale": "why this is a good match"
    }
  ]
}

Rules:
- If a section has no data, return an empty array [] or null. Never invent facts.
- Base recurring_concerns and behavioural_drift ONLY on the provided history.
- Keep quotes exact and short.
- Respond ONLY with the JSON object. No markdown, no explanation.
"""


# =============================================================================
# STEP 4 - LA CHIAMATA PRINCIPALE A GPT-4o (una sola per tutti i widget)
# =============================================================================

def analyze_call(transcript: str, client_ctx: dict, market_news: str = "") -> dict:
    """
    Chiamata principale post-call. Restituisce il JSON completo della dashboard.

    transcript   : la trascrizione della call
    client_ctx   : dizionario dal database (output di get_client_context)
    market_news  : testo opzionale con news di mercato già recuperate
    """
    context_text = build_context_text(client_ctx)

    user_content = f"""
=== CALL TRANSCRIPT ===
{transcript}

=== CLIENT HISTORICAL CONTEXT ===
{context_text}

=== RECENT MARKET NEWS (optional) ===
{market_news if market_news else "No news provided."}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0,                              # consistenza massima
        response_format={"type": "json_object"},    # output JSON garantito
    )

    return json.loads(response.choices[0].message.content)


# =============================================================================
# STEP 5 - GENERAZIONE PROPOSAL (chiamata SEPARATA, on-demand)
# =============================================================================
# Questa NON sta nella chiamata principale. Gira solo quando l'RM clicca il
# bottone "Generate Proposal" su un topic/opportunità specifica.

PROPOSAL_SYSTEM_PROMPT = """
You are a Julius Bär investment advisor. Write a concise, professional client-facing
proposal responding to a specific client need or opportunity identified during a call.

The proposal must:
- Directly address the client's expressed need or concern.
- Be consistent with the client's risk profile and current portfolio.
- Be a concrete PROPOSAL (a recommended course of action), NOT a market analysis.
- Be written in a warm, professional private-banking tone.
- Be 150-250 words.

Respond with the proposal text only.
"""

def generate_proposal(topic: str, client_ctx: dict, transcript_excerpt: str = "") -> str:
    """
    Genera una proposal su richiesta per un topic specifico.
    Chiamata separata, attivata dal click dell'RM.
    """
    context_text = build_context_text(client_ctx)

    user_content = f"""
Client need / opportunity to address: {topic}

Relevant excerpt from the call:
{transcript_excerpt}

Client context:
{context_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": PROPOSAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.4,   # un po' più alta: vogliamo testo naturale, non rigido
    )

    return response.choices[0].message.content


# =============================================================================
# ESEMPIO DI UTILIZZO / TEST
# =============================================================================

if __name__ == "__main__":

    test_transcript = """
    Client: I have to be honest, I'm quite worried about my portfolio after
    last quarter. The returns were disappointing and I expected more from
    Julius Bär. I also keep reading about tensions in Asia and it makes me
    nervous about my exposure there. By the way, I really should start thinking
    about how to pass some of this on to my daughter one day.
    RM: I understand your concerns, let me walk you through what happened...
    Client: Okay, that actually makes me feel a bit better about the bond side.
    """

    # In produzione: client_ctx = get_client_context(client_id, db_connection)
    # Qui simuliamo un contesto finto per il test:
    fake_ctx = {
        "profile": {"risk_profile": "balanced", "goals": "wealth preservation",
                    "preferences": "low volatility, ESG"},
        "portfolio": ["Asian equity 40%", "EU bonds 30%", "Cash 5%", "Gold 10%"],
        "past_calls": [
            "2025-09: client worried about liquidity, not resolved",
            "2025-06: client worried about liquidity",
        ],
        "transactions": ["2025-05: bought Asian equity ETF"],
    }

    result = analyze_call(test_transcript, fake_ctx)
    print(json.dumps(result, indent=2, ensure_ascii=False))