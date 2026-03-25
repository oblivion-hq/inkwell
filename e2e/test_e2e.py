import os
from playwright.sync_api import Page

BASE_URL = os.environ.get("BASE_URL", "http://localhost:80")


def test_homepage_loads(page: Page):
    """Public landing page shows the hero section."""
    page.goto(BASE_URL)
    assert page.title() == "Inkwell — A place for your thoughts"
    assert page.locator("h1").is_visible()


def test_register_page_loads(page: Page):
    """Register page is reachable and has a submit button."""
    page.goto(f"{BASE_URL}/user/register/")
    assert page.locator("input[name='username']").is_visible()
    assert page.locator("button[type='submit']").is_visible()


def test_login_page_loads(page: Page):
    """Login page is reachable and has username/password fields."""
    page.goto(f"{BASE_URL}/accounts/login/")
    assert page.locator("input[name='username']").is_visible()
    assert page.locator("input[name='password']").is_visible()
