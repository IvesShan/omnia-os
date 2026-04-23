# 技能数量诊断报告

## 📊 数据对比

| 来源 | 数量 | 说明 |
|------|------|------|
| **前端面板显示** | ? | 需要检查后端返回值 |
| **后端 API 返回** | 3 | 统计 `.omnia/*.md` 文件 |
| **active_skills.json** | 7 | 激活的技能 |
| **imported/ 目录** | 18 | 所有导入的技能 |

## 🔍 问题分析

### 后端代码问题

```python
# backend/omnia_backend.py 第 500-519 行
@app.route('/api/skills/list', methods=['GET'])
def list_skills():
    skills_dir = Path(__file__).parent.parent / 'skills' / '.omnia'
    
    if not skills_dir.exists():
        return jsonify({'skills': [], 'count': 0})
    
    skills = []
    for skill_file in skills_dir.glob('*.md'):  # ❌ 错误：统计 MD 文件
        skills.append({...})
    
    return jsonify({
        'skills': skills,
        'count': len(skills)  # 返回 3
    })
```

### 根本原因

1. **后端统计的是 `.md` 文件**，而不是实际技能
2. **应该从 `active_skills.json` 读取激活技能**
3. **或者统计 `imported/` 目录下的技能文件夹**

## ✅ 修复方案

### 方案 1：统计激活技能（推荐）

从 `active_skills.json` 读取激活的技能数量：

```python
@app.route('/api/skills/list', methods=['GET'])
def list_skills():
    skills_file = Path(__file__).parent.parent / 'skills' / '.omnia' / 'active_skills.json'
    
    if skills_file.exists():
        with open(skills_file, 'r') as f:
            data = json.load(f)
            active_skills = data.get('active_skills', [])
            return jsonify({
                'skills': active_skills,
                'count': len(active_skills),
                'total': len(active_skills) + len(data.get('inactive_skills', []))
            })
    
    return jsonify({'skills': [], 'count': 0, 'total': 0})
```

### 方案 2：统计所有导入技能

统计 `imported/` 目录下的技能文件夹：

```python
@app.route('/api/skills/count', methods=['GET'])
def get_skills_count():
    imported_dir = Path(__file__).parent.parent / 'skills' / 'imported'
    
    if imported_dir.exists():
        count = len([d for d in imported_dir.iterdir() if d.is_dir()])
        return jsonify({'count': count})
    
    return jsonify({'count': 0})
```

## 📋 推荐修复

使用 **方案 1**，因为：
1. 更符合 Omnia 的技能管理逻辑
2. 区分"激活技能"和"总技能"
3. 数据来源可靠（active_skills.json）

## 🎯 预期结果

修复后，前端面板应该显示：

- **激活技能**: 7
- **总技能**: 18
- **未激活**: 11
