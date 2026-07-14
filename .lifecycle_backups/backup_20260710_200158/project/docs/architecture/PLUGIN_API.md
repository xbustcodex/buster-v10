# Plugin API

```python
class ExamplePlugin:
    name = 'example'
    version = '1.0.0'

    def register(self, runtime):
        runtime.services.register('example', self)
```
