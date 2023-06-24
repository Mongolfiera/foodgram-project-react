from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Права на изменение - для администратора."""

    def has_permission(self, request, view):
        """Разрешения на уровне запроса."""
        return (request.method in SAFE_METHODS
                or (request.user.is_staff))


class IsAuthorOrReadOnly(BasePermission):
    """Права на изменение - для автора."""

    def has_object_permission(self, request, view, obj):
        """Разрешения на уровне объекта."""
        return (
            request.method in SAFE_METHODS
            or request.user == obj.author)
