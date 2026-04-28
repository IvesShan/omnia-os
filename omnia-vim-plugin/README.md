# Omnia IDE Bridge - Vim Plugin

将 Vim 的编辑上下文同步到 Omnia AIOS。

## 安装

### 方法一：手动安装
```bash
mkdir -p ~/.vim/pack/omnia/start
ln -s /home/shan/omnia-os/omnia-vim-plugin ~/.vim/pack/omnia/start/omnia
```

### 方法二：使用 Vim 8+ 内置包管理
```bash
# 直接复制
cp -r /home/shan/omnia-os/omnia-vim-plugin ~/.vim/pack/omnia/start/omnia
```

### 方法三：使用 vim-plug
在 `~/.vimrc` 中添加：
```vim
Plug 'file:///home/shan/omnia-os/omnia-vim-plugin', {'as': 'omnia'}
```

## 使用

安装后重启 Vim，插件会自动工作。

### 手动命令
```vim
:OmniaSync    " 手动发送上下文
```

### 配置选项
在 `~/.vimrc` 中添加：
```vim
" Omnia 配置
let g:omnia_host = '127.0.0.1'
let g:omnia_port = 5001
let g:omnia_auto_sync = 1        " 自动同步
let g:omnia_sync_interval = 1000 " 同步间隔（毫秒）
```

## 功能

- ✅ 自动同步当前文件路径
- ✅ 自动同步光标位置（行号、列号）
- ✅ 自动检测文件类型
- ✅ 支持选中文本同步
- ✅ 本地缓存文件：`~/.omnia/ide_context.json`

## 验证

```bash
# 检查缓存文件
cat ~/.omnia/ide_context.json

# 测试端点
curl http://127.0.0.1:5001/ide-context
```

## 故障排除

如果插件不工作：
1. 确认 Omnia 服务正在运行
2. 确认端口 5001 可访问
3. 检查 Vim 版本（需要 8.0+）

```bash
vim --version | head -n 1
```
