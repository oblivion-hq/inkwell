import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from .models import Post, Tag

pytestmark = pytest.mark.django_db


@pytest.fixture
def user():
    return User.objects.create_user(username="testuser", password="pass1234")


@pytest.fixture
def other_user():
    return User.objects.create_user(username="otheruser", password="pass1234")


@pytest.fixture
def post(user):
    return Post.objects.create(
        title="Hello World",
        content="Some **markdown** content",
        author=user,
        published=True,
    )


@pytest.fixture
def auth_client(user):
    c = Client()
    c.login(username="testuser", password="pass1234")
    return c


def test_post_slug_auto_generated(user):
    post = Post.objects.create(title="My Great Post", content="x", author=user)
    assert post.slug == "my-great-post"


def test_tag_slug_auto_generated():
    tag = Tag.objects.create(name="Django Tips")
    assert tag.slug == "django-tips"


def test_post_content_rendered_as_html(post):
    html = post.get_content_html()
    assert "<strong>markdown</strong>" in html


def test_home_view_redirects_anonymous():
    response = Client().get(reverse("blog:blog-home"))
    assert response.status_code == 302
    assert "/login/" in response["Location"]


def test_home_view_authenticated(auth_client):
    response = auth_client.get(reverse("blog:blog-home"))
    assert response.status_code == 200


def test_post_create_saves_and_redirects(auth_client, user):
    response = auth_client.post(
        reverse("blog:post-create"),
        {"title": "Brand New Post", "content": "Hello world", "excerpt": "", "published": False},
    )
    assert response.status_code == 302
    assert Post.objects.filter(title="Brand New Post", author=user).exists()


def test_post_edit_by_non_owner_returns_404(other_user, post):
    c = Client()
    c.login(username="otheruser", password="pass1234")
    response = c.get(reverse("blog:post-edit", kwargs={"slug": post.slug}))
    assert response.status_code == 404


def test_post_delete_by_owner(auth_client, post):
    slug = post.slug
    response = auth_client.post(reverse("blog:post-delete", kwargs={"slug": slug}))
    assert response.status_code == 302
    assert not Post.objects.filter(slug=slug).exists()


def test_blog_home_shows_only_own_posts(auth_client, user, other_user):
    Post.objects.create(title="My Post", content="x", author=user, published=True)
    Post.objects.create(title="Other User Post", content="x", author=other_user, published=True)
    response = auth_client.get(reverse("blog:blog-home"))
    assert b"My Post" in response.content
    assert b"Other User Post" not in response.content
