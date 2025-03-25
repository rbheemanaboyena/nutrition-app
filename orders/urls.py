from django.urls import path
from . import views
from .views import CartView, ViewCart, RemoveFromCart, Checkout

urlpatterns = [
    path('api/cart/add', CartView.as_view(), name='add_to_cart'),
    path('api/cart/remove/<str:item_id>/', RemoveFromCart.as_view(), name='remove_from_cart'),
    path('api/cart', ViewCart.as_view(), name='view_cart'),
     path('api/order/checkout/', Checkout.as_view(), name='checkout'),
    path('api/order/payment', views.payment_processing, name='payment_processing'),
    path('api/order/history', views.order_history, name='order_history'),
]
