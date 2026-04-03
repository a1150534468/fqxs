from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for auth responses."""

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_active', 'is_staff')


class LoginSerializer(TokenObtainPairSerializer):
    """JWT login serializer that also returns serialized user data."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
