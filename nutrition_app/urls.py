from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Schema view for Swagger UI
schema_view = get_schema_view(
    openapi.Info(
        title="Food Menu API",
        default_version='v1',
        description="API documentation for the Nutrition app",
        terms_of_service="https://www.nutrition-app.com/terms/",
        contact=openapi.Contact(email="rbheemana.lab@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),  # Users API
    path('menu/', include('menu.urls')),  # Ensure menu URLs are included correctly
    # Swagger URLs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('accounts/', include('django.contrib.auth.urls')),
]
