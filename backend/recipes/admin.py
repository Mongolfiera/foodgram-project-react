from django.contrib import admin

from recipes.models import (
    Favorite, Follow, Ingredient, IngredientInRecipe, Recipe, ShoppingCart,
    Tag,
)


class IngredientRecipeInline(admin.TabularInline):
    """Админ для списка ингредиентов."""

    list_display = ('name',)
    model = IngredientInRecipe
    min_num = 1
    extra = 1


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Админ для модели ингредиента."""

    list_display = ('id', 'name', 'measurement_unit')
    list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Админ для модели тега."""

    list_display = ('id', 'name', 'color', 'slug')
    search_fields = ('name',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Админ для модели рецепта."""

    inlines = (IngredientRecipeInline,)
    list_display = (
        'id',
        'pub_date',
        'author',
        'name',
        'text',
        'cooking_time',
        'count_favorites',
    )
    list_filter = ('name', 'author', 'tags', 'ingredients')
    search_fields = ('name',)
    filter_horizontal = ('tags',)
    autocomplete_fields = ('ingredients',)
    readonly_fields = ('count_favorites',)

    @admin.display(description='Добавлений в избранное')
    def count_favorites(self, obj):
        """Получает число добавлений в избранное."""
        return Favorite.objects.filter(recipe=obj).count()


@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    """Админ для ингредиента в рецепте."""

    fields = ('recipe', 'ingredient', 'amount')
    list_filter = ('recipe', 'ingredient')


admin.site.register(Favorite)
admin.site.register(ShoppingCart)
admin.site.register(Follow)
