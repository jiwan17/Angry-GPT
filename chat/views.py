import json
import os
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async

from .prompts import ANGRY_GPT_PROMPT
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.contrib.auth.models import User
from .models import Conversation, Message
from asgiref.sync import sync_to_async
from django.http import StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import asyncio


def index(request):
    """Render a simple page with a prompt form."""
    return redirect('chat-index')


def signup_view(request):
    if request.method == 'POST':
        data = request.POST
        username = data.get('username')
        password = data.get('password')
        if username and password:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            return redirect('chat-index')
    return render(request, 'registration/signup.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('chat-index')
        else:
            return render(request, 'registration/login.html', {'error': 'Invalid credentials'})
    return render(request, 'registration/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def chats_list(request):
    """Show the user's conversations and a New Chat button."""
    convs = Conversation.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'chat/chats.html', {'conversations': convs})


@login_required
def new_chat(request):
    conv = Conversation.objects.create(user=request.user, title='New chat')
    return redirect('chat-detail', conv_id=conv.id)


@login_required
def chat_detail(request, conv_id):
    try:
        conv = Conversation.objects.get(pk=conv_id, user=request.user)
    except Conversation.DoesNotExist:
        return redirect('chat-index')
    messages = conv.messages.all()
    # also provide the user's conversation list for the sidebar
    convs = Conversation.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'chat/chat_detail.html', {'conversation': conv, 'messages': messages, 'conversations': convs})


@csrf_exempt
async def chat_stream(request):
    """Stream assistant tokens as SSE-formatted chunks.

    Expects JSON body: {message, tone, conversation_id}
    Returns content_type 'text/event-stream' with lines 'data: <token>\n\n'
    """
    if request.method != 'POST':
        return HttpResponse('POST only', status=405)
    try:
        body = json.loads(request.body)
        user_message = body.get('message', '')
        tone = body.get('tone', 'mean')
        conv_id = body.get('conversation_id')

        # Build composed prompt from conversation if present
        composed_user_prompt = user_message
        conv = None
        if conv_id:
            try:
                conv = await Conversation.objects.aget(pk=conv_id, user=request.user)
                recent_msgs = await sync_to_async(list)(conv.messages.all())
                # this is same as above
                # recent_msgs = [msg async for msg in conv.messages.all().aiterator()]
                lines = []
                for m in recent_msgs:
                    label = 'User' if m.role == 'user' else 'Assistant'
                    lines.append(f"{label}: {m.content}")
                transcript = "\n".join(lines)
                if transcript:
                    composed_user_prompt = f"Conversation:\n{transcript}\nUser: {user_message}\nAssistant:"
            except Exception:
                conv = None

        from .service import stream_ollama

        async def stream_response():
            assistant_text = ''
            try:
                # If conversation exists, save the user's message first
                if conv is not None:
                    # await sync_to_async(Message.objects.create)(conversation=conv, role='user', content=user_message)
                    await Message.objects.acreate(conversation=conv, role='user', content=user_message)
                    
                    # Update conversation title to the latest user question (truncate to 200 chars)
                    try:
                        conv.title = (user_message or "").strip()[:200]
                        # await conv.asave()
                        await sync_to_async(conv.save)()
                    except Exception:
                        pass

                async for token in stream_ollama(composed_user_prompt, tone=tone):
                    assistant_text += token
                    chunk = f"data: {token}\n\n"
                    yield chunk.encode('utf-8')

                # final event to signal done
                yield b"event: done\ndata: \n\n"

                # Persist assistant reply when streaming completes
                if conv is not None:
                    await sync_to_async(Message.objects.create)(conversation=conv, role='assistant', content=assistant_text)
            except Exception as e:
                # send an error event and re-raise/log
                yield f"event: error\ndata: {str(e)}\n\n".encode('utf-8')

        response = StreamingHttpResponse(stream_response(), content_type='text/event-stream')
        return response
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def rename_conversation(request, conv_id):
    if request.method == 'POST':
        new_title = request.POST.get('title', '').strip()
        try:
            conv = Conversation.objects.get(pk=conv_id, user=request.user)
            conv.title = new_title or conv.title
            conv.save()
        except Conversation.DoesNotExist:
            pass
    return redirect('chat-detail', conv_id=conv_id)


@login_required
def delete_conversation(request, conv_id):
    if request.method == 'POST':
        try:
            conv = Conversation.objects.get(pk=conv_id, user=request.user)
            conv.delete()
        except Conversation.DoesNotExist:
            pass
    return redirect('chat-index')


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

        # If a conversation id is provided, persist to that conversation.
        conv_id = None
        try:
            conv_id = int(body.get('conversation_id'))
        except Exception:
            conv_id = None

        # Build prompt from conversation history if conversation exists
        composed_user_prompt = user_message
        if conv_id:
            try:
                conv = await sync_to_async(Conversation.objects.get)(pk=conv_id, user=request.user)
                # load recent messages
                recent_msgs = await sync_to_async(list)(conv.messages.all())
                # create a transcript
                lines = []
                for m in recent_msgs:
                    label = 'User' if m.role == 'user' else 'Assistant'
                    lines.append(f"{label}: {m.content}")
                transcript = "\n".join(lines)
                if transcript:
                    composed_user_prompt = f"Conversation:\n{transcript}\nUser: {user_message}\nAssistant:"
            except Conversation.DoesNotExist:
                conv = None
        else:
            conv = None

        # Import locally to avoid import cycles and keep startup cheap.
        from .service import stream_ollama

        parts = []
        async for token in stream_ollama(composed_user_prompt, tone=tone):
            parts.append(token)

        ai_reply = "".join(parts).strip()

        # Persist messages if conversation is present; otherwise do not persist.
        if conv is not None:
            await sync_to_async(Message.objects.create)(conversation=conv, role='user', content=user_message)
            # Update conversation title to the latest user question (truncate to 200 chars)
            try:
                conv.title = (user_message or "").strip()[:200]
                await sync_to_async(conv.save)()
            except Exception:
                pass
            await sync_to_async(Message.objects.create)(conversation=conv, role='assistant', content=ai_reply)

        return JsonResponse({"reply": ai_reply, "conversation_id": conv_id})
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