from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from users.models import User


# Schema view for Swagger UI
schema_view = get_schema_view(
    openapi.Info(
        title="Nutrition Food Delivery API",
        default_version='v0.1',
        description="API documentation for the Nutrition app",
        terms_of_service="https://www.nutrition-app.com/terms/",
        contact=openapi.Contact(email="rbheemana.lab@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],  # Require authentication for accessing Swagger UI
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),  # Users API
    path('restaurants/', include('menu.urls')),  # Ensure menu URLs are included correctly
    path('orders/', include('orders.urls')),
    # Swagger URLs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    # JWT Authentication URLs
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# Add a view to handle Swagger UI access account

@login_required
def swagger_access(request):
    return redirect('schema-swagger-ui')

urlpatterns += [
    path('swagger-access/', swagger_access, name='swagger-access'),
]
