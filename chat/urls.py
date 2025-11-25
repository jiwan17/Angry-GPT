
from django.urls import path
from .views import index, chat_api, clear_history


urlpatterns = [
    path("", index, name="chat-index"),
    path("api/", chat_api, name="chat-api"),
    path("api/clear/", clear_history, name="chat-clear"),
]
