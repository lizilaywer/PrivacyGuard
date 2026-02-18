"""
临时文件管理器

v36.5: 模块化拆分，从 main.py 提取
安全特性:
- 使用 atexit 注册退出清理钩子
- 类级别注册表追踪所有实例
- 线程锁保护
"""

import os
import threading
import atexit
import tempfile


class TempFileManager:
    """统一临时文件管理器，确保资源正确释放（v36.5: 线程安全版）

    安全特性:
    - 使用 atexit 注册退出清理钩子，确保程序退出时自动清理
    - 类级别注册表追踪所有实例
    - 使用具体异常类型处理删除错误 (OSError, IOError)
    - 防止临时文件泄露
    - v36.5: 添加线程锁保护，确保多线程安全

    使用示例:
        manager = TempFileManager()
        temp_file = manager.create_temp_file(suffix='.pdf')
        temp_dir = manager.create_temp_dir()
        # 文件在程序退出时自动清理（无需手动调用 cleanup）
    """

    # 类级别注册表，跟踪所有实例
    _instances = []
    _global_lock = threading.Lock()  # v36.5: 类级别锁

    def __init__(self):
        self.temp_files = []
        self.temp_dirs = []
        self._instance_lock = threading.Lock()  # v36.5: 实例级别锁
        # 注册到类级别列表
        with TempFileManager._global_lock:
            TempFileManager._instances.append(self)
        # 注册 atexit 清理（只注册一次）
        self._register_atexit()

    @classmethod
    def _register_atexit(cls):
        """注册 atexit 清理函数（只注册一次）"""
        if not hasattr(cls, '_atexit_registered'):
            atexit.register(cls._cleanup_all)
            cls._atexit_registered = True

    @classmethod
    def _cleanup_all(cls):
        """清理所有实例的临时文件（atexit 回调）"""
        with cls._global_lock:
            instances = cls._instances[:]
        for instance in instances:
            try:
                instance.cleanup()
            except Exception:
                pass  # 清理失败不抛出异常

    def create_temp_file(self, suffix='', content=None):
        """创建临时文件并追踪（v36.5: 线程安全）"""
        temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_name = temp.name
        temp.close()  # 立即关闭文件句柄

        # v36.5: 线程安全地添加到列表
        with self._instance_lock:
            self.temp_files.append(temp_name)

        if content:
            with open(temp_name, 'wb') as f:
                f.write(content)

        return temp_name

    def create_temp_dir(self):
        """创建临时目录并追踪（v36.5: 线程安全）"""
        temp_dir = tempfile.mkdtemp()

        # v36.5: 线程安全地添加到列表
        with self._instance_lock:
            self.temp_dirs.append(temp_dir)

        return temp_dir

    def cleanup(self):
        """清理所有临时文件和目录（v36.5: 线程安全）

        Returns:
            list: 清理过程中的错误列表
        """
        errors = []

        # v36.5: 线程安全地复制列表
        with self._instance_lock:
            files_to_clean = self.temp_files[:]
            dirs_to_clean = self.temp_dirs[:]

        # 清理文件
        for f in files_to_clean:
            try:
                if os.path.exists(f):
                    os.remove(f)
                    with self._instance_lock:
                        if f in self.temp_files:
                            self.temp_files.remove(f)
            except (OSError, IOError) as e:
                errors.append(f"清理文件失败 {f}: {e}")

        # 清理目录
        for d in dirs_to_clean:
            try:
                if os.path.exists(d):
                    import shutil
                    shutil.rmtree(d)
                    with self._instance_lock:
                        if d in self.temp_dirs:
                            self.temp_dirs.remove(d)
            except (OSError, IOError) as e:
                errors.append(f"清理目录失败 {d}: {e}")

        return errors

    def __del__(self):
        """析构时自动清理（作为后备）"""
        try:
            self.cleanup()
        except Exception:
            pass
