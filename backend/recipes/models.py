from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

User = get_user_model()


class Ingredient(models.Model):
    """Ингредиенты.

    Args:
        name(str): Название.
        measurement_unit(str): Единица измерения.
    """

    name = models.CharField(
        max_length=200,
        verbose_name='Название ингредиента',
    )
    measurement_unit = models.CharField(
        max_length=200,
        verbose_name='Единица измерения',
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient',
            ),
        ]

    def __str__(self):
        return self.name


class Tag(models.Model):
    """Тег - при нажатии на тег выводится список рецептов, c этим тегом.

    Args:
        name(str): Название тэга.
        color(str): Цветовой HEX-код.
        slug(str): slug.
    """

    name = models.CharField(
        max_length=200,
        verbose_name='Название тэга',
        unique=True,
    )
    color = models.CharField(
        max_length=7,
        verbose_name='Цвет',
        unique=True,
        validators=[
            RegexValidator(
                regex='(^#[0-9a-fA-F]{3}$)|(^#[0-9a-fA-F]{6}$)',
                message='Введите цвет в формате HEX.',
            ),
        ],
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        validators=[
            RegexValidator(
                regex='^[-a-zA-Z0-9_]+$',
            ),
        ],
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return self.name


class RecipeQuerySet(models.QuerySet):
    """Менеджер запросов для получения количества избранных."""

    def add_user_annotations(self, user_id):
        """Получение количества избранных рецептов и рецептов в корзине."""
        return self.annotate(
            is_favorite=models.Exists(
                Favorite.objects.filter(
                    user_id=user_id, recipe__pk=models.OuterRef('pk'),
                ),
            ),
            is_in_shopping_cart=models.Exists(
                ShoppingCart.objects.filter(
                    user_id=user_id, recipe__pk=models.OuterRef('pk'),
                ),
            ),
        )

    def filter_by_tag(self, tags):
        """Фильтрация по тегам."""
        if tags:
            return self.filter(tags__slug__in=tags).distinct()
        return self


class Recipe(models.Model):
    """Рецепт.

    Args:
        tags(list[Tag]): Список тегов.
        author(User): Автор рецепта.
        ingredients(list[Ingredient]): Список ингредиентов.
        name(str): Название тэга.
        image(string <url>): Ссылка на картинку на сайте.
        text(str): Описание рецепта.
        cooking_time(int): Время приготовления (в минутах).
    """

    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True,
        db_index=True,
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        max_length=200,
        verbose_name='Название рецепта',
        help_text='Название рецепта',
    )
    image = models.ImageField(
        verbose_name='Картинка рецепта',
        upload_to='recipes/',
    )
    text = models.TextField(
        verbose_name='Описание рецепта',
        help_text='Описание рецепта',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        through_fields=('recipe', 'ingredient'),
        related_name='recipes',
        verbose_name='Список ингредиентов',
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Список тегов',
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления (в минутах)',
        help_text='Время приготовления (в минутах)',
        validators=[
            MinValueValidator(1, message='Введите время не меньше 1 мин'),
        ],
    )

    objects = RecipeQuerySet.as_manager()

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'author'),
                name='unique_author_recipe',
            ),
        ]

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    """Ингредиент и его количество в рецепте.

    Args:
        amount(int): Количество ингридиента в рецепте.
    """

    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipe',
        verbose_name='Ингредиент',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_recipe',
        verbose_name='Рецепт',
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[
            MinValueValidator(1, message='Введите количество не меньше 1'),
        ],
    )

    class Meta:
        ordering = ('recipe',)
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=('ingredient', 'recipe'),
                name='unique_ingredient_recipe',
            ),
        ]

    def __str__(self):
        return f'{self.ingredient} в {self.recipe}'


class Favorite(models.Model):
    """Избранные рецепты.

    Args:
        user(User): Пользователь.
        recipe(Recipe): Рецепт.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт',
    )

    class Meta:
        ordering = ('recipe',)
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite_user_recipe',
            ),
        ]

    def __str__(self):
        return f'Рецепт {self.recipe} в избранных у {self.user}'


class ShoppingCart(models.Model):
    """Рецепты в корзине покупок.

    Args:
        user(User): Пользователь.
        recipe(Recipe): Рецепт.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Хозяин корзины',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Рецепт',
    )

    class Meta:
        ordering = ('recipe',)
        verbose_name = 'Рецепт в корзине'
        verbose_name_plural = 'Рецепты в корзине'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_recipe_cart',
            ),
        ]

    def __str__(self):
        return f'Рецепт {self.recipe} в корзине у {self.user}'


class Follow(models.Model):
    """Класс подписчика."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор',
    )

    class Meta:
        ordering = ('author',)
        verbose_name = 'Подписку'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_user_author_pair',
            ),
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'
