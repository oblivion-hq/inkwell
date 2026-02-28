### Pipeline flow on every push to "main"

```
push -> lint (flake8) -> pytest -> build image -> push :latest -> :sha -> ssh deploy 
```
