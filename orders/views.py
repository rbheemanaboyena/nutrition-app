from django.shortcuts import render
from django.http import JsonResponse
from .models import Order, OrderItem, Address, Payment
from django.db import transaction
import redis
import uuid
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from users.models import User

# Redis connection setup (Example configuration)
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

class CartView(APIView):
    """
    POST /api/cart/add
    Adds an item to the cart for a user.
    """
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_STRING, description='User ID'),
                'item_id': openapi.Schema(type=openapi.TYPE_STRING, description='Item ID'),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Quantity to add'),
            },
        ),
        responses={
            200: openapi.Response('Item added to cart successfully', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'cart': openapi.Schema(type=openapi.TYPE_OBJECT),
                }
            )),
            400: "Invalid input",
            500: "Internal server error"
        }
    )
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
    """
    DELETE /api/cart/remove/{item_id}
    Removes an item from the cart for a user.
    """
    @swagger_auto_schema(
        responses={
            200: openapi.Response('Item removed from cart successfully', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )),
            400: "Invalid input",
            404: "Item not found in cart",
            500: "Internal server error"
        }
    )
    def delete(self, request, *args, **kwargs):
        """
        DELETE /api/cart/user_id/remove/{item_id}
        Removes an item from the cart for a user.
        """
        # Get the user_id from POST data
        user_id = kwargs.get('user_id')
        item_id = kwargs.get('item_id')

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
    """
    GET /api/cart/view
    Views the items in the cart for a user.
    """
    def get(self, request, *args, **kwargs):
        """
        GET /api/cart
    def get(self, request):
        """
        # Get the user_id from the path parameters
        user_id = kwargs.get('user_id')

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
    """
    POST /api/order/checkout
    Handles the checkout process, including saving addresses, payments, and creating an order.
    """
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_STRING, description='User ID'),
                'street': openapi.Schema(type=openapi.TYPE_STRING, description='Street address'),
                'city': openapi.Schema(type=openapi.TYPE_STRING, description='City'),
                'state': openapi.Schema(type=openapi.TYPE_STRING, description='State'),
                'zip_code': openapi.Schema(type=openapi.TYPE_STRING, description='Zip code'),
                'country': openapi.Schema(type=openapi.TYPE_STRING, description='Country'),
                'payment_method': openapi.Schema(type=openapi.TYPE_STRING, description='Payment method (card, cash, etc.)'),
                'card_number': openapi.Schema(type=openapi.TYPE_STRING, description='Card number (if applicable)', nullable=True),
                'expiry_date': openapi.Schema(type=openapi.TYPE_STRING, description='Expiry date (if applicable)', nullable=True),
                'cvv': openapi.Schema(type=openapi.TYPE_STRING, description='CVV (if applicable)', nullable=True),
                'promo_code': openapi.Schema(type=openapi.TYPE_STRING, description='Promo code (optional)'),
            },
        ),
        responses={
            201: openapi.Response('Order created successfully', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'order_id': openapi.Schema(type=openapi.TYPE_STRING),
                    'total_price': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'payment_status': openapi.Schema(type=openapi.TYPE_STRING),
                    'order_status': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )),
            400: "Invalid input",
            500: "Internal server error"
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Handles the checkout process, including saving addresses, payments, and creating an order.
        """
        user_id = request.data.get('user_id')
        street = request.data.get('street')
        city = request.data.get('city')
        state = request.data.get('state')
        zip_code = request.data.get('zip_code')
        country = request.data.get('country')
        payment_method = request.data.get('payment_method')
        card_number = request.data.get('card_number', None)
        expiry_date = request.data.get('expiry_date', None)
        cvv = request.data.get('cvv', None)
        promo_code = request.data.get('promo_code', None)

        # Ensure required fields are provided
        if not user_id or not street or not city or not state or not zip_code or not country or not payment_method:
            return Response({"error": "user_id, street, city, state, zip_code, country, and payment_method are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate user exists
        # try:
        #     user = User.objects.get(user_id=user_id)
        # except User.DoesNotExist:
        #     return Response({"error": "Invalid user ID."}, status=status.HTTP_400_BAD_REQUEST)

        cart_key = f'cart:{user_id}'
        cart = r.hgetall(cart_key)

        # Check if the cart is empty
        if not cart:
            return JsonResponse({"message": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate total price
        total_price = sum(10.99 * int(quantity) for item_id, quantity in cart.items())

        # Apply promo code discount if valid
        discount = 0.00
        if promo_code == "DISCOUNT10":
            discount = total_price * 0.10
            total_price -= discount

        # Use transaction to ensure atomicity
        try:
            with transaction.atomic():
                # Save address
                user = User.objects.get(user_id=user_id)  # Fetch the User instance
                address = Address.objects.create(
                    user_id=user,
                    street=street,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    country=country,
                    is_default=True  # Mark the address as default if needed
                )

                # Create order
                order = Order.objects.create(
                    user_id=user,
                    total_price=total_price,
                    discount=discount,
                    payment_status='pending',
                    order_status='processing'
                )

                # Save order items
                for item_id, quantity in cart.items():
                    OrderItem.objects.create(
                        order_id=order.order_id,
                        item_id=item_id,
                        quantity=int(quantity),
                        price=10.99
                    )

                # Save payment details
                if payment_method == 'card':
                    # Extract card details
                    card_last4 = card_number[-4:] if card_number else None
                    card_type = 'Other'  # Default card type, can be updated based on card validation logic
                    exp_month, exp_year = map(int, expiry_date.split('/')) if expiry_date else (None, None)

                    # Save payment details
                    payment = Payment.objects.create(
                        user_id=user,
                        card_last4=card_last4,
                        card_type=card_type,
                        exp_month=exp_month,
                        exp_year=exp_year,
                        is_default=True  # Mark as default if needed
                    )
                else:
                    payment = Payment.objects.create(
                        user_id=user,
                        card_last4=None,
                        card_type='Other',
                        exp_month=None,
                        exp_year=None,
                        is_default=False
                    )

            # Remove cart from Redis after successful order placement
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

class PaymentPrcessing(APIView):
    """
    POST /api/order/payment
    Handles payment processing for an order.
    """
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'order_id': openapi.Schema(type=openapi.TYPE_STRING, description='Order ID'),
                'payment_token': openapi.Schema(type=openapi.TYPE_STRING, description='Payment token from Stripe/PayPal'),
            },
        ),
        responses={
            200: openapi.Response('Payment successful', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'payment_status': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )),
            400: "Invalid input",
            500: "Internal server error"
        }
    )
    def post(self, request):
        """
        Handles payment processing for an order.
        """
        # Get the order ID and payment token from the request
        order_id = request.data.get('order_id')
        payment_token = request.data.get('payment_token')

        # Validate input
        if not order_id or not payment_token:
            return Response({"error": "order_id and payment_token are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Process payment with external service (e.g., Stripe/PayPal)
            # This is a placeholder for actual payment processing logic
            # For example, using Stripe API to charge the card

            # Simulate successful payment processing
            payment_status = "completed"  # Change this based on actual payment result

            return Response({"message": "Payment processed successfully.", "payment_status": payment_status}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"Payment processing failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderHistory(APIView):
    """
    GET /api/order/history
    Retrieves the order history for a given user.
    """
    def get(self, request, **kwargs):
        user_id_str = kwargs.get('user_id')

        # Validate user_id presence
        if not user_id_str:
            return Response({"error": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate UUID format for user_id
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            return Response({"error": f"Invalid user_id format: {user_id_str}. Ensure it's a valid UUID."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        # Fetch order history
        orders = Order.objects.filter(user_id=user_id).values(
            "order_id", "total_price", "order_status", "created_at"
        )

        return Response({"orders": list(orders)}, status=status.HTTP_200_OK)