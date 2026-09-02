"""utils 包入口。

副作用：尝试把 stdout/stderr 切到 UTF-8，避免 Windows GBK 终端输出 emoji 时崩。
"""
import sys

# Python 3.7+ 提供 reconfigure
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, Exception):
    pass
