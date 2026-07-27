# fix_mac_paths.sh - 修复路径和环境变量
set -e

cd ~/omnia-os

# 修复 Python 文件中的路径 (macOS 兼容方式)
find . -name "*.py" -type f | while read -r file; do
  sed -i '' 's|/home/shan/omnia-os|/Users/xushiyao/omnia-os|g' "$file"
  sed -i '' 's|/home/shan|/Users/xushiyao|g' "$file"
done

# 修复 .env 文件中的路径
for f in .env .env.local .env.mac; do
  if [ -f "$f" ]; then
    sed -i '' 's|/home/shan/omnia-os|/Users/xushiyao/omnia-os|g' "$f"
    sed -i '' 's|/home/shan|/Users/xushiyao|g' "$f"
  fi
done

# 修复配置文件中的路径
for f in config.json setup.json; do
  if [ -f "$f" ]; then
    sed -i '' 's|/home/shan/omnia-os|/Users/xushiyao/omnia-os|g' "$f"
    sed -i '' 's|/home/shan|/Users/xushiyao|g' "$f"
  fi
done

# 修复 requirements.txt 中的系统级依赖 (Linux-only packages)
if [ -f requirements.txt ]; then
  sed -i '' '/^systemd-python/d' requirements.txt
  sed -i '' '/^dbus-python/d' requirements.txt
fi

echo "✅ 路径修复完成！"
