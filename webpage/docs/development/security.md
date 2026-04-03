# 🛡️ 前端安全要求 (Security)

作为论坛类型的前后端分离业务体系，Odysseia 采用最高规格的方式防御常见的网络前端攻击。

## 1. 跨站脚本攻击 (XSS) 防护

我们允许并大量呈现富文本内容及 Markdown 文本，这通常是高频导致 DOM 型或存储型 XSS 的载体。

### 1.1 React 内置保护
任何由大括号构成的正常变量渲染，都会被 React 进行原生 `htmlspecialchars` 转义。
> `<div>{user_input_content}</div>` 是绝对安全的。

### 1.2 dangerouslySetInnerHTML 使用红线
**绝对禁止**直接将后端文本传入 `dangerouslySetInnerHTML`（除非经过可靠的后端 DOMpurify 过滤且由非常确定的内部管理模块提供）。业务端原则上禁止使用此属性。

### 1.3 Markdown 安全渲染
我们的 `MarkdownText` 组件集成的是生态成熟的 `react-markdown` 库，它通过解析出 AST 而不是直接注入 HTML 字符串来预防脚本执行。
如果是外部图片链接嵌入，注意防范 `src=javascript:alert(1)` 的极端情况检测，或限定前缀为合法的 `http://` / `https://`。

## 2. 身份认证与跨站请求伪造 (CSRF)

- 与后端通信所采用的 `Authorization: Bearer <token>` 这种显式携带请求头的机制，在绝大部分情况下天然免疫老式的 CSRF 攻击机制（因为它是无 Cookie 状态管理，浏览器发起跨站请求时无法伪造头部的 `Authorization` 字段）。
- 然而，我们如果使用 `localStorage` 保存 Token，可能会遭受被 XSS 窃取 Token 的风险。所以必须要**做死第一步的防线，即防范 XSS 注入**。

## 3. 第三方依赖审查 (Dependency Auditing)

请确保 `package.json` 中的构建脚本不会带来构建时的后门漏洞。定期执行 `npm audit` 审查关键依赖的子包安全警报，尤其是像 React 解析器、Markdown 解析器这种直接操作 DOM 的直接包。
