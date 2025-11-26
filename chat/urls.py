
from django.urls import path
from . import views


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
]
