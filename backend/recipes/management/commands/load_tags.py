from django.core.management import BaseCommand

from recipes.models import Tag


class Command(BaseCommand):
    """Комагда для создания тегов."""

    def handle(self, *args, **kwargs):
        """Создание тегов."""
        tags = (
            ('Завтрак', '#E26C2D', 'breakfast'),
            ('Обед', '#008000', 'dinner'),
            ('Ужин', '#7366BD', 'supper'),
        )

        Tag.objects.bulk_create(
            [Tag(name=name, color=color, slug=slug)
                for name, color, slug in tags])
