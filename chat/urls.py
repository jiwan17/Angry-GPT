
from django.urls import path
from .views import index, chat_api


urlpatterns = [
    path("", index, name="chat-index"),
    path("api/", chat_api, name="chat-api"),
]
