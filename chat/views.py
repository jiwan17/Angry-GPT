import json
import os
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .prompts import ANGRY_GPT_PROMPT


def index(request):
    """Render a simple page with a prompt form."""
    return render(request, "chat/index.html")


@csrf_exempt
async def chat_api(request):
    """JSON API: accepts POST {message, tone?} and returns {reply}.

    Uses the local `stream_ollama` generator to talk to a local Ollama server
    (no OpenAI API key needed). The view collects streamed tokens and
    returns the concatenated final reply.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        body_bytes = request.body
        body = json.loads(body_bytes)
        user_message = body.get("message", "")
        tone = body.get("tone", "mean")

        # Import locally to avoid import cycles and keep startup cheap.
        from .service import stream_ollama

        parts = []
        async for token in stream_ollama(user_message, tone=tone):
            parts.append(token)

        ai_reply = "".join(parts)
        return JsonResponse({"reply": ai_reply})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)