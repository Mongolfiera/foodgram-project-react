from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from api.fields import Base64ImageField
from recipes.models import Follow, Ingredient, IngredientInRecipe, Recipe, Tag

User = get_user_model()


class CustomUserSerializer(UserSerializer):
    """Сериализатор для пользователя."""

    is_subscribed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        """Подписан ли пользователь на автора."""
        user = self.context.get('request').user
        return (user.is_authenticated
                and user.follower.filter(author=obj).exists())


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для создания пользователя."""

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'email',
                  'first_name', 'last_name')


class RecipeShortSerializer(serializers.ModelSerializer):
    """Сериализатор для коротких представлений рецептов в списках."""

    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FollowSerializer(CustomUserSerializer):
    """Сериализатор для подписок пользователя."""

    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField(read_only=True)

    class Meta(CustomUserSerializer.Meta):
        fields = CustomUserSerializer.Meta.fields + (
            'recipes', 'recipes_count',
        )
        read_only_fields = ('email', 'username', 'first_name', 'last_name')

    def validate(self, data):
        """Проверка корректности подписки."""
        user = self.context.get('request').user
        author = self.instance
        if user == author:
            raise serializers.ValidationError(
                'Вы не можете подписаться на себя.',
            )
        if Follow.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого автора.',
            )
        return data

    def get_recipes(self, obj):
        """Получает рецепты автора."""
        request = self.context.get('request')
        recipes_limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if recipes_limit:
            recipes = recipes[: int(recipes_limit)]
        return RecipeShortSerializer(
            recipes, many=True).data

    def get_recipes_count(self, obj):
        """Получает количество рецептов автора."""
        return obj.recipes.count()


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте."""

    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all(),
    )
    name = serializers.ReadOnlyField(
        source='ingredient.name',
    )
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit',
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientInRecipeWriteSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all(),
    )
    recipe = serializers.PrimaryKeyRelatedField(read_only=True)
    amount = serializers.IntegerField(write_only=True, min_value=1)

    class Meta:
        model = IngredientInRecipe
        fields = ('recipe', 'id', 'amount')

    def validate_amount(self, amount):
        """Проверка количества ингредиента."""
        if amount < 1:
            raise serializers.ValidationError(
                'Введите количество не меньше 1.',
            )
        return amount


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для чтения рецептов."""

    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeSerializer(many=True, read_only=True,
                                               source='ingredient_recipe')
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField(read_only=True)
    is_in_shopping_cart = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )

    def get_is_favorited(self, recipe):
        """Добавлен ли рецепт в избранное."""
        user = self.context.get('request').user
        return (user.is_authenticated
                and user.favorites.filter(recipe=recipe).exists())

    def get_is_in_shopping_cart(self, recipe):
        """Добавлен ли рецепт в список покупок."""
        user = self.context.get('request').user
        return (user.is_authenticated
                and user.shopping_cart.filter(recipe=recipe).exists())


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор для записи (создания и модификации) рецептов."""

    tags = serializers.PrimaryKeyRelatedField(many=True,
                                              queryset=Tag.objects.all())
    ingredients = IngredientInRecipeWriteSerializer(many=True)
    author = CustomUserSerializer(read_only=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'tags', 'ingredients',
            'name', 'image', 'text', 'cooking_time',
        )

    def validate_ingredients(self, ingredients):
        """Проверка наличия и уникальности ингредиентов."""
        ingredients_list = [
            ingredient.get('ingredient') for ingredient in ingredients
        ]
        if not ingredients:
            raise serializers.ValidationError('Добавьте ингредиенты.')
        if len(ingredients_list) > len(set(ingredients_list)):
            raise serializers.ValidationError(
                'Ингредиенты не могут повторяться.',
            )
        return ingredients

    def validate_tags(self, tags):
        """Проверка наличия и уникальности тэгов."""
        if len(tags) < 1:
            raise serializers.ValidationError('Добавьте тэги.')
        if len(tags) > len(set(tags)):
            raise serializers.ValidationError('Теги не могут повторяться.')
        return tags

    def save_ingredients(self, recipe, ingredients):
        IngredientInRecipe.objects.bulk_create(
            [
                IngredientInRecipe(
                    recipe=recipe,
                    ingredient=ingredient.get('ingredient'),
                    amount=ingredient.get('amount'),
                )
                for ingredient in ingredients
            ],
        )
        return ingredients

    @transaction.atomic
    def create(self, validated_data):
        """Сериализация создания рецепта."""
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.save_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        """Сериализация модификации рецепта."""
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        if tags:
            instance.tags.set(tags)
        if ingredients:
            instance.ingredients.clear()
            self.save_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        """Возвращаем прдеставление в таком же виде, как и GET-запрос."""
        request = self.context.get('request')
        context = {'request': request}
        return RecipeSerializer(instance, context=context).data
