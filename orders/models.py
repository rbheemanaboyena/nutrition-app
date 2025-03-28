from django.db import models
import uuid
from users.models import User

# Cart model using Redis for session-based storage (not a Django model but a reference)
# You can use `django-redis` to handle Redis operations in your application.

# Cart table - Redis-based session storage (pseudo-code as Redis is not a Django model)
# Example: cart:{user_id} => { item_id: quantity, item_price }

# Order model
class Order(models.Model):
    order_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="Order")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed')], default='pending')
    order_status = models.CharField(max_length=20, choices=[('processing', 'Processing'), ('delivered', 'Delivered')], default='processing')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.order_id}"

# OrderItems model
class OrderItem(models.Model):
    order_item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    item_id = models.UUIDField()  # Item ID from your inventory system
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Item {self.item_id} for Order {self.order_id}"

# Address Model
class Address(models.Model):
    address_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"
    
# Payment Model
class Payment(models.Model):
    CARD_TYPES = [
        ('VISA', 'Visa'),
        ('MasterCard', 'MasterCard'),
        ('AMEX', 'American Express'),
        ('Other', 'Other'),
    ]

    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    card_last4 = models.CharField(max_length=4)
    card_type = models.CharField(max_length=20, choices=CARD_TYPES)
    exp_month = models.PositiveIntegerField()
    exp_year = models.PositiveIntegerField()
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.card_type} ****{self.card_last4}"