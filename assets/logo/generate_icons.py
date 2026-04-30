#!/usr/bin/env python3
"""
PrivacyGuard Logo 图标生成脚本
自动生成各平台所需的图标尺寸

使用方法:
    python3 generate_icons.py

依赖:
    pip install cairosvg pillow
"""

import os
import sys
import subprocess
from pathlib import Path

# 需要的尺寸列表
SIZES = [16, 24, 32, 48, 64, 128, 256, 512, 1024]

# Windows ICO 需要的尺寸
WINDOWS_ICO_SIZES = [16, 32, 48, 256]

# macOS ICNS 需要的尺寸
MACOS_ICNS_SIZES = [16, 32, 128, 256, 512, 1024]

def check_dependencies():
    """检查必要的依赖是否已安装"""
    try:
        import cairosvg
        from PIL import Image
        print("✓ 依赖检查通过")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install cairosvg pillow")
        return False

def generate_png_from_svg(svg_path, output_path, size):
    """从 SVG 生成 PNG"""
    try:
        import cairosvg
        from PIL import Image
        
        # 使用 cairosvg 转换
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(output_path),
            output_width=size,
            output_height=size
        )
        
        # 使用 Pillow 优化
        img = Image.open(output_path)
        
        # 确保是 RGBA 模式（支持透明）
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 保存优化后的图片
        img.save(output_path, 'PNG', optimize=True)
        
        return True
    except Exception as e:
        print(f"  ✗ 生成失败 {size}x{size}: {e}")
        return False

def generate_all_pngs():
    """生成所有尺寸的 PNG"""
    print("\n=== 生成 PNG 图标 ===")
    
    base_dir = Path(__file__).parent
    source_dir = base_dir / "source"
    export_dir = base_dir / "export"
    
    # 生成标准版和深色版
    variants = [
        ("logo_master.svg", "logo_default"),
        ("logo_dark.svg", "logo_dark")
    ]
    
    for svg_file, name_prefix in variants:
        svg_path = source_dir / svg_file
        if not svg_path.exists():
            print(f"✗ 源文件不存在: {svg_path}")
            continue
        
        print(f"\n生成 {name_prefix} 变体...")
        
        for size in SIZES:
            size_dir = export_dir / str(size)
            size_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = size_dir / f"{name_prefix}_{size}.png"
            
            if generate_png_from_svg(svg_path, output_path, size):
                print(f"  ✓ {size}x{size}")

def generate_windows_ico():
    """生成 Windows ICO 文件（手动构建多尺寸 ICO）"""
    print("\n=== 生成 Windows ICO ===")
    
    try:
        from PIL import Image
        import struct
        import io
        
        base_dir = Path(__file__).parent
        windows_dir = base_dir / "windows"
        windows_dir.mkdir(parents=True, exist_ok=True)
        
        # 收集所有图像数据
        images_data = []
        for size in WINDOWS_ICO_SIZES:
            png_path = base_dir / "export" / str(size) / f"logo_default_{size}.png"
            if png_path.exists():
                img = Image.open(png_path)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 将图像保存为 PNG 格式到内存
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_data = img_bytes.getvalue()
                
                images_data.append({
                    'width': size,
                    'height': size,
                    'data': img_data,
                    'size': len(img_data)
                })
                print(f"  ✓ 添加 {size}x{size}")
        
        if len(images_data) >= 1:
            ico_path = windows_dir / "app_icon.ico"
            
            # 计算目录项的偏移量
            header_size = 6 + len(images_data) * 16
            
            with open(ico_path, 'wb') as f:
                # 写入 ICONDIR
                f.write(struct.pack('<HHH', 0, 1, len(images_data)))
                
                # 计算每个图像数据的起始偏移
                current_offset = header_size
                
                # 写入 ICONDIRENTRY 数组
                for img_info in images_data:
                    width = img_info['width'] if img_info['width'] < 256 else 0
                    height = img_info['height'] if img_info['height'] < 256 else 0
                    f.write(struct.pack('<BBBBHHII', 
                        width, height,  # 宽度和高度 (0 表示 256)
                        0,              # 颜色数 (0 = 256+)
                        0,              # 保留
                        1,              # 颜色平面
                        32,             # 每像素位数
                        img_info['size'],
                        current_offset
                    ))
                    current_offset += img_info['size']
                
                # 写入图像数据
                for img_info in images_data:
                    f.write(img_info['data'])
            
            print(f"✓ ICO 文件已生成: {ico_path} ({ico_path.stat().st_size / 1024:.1f} KB)")
        else:
            print("✗ 没有可用的图片生成 ICO")
            
    except Exception as e:
        print(f"✗ 生成 ICO 失败: {e}")

