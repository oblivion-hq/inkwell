from django.urls import path

from .views import home, post_create

app_name = "blog"

urlpatterns = [
    path("", home, name="blog-home"),
    path("new/", post_create, name="post-create"),
]
