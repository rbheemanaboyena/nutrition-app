from django.urls import path
from . import views
from .views import CartView, ViewCart, RemoveFromCart, Checkout, PaymentPrcessing, OrderHistory

urlpatterns = [
    path('cart/add', CartView.as_view(), name='add_to_cart'),
    path('cart/<str:user_id>/remove/<str:item_id>', RemoveFromCart.as_view(), name='remove_from_cart'),
    path('cart/<str:user_id>/view', ViewCart.as_view(), name='view_cart'),
    path('<str:user_id>/checkout', Checkout.as_view(), name='checkout'),
    path('<str:user_id>/payment', PaymentPrcessing.as_view(), name='payment_processing'),
    path('<str:user_id>/history', OrderHistory.as_view(), name='order_history'),
]
