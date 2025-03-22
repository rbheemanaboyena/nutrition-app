from django.urls import path
from .views import RestaurantView, MenuItemView

urlpatterns = [
    # Restaurant-related endpoints
    path('restaurants/', RestaurantView.as_view(), name='restaurant-list'),  # List all restaurants
    path('restaurants/<uuid:id>/', RestaurantView.as_view(), name='restaurant-detail'),  # Get, update, or delete a specific restaurant by id

    # MenuItem-related endpoints
    path('restaurants/<uuid:id>/menu/', MenuItemView.as_view(), name='menu-item-list'),  # List all menu items for a specific restaurant
    path('restaurants/<uuid:id>/menu/<uuid:item_id>/', MenuItemView.as_view(), name='menu-item-detail'),  # Get, update, or delete a specific menu item
]

