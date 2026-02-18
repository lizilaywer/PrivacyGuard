"""
PrivacyGuard 自定义异常类

v36.5: 模块化拆分，从 main.py 提取
"""


class PrivacyAppError(Exception):
    """应用基础异常"""

    def __init__(self, message, suggestion=None):
        super().__init__(message)
        self.suggestion = suggestion

    def user_message(self):
        """获取用户友好的错误消息"""
        msg = str(self)
        if self.suggestion:
            msg += f"\n\n建议：{self.suggestion}"
        return msg


class ConversionError(PrivacyAppError):
    """文件转换错误"""
    pass


class FileFormatError(PrivacyAppError):
    """文件格式错误"""
    pass


class SecurityError(PrivacyAppError):
    """安全错误"""
    pass


class MemoryLimitError(PrivacyAppError):
    """内存限制"""
    pass


class WorkerCancelledError(PrivacyAppError):
    """用户取消操作"""
    pass
