from django.urls import path

from .views import (
    api_docs, api_post_detail, api_post_list,
    home, post_create, post_delete, post_detail, post_edit,
)

app_name = "blog"

urlpatterns = [
    path("", home, name="blog-home"),
    path("new/", post_create, name="post-create"),
    # API — must come before <slug:slug>/ to avoid collision
    path("api/", api_docs, name="api-docs"),
    path("api/posts/", api_post_list, name="api-post-list"),
    path("api/posts/<slug:slug>/", api_post_detail, name="api-post-detail"),
    path("<slug:slug>/edit/", post_edit, name="post-edit"),
    path("<slug:slug>/delete/", post_delete, name="post-delete"),
    path("<slug:slug>/", post_detail, name="post-detail"),
]
