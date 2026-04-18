from django.urls import path

from apps.novels.views import GenerationContextView, WorkbenchContextView

urlpatterns = [
    path('<int:project_id>/context/', WorkbenchContextView.as_view(), name='workbench-context'),
    path('<int:project_id>/generation-context/', GenerationContextView.as_view(), name='generation-context'),
]
