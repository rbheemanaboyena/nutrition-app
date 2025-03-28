from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
from django.core.mail import send_mail
from .models import User, OTPVerification
import jwt, datetime, redis
from django.conf import settings
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

# Redis connection
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

class RegisterView(APIView):
    """
    User Registration View
    Handles user registration and sends an OTP for email verification."
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'full_name': openapi.Schema(type=openapi.TYPE_STRING),
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                'role': openapi.Schema(type=openapi.TYPE_STRING, default='customer')
            }
        ),
        responses={
            201: openapi.Response(
                description="User registered successfully.",
                examples={
                    "application/json": {
                        "message": "User registered successfully. Verify email to continue.",
                        "user_id": "<user_id>"
                    }
                }
            )
        }
    )
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
        response= Response({"message": "User registered successfully. Verify email to continue.", "user_id": str(user.user_id)}, status=status.HTTP_201_CREATED)
        response["Access-Control-Allow-Origin"] = "*"
        return response

class VerifyEmailView(APIView):
    """
    Email Verification View
    Handles email verification using OTP."
    """
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'otp': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            200: openapi.Response(
                description="Email verified successfully.",
                examples={
                    "application/json": {
                        "message": "Email verified successfully."
                    }
                }
            )
        }
    )
    def post(self, request):
        data = request.data
        otp_record = OTPVerification.objects.filter(email=data['email'], otp_code=data['otp']).first()
        if not otp_record or otp_record.expires_at < now():
            return Response({"message": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.get(email=data['email'])
        user.is_active = True
        user.save()
        otp_record.delete()
        response = Response({"message": "Email verified successfully."}, status=status.HTTP_200_OK)
        response["Access-Control-Allow-Origin"] = "*"
        return response

class LoginView(APIView):
    """
    User Login View
    Handles user login and generates JWT tokens."
    """
    permission_classes = [AllowAny]
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            200: openapi.Response(
                description="User logged in successfully.",
                examples={
                    "application/json": {
                        "access_token": "<access_token>",
                        "refresh_token": "<refresh_token>",
                        "user_id": "<user_id>",
                        "expires_in": 900
                    }
                }
            )
        }
    )
    def post(self, request):
        data = request.data
        user = User.objects.filter(email=data['email']).first()
        if not user or not check_password(data['password'], user.password_hash):
            return Response({"message": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        access_token = jwt.encode({"user_id": str(user.user_id), "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, settings.SECRET_KEY, algorithm='HS256')
        refresh_token = jwt.encode({"user_id": str(user.user_id), "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)}, settings.SECRET_KEY, algorithm='HS256')
        redis_client.setex(f'session:{user.user_id}', 900, access_token)
        response= Response({"access_token": access_token, "refresh_token": refresh_token, "user_id": str(user.user_id), "expires_in": 900}, status=status.HTTP_200_OK)
        response["Access-Control-Allow-Origin"] = "*"
        return response

class LogoutView(APIView):
    """
    User Logout View
    Handles user logout and invalidates the session."
    """
    permission_classes = [IsAuthenticated]
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_STRING)
            }
        ),
        responses={
            200: openapi.Response(
                description="User logged out successfully.",
                examples={
                    "application/json": {
                        "message": "User logged out successfully."
                    }
                }
            )
        }
    )
    def post(self, request):
        user_id = request.data.get('user_id')
        redis_client.delete(f'session:{user_id}')
        response= Response({"message": "User logged out successfully."}, status=status.HTTP_200_OK)
        response["Access-Control-Allow-Origin"] = "*"
        return response

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        try:
            decoded = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = decoded['user_id']
            new_access_token = jwt.encode({"user_id": user_id, "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)}, settings.SECRET_KEY, algorithm='HS256')
            redis_client.setex(f'session:{user_id}', 900, new_access_token)
            response = Response({"access_token": new_access_token, "expires_in": 900}, status=status.HTTP_200_OK)
            response["Access-Control-Allow-Origin"] = "*"
            return response
        except jwt.ExpiredSignatureError:
            return Response({"message": "Refresh token expired."}, status=status.HTTP_401_UNAUTHORIZED)

# Function to extract user from JWT token
def get_user_from_token(request):
    auth_header = request.headers.get("Authorization", None)
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthenticationFailed("Authentication token missing or invalid.")

    token = auth_header.split(" ")[1]  # Extract token from "Bearer <token>"

    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token.get("user_id")

        if not user_id:
            raise AuthenticationFailed("Invalid token payload.")

        user = User.objects.filter(user_id=user_id).first()
        if not user:
            raise AuthenticationFailed("User not found.")

        return user

    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Token has expired.")
    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Invalid token.")

class UserProfileView(APIView):
    """
    User Profile View
    Fetches user profile information based on user_id."
    """
    permission_classes = [AllowAny]
    def get(self, *args, **kwargs):
        print("Fetching user profile")
        user_id = kwargs.get('user_id')

        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Fetch the user based on user_id
            user = get_object_or_404(User, user_id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        profile_data = {
            "user_id": str(user.user_id),
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "role": user.role,
            "oauth_provider": user.oauth_provider,
            "oauth_id": user.oauth_id,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        return Response(profile_data, status=status.HTTP_200_OK)


class PasswordResetView(APIView):
    """
    Password Reset View
    Handles password reset functionality."
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # Extract the user_id, old password, and new password from the request data
        user_id = request.data.get('user_id')
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not all([user_id, old_password, new_password]):
            return Response({"detail": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the user from the database using the user_id
        user = get_object_or_404(User, user_id=user_id)

        # Check if the old password is correct
        if not check_password(old_password, user.password_hash):
            raise AuthenticationFailed("Old password is incorrect.")

        # Update the password
        user.password_hash = make_password(new_password)  # Hash the new password
        user.save()  # Save the updated user record

        return Response({"message": "Password updated successfully."}, status=status.HTTP_200_OK)
