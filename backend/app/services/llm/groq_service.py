from groq import Groq

from app.config.settings import settings


class GroqService:
    """Thin wrapper around the Groq chat completions API."""

    def __init__(self, model: str | None = None):
        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not configured. "
                "Set GROQ_API_KEY in the environment or .env file."
            )

        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = model or settings.GROQ_MODEL

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content or ""

    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
    ):
        """Yield answer text deltas as the model streams them."""
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            stream=True,
        )

        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
