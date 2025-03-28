from django.urls import path
from .views import RegisterView, LoginView, LogoutView, VerifyEmailView, RefreshTokenView, UserProfileView, PasswordResetView

urlpatterns = [
    path('auth/register', RegisterView.as_view(), name='register'),
    path('auth/verify-email', VerifyEmailView.as_view(), name='verify-email'),
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/logout', LogoutView.as_view(), name='logout'),
    path('auth/refresh', RefreshTokenView.as_view(), name='refresh-token'),
    path('auth/password-reset', PasswordResetView.as_view(), name='password-reset'),
    path('profile/<str:user_id>', UserProfileView.as_view(), name='user-profile'),
]
