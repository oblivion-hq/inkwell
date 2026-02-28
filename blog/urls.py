from django.urls import path

from .views import home, post_create, post_detail

app_name = "blog"

urlpatterns = [
    path("", home, name="blog-home"),
    path("new/", post_create, name="post-create"),
    path("<slug:slug>/", post_detail, name="post-detail"),
]
