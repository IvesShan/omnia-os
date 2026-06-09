---
name: video-generation
description: AI 视频生成技能 - 支持多种 AI 视频生成模型的调用和管理
tags: [video, ai, generation, multimedia]
created: 2026-06-09
version: 1.0.0
---

## Description

整合主流 AI 视频生成 API，提供统一的视频生成接口。支持文本生成视频、图片生成视频等多种模式。

## Capabilities

- text-to-video: 文本描述生成视频
- image-to-video: 静态图片生成动态视频
- video-extend: 视频续写/延长
- 多模型支持: Kling, Runway, Pika, Sora 等

## Triggers

当用户提到以下关键词时自动激活：
- 生成视频 / AI 视频 / text to video
- 图片转视频 / image to video
- 视频生成 / video generation

## Usage

```
"帮我生成一个日落海边的视频" → 激活此技能
"把这张图片变成视频" → 激活此技能
```
