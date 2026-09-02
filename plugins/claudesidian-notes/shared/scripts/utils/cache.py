"""API 调用缓存装饰器。

把任意函数的返回值序列化为 JSON 缓存到指定目录。
适用于：Semantic Scholar / Unpaywall / Crossref 等幂等 API 查询。
"""
import json
import hashlib
from pathlib import Path
from functools import wraps


def cached_call(cache_dir: str):
    """装饰器：将函数返回值缓存到本地 JSON。

    用法：
        @cached_call("cache/semantic_scholar")
        def fetch_paper(doi: str) -> dict: ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_path = Path(cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)
            # 用函数名 + 参数 hash 作为缓存键
            payload = json.dumps(
                {"fn": func.__name__, "args": args, "kwargs": kwargs},
                default=str,
                sort_keys=True,
            )
            key = hashlib.md5(payload.encode("utf-8")).hexdigest()
            cache_file = cache_path / f"{key}.json"
            if cache_file.exists():
                return json.loads(cache_file.read_text(encoding="utf-8"))
            result = func(*args, **kwargs)
            cache_file.write_text(
                json.dumps(result, ensure_ascii=False),
                encoding="utf-8",
            )
            return result
        return wrapper
    return decorator
