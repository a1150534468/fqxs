"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/users/", include("apps.users.urls")),
    path("api/inspirations/", include("apps.inspirations.urls")),
    path("api/novels/", include("apps.novels.urls")),
    path("api/chapters/", include("apps.chapters.urls")),
    path("api/tasks/", include("apps.tasks.urls")),
    path("api/stats/", include("apps.stats.urls")),
    path("api/llm-providers/", include("apps.llm_providers.urls")),
    path("api/", include("apps.monitoring.urls")),
]
