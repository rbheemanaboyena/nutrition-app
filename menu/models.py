import uuid
from django.db import models

class Restaurant(models.Model):
    restaurant_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.UUIDField()
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
        ('Snacks', 'Snacks'),
    ]
    
    item_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField(max_length=255, null=True, blank=True)
    tags = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Ingredient(models.Model):
    ingredient_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='ingredients')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class NutritionFact(models.Model):
    nutrition_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='nutrition_facts')
    calories = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    protein = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carbohydrates = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fiber = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sugar = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sodium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

