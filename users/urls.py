from django.urls import path
from .views import RegisterView, LoginView, LogoutView, VerifyEmailView, RefreshTokenView, PasswordResetRequestView, PasswordResetView

urlpatterns = [
    path('api/auth/register', RegisterView.as_view(), name='register'),
    path('api/auth/verify-email', VerifyEmailView.as_view(), name='verify-email'),
    path('api/auth/login', LoginView.as_view(), name='login'),
    path('api/auth/logout', LogoutView.as_view(), name='logout'),
    path('api/auth/refresh', RefreshTokenView.as_view(), name='refresh-token'),
    path('api/auth/reset-password', PasswordResetRequestView.as_view(), name='reset-password'),
    path('api/auth/set-password', PasswordResetView.as_view(), name='set-password'),
]
