---
name: full-stack-dev-2026
description: 2026年全栈开发完整技能包 - 前端+后端+数据库+移动端+DevOps
---

# 全栈开发技能包 2026

## 一、前端开发

### 1.1 技术栈
- **框架**: Next.js 16 + React 19
- **语言**: TypeScript 5.4 (严格模式)
- **样式**: Tailwind CSS 4.2
- **组件**: shadcn/ui + Radix UI
- **状态**: Zustand / Jotai / React Query

### 1.2 核心概念
- **Server Components**: 服务端组件减少客户端JS
- **Streaming**: 流式渲染提升首屏速度
- **Parallel Routes**: 并行路由实现复杂布局
- **Intercepting Routes**: 拦截路由实现模态框

### 1.3 设计系统
- **色彩**: CSS变量管理主题色
- **间距**: 4px基准的8点网格系统
- **字体**: 系统字体栈，保证性能
- **动画**: Framer Motion / CSS transitions

## 二、后端开发

### 2.1 API设计
- **RESTful**: 资源导向的URL设计
- **GraphQL**: 按需获取数据
- **tRPC**: 端到端类型安全
- **WebSocket**: 实时双向通信

### 2.2 设计原则
```
GET    /api/resources      # 列表
GET    /api/resources/:id  # 详情
POST   /api/resources      # 创建
PUT    /api/resources/:id  # 全量更新
PATCH  /api/resources/:id  # 部分更新
DELETE /api/resources/:id  # 删除
```

### 2.3 认证授权
- **JWT**: 无状态认证
- **OAuth 2.0**: 第三方登录
- **RBAC**: 基于角色的权限控制
- **API Key**: 服务间调用

## 三、数据库

### 3.1 数据库选型
| 场景 | 推荐 |
|------|------|
| 关系型数据 | PostgreSQL |
| 缓存 | Redis |
| 文档存储 | MongoDB |
| 搜索 | Elasticsearch |
| 时序数据 | InfluxDB |

### 3.2 ORM - Prisma
```typescript
// schema.prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  posts     Post[]
}

model Post {
  id       String @id @default(cuid())
  title    String
  content  String?
  author   User   @relation(fields: [authorId], references: [id])
  authorId String
}
```

### 3.3 数据库设计原则
- **范式**: 第三范式减少冗余
- **索引**: 查询字段加索引
- **分表**: 大数据量时分库分表
- **迁移**: 版本化管理Schema变更

## 四、移动端开发

### 4.1 技术选型
- **跨平台**: React Native / Flutter
- **原生**: Swift (iOS) / Kotlin (Android)
- **小程序**: 微信/支付宝/抖音
- **PWA**: 渐进式Web应用

### 4.2 React Native 2026
- **新架构**: Fabric + TurboModules
- **性能**: 接近原生体验
- **热更新**: OTA更新无需审核
- **生态**: Expo SDK 50+

### 4.3 移动端设计
- **安全区域**: 适配刘海屏/灵动岛
- **手势**: 滑动返回、下拉刷新
- **离线**: 本地存储+同步策略
- **推送**: 本地通知+远程推送

## 五、DevOps & 部署

### 5.1 容器化
```dockerfile
# Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### 5.2 CI/CD
- **GitHub Actions**: 自动化测试部署
- **Vercel**: 前端自动部署
- **Docker Hub**: 镜像仓库
- **Kubernetes**: 容器编排

### 5.3 监控告警
- **日志**: Winston / Pino
- **指标**: Prometheus + Grafana
- **追踪**: OpenTelemetry
- **告警**: PagerDuty / OpsGenie

## 六、AI集成

### 6.1 LLM应用
- **OpenAI**: GPT-4 / GPT-4o
- **Anthropic**: Claude 3
- **本地**: Ollama + Llama 2
- **国内**: 文心一言 / 通义千问

### 6.2 AI功能实现
- **聊天**: 流式响应SSE
- **生成**: 文本/图片/代码
- **嵌入**: 向量搜索
- **Agent**: 工具调用+推理

### 6.3 AI开发框架
- **LangChain**: 链式调用
- **LlamaIndex**: 数据索引
- **Vercel AI SDK**: 流式UI
- **Transformers.js**: 浏览器端推理

## 七、安全

### 7.1 前端安全
- **XSS**: 输入过滤+输出编码
- **CSRF**: Token验证
- **CSP**: 内容安全策略
- **HTTPS**: 强制TLS

### 7.2 后端安全
- **SQL注入**: 参数化查询
- **认证**: 密码哈希+bcrypt
- **限流**: Rate limiting
- **审计**: 操作日志

## 八、性能优化

### 8.1 前端优化
- **懒加载**: 图片/组件/路由
- **预加载**: 关键资源
- **缓存**: Service Worker
- **压缩**: Gzip / Brotli

### 8.2 后端优化
- **缓存**: Redis缓存热点数据
- **数据库**: 查询优化+索引
- **CDN**: 静态资源加速
- **连接池**: 数据库连接复用

## 九、测试

### 9.1 测试类型
- **单元测试**: Jest / Vitest
- **集成测试**: Playwright
- **E2E测试**: Cypress
- **性能测试**: Lighthouse

### 9.2 测试原则
- **覆盖率**: 核心代码>80%
- **自动化**: CI中自动运行
- **Mock**: 隔离外部依赖
- **快照**: UI回归测试

## 十、项目管理

### 10.1 敏捷开发
- **Scrum**: 2周一个Sprint
- **Kanban**: 看板管理任务
- **Daily**: 每日站会
- **Retro**: 迭代回顾

### 10.2 代码规范
- **ESLint**: 代码质量
- **Prettier**: 代码格式
- **Husky**: Git钩子
- **Commitizen**: 规范提交

### 10.3 文档
- **README**: 项目说明
- **API文档**: Swagger/OpenAPI
- **架构图**: 系统架构
- **Changelog**: 版本变更

---

## 应用案例：无人机维修系统

### 已应用技术
- ✅ Next.js + React 架构
- ✅ Tailwind CSS 样式
- ✅ shadcn/ui 组件设计
- ✅ RESTful API 设计
- ✅ SQLite + Prisma ORM
- ✅ AI 诊断集成
- ✅ 响应式移动端适配
- ✅ 类型安全 TypeScript

### 待优化项
- [ ] Redis 缓存热点数据
- [ ] 单元测试覆盖
- [ ] CI/CD 自动化部署
- [ ] 监控告警系统
- [ ] 性能优化（懒加载）

---

**更新日期**: 2026-04-02
**版本**: 2.0.0
**适用场景**: Web应用、移动应用、全栈开发
