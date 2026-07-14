# Buster v7.1 Internet Intelligence Core

## Install dependencies

```bash
pip install requests beautifulsoup4
```

## Test

```bash
pytest
```

## Quick manual test

```python
from buster.web.internet_service import InternetService

internet = InternetService()
result = internet.query("latest Python release")
print(result.answer)

for source in result.sources:
    print(source.title, source.url)
```

## Safe command integration

Start by adding one manual command to your dispatcher:

```python
elif cmd == "web":
    from buster.web.internet_service import InternetService
    internet = InternetService()
    result = internet.query(args)
    print(result.answer)
```

Then later connect `WebBrain` into your main Buster agent loop.
