
from django.urls import path
from . import views
from . import apis


urlpatterns = [
    path("", views.chats_list, name="chat-index"),
    path("new/", views.new_chat, name="chat-new"),
    path("<int:conv_id>/", views.chat_detail, name="chat-detail"),
    path("api/", views.chat_api, name="chat-api"),
    path("api/clear/", views.clear_history, name="chat-clear"),
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("api/stream/", views.chat_stream, name="chat-stream"),
    path("<int:conv_id>/rename/", views.rename_conversation, name="chat-rename"),
    path("<int:conv_id>/delete/", views.delete_conversation, name="chat-delete"),
    # API v1 endpoints (JSON)
    path("api/v1/chats/", apis.chats_list_api, name="api-chats"),
    path("api/v1/chats/new/", apis.new_chat_api, name="api-chat-new"),
    path("api/v1/chats/<int:conv_id>/", apis.chat_detail_api, name="api-chat-detail"),
    path("api/v1/chat/", apis.chat_api_proxy, name="api-chat-proxy"),
    path("api/v1/stream/", apis.chat_stream_proxy, name="api-chat-stream-proxy"),
    path("api/v1/clear/", apis.clear_history_api, name="api-clear-v1"),
    path("api/v1/signup/", apis.signup_api, name="api-signup-v1"),
    path("api/v1/login/", apis.login_api, name="api-login-v1"),
    path("api/v1/logout/", apis.logout_api, name="api-logout-v1"),
    path("api/v1/chats/<int:conv_id>/rename/", apis.rename_conversation_api, name="api-chat-rename-v1"),
    path("api/v1/chats/<int:conv_id>/delete/", apis.delete_conversation_api, name="api-chat-delete-v1"),
]
