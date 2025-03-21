from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.core.mail import send_mail
from .models import User, OTPVerification
import jwt, datetime, redis
from django.conf import settings

# Redis connection
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        data = request.data
        password_hash = make_password(data['password'])
        user = User.objects.create(
            full_name=data['full_name'],
            email=data['email'],
            password_hash=password_hash,
            phone_number=data['phone_number'],
            role=data.get('role', 'customer')
        )
        otp_code = get_random_string(length=6, allowed_chars='0123456789')
        OTPVerification.objects.create(email=user.email, otp_code=otp_code, expires_at=now() + datetime.timedelta(minutes=5))
        send_mail('Verify Your Email', f'Your OTP code is {otp_code}', 'noreply@example.com', [user.email])
        return Response({"message": "User registered successfully. Verify email to continue.", "user_id": str(user.user_id)}, status=status.HTTP_201_CREATED)

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        data = request.data
        otp_record = OTPVerification.objects.filter(email=data['email'], otp_code=data['otp']).first()
        if not otp_record or otp_record.expires_at < now():
            return Response({"message": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.get(email=data['email'])
        user.is_active = True
        user.save()
        otp_record.delete()
        return Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        data = request.data
        user = User.objects.filter(email=data['email']).first()
        if not user or not check_password(data['password'], user.password_hash):
            return Response({"message": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        access_token = jwt.encode({"user_id": str(user.user_id), "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, settings.SECRET_KEY, algorithm='HS256')
        refresh_token = jwt.encode({"user_id": str(user.user_id), "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)}, settings.SECRET_KEY, algorithm='HS256')
        redis_client.setex(f'session:{user.user_id}', 900, access_token)
        return Response({"access_token": access_token, "refresh_token": refresh_token, "expires_in": 900}, status=status.HTTP_200_OK)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user_id = request.data.get('user_id')
        redis_client.delete(f'session:{user_id}')
        return Response({"message": "User logged out successfully."}, status=status.HTTP_200_OK)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        try:
            decoded = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = decoded['user_id']
            new_access_token = jwt.encode({"user_id": user_id, "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, settings.SECRET_KEY, algorithm='HS256')
            redis_client.setex(f'session:{user_id}', 900, new_access_token)
            return Response({"access_token": new_access_token, "expires_in": 900}, status=status.HTTP_200_OK)
        except jwt.ExpiredSignatureError:
            return Response({"message": "Refresh token expired."}, status=status.HTTP_401_UNAUTHORIZED)

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()
        if user:
            otp_code = get_random_string(length=6, allowed_chars='0123456789')
            redis_client.setex(f'password_reset:{email}', 300, otp_code)
            send_mail('Password Reset', f'Your OTP code is {otp_code}', 'noreply@example.com', [email])
        return Response({"message": "Password reset link sent to email."}, status=status.HTTP_200_OK)

class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        data = request.data
        otp_code = redis_client.get(f'password_reset:{data["email"]}')
        if not otp_code or otp_code != data['otp']:
            return Response({"message": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.get(email=data['email'])
        user.password_hash = make_password(data['new_password'])
        user.save()
        redis_client.delete(f'password_reset:{data["email"]}')
        return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)

