import json
import os
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async

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

        # session-based conversation memory
        MAX_TURNS = 6  # keep last N exchanges (user+assistant)
        # request.session is synchronous; in async views access it via sync_to_async
        history = await sync_to_async(lambda: request.session.get("history", []), thread_sensitive=True)()

        # Build a compact transcript of recent turns
        recent = history[-(MAX_TURNS * 2) :]
        transcript_lines = []
        for h in recent:
            if h.get("role") == "user":
                transcript_lines.append(f"User: {h.get('content', '')}")
            else:
                transcript_lines.append(f"Assistant: {h.get('content', '')}")

        # Append the current user message as the last user turn
        transcript = "\n".join(transcript_lines)
        if transcript:
            composed_user_prompt = f"Conversation:\n{transcript}\nUser: {user_message}\nAssistant:"
        else:
            composed_user_prompt = f"User: {user_message}\nAssistant:"

        # Import locally to avoid import cycles and keep startup cheap.
        from .service import stream_ollama

        parts = []
        async for token in stream_ollama(composed_user_prompt, tone=tone):
            parts.append(token)

        ai_reply = "".join(parts).strip()

        # Save the new exchange back to session history (use sync_to_async)
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": ai_reply})
        # Trim history to keep size bounded
        if len(history) > MAX_TURNS * 2:
            history = history[-(MAX_TURNS * 2) :]
        await sync_to_async(request.session.__setitem__, thread_sensitive=True)("history", history)
        await sync_to_async(setattr, thread_sensitive=True)(request.session, "modified", True)

        return JsonResponse({"reply": ai_reply})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def clear_history(request):
    """Clear the session conversation history."""
    try:
        request.session.pop("history", None)
        request.session.modified = True
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)