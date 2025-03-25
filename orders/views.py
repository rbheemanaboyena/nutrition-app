from django.shortcuts import render
from django.http import JsonResponse
from .models import Order, OrderItem
from django.db import transaction
import redis
import uuid
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# Redis connection setup (Example configuration)
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

class CartView(APIView):
    def post(self, request, *args, **kwargs):
        """
        POST /api/cart/add
        Adds an item to the cart.
        """
        # Get the data from the request
        user_id = request.data.get('user_id')
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity')

        # Validate the inputs
        if not user_id or not item_id or quantity is None:
            return Response({"error": "Missing required parameters"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Convert quantity to an integer
            quantity = int(quantity)
        except ValueError:
            return Response({"error": "Invalid quantity value"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate cart key for Redis
        cart_key = f'cart:{user_id}'

        # Fetch current cart items
        cart = r.hgetall(cart_key)

        # Add or update item in the cart
        current_quantity = int(cart.get(item_id, 0))
        updated_quantity = current_quantity + quantity

        # Set new quantity and reset TTL to 30 minutes
        r.hset(cart_key, item_id, updated_quantity)
        r.expire(cart_key, 1800)  # Set TTL for 30 minutes

        # Return a success response
        return JsonResponse({"message": "Item added to cart successfully.", "cart": {item_id: updated_quantity}}, status=status.HTTP_200_OK)



class RemoveFromCart(APIView):
    def delete(self, request, item_id, *args, **kwargs):
        """
        DELETE /api/cart/remove/{item_id}
        Removes an item from the cart for a user.
        """
        # Get the user_id from POST data
        user_id = request.data.get('user_id')

        # If user_id is missing, return a bad request error
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        cart_key = f'cart:{user_id}'

        # Remove item from the cart in Redis
        item_removed = r.hdel(cart_key, item_id)

        # If the item was not found in the cart
        if item_removed == 0:
            return JsonResponse({"message": "Item not found in the cart."}, status=status.HTTP_404_NOT_FOUND)

        # Reset TTL (Time-to-Live) for the cart key
        r.expire(cart_key, 1800)  # Set TTL for 30 minutes

        return JsonResponse({"message": "Item removed from cart successfully."}, status=status.HTTP_200_OK)


class ViewCart(APIView):
    def get(self, request, *args, **kwargs):
        """
        GET /api/cart
        Views the items in the cart for a user.
        """
        # Get the user_id from query parameters
        user_id = request.GET.get('user_id')

        # If user_id is missing, return a bad request error
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        cart_key = f'cart:{user_id}'
        
        # Fetch cart details from Redis
        cart = r.hgetall(cart_key)

        # Check if the cart is not empty
        if cart:
            total_price = 0
            cart_details = []

            # Assuming price for each item is retrieved from an inventory system or DB
            for item_id, quantity in cart.items():
                price = 10.99  # Example fixed price for demonstration
                total_price += price * int(quantity)
                cart_details.append({
                    'item_id': item_id,
                    'quantity': int(quantity),
                    'price': price
                })

            # Return the cart details with the total price
            return JsonResponse({"cart": cart_details, "total_price": total_price}, status=status.HTTP_200_OK)
        else:
            # If the cart is empty, return a message
            return JsonResponse({"message": "Cart is empty."}, status=status.HTTP_200_OK)


class Checkout(APIView):
    def post(self, request, *args, **kwargs):
        """
        POST /api/order/checkout
        Handles the checkout process, including applying promo codes and creating an order.
        """
        # Get the user details from the request
        user_id_str = request.data.get('user_id')
        delivery_address = request.data.get('delivery_address')
        payment_method = request.data.get('payment_method')
        promo_code = request.data.get('promo_code', None)

        # Ensure user_id, delivery_address, and payment_method are provided
        if not user_id_str or not delivery_address or not payment_method:
            return Response({"error": "user_id, delivery_address, and payment_method are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Convert user_id to a UUID format
        try:
            user_id = uuid.UUID(user_id_str)  # Converts the string to a UUID
        except ValueError:
            return JsonResponse({"error": "Invalid user_id format."}, status=status.HTTP_400_BAD_REQUEST)

        cart_key = f'cart:{user_id}'
        cart = r.hgetall(cart_key)

        # Check if the cart is empty
        if not cart:
            return JsonResponse({"message": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate total price (apply discount if promo_code is valid)
        total_price = 0
        for item_id, quantity in cart.items():
            price = 10.99  # Example price for each item
            total_price += price * int(quantity)

        # Apply promo code discount if valid
        if promo_code == "DISCOUNT10":
            total_price *= 0.9  # Apply 10% discount

        # Create an order entry with a transaction to ensure atomicity
        try:
            with transaction.atomic():
                # Create the Order
                order = Order.objects.create(
                    user_id=user_id,
                    total_price=total_price,
                    discount=0.00,  # If any discount applied, update here
                    payment_status='pending',  # Default payment status is pending
                    order_status='processing',  # Default order status is processing
                )

                # Add items to the OrderItems table
                for item_id, quantity in cart.items():
                    price = 10.99  # Example price for each item
                    OrderItem.objects.create(
                        order=order,
                        item_id=item_id,
                        quantity=int(quantity),
                        price=price
                    )

            # Remove cart from Redis after order creation
            r.delete(cart_key)

            return JsonResponse({
                "message": "Order placed successfully.",
                "order_id": order.order_id,
                "total_price": total_price,
                "payment_status": order.payment_status,
                "order_status": order.order_status
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return JsonResponse({"message": f"Error occurred while placing the order: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def payment_processing(request):
    # POST /api/order/payment
    order_id = request.POST.get('order_id')
    payment_token = request.POST.get('payment_token')

    # Payment processing with external service (Stripe/PayPal) would go here
    # For demonstration, we assume the payment is successful

    order = Order.objects.get(order_id=order_id)
    order.payment_status = "completed"
    order.save()

    return JsonResponse({"message": "Payment successful.", "payment_status": "completed"})


def order_history(request):
    # GET /api/order/history
    user_id = request.GET.get('user_id')
    orders = Order.objects.filter(user_id=user_id).values("order_id", "total_price", "order_status", "created_at")

    return JsonResponse({"orders": list(orders)})
