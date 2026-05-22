# GitHub SSH Key 配置指南

## 你的 SSH 公钥

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJbdWlx451lfv8qIV1C9LR3vdSD7CVGsTvNURvUIPFxe omnia-deploy
```

## 配置步骤

### 1. 添加 SSH Key 到 GitHub

1. 登录 GitHub: https://github.com/login
2. 点击右上角头像 → **Settings**
3. 左侧菜单 → **SSH and GPG keys**
4. 点击 **New SSH key**
5. Title 填: `Omnia Deploy`
6. Key 填: 上面的公钥（整行复制）
7. 点击 **Add SSH key**

### 2. 创建仓库

1. 访问: https://github.com/new
2. Repository name: `omnia-os`
3. 选择 **Private**（私有仓库）
4. **不要**勾选任何初始化选项
5. 点击 **Create repository**

### 3. 告诉我完成

配置完成后告诉我，我会帮你：
- 推送代码到 GitHub
- 创建版本标签
- 触发自动打包

---

## ⚠️ 安全提醒

刚才你分享了 GitHub 密码，**请立即修改密码**：
https://github.com/settings/security
