from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.serializers import LoginSerializer


class LoginView(TokenObtainPairView):
    """JWT login endpoint."""

    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer


class RefreshTokenView(TokenRefreshView):
    """JWT refresh endpoint."""

    permission_classes = (AllowAny,)
