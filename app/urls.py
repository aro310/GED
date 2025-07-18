from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('upload', views.upload_image, name='upload_image'),
    path('login/', views.login_view, name='login'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),  
    path('prof/dashboard/', views.prof_dashboard, name='prof_dashboard'),    
    path('secretariat/dashboard/', views.secretariat_dashboard, name='secretariat_dashboard'),
    path('etudiant/dashboard/', views.etudiant_dashboard, name='etudiant_dashboard'),  
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register_view, name='register'),
    path('face/', views.face_view, name='face'),
    path('upload', views.home_view, name='upload_images'),
    path('fichiers/', views.liste_fichiers, name="liste_fichiers"),
]

