from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from grading.views import home

admin.site.site_header = "PO Takip Sistemi"
admin.site.site_title = "PO Takip Sistemi"

urlpatterns = [
    path("", home, name="home"),
    path(
        "giris/",
        auth_views.LoginView.as_view(redirect_authenticated_user=True),
        name="login",
    ),
    path("cikis/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
]
