from django.urls import path
from counter import views
urlpatterns = [path('', views.dashboard), path('api/sessions/', views.sessions), path('api/sessions/<uuid:session_id>/stop/', views.stop), path('api/sessions/<uuid:session_id>/frames/', views.frame), path('api/export.csv', views.export_csv)]
