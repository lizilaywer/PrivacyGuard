"""Minimal stdlib-only subprocess protocol. Never logs text or writes files."""
import json
import re
import sys
import os


def _stream(stream, number, mode):
    if stream is not None:
        return stream.buffer
    if os.name == "nt":
        import ctypes
        import msvcrt
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetStdHandle.argtypes = [ctypes.c_uint32]
        kernel.GetStdHandle.restype = ctypes.c_void_p
        handle = kernel.GetStdHandle(number & 0xffffffff)
        if not handle or handle == ctypes.c_void_p(-1).value:
            raise OSError("Missing redirected pipe")
        flags = os.O_BINARY | (os.O_RDONLY if mode == "rb" else os.O_WRONLY)
        return os.fdopen(msvcrt.open_osfhandle(handle, flags), mode)
    return open(0 if mode == "rb" else 1, mode, closefd=False)


def run_service():
    reader, writer = _stream(sys.stdin, -10, "rb"), _stream(sys.stdout, -11, "wb")
    writer.write(b'{"ready":true}\n')
    writer.flush()
    for line in reader:
        try:
            if len(line) > 8 * 1024 * 1024:
                raise ValueError("limit")
            request = json.loads(line)
            pattern, text = request["pattern"], request["text"]
            if not isinstance(pattern, str) or not isinstance(text, str) or len(pattern) > 2048 or len(text) > 1000000:
                raise ValueError("limit")
            spans = []
            for match in re.finditer(pattern, text, re.IGNORECASE):
                if match.start() < match.end():
                    spans.append([match.start(), match.end()])
                if len(spans) > 100000:
                    raise ValueError("limit")
            response = {"spans": spans}
        except Exception:
            response = {"error": "invalid_or_limit"}
        writer.write((json.dumps(response) + "\n").encode("utf-8"))
        writer.flush()


if __name__ == "__main__":
    run_service()
