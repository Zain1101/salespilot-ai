
import os
import httpx


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def main():
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    if not api_key:
        print("ERROR: GROQ_API_KEY is not configured.")
        return

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are SalesPilot AI, a helpful "
                    "sales assistant."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Say hello and explain your purpose "
                    "in two short sentences."
                ),
            },
        ],
        "temperature": 0.2,
        "max_completion_tokens": 300,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        response.raise_for_status()
        data = response.json()

        message = data["choices"][0]["message"]

        print("\nGroq connection successful!")
        print("Model:", data.get("model", model))
        print("\nAI Response:")
        print(message.get("content") or "[No text returned]")

    except httpx.HTTPStatusError as exc:
        print("Groq returned HTTP", exc.response.status_code)
        print(
            "Check your API key, model access, "
            "rate limits and account configuration."
        )

    except (httpx.RequestError, ValueError, KeyError, IndexError):
        print(
            "Connection or response error. "
            "Check your network and Groq configuration."
        )


if __name__ == "__main__":
    main()
