# === 主题系统模块 ===
# Windows-first 办公软件风格主题定义
# 支持浅色/深色主题切换


class Theme:
    """主题颜色和样式定义"""

    # 浅色主题（Windows / 中文办公场景优先）
    LIGHT = {
        "background": "#F7F8FA",
        "surface": "#FFFFFF",
        "primary": "#0F6CBD",
        "secondary": "#5F6B7A",
        "accent": "#0FA968",
        "text": "#18212F",
        "text_secondary": "#5F6B7A",
        "border": "#E2E8F0",
        "shadow": "rgba(18, 31, 53, 0.10)",
        "info_bar": "#F9FBFD",
        "scroll_area": "#F6F8FB",
        "hover": "#EEF4FB",
        "pressed": "#E3ECF8",
        "success": "#0FA968",
        "danger": "#D64545",
        "warning": "#D9831F",
    }

    # 深色主题
    DARK = {
        "background": "#151C26",
        "surface": "#1E2836",
        "primary": "#56A8FF",
        "secondary": "#9AA8BA",
        "accent": "#34D399",
        "text": "#F6F8FC",
        "text_secondary": "#AAB5C5",
        "border": "#324255",
        "shadow": "rgba(0,0,0,0.30)",
        "info_bar": "#1E2A3B",
        "scroll_area": "#1A2330",
        "hover": "#263241",
        "pressed": "#314155",
        "success": "#34D399",
        "danger": "#FF6B6B",
        "warning": "#FFB454",
    }

    # 布局常量
    BORDER_RADIUS = 12
    BUTTON_RADIUS = 10
    SPACING_SMALL = 8
    SPACING_MEDIUM = 14
    SPACING_LARGE = 22

    # 字体
    FONT_FAMILY = "'Segoe UI Variable', 'Segoe UI', 'Microsoft YaHei UI', 'Microsoft YaHei', Arial, sans-serif"
    FONT_SIZE_SMALL = 12
    FONT_SIZE_NORMAL = 14
    FONT_SIZE_LARGE = 18

    # 动画
    ANIMATION_DURATION = 200  # ms

    @staticmethod
    def get_theme(theme_name="light"):
        """获取主题配置"""
        return Theme.LIGHT if theme_name == "light" else Theme.DARK

    @staticmethod
    def adjust_color(hex_color, amount):
        """调整颜色亮度

        Args:
            hex_color: 十六进制颜色值（如 #007AFF）
            amount: 调整量（正数变亮，负数变暗）

        Returns:
            调整后的十六进制颜色值
        """
        if hex_color.startswith('#'):
            hex_color = hex_color[1:]
        try:
            r = max(0, min(255, int(hex_color[0:2], 16) + amount))
            g = max(0, min(255, int(hex_color[2:4], 16) + amount))
            b = max(0, min(255, int(hex_color[4:6], 16) + amount))
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, TypeError):
            return hex_color