def generate_macos_icns():
    """生成 macOS ICNS 文件"""
    print("\n=== 生成 macOS ICNS ===")
    
    base_dir = Path(__file__).parent
    macos_dir = base_dir / "macos"
    macos_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建临时 iconset 目录
    iconset_dir = macos_dir / "AppIcon.iconset"
    iconset_dir.mkdir(parents=True, exist_ok=True)
    
    # macOS 图标命名规范
    iconset_files = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]
    
    try:
        for size, filename in iconset_files:
            png_path = base_dir / "export" / str(size) / f"logo_default_{size}.png"
            target_path = iconset_dir / filename
            
            if png_path.exists():
                from PIL import Image
                img = Image.open(png_path)
                img.save(target_path, 'PNG')
                print(f"  ✓ {filename}")
        
        # 使用 iconutil 生成 icns（仅在 macOS 上有效）
        icns_path = macos_dir / "AppIcon.icns"
        
        if sys.platform == 'darwin':
            result = subprocess.run(
                ['iconutil', '-c', 'icns', str(iconset_dir), '-o', str(icns_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✓ ICNS 文件已生成: {icns_path}")
            else:
                print(f"✗ iconutil 失败: {result.stderr}")
        else:
            # 非 macOS 系统，使用 Pillow 生成一个多尺寸 PNG 作为替代
            print("  ℹ 非 macOS 系统，生成多尺寸 PNG 替代方案")
            generate_macos_png_alternative(macos_dir, base_dir)
        
        # 清理临时 iconset 目录
        import shutil
        shutil.rmtree(iconset_dir, ignore_errors=True)
        
    except Exception as e:
        print(f"✗ 生成 ICNS 失败: {e}")

def generate_macos_png_alternative(macos_dir, base_dir):
    """为非 macOS 系统生成 macOS 图标替代方案"""
    try:
        from PIL import Image
        
        # 复制 1024x1024 作为主图标
        src = base_dir / "export" / "1024" / "logo_default_1024.png"
        dst = macos_dir / "AppIcon_1024.png"
        if src.exists():
            Image.open(src).save(dst, 'PNG')
            print(f"  ✓ 替代方案: {dst}")
        
        # 生成 512x512
        src = base_dir / "export" / "512" / "logo_default_512.png"
        dst = macos_dir / "AppIcon_512.png"
        if src.exists():
            Image.open(src).save(dst, 'PNG')
            print(f"  ✓ 替代方案: {dst}")
            
    except Exception as e:
        print(f"  ✗ 替代方案生成失败: {e}")

def generate_linux_icons():
    """生成 Linux 图标"""
    print("\n=== 生成 Linux 图标 ===")
    
    base_dir = Path(__file__).parent
    linux_dir = base_dir / "linux"
    linux_dir.mkdir(parents=True, exist_ok=True)
    
    linux_sizes = [16, 22, 24, 32, 48, 64, 128, 256, 512]
    
    try:
        from PIL import Image
        
        for size in linux_sizes:
            src = base_dir / "export" / str(size) / f"logo_default_{size}.png"
            dst = linux_dir / f"privacyguard_{size}x{size}.png"
            
            if src.exists():
                Image.open(src).save(dst, 'PNG')
                print(f"  ✓ {size}x{size}")
        
        # 同时创建一个默认名称的
        src = base_dir / "export" / "256" / "logo_default_256.png"
        dst = linux_dir / "privacyguard.png"
        if src.exists():
            Image.open(src).save(dst, 'PNG')
            print(f"  ✓ 默认图标: {dst}")
            
    except Exception as e:
        print(f"✗ 生成 Linux 图标失败: {e}")

def generate_marketing_assets():
    """生成营销物料"""
    print("\n=== 生成营销物料 ===")
    
    base_dir = Path(__file__).parent
    marketing_dir = base_dir / "marketing"
    marketing_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # 复制 1024 版本作为 App Store 图标
        src = base_dir / "export" / "1024" / "logo_default_1024.png"
        dst = marketing_dir / "app_store_icon.png"
        if src.exists():
            Image.open(src).save(dst, 'PNG')
            print(f"  ✓ App Store 图标")
        
        # 生成 OG 图片 (1200x630)
        print(f"  ℹ OG 图片需要手动设计，建议使用 1200x630 尺寸")
        
        # 生成简单横幅
        banner = Image.new('RGB', (1200, 400), color='#2563EB')
        draw = ImageDraw.Draw(banner)
        
        # 尝试添加文字
        try:
            # 使用默认字体
            draw.text((600, 200), "PrivacyGuard 脱敏卫士", 
                     fill='white', anchor='mm', font_size=60)
            draw.text((600, 280), "智能文档脱敏工具", 
                     fill='white', anchor='mm', font_size=32)
        except:
            pass  # 如果字体渲染失败，只保存纯色背景
        
        banner.save(marketing_dir / "banner_basic.png", 'PNG')
        print(f"  ✓ 基础横幅 (可进一步设计)")
        
    except Exception as e:
        print(f"✗ 生成营销物料失败: {e}")

def print_summary():
    """打印生成摘要"""
    print("\n" + "=" * 50)
    print("图标生成完成!")
    print("=" * 50)
    
    base_dir = Path(__file__).parent
    
    files_to_check = [
        ("Windows ICO", base_dir / "windows" / "app_icon.ico"),
        ("macOS ICNS", base_dir / "macos" / "AppIcon.icns"),
        ("Linux PNG", base_dir / "linux" / "privacyguard.png"),
        ("App Store 图标", base_dir / "marketing" / "app_store_icon.png"),
    ]
    
    for name, path in files_to_check:
        if path.exists():
            size = path.stat().st_size / 1024  # KB
            print(f"✓ {name}: {path} ({size:.1f} KB)")
        else:
            # 检查替代文件
            alt_path = base_dir / "macos" / "AppIcon_1024.png"
            if "macOS" in name and alt_path.exists():
                print(f"~ {name}: 使用替代方案 {alt_path}")
            else:
                print(f"✗ {name}: 未生成")
    
    print("\n各尺寸 PNG 图标位置:")
    print(f"  {base_dir}/export/{{size}}/logo_default_{{size}}.png")
    
    print("\n打包引用指南:")
    print("  Windows: assets/logo/windows/app_icon.ico")
    print("  macOS:   assets/logo/macos/AppIcon.icns")
    print("  Linux:   assets/logo/linux/privacyguard.png")

def main():
    """主函数"""
    print("PrivacyGuard Logo 图标生成器")
    print("=" * 50)
    
    if not check_dependencies():
        sys.exit(1)
    
    # 生成所有图标
    generate_all_pngs()
    generate_windows_ico()
    generate_macos_icns()
    generate_linux_icons()
    generate_marketing_assets()
    
    # 打印摘要
    print_summary()

if __name__ == "__main__":
    main()
