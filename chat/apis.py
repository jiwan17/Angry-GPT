import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Conversation, Message

from . import views as _views


def _unauthenticated():
    return JsonResponse({"error": "unauthenticated"}, status=401)


def serialize_conv(conv):
    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat(),
        "message_count": conv.messages.count(),
    }


def serialize_msg(m):
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
    }


@csrf_exempt
def chats_list_api(request):
    if not request.user.is_authenticated:
        return _unauthenticated()
    if request.method == 'GET':
        convs = Conversation.objects.filter(user=request.user).order_by('-created_at')
        data = [serialize_conv(c) for c in convs]
        return JsonResponse({"conversations": data})
    if request.method == 'POST':
        payload = request.POST or json.loads(request.body or '{}')
        title = payload.get('title') or 'New chat'
        conv = Conversation.objects.create(user=request.user, title=title)
        return JsonResponse(serialize_conv(conv))
    return JsonResponse({"error": "method not allowed"}, status=405)


@csrf_exempt
def new_chat_api(request):
    if not request.user.is_authenticated:
        return _unauthenticated()
    if request.method != 'POST':
        return JsonResponse({"error": "POST only"}, status=405)
    payload = request.POST or json.loads(request.body or '{}')
    title = payload.get('title') or 'New chat'
    conv = Conversation.objects.create(user=request.user, title=title)
    return JsonResponse(serialize_conv(conv))


@csrf_exempt
def chat_detail_api(request, conv_id):
    if not request.user.is_authenticated:
        return _unauthenticated()
    try:
        conv = Conversation.objects.get(pk=conv_id, user=request.user)
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)
    if request.method == 'GET':
        msgs = [serialize_msg(m) for m in conv.messages.all()]
        data = serialize_conv(conv)
        data['messages'] = msgs
        return JsonResponse(data)
    return JsonResponse({"error": "method not allowed"}, status=405)


@csrf_exempt
def signup_api(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST only"}, status=405)
    payload = request.POST or json.loads(request.body or '{}')
    username = payload.get('username')
    password = payload.get('password')
    if not username or not password:
        return JsonResponse({"error": "username and password required"}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "user exists"}, status=400)
    user = User.objects.create_user(username=username, password=password)
    login(request, user)
    return JsonResponse({"ok": True, "username": user.username})


@csrf_exempt
def login_api(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST only"}, status=405)
    payload = request.POST or json.loads(request.body or '{}')
    username = payload.get('username')
    password = payload.get('password')
    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        return JsonResponse({"ok": True, "username": user.username})
    return JsonResponse({"error": "invalid credentials"}, status=401)


@csrf_exempt
def logout_api(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST only"}, status=405)
    logout(request)
    return JsonResponse({"ok": True})


@csrf_exempt
def clear_history_api(request):
    try:
        request.session.pop("history", None)
        request.session.modified = True
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def rename_conversation_api(request, conv_id):
    if not request.user.is_authenticated:
        return _unauthenticated()
    if request.method != 'POST':
        return JsonResponse({"error": "POST only"}, status=405)
    payload = request.POST or json.loads(request.body or '{}')
    new_title = payload.get('title', '').strip()
    try:
        conv = Conversation.objects.get(pk=conv_id, user=request.user)
        conv.title = new_title or conv.title
        conv.save()
        return JsonResponse({"ok": True, "title": conv.title})
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)


@csrf_exempt
def delete_conversation_api(request, conv_id):
    if not request.user.is_authenticated:
        return _unauthenticated()
    if request.method != 'POST':
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        conv = Conversation.objects.get(pk=conv_id, user=request.user)
        conv.delete()
        return JsonResponse({"ok": True})
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)


@csrf_exempt
async def chat_api_proxy(request):
    """Proxy to the existing `chat_api` async view so API users can call `/api/v1/chat/`.
    This simply forwards the request to the existing implementation in `views.chat_api`.
    """
    return await _views.chat_api(request)


@csrf_exempt
async def chat_stream_proxy(request):
    """Proxy to the `chat_stream` endpoint (streaming)."""
    return await _views.chat_stream(request)
