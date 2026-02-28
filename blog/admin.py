from django.contrib import admin

from .models import Comment, Post, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "published", "created_at"]
    list_filter = ["published", "created_at", "tags"]
    search_fields = ["title", "content"]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ["tags"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["author", "post", "created_at", "approved"]
    list_filter = ["approved", "created_at"]
    search_fields = ["body"]
