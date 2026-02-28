from blog_project.settings import *  # noqa: F401, F403

# Override database to SQLite for fast, dependency-free tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
