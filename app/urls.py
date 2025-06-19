from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('upload', views.upload_image, name='upload_image'),
    path('login/', views.login_view, name='login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),  # Exemple
    path('prof/dashboard/', views.prof_dashboard, name='prof_dashboard'),    # Exemple
    path('secretariat/dashboard/', views.secretariat_dashboard, name='secretariat_dashboard'),  # Exemple
    path('etudiant/dashboard/', views.etudiant_dashboard, name='etudiant_dashboard'),  # Exemple
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register_view, name='register'),
]
