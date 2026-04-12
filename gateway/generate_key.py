"""
密钥生成工具

用于生成安全的 HMAC_SECRET_KEY
"""

import secrets
import argparse


def generate_secret_key(length: int = 32) -> str:
    """
    生成安全的随机密钥
    
    Args:
        length: 密钥长度（字节），默认32字节（256位）
    
    Returns:
        URL安全的Base64编码字符串
    """
    return secrets.token_urlsafe(length)


def update_env_file(env_path: str, key: str) -> bool:
    """
    更新 .env 文件中的 HMAC_SECRET_KEY
    
    Args:
        env_path: .env 文件路径
        key: 新生成的密钥
    
    Returns:
        是否成功更新
    """
    import os
    from pathlib import Path
    
    env_file = Path(env_path)
    
    # 如果文件不存在，创建新文件
    if not env_file.exists():
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(f"HMAC_SECRET_KEY={key}\n")
        print(f"[OK] 已创建 {env_path} 并写入密钥")
        return True
    
    # 读取现有内容
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找并更新 HMAC_SECRET_KEY
    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith('HMAC_SECRET_KEY='):
            new_lines.append(f"HMAC_SECRET_KEY={key}\n")
            updated = True
        else:
            new_lines.append(line)
    
    # 如果没有找到，添加新的配置
    if not updated:
        new_lines.append(f"\n# HMAC 密钥（自动生成）\nHMAC_SECRET_KEY={key}\n")
    
    # 写回文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    if updated:
        print(f"[OK] 已更新 {env_path} 中的 HMAC_SECRET_KEY")
    else:
        print(f"[OK] 已在 {env_path} 中添加 HMAC_SECRET_KEY")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="生成安全的密钥")
    parser.add_argument(
        "-l", "--length",
        type=int,
        default=32,
        help="密钥长度（字节），默认32"
    )
    parser.add_argument(
        "-c", "--copy",
        action="store_true",
        help="复制到剪贴板（需要 pyperclip 库）"
    )
    parser.add_argument(
        "-u", "--update-env",
        action="store_true",
        help="自动更新 .env 文件"
    )
    parser.add_argument(
        "-e", "--env-file",
        type=str,
        default=".env",
        help=".env 文件路径，默认 .env"
    )
    
    args = parser.parse_args()
    
    key = generate_secret_key(args.length)
    
    print("=" * 60)
    print("生成的密钥：")
    print(key)
    print("=" * 60)
    
    # 自动更新 .env 文件
    if args.update_env:
        try:
            update_env_file(args.env_file, key)
        except Exception as e:
            print(f"[ERROR] 更新 .env 文件失败: {e}")
            print(f"\n请手动将密钥添加到 {args.env_file}：")
            print(f"HMAC_SECRET_KEY={key}")
    else:
        print(f"\n使用方法：")
        print(f"1. 将密钥添加到 .env 文件：")
        print(f"   HMAC_SECRET_KEY={key}")
        print(f"\n2. 或设置为环境变量：")
        print(f"   export HMAC_SECRET_KEY='{key}'")
        print(f"\n提示：使用 -u 参数可自动更新 .env 文件")
        print(f"示例：python generate_key.py -u")
    
    if args.copy:
        try:
            import pyperclip
            pyperclip.copy(key)
            print("\n[OK] 密钥已复制到剪贴板！")
        except ImportError:
            print("\n[WARNING] 未安装 pyperclip 库，无法复制到剪贴板")
            print("   安装命令: pip install pyperclip")


if __name__ == "__main__":
    main()