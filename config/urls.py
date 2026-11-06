from django.contrib import admin
from django.urls import path

from grading.views import home

admin.site.site_header = "PO Takip Sistemi"
admin.site.site_title = "PO Takip Sistemi"

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
]
