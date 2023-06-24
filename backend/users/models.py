from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models


def me_validator(value):
    """Проверка имени пользователя."""
    if value.lower() == 'me':
        raise ValidationError(
            'Выберите другое имя.',
        )


class User(AbstractUser):
    """Кастомный класс пользователя."""

    email = models.EmailField(
        max_length=254,
        unique=True,
        verbose_name='Адрес электронной почты',
    )
    first_name = models.CharField(
        max_length=150,
        verbose_name='Имя',
    )
    last_name = models.CharField(
        max_length=150,
        verbose_name='Фамилия',
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Уникальный юзернейм',
        validators=(
            RegexValidator(regex=r'^[\w.@+-]+\Z'),
            me_validator),
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'first_name', 'last_name')

    class Meta:
        ordering = ('-date_joined',)
        verbose_name = 'Пользователя'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username
