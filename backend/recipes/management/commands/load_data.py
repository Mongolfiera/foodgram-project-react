import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient

FILE_NAME = 'ingredients.csv'
TABLE = Ingredient


class Command(BaseCommand):
    """Команда для загрузки ингредиентов."""

    def handle(self, *args, **options):
        """Загрузка ингредиентов."""
        with open(os.path.join(
            settings.BASE_DIR, 'data', FILE_NAME,
        ), encoding='utf-8') as file:

            reader = list(csv.reader(file))
            TABLE.objects.bulk_create(
                [TABLE(name=name, measurement_unit=measurement_unit)
                    for name, measurement_unit in reader], batch_size=1000)
