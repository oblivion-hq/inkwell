from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from blog.models import Comment, Post


class RegisterView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "registration/register.html"


@login_required
def profile(request):
    user = request.user
    posts = Post.objects.filter(author=user)

    total_posts = posts.count()
    published_posts = posts.filter(published=True).count()
    draft_posts = total_posts - published_posts
    total_comments = Comment.objects.filter(author=user).count()

    # Post counts per day (date → count)
    post_counts = {
        entry["day"]: entry["count"]
        for entry in (
            posts
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
        )
    }

    def level(count):
        if count == 0:
            return 0
        if count == 1:
            return 1
        if count == 2:
            return 2
        if count <= 4:
            return 3
        return 4

    start_date = user.date_joined.date()
    today = date.today()

    # Pad grid to full weeks (Monday … Sunday)
    grid_start = start_date - timedelta(days=start_date.weekday())
    grid_end = today + timedelta(days=(6 - today.weekday()))

    weeks = []
    month_row = []   # one label (or '') per week column
    prev_month = None
    d = grid_start

    while d <= grid_end:
        week = []
        for _ in range(7):
            outside = d < start_date or d > today
            count = post_counts.get(d, 0)
            week.append({
                "date": d,
                "count": count,
                "level": 0 if outside else level(count),
                "outside": outside,
                "label": (
                    f"{d.strftime('%b %d, %Y')}: {count} post{'s' if count != 1 else ''}"
                    if not outside else ""
                ),
            })
            d += timedelta(days=1)

        # Month label: first non-outside day whose month changed
        col_label = ""
        for day in week:
            if not day["outside"]:
                if day["date"].month != prev_month:
                    col_label = day["date"].strftime("%b")
                    prev_month = day["date"].month
                break

        month_row.append(col_label)
        weeks.append(week)

    return render(request, "user/profile.html", {
        "total_posts": total_posts,
        "published_posts": published_posts,
        "draft_posts": draft_posts,
        "total_comments": total_comments,
        "weeks": weeks,
        "month_row": month_row,
        "start_date": start_date,
    })


def public_profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=author, published=True).order_by("-created_at")
    return render(request, "user/public_profile.html", {
        "author": author,
        "posts": posts,
    })
