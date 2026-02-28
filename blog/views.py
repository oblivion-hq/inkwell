from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .forms import PostForm
from .models import Post


@login_required
def home(request):
    posts = Post.objects.select_related("author").prefetch_related("tags").order_by("-created_at")
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
def post_detail(request, slug):
    post = get_object_or_404(Post.objects.select_related("author").prefetch_related("tags", "comments__author"), slug=slug)
    return render(request, "blog/post_detail.html", {"post": post})
