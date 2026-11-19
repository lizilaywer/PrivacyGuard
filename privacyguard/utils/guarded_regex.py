"""Run custom Word regex with a process timeout, preserving Python re.

Only the regex subprocess is killed on timeout. No QThread is terminated.
The persistent child uses stdlib only, no models, no files, no network.
"""
import atexit
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading


class RuleBudgetError(RuntimeError):
    pass


class RegexService:
    def __init__(self):
        self.process = None
        self.messages = None
        self.lock = threading.Lock()

    def _start(self):
        command = ([sys.executable, "--pg-regex-worker"] if getattr(sys, "frozen", False)
                   else [sys.executable, "-I", str(Path(__file__).with_name("regex_service.py"))])
        self.messages = queue.Queue(maxsize=2)
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL,
                                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        process, messages = self.process, self.messages
        def read():
            try:
                for line in process.stdout:
                    messages.put(line)
            except (OSError, ValueError):
                pass
            finally:
                messages.put(None)
        threading.Thread(target=read, daemon=True, name="PrivacyGuard-regex-reader").start()
        try:
            ready = self.messages.get(timeout=4)
            if not ready or not json.loads(ready).get("ready"):
                raise RuleBudgetError("规则处理进程未就绪，文件未导出。")
        except (queue.Empty, ValueError) as error:
            self.close()
            raise RuleBudgetError("规则处理进程无法启动，文件未导出。") from error

    def close(self):
        process, self.process = self.process, None
        if process is None:
            return
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        for stream in (process.stdin, process.stdout):
            if stream:
                stream.close()

    def spans(self, pattern, text, timeout=.25):
        if len(pattern) > 2048 or len(text) > 1000000:
            raise RuleBudgetError("规则或文本超出处理上限，请缩短规则或拆分内容。")
        with self.lock:
            first = self.process is None or self.process.poll() is not None
            if first:
                self.close()
                self._start()
            try:
                self.process.stdin.write((json.dumps({"pattern": pattern, "text": text}, ensure_ascii=True) + "\n").encode())
                self.process.stdin.flush()
                line = self.messages.get(timeout=timeout)
                if not line:
                    raise RuleBudgetError("规则处理进程退出，请简化规则后重试。")
                result = json.loads(line)
                if "error" in result:
                    raise RuleBudgetError("规则无效或命中过多，请简化规则后重试。")
                return result["spans"]
            except queue.Empty as error:
                self.close()
                raise RuleBudgetError("这条正则执行过慢，已停止；文件未按不完整结果导出。请改用精确词或简化正则。") from error
            except (OSError, ValueError) as error:
                self.close()
                raise RuleBudgetError("规则处理失败，未继续导出。") from error


_service = RegexService()
atexit.register(_service.close)


def find_spans(pattern, text):
    return _service.spans(pattern, text)
