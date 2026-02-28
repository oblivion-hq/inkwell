from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .forms import CommentForm, PostForm
from .models import Post


def public_home(request):
    posts = Post.objects.filter(published=True).select_related("author").prefetch_related("tags").order_by("-created_at")
    return render(request, "home.html", {"posts": posts})


@login_required
def home(request):
    posts = Post.objects.filter(author=request.user).select_related("author").prefetch_related("tags").order_by("-created_at")
    return render(request, "blog/home.html", {"posts": posts})


@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            # Deduplicate slug — Post.save() auto-generates from title but
            # the unique constraint will raise IntegrityError on duplicates.
            base_slug = slugify(post.title)
            slug, n = base_slug, 1
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            post.slug = slug
            post.save()
            form.save_m2m()  # must come after post.save()
            return redirect("blog:blog-home")
    else:
        form = PostForm()
    return render(request, "blog/post_create.html", {"form": form})


@login_required
def post_delete(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    if request.method == "POST":
        post.delete()
    return redirect("blog:blog-home")


@login_required
def post_edit(request, slug):
    post = get_object_or_404(Post, slug=slug, author=request.user)
    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            return redirect("blog:post-detail", slug=post.slug)
    else:
        form = PostForm(instance=post)
    return render(request, "blog/post_edit.html", {"form": form, "post": post})


@login_required
def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects.select_related("author").prefetch_related("tags", "comments__author"),
        slug=slug,
    )
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect("blog:post-detail", slug=slug)
    else:
        form = CommentForm()
    comments = post.comments.filter(approved=True).select_related("author")
    return render(request, "blog/post_detail.html", {"post": post, "comments": comments, "form": form})
