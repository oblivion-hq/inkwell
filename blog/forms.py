from django import forms

from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "excerpt", "content", "tags", "published"]
        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "Post title...",
                "autofocus": True,
            }),
            "excerpt": forms.Textarea(attrs={
                "rows": 2,
                "placeholder": "Short summary shown in listings (optional)...",
            }),
            "content": forms.Textarea(attrs={
                "id": "md-editor",
                "rows": 20,
                "placeholder": "Write your post in Markdown...",
                "spellcheck": "false",
            }),
            "tags": forms.CheckboxSelectMultiple(),
        }
