from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the initial admin superuser if it does not already exist."

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = "admin"
        email = "admin@example.com"
        password = "admin123"

        if user_model.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING("Admin user already exists."))
            return

        user_model.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        self.stdout.write(self.style.SUCCESS("Admin user created successfully."))
