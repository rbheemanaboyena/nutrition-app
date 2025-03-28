from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
import json
import uuid
from .models import Restaurant, MenuItem, Ingredient, NutritionFact
from .serializers import MenuItemSerializer
from rest_framework import viewsets
from rest_framework import status
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class RestaurantView(APIView):
    # Define the schema for the request body
    restaurant_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'owner_id': openapi.Schema(type=openapi.TYPE_STRING),
            'name': openapi.Schema(type=openapi.TYPE_STRING),
            'description': openapi.Schema(type=openapi.TYPE_STRING, default='')
        }
    )
    # Define the schema for the response body
    restaurant_response_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'message': openapi.Schema(type=openapi.TYPE_STRING),
            'restaurant_id': openapi.Schema(type=openapi.TYPE_STRING)
        }
    )

    @method_decorator(csrf_exempt)  # Disable CSRF
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        data = json.loads(request.body)
        restaurant = Restaurant.objects.create(
            restaurant_id=uuid.uuid4(),
            owner_id=data['owner_id'],
            name=data['name'],
            description=data.get('description', '')
        )
        return JsonResponse({"message": "Restaurant created successfully.", "restaurant_id": str(restaurant.restaurant_id)})

    def get(self, request, id=None):
        if id:
            restaurant = get_object_or_404(Restaurant, restaurant_id=id)
            return JsonResponse({
                "restaurant_id": str(restaurant.restaurant_id),
                "name": restaurant.name,
                "description": restaurant.description
            })
        else:
            restaurants = list(Restaurant.objects.values('restaurant_id', 'name', 'description'))
            return JsonResponse(restaurants, safe=False)

    def put(self, request, id):
        data = json.loads(request.body)
        restaurant = get_object_or_404(Restaurant, restaurant_id=id)
        restaurant.name = data.get('name', restaurant.name)
        restaurant.description = data.get('description', restaurant.description)
        restaurant.save()
        return JsonResponse({"message": "Restaurant updated successfully."}, status=status.HTTP_200_OK)

    def delete(self, request, id):
        restaurant = get_object_or_404(Restaurant, restaurant_id=id)
        restaurant.delete()
        return JsonResponse({"message": "Restaurant deleted successfully."})

class MenuItemView(APIView):

    @method_decorator(csrf_exempt)  # Disable CSRF
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, id):
        restaurant = get_object_or_404(Restaurant, restaurant_id=id)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

        # Step 1: Create Menu Item
        menu_item = MenuItem.objects.create(
            item_id=uuid.uuid4(),
            restaurant=restaurant,
            name=data['name'],
            description=data.get('description', ''),
            category=data['category'],
            price=data['price'],
            image_url=data.get('image_url', ''),
            tags=data.get('tags', [])
        )

        # Step 2: Add Ingredients
        ingredients = data.get('ingredients', [])
        for ingredient in ingredients:
            Ingredient.objects.create(
                ingredient_id=uuid.uuid4(),
                item=menu_item,
                name=ingredient['name'],
                quantity=ingredient['quantity'],
                unit=ingredient.get('unit', '')
            )

        # Step 3: Add Nutrition Facts
        nutrition_data = data.get('nutrition_facts', {})
        if nutrition_data:
            NutritionFact.objects.create(
                nutrition_id=uuid.uuid4(),
                item=menu_item,
                calories=nutrition_data.get('calories'),
                protein=nutrition_data.get('protein'),
                carbohydrates=nutrition_data.get('carbohydrates'),
                fat=nutrition_data.get('fat'),
                fiber=nutrition_data.get('fiber'),
                sugar=nutrition_data.get('sugar'),
                sodium=nutrition_data.get('sodium')
            )

        return JsonResponse({
            "message": "Menu item added successfully.",
            "item_id": str(menu_item.item_id)
        }, status=201)

    def get(self, request, id, item_id=None):
        restaurant = get_object_or_404(Restaurant, restaurant_id=id)

        #  Get ALL items (Without ingredients & nutrition_facts)
        if item_id is None:
            menu_items = MenuItem.objects.filter(restaurant=restaurant)
            data = [
                {
                    "item_id": str(item.item_id),
                    "name": item.name,
                    "description": item.description,
                    "category": item.category,
                    "price": float(item.price),
                    "image_url": item.image_url,
                    "tags": item.tags,
                }
                for item in menu_items
            ]
            return JsonResponse({"menu_items": data}, status=200)

        item = get_object_or_404(MenuItem.objects.prefetch_related("ingredients", "nutrition_facts"), item_id=item_id, restaurant=restaurant)

        # Fetch first NutritionFact (if exists)
        nutrition = item.nutrition_facts.first()

        data = {
            "item_id": str(item.item_id),
            "name": item.name,
            "description": item.description,
            "category": item.category,
            "price": float(item.price),
            "image_url": item.image_url,
            "tags": item.tags,
            "ingredients": [
                {
                    "name": ingredient.name,
                    "quantity": float(ingredient.quantity),
                    "unit": ingredient.unit
                } for ingredient in item.ingredients.all()
            ],
            "nutrition_facts": {
                "calories": float(nutrition.calories) if nutrition else None,
                "protein": float(nutrition.protein) if nutrition else None,
                "carbohydrates": float(nutrition.carbohydrates) if nutrition else None,
                "fat": float(nutrition.fat) if nutrition else None,
                "fiber": float(nutrition.fiber) if nutrition else None,
                "sugar": float(nutrition.sugar) if nutrition else None,
                "sodium": float(nutrition.sodium) if nutrition else None
            }
        }

        return JsonResponse(data, status=200)

    def put(self, request, id, item_id):
        data = json.loads(request.body)
        menu_item = get_object_or_404(MenuItem, restaurant_id=id, item_id=item_id)
        menu_item.name = data.get('name', menu_item.name)
        menu_item.description = data.get('description', menu_item.description)
        menu_item.category = data.get('category', menu_item.category)
        menu_item.price = data.get('price', menu_item.price)
        menu_item.image_url = data.get('image_url', menu_item.image_url)
        menu_item.tags = data.get('tags', menu_item.tags)
        menu_item.save()
        return JsonResponse({"message": "Menu item updated successfully."})

    @swagger_auto_schema(
        operation_description="Delete a menu item",
        responses={200: openapi.Response("Menu item deleted successfully.")}
    )
    def delete(self, request, id, item_id):
        menu_item = get_object_or_404(MenuItem, restaurant_id=id, item_id=item_id)
        menu_item.delete()
        return JsonResponse({"message": "Menu item deleted successfully."}, status=status.HTTP_200_OK)

