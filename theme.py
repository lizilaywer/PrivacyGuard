# === 主题系统模块 ===
# macOS BigSur 风格主题定义
# 支持浅色/深色主题切换


class Theme:
    """主题颜色和样式定义"""

    # 浅色主题
    LIGHT = {
        "background": "#F5F5F7",
        "surface": "#FFFFFF",
        "primary": "#007AFF",
        "secondary": "#8E8E93",
        "accent": "#34C759",
        "text": "#1D1D1F",
        "text_secondary": "#86868B",
        "border": "#D1D1D6",
        "shadow": "rgba(0,0,0,0.08)",
        "info_bar": "#FFF3CD",
        "scroll_area": "#E5E5EA",
        "hover": "#E5E5EA",
        "pressed": "#D1D1D6",
        "success": "#34C759",
        "danger": "#FF3B30",
        "warning": "#FF9500",
    }

    # 深色主题
    DARK = {
        "background": "#1C1C1E",
        "surface": "#2C2C2E",
        "primary": "#0A84FF",
        "secondary": "#8E8E93",
        "accent": "#30D158",
        "text": "#FFFFFF",
        "text_secondary": "#98989D",
        "border": "#38383A",
        "shadow": "rgba(0,0,0,0.3)",
        "info_bar": "#323232",
        "scroll_area": "#2C2C2E",
        "hover": "#3A3A3C",
        "pressed": "#48484A",
        "success": "#30D158",
        "danger": "#FF453A",
        "warning": "#FF9F0A",
    }

    # 布局常量
    BORDER_RADIUS = 10
    BUTTON_RADIUS = 8
    SPACING_SMALL = 6
    SPACING_MEDIUM = 12
    SPACING_LARGE = 20

    # 字体
    FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    FONT_SIZE_SMALL = 11
    FONT_SIZE_NORMAL = 13
    FONT_SIZE_LARGE = 16

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
        except:
            return hex_color
