from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .forms import CommentForm, PostForm
from .models import Post


# ── API helpers ──────────────────────────────────────────────────────────────

def _post_to_dict(post, include_content=False):
    data = {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "excerpt": post.excerpt,
        "author": post.author.username,
        "tags": [t.name for t in post.tags.all()],
        "created_at": post.created_at.isoformat(),
        "updated_at": post.updated_at.isoformat(),
    }
    if include_content:
        data["content"] = post.content
        data["content_html"] = str(post.get_content_html())
    return data


def _api_response(data):
    r = JsonResponse(data)
    r["Access-Control-Allow-Origin"] = "*"
    return r


def api_docs(request):
    base_url = request.build_absolute_uri("/").rstrip("/")
    return render(request, "blog/api_docs.html", {"base_url": base_url})


def api_post_list(request):
    qs = (Post.objects
          .filter(published=True)
          .select_related("author")
          .prefetch_related("tags")
          .order_by("-created_at"))
    author = request.GET.get("author")
    if author:
        qs = qs.filter(author__username=author)
    return _api_response({"count": qs.count(), "posts": [_post_to_dict(p) for p in qs]})


def api_post_detail(request, slug):
    post = get_object_or_404(
        Post.objects.select_related("author").prefetch_related("tags"),
        slug=slug, published=True,
    )
    return _api_response(_post_to_dict(post, include_content=True))


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
