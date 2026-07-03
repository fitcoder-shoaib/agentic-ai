const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";

export async function handler(event) {
  if (event.httpMethod !== "POST") {
    return json(405, { error: "Method not allowed" });
  }

  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    return json(200, {
      mode: "local",
      answer: "ThinkDesk AI is not connected yet. Add GROQ_API_KEY in Netlify environment variables to enable live AI responses.",
    });
  }

  let body;
  try {
    body = JSON.parse(event.body || "{}");
  } catch {
    return json(400, { error: "Invalid JSON body" });
  }

  const question = String(body.question || "").trim();
  const summary = String(body.summary || "No uploaded finance data was provided.").slice(0, 12000);

  if (!question) {
    return json(400, { error: "Question is required" });
  }

  try {
    const response = await fetch(GROQ_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "llama-3.3-70b-versatile",
        messages: [
          {
            role: "system",
            content:
              "You are ThinkDesk, Finguide's careful personal finance guide. Use only the provided transaction summary. Give concrete, kind, non-judgmental advice. Do not provide tax, legal, or investment guarantees.\n\n" +
              summary,
          },
          { role: "user", content: question },
        ],
        temperature: 0.35,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return json(502, { error: `Groq request failed: ${errorText}` });
    }

    const data = await response.json();
    const answer = data?.choices?.[0]?.message?.content || "ThinkDesk could not produce an answer.";
    return json(200, { mode: "groq", answer });
  } catch (error) {
    return json(500, { error: error.message || "Unexpected ThinkDesk error" });
  }
}

function json(statusCode, payload) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  };
}
