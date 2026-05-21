import httpx
from config import settings

SYSTEM_PROMPT = """Eres un asistente académico para estudiantes de Bachillerato (16-18 años).
Responde siempre en español. Sé claro, preciso y pedagógico.
Adapta el nivel al estudiante. Si la pregunta no es académica, redirige amablemente.
Materias: Matemáticas, Física, Lengua, Literatura, Inglés, Química, Biología, Historia, Ciencias Sociales."""


async def call_ollama(messages: list[dict]) -> str:
    payload = {
        "model": settings.ollama_model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        response = await client.post(
            f"{settings.ollama_url}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
