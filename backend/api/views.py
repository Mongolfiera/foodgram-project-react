from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import CustomPagination
from api.permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from api.serializers import (
    CustomUserSerializer, FollowSerializer, IngredientSerializer,
    RecipeSerializer, RecipeShortSerializer, RecipeWriteSerializer,
    TagSerializer,
)
from recipes.models import (
    Favorite, Follow, Ingredient, IngredientInRecipe, Recipe, ShoppingCart,
    Tag,
)

User = get_user_model()


class CustomUserViewSet(UserViewSet):
    """Представление для пользователей."""

    http_method_names = ['get', 'post', 'delete']
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def subscribe(self, request, **kwargs):
        """Подписка / отписка на / от автора."""
        user = request.user
        author = get_object_or_404(User, id=kwargs.get('id'))

        if request.method == 'POST':
            serializer = FollowSerializer(
                author, data=request.data, context={'request': request},
            )
            if serializer.is_valid(raise_exception=True):
                Follow.objects.create(user=user, author=author)
                return Response(serializer.data,
                                status=status.HTTP_201_CREATED)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        get_object_or_404(Follow, user=user, author=author).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )
    def subscriptions(self, request):
        """Получить список авторов, на которые подписан пользователь."""
        user = request.user
        queryset = User.objects.filter(following__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages, many=True, context={'request': request},
        )
        return self.get_paginated_response(serializer.data)


class IngredientViewSet(ReadOnlyModelViewSet):
    """Представление для ингредиентов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAdminOrReadOnly,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class TagViewSet(ReadOnlyModelViewSet):
    """Представление для тегов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = None


class RecipeViewSet(ModelViewSet):
    """Представление для рецептов."""

    http_method_names = ['get', 'post', 'patch', 'delete']
    queryset = Recipe.objects.all()
    permission_classes = (IsAuthorOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от метода."""
        if self.action in SAFE_METHODS:
            return RecipeSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        """Сохранение объекта."""
        serializer.save(author=self.request.user)

    def add_to(self, model, recipe, user):
        if model.objects.filter(user=user, recipe=recipe).exists():
            return Response(
                {'errors': 'Рецепт уже добавлен.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        model.objects.create(user=user, recipe=recipe)
        return Response(
            RecipeShortSerializer(recipe).data,
            status=status.HTTP_201_CREATED
        )

    def delete_from(self, model, recipe, user):
        obj = model.objects.filter(user=user, recipe=recipe)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Такого рецепта нет в списке.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def shopping_cart(self, request, **kwargs):
        """Добавление в список покупок."""
        recipe = get_object_or_404(Recipe, id=kwargs.get('pk'))
        user = request.user
        if request.method == 'POST':
            return self.add_to(ShoppingCart, recipe, user)
        return self.delete_from(ShoppingCart, recipe, user)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(IsAuthenticated,),
    )
    def favorite(self, request, **kwargs):
        """Добавление в избранное."""
        recipe = get_object_or_404(Recipe, id=kwargs.get('pk'))
        user = request.user

        if request.method == 'POST':
            return self.add_to(Favorite, recipe, user)
        return self.delete_from(Favorite, recipe, user)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
    )
    def download_shopping_cart(self, request):
        """Выгрузка списка покупок в файл."""
        user = request.user
        if not user.shopping_cart.exists():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        ingredients = (
            IngredientInRecipe.objects.filter(
                recipe__shopping_cart__user=user,
            )
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(quantity=Sum('amount')).order_by()
        )

        shopping_list = ('Список покупок: \n\n')
        shopping_list += ''.join([
            f'- {ingredient["ingredient__name"]}, '
            + f'({ingredient["ingredient__measurement_unit"]})'
            + f' - {ingredient["quantity"]}\n'
            for ingredient in ingredients
        ])

        filename = f'{user.username}_shopping_list.txt'
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename={filename}'

        return response
