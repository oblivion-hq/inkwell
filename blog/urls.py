from django.urls import path

from .views import home, post_create, post_delete, post_detail, post_edit

app_name = "blog"

urlpatterns = [
    path("", home, name="blog-home"),
    path("new/", post_create, name="post-create"),
    path("<slug:slug>/edit/", post_edit, name="post-edit"),
    path("<slug:slug>/delete/", post_delete, name="post-delete"),
    path("<slug:slug>/", post_detail, name="post-detail"),
]
