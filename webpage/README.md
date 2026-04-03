<div align="center">
  <img src="src/assets/images/mascot/durvis_spin.gif" width="250" alt="Mascot" />
</div>

<h1 align="center">Odysseia Forum Webpage</h1>

<p align="center">
  现代化、高性能的社区论坛前端平台系统
</p>

<p align="center">
  <a href="https://reactjs.org/"><img src="https://img.shields.io/badge/React-18-blue.svg?style=flat&logo=react" alt="React" /></a>
  <a href="https://vitejs.dev/"><img src="https://img.shields.io/badge/Vite-5-646CFF.svg?style=flat&logo=vite&logoColor=white" alt="Vite" /></a>
  <a href="https://www.typescriptlang.org/"><img src="https://img.shields.io/badge/TypeScript-5-3178C6.svg?style=flat&logo=typescript&logoColor=white" alt="TypeScript" /></a>
  <a href="https://tailwindcss.com/"><img src="https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC.svg?style=flat&logo=tailwind-css&logoColor=white" alt="Tailwind CSS" /></a>
  <a href="https://zustand-demo.pmnd.rs/"><img src="https://img.shields.io/badge/Zustand-4.5-56291C.svg?style=flat" alt="Zustand" /></a>
  <a href="https://tanstack.com/query/latest"><img src="https://img.shields.io/badge/React_Query-5-FF4154.svg?style=flat&logo=react-query&logoColor=white" alt="React Query" /></a>
</p>

---

## 概述

Odysseia Forum Webpage 是一个基于 **Feature-Sliced Design (FSD)** 架构方法论开发的前端单页应用 (SPA)。致力于为大规模文本社区提供极速、丝滑且跨平台响应式的阅读和探索体验。

<div align="center">
  <img src="src/assets/images/background/winter.png" width="900" alt="App Background" />
</div>

## 核心特性

- **极致性能**: 结合 Vite 冷链接构建，采用 React 18 并发渲染与组件级的路由状态切片懒加载。长列表通过 `@tanstack/react-virtual` 进行无限滚动虚拟化。
- **动态检索引擎**: 内置无缝交互的高级语法搜索面板，将状态精准降级为 `URLSearchParams`，实现随改随查。
- **现代化主题引擎**: 由 Tailwind CSS 驱动，支持无级调节和极速响应的深浅色 (Dark / Light) 切换方案。
- **看板娘赋能**: 独有的看板娘交互逻辑，贯穿项目搜索与等待，降低纯文本论坛引发的视觉疲劳。

## 架构与开发体系

我们拥有完善、结构清晰且极简的前端开发规范。如需进一步了解本项目的技术细节、组件组织模式或是测试流程，请查阅我们的开发文档中心：

- [基础项目概览 (Overview)](docs/architecture/overview.md)
- [FSD 目录结构索引 (Directory Structure)](docs/architecture/structure.md)
- [核心页面功能矩阵 (Pages Overview)](docs/architecture/pages_overview.md)
- [状态流转与 UI 组件规范 (Development Guide)](docs/development/)
- [安全防线要求 (Security)](docs/development/security.md)
- [自动化拦截与测试 (Testing & CI)](docs/testing/vitest_ci_process.md)

## 本地快速体验

```bash
npm install
cp .env.example .env
npm run dev
```
打开你的浏览器访问 `http://localhost:3000` 即可加载带有默认 Mock 及看板娘辅助功能的数据面板。

<div align="center">
  <br />
  <img src="src/assets/images/mascot/letsgo.png" width="120" alt="Let's Go" />
  <p><i>Enjoy coding.</i></p>
</div>
