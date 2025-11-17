
(function(){
	"use strict";

	const url = new URL(window.location.href);
	const error = url.searchParams.get("error");
	if(error){
		alert("登录失败: " + error);
	}

	/** 数据与状态 **/
	const state = {
		filtered: [],
		total: 0,
		page: 1,
		perPage: 24,
		sort: "last_active_desc",
		query: "",
		selectedChannel: null, // 单选频道，null表示全频道搜索
		tagStates: new Map(), // 标签状态: null(默认), 'excluded'(排除), 'included'(包含)
		tagLogic: "and", // 标签逻辑：and 或 or
		tagMode: 'included', // 标签点击模式：'included'(包含) 或 'excluded'(排除)
		timeFrom: null,
		timeTo: null,
		authed: true,
		loading: false,
		availableChannels: new Map(),
		availableTags: [], // 当前可用的标签列表
		currentPanel: 'channels', // 当前活动面板
		user: null, // 用户信息
		unreadCount: 0, // 未读更新数量
		follows: [], // 关注列表
		followsTotal: 0, // 关注总数
		viewMode: 'search', // 'search' 或 'follows'
		// 关注列表筛选状态
		followsQuery: '', // 关注列表搜索关键词
		followsTagStates: new Map(), // 关注列表tag状态
		followsAvailableTags: [], // 关注列表可用tags
		followsPage: 1, // 关注列表当前页
		followsPerPage: 24, // 关注列表每页数量
		openMode: 'app', // 帖子打开方式：'app' 或 'web'
		imageRefreshQueue: new Map(), // 等待刷新封面的线程 -> 元数据
		imageRefreshTimer: null, // 定时器句柄
		imageRefreshProcessing: false, // 是否正在请求刷新
		// Banner轮播状态
		bannerCarousel: [], // Banner列表
		currentBannerIndex: 0, // 当前显示的banner索引
		bannerAutoPlay: null // 自动播放定时器
	};

	let savedOpenMode;
	try{
		savedOpenMode = window.localStorage.getItem('open_mode');
	}catch{}
	if(savedOpenMode === 'web' || savedOpenMode === 'app'){
		state.openMode = savedOpenMode;
	}

	const IMAGE_REFRESH_DEBOUNCE = 5000;
	const PLACEHOLDER_IMAGE = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="120" height="68" viewBox="0 0 120 68"%3E%3Crect width="120" height="68" rx="12" fill="%23141926"/%3E%3Cpath d="M18 46L40 26l14 12 18-16 30 24H18Z" fill="%2330527c" opacity=".65"/%3E%3Ccircle cx="86" cy="20" r="6" fill="%23ffffff" opacity=".35"/%3E%3C/svg%3E';

	// iOS 兼容：从回调 URL 片段中获取 token 并持久化
	(function hydrateAuthToken(){
		try{
			const m = location.hash && location.hash.match(/[#&]token=([^&]+)/);
			const fromHash = m ? decodeURIComponent(m[1]) : null;
			const fromStorage = window.localStorage.getItem('auth_token') || null;
			if(fromHash){
				window.AUTH_TOKEN = fromHash;
				window.localStorage.setItem('auth_token', fromHash);
				history.replaceState({}, '', location.pathname + location.search);
			}else if(fromStorage){
				window.AUTH_TOKEN = fromStorage;
			}
		}catch{}
	})();

	function authHeaders(){
		const h = {};
		if(window.AUTH_TOKEN){ h['Authorization'] = 'Bearer ' + window.AUTH_TOKEN; }
		return h;
	}

	/** DOM **/
	const el = {
		keyword: document.getElementById("keywordInput"),
		searchBtn: document.getElementById("searchBtn"),
		timeFrom: document.getElementById("timeFrom"),
		timeTo: document.getElementById("timeTo"),
		sort: document.getElementById("sortSelect"),
		perPage: document.getElementById("perPage"),
		openMode: document.getElementById("openMode"),
		tagLogic: document.getElementById("tagLogic"),
		tagModeSwitch: document.getElementById("tagModeSwitch"),
		stats: document.getElementById("resultCount"),
		results: document.getElementById("results"),
		pagination: document.getElementById("pagination"),
		// 侧边栏相关
		sidebar: document.getElementById("sidebar"),
		drawerToggle: document.getElementById("drawerToggle"),
		userAvatar: document.getElementById("userAvatar"),
		userName: document.getElementById("userName"),
		channelList: document.getElementById("channelList"),
		tagPillsSection: document.getElementById("tagPillsSection"),
		tagPills: document.getElementById("tagPills"),
		followsBadge: document.getElementById("followsBadge"),
		// 筛选器相关
		filters: document.getElementById("filters"),
		viewControls: document.querySelector(".view-controls")
	};

	/** 工具函数 **/
	const fmtDate = (d)=> {
		if(!d) return "";
		let dt;
		if(typeof d === 'string'){
			if(!d.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(d)){
				dt = new Date(d + 'Z');
			} else {
				dt = new Date(d);
			}
		} else {
			dt = new Date(d);
		}
		
		const now = Date.now();
		const diff = now - dt.getTime();
		
		if(diff < 0) return "刚刚";
		
		const sec = Math.floor(diff / 1000);
		const min = Math.floor(sec / 60);
		const hour = Math.floor(min / 60);
		const day = Math.floor(hour / 24);
		
		if(sec < 60) return "刚刚";
		if(min < 60) return `${min}分钟前`;
		if(hour < 24) return `${hour}小时前`;
		if(day < 7) return `${day}天前`;
		
		const year = dt.getFullYear();
		const month = dt.getMonth() + 1;
		const date = dt.getDate();
		const thisYear = new Date().getFullYear();
		
		if(year === thisYear) return `${month}月${date}日`;
		return `${year}年${month}月${date}日`;
	};

	const debounce = (fn,ms)=>{ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a),ms); }; };
	function escapeHtml(s){ return (s==null?"":String(s)).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }
	function escapeAttr(s){ return String(s||"").replace(/"/g,'&quot;'); }
	
	/** 简单的 Markdown 渲染器 **/
	function renderMarkdown(text){
		if(!text) return "";
		let html = escapeHtml(text);
		
		// 步骤1: 保护特殊内容（链接和代码块），用占位符替换
		// 使用null字符作为占位符，不会与markdown语法冲突
		const protected_content = [];
		let counter = 0;
		
		// 保护Discord表情
		html = html.replace(/&lt;a?:([^:]+):(\d+)&gt;/g, (match, name, id) => {
			const placeholder = `\x00MDPROTECT${counter++}\x00`;
			protected_content.push(`<img class="discord-emoji" src="https://cdn.discordapp.com/emojis/${id}.webp" alt=":${name}:" title=":${name}:" loading="lazy">`);
			return placeholder;
		});
		
		// 保护代码块
		html = html.replace(/```([^`]+)```/g, (match, code) => {
			const placeholder = `\x00MDPROTECT${counter++}\x00`;
			protected_content.push(`<pre><code>${code}</code></pre>`);
			return placeholder;
		});
		
		// 保护行内代码
		html = html.replace(/`([^`]+)`/g, (match, code) => {
			const placeholder = `\x00MDPROTECT${counter++}\x00`;
			protected_content.push(`<code>${code}</code>`);
			return placeholder;
		});
		
		// 保护链接（包括链接文本和URL）
		html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, text, url) => {
			const placeholder = `\x00MDPROTECT${counter++}\x00`;
			protected_content.push(`<a href="${url}" target="_blank" rel="noopener">${text}</a>`);
			return placeholder;
		});
		
		// 步骤2: 处理其他markdown格式
		html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
		html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>');
		html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
		html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
		html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>');
		html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
		html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
		html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
		html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
		html = html.replace(/^[*-] (.+)$/gm, '<li>$1</li>');
		html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');
		html = html.replace(/\n/g, '<br>');
		
		// 步骤3: 还原保护的内容
		protected_content.forEach((content, index) => {
			html = html.replace(`\x00MDPROTECT${index}\x00`, content);
		});
		
		return html;
	}

	/** URL 状态同步 **/
	function readFromURL(){
		const p = new URLSearchParams(location.search);
		
		// 检查是否是关注列表模式
		const mode = p.get("mode");
		if(mode === "follows"){
			state.viewMode = "follows";
			state.followsQuery = p.get("q") || "";
			state.followsPage = +(p.get("page") || 1) || 1;
			
			// 读取关注列表的标签状态
			const included = (p.get("ti")||"").split("|").filter(Boolean);
			const excluded = (p.get("te")||"").split("|").filter(Boolean);
			state.followsTagStates.clear();
			included.forEach(tag => state.followsTagStates.set(tag, 'included'));
			excluded.forEach(tag => state.followsTagStates.set(tag, 'excluded'));
		} else {
			// 搜索模式
			state.viewMode = "search";
			state.query = p.get("q") || "";
			state.sort = p.get("sort") || "last_active_desc";
			state.page = +(p.get("page") || 1) || 1;
			state.perPage = +(p.get("pp") || 24) || 24;
			state.selectedChannel = p.get("ch") || null;
			state.tagLogic = p.get("tl") || "and";
			
			// 读取搜索的标签状态
			const included = (p.get("ti")||"").split("|").filter(Boolean);
			const excluded = (p.get("te")||"").split("|").filter(Boolean);
			state.tagStates.clear();
			included.forEach(tag => state.tagStates.set(tag, 'included'));
			excluded.forEach(tag => state.tagStates.set(tag, 'excluded'));
			
			state.timeFrom = p.get("tf") ? new Date(+p.get("tf")) : null;
			state.timeTo = p.get("tt") ? new Date(+p.get("tt")) : null;
		}
	}

	function writeToURL(replace=false){
		const p = new URLSearchParams();
		
		if(state.viewMode === 'follows'){
			// 关注列表模式
			p.set("mode", "follows");
			if(state.followsQuery) p.set("q", state.followsQuery);
			if(state.followsPage>1) p.set("page", String(state.followsPage));
			
			// 写入关注列表的标签状态
			const included = [];
			const excluded = [];
			state.followsTagStates.forEach((status, tag) => {
				if(status === 'included') included.push(tag);
				else if(status === 'excluded') excluded.push(tag);
			});
			if(included.length) p.set("ti", included.join("|"));
			if(excluded.length) p.set("te", excluded.join("|"));
		} else {
			// 搜索模式
			if(state.query) p.set("q", state.query);
			if(state.sort && state.sort!=="last_active_desc") p.set("sort", state.sort);
			if(state.page>1) p.set("page", String(state.page));
			if(state.perPage!==24) p.set("pp", String(state.perPage));
			if(state.selectedChannel) p.set("ch", state.selectedChannel);
			if(state.tagLogic && state.tagLogic!=="and") p.set("tl", state.tagLogic);
			
			// 写入搜索的标签状态
			const included = [];
			const excluded = [];
			state.tagStates.forEach((status, tag) => {
				if(status === 'included') included.push(tag);
				else if(status === 'excluded') excluded.push(tag);
			});
			if(included.length) p.set("ti", included.join("|"));
			if(excluded.length) p.set("te", excluded.join("|"));
			
			if(state.timeFrom) p.set("tf", String(+state.timeFrom));
			if(state.timeTo) p.set("tt", String(+state.timeTo));
		}
		
		const url = `${location.pathname}?${p.toString()}`;
		history[replace?"replaceState":"pushState"]({}, "", url);
	}

	/** 侧边栏面板切换 **/
	function switchPanel(panelName){
		// 特殊处理退出登录
		if(panelName === 'logout'){
			if(confirm('确定要退出登录吗？')){
				logout();
			}
			return;
		}
		
		state.currentPanel = panelName;
		
		// 更新导航按钮状态
		document.querySelectorAll('.nav-btn').forEach(btn => {
			if(btn.getAttribute('data-panel') === panelName){
				btn.classList.add('active');
			} else {
				btn.classList.remove('active');
			}
		});
		
		// 更新面板显示
		document.querySelectorAll('.panel').forEach(panel => {
			if(panel.id === `panel-${panelName}`){
				panel.classList.add('active');
			} else {
				panel.classList.remove('active');
			}
		});
		
		// 如果切换到关注列表，切换视图模式并加载
		if(panelName === 'follows'){
			state.viewMode = 'follows';
			// 只隐藏筛选器，保留分页数量控件
			if(el.filters) el.filters.style.display = 'none';
			loadFollows();
			markFollowsViewed();
			writeToURL(true);  // 更新URL
			// 关闭抽屉（移动端）
			if(window.innerWidth <= 720){
				el.sidebar.classList.remove('open');
			}
		} else if(state.viewMode === 'follows'){
			// 从关注列表切换回搜索模式
			state.viewMode = 'search';
			// 显示筛选器
			if(el.filters) el.filters.style.display = '';
			state.followsQuery = '';
			state.followsTagStates.clear();
			syncAndSearch();
		}

		updateBannerVisibility();
	}

	/** 初始化频道列表 **/
	async function initChannels(){
		const byId = window.CHANNELS || {};
		state.availableChannels = new Map(Object.entries(byId).map(([id, name]) => [id, name]));
		
		const categories = window.CHANNEL_CATEGORIES || [];
		
		// 全频道选项
		const isAllActive = !state.selectedChannel;
		let html = `<div class="channel-item all-channels${isAllActive?' active':''}" data-channel-id="">🌐 全频道搜索</div>`;
		
		// 渲染分类
		categories.forEach(category => {
			html += `<div class="channel-category">`;
			html += `<div class="category-title">${escapeHtml(category.name)}</div>`;
			html += `<div class="category-channels">`;
			category.channels.forEach(channel => {
				const isActive = channel.id === state.selectedChannel;
				html += `<div class="channel-item${isActive?' active':''}" data-channel-id="${channel.id}">${escapeHtml(channel.name)}</div>`;
			});
			html += `</div></div>`;
		});
		
		el.channelList.innerHTML = html;
	}

	/** 更新标签胶囊显示 **/
	function updateTagPills(){
		// 根据当前模式选择不同的tags和状态
		const tags = state.viewMode === 'follows' ? state.followsAvailableTags : state.availableTags;
		const tagStates = state.viewMode === 'follows' ? state.followsTagStates : state.tagStates;
		
		// 没有可用标签或(搜索模式下)全频道搜索时隐藏标签栏
		if(tags.length === 0 || (state.viewMode === 'search' && state.selectedChannel === null)){
			el.tagPillsSection.classList.add('hidden');
			return;
		}
		
		el.tagPillsSection.classList.remove('hidden');
		el.tagPills.innerHTML = tags.map(tag => {
			const status = tagStates.get(tag) || null;
			const className = status ? `tag-pill ${status}` : 'tag-pill';
			return `<div class="${className}" data-tag="${escapeAttr(tag)}">${escapeHtml(tag)}</div>`;
		}).join('');
	}

	/** 标签胶囊点击 - 三态切换 **/
	function cycleTagState(tag){
		const current = state.tagStates.get(tag) || null;
		const mode = state.tagMode; // 使用全局的tag模式
		
		if(current === mode){
			// 如果已经是当前模式，则取消选择
			state.tagStates.delete(tag);
		} else {
			// 否则设置为当前模式
			state.tagStates.set(tag, mode);
		}
		
		updateTagPills();
	}

	/** 构建搜索请求参数 **/
	function buildSearchRequest(){
		const sortMap = {
			"relevance": { method: "comprehensive", order: "desc" },
			"last_active_desc": { method: "last_active", order: "desc" },
			"created_desc": { method: "created_at", order: "desc" },
			"reply_desc": { method: "reply_count", order: "desc" },
			"reaction_desc": { method: "reaction_count", order: "desc" }
		};
		const sortConfig = sortMap[state.sort] || sortMap["relevance"];
		
		// 构建标签过滤
		const includeTags = [];
		const excludeTags = [];
		state.tagStates.forEach((status, tag) => {
			if(status === 'included') includeTags.push(tag);
			else if(status === 'excluded') excludeTags.push(tag);
		});
		
		return {
			channel_ids: state.selectedChannel ? [state.selectedChannel] : null,
			include_tags: includeTags.length > 0 ? includeTags : [],
			exclude_tags: excludeTags.length > 0 ? excludeTags : [],
			tag_logic: state.tagLogic,
			keywords: state.query || null,
			created_after: state.timeFrom ? formatDateForAPI(state.timeFrom) : null,
			created_before: state.timeTo ? formatDateForAPI(state.timeTo) : null,
			sort_method: sortConfig.method,
			sort_order: sortConfig.order,
			limit: state.perPage,
			offset: (state.page - 1) * state.perPage
		};
	}

	function formatDateForAPI(date){
		const d = new Date(date);
		const year = d.getFullYear();
		const month = String(d.getMonth() + 1).padStart(2, '0');
		const day


 = String(d.getDate()).padStart(2, '0');
		return `${year}-${month}-${day}`;
	}

	/** 从服务端获取搜索结果 **/
	async function fetchSearchResults(){
		if(state.loading) return;
		
		state.loading = true;
		showLoadingPlaceholders();
		
		try{
			const searchRequest = buildSearchRequest();
			const res = await fetch(window.AUTH_URL + '/search', {
				method: 'POST',
				credentials: 'include',
				headers: {
					'Content-Type': 'application/json',
					...authHeaders()
				},
				body: JSON.stringify(searchRequest)
			});
			
			if(!res || res.status === 401){
				state.authed = false;
				state.loading = false;
				render();
				return;
			}
			
			if(!res.ok){
				console.error('搜索请求失败:', res.status);
				state.loading = false;
				el.stats.textContent = "搜索失败，请稍后重试";
				el.results.innerHTML = '<div class="error-message">搜索失败，请稍后重试</div>';
				return;
			}
			const data = await res.json();
			state.filtered = data.results || [];
			state.total = data.total || 0;
			
			// 更新可用标签列表
			state.availableTags = data.available_tags || [];
			
			// 更新未读数量（如后端提供）
			if (typeof data.unread_count === 'number') {
				state.unreadCount = data.unread_count;
				updateUnreadBadge();
			}
			
			// 更新Banner轮播列表
			updateBannerCarousel(data.banner_carousel || []);
			
			
		}catch(e){
			console.error('获取搜索结果时出错:', e);
			state.loading = false;
			el.stats.textContent = "搜索出错";
			el.results.innerHTML = '<div class="error-message">搜索出错，请稍后重试</div>';
			return;
		}
		
		state.loading = false;
		render();
	}

	/** 显示加载占位符 **/
	function showLoadingPlaceholders(){
		const placeholders = Array(state.perPage).fill(0).map(() => `
			<article class="card loading-card">
				<div class="card-media">
					<div class="media-img skeleton"></div>
					<div class="excerpt skeleton-text">
						<div class="skeleton-line"></div>
						<div class="skeleton-line"></div>
						<div class="skeleton-line short"></div>
					</div>
				</div>
				<div class="card-body">
					<div class="skeleton-title"></div>
					<div class="card-meta">
						<span class="skeleton-badge"></span>
						<span class="skeleton-badge"></span>
						<span class="skeleton-badge"></span>
					</div>
				</div>
			</article>
		`).join('');
		
		el.results.innerHTML = placeholders;
		el.stats.textContent = "加载中...";
		
		// 清空banner显示
		const bannerSection = document.getElementById('bannerCarousel');
		if(bannerSection){
			bannerSection.innerHTML = '<div class="banner-placeholder"><p>🎉 加载中...</p></div>';
		}
	}

	/** 渲染 **/
	function render(){
		if(!state.authed){
			el.stats.textContent = "您需要先登录才能浏览搜索结果";
			el.results.innerHTML = `<div class="auth-required">
				<div class="auth-card">
					<h3>需要登录</h3>
					<p>请先使用 Discord 登录以加载搜索索引并浏览搜索结果。</p>
					<button id="loginBtn" class="btn primary">登录 Discord</button>
				</div>
			</div>`;
			el.pagination.innerHTML = "";
			const btn = document.getElementById('loginBtn');
			if(btn){ btn.addEventListener('click', ()=> login()); }
			return;
		}
		
		const total = state.total;
		const pages = Math.max(1, Math.ceil(total / state.perPage));
		if(state.page > pages && pages > 0) state.page = pages;
		
		el.stats.textContent = `共 ${total} 条结果 · 第 ${state.page}/${pages} 页`;
		el.results.innerHTML = state.filtered.map(renderCard).join("");
		renderPagination(state.page, pages);
		updateTagPills();
		attachImageErrorHandlers();
		
		window.scrollTo({top: 0, behavior: 'smooth'});
	}

	function renderCard(item){
		const author = item.author || {};
		const hasThumbnail = Boolean(item.thumbnail_url);
		const cardClassName = hasThumbnail ? "card" : "card card--no-thumb";
		const mediaClassName = hasThumbnail ? "card-media" : "card-media card-media--no-thumb";
		const mediaImgHtml = hasThumbnail
			? `<div class="media-img"><img src="${escapeAttr(item.thumbnail_url)}" alt="${escapeAttr(item.title)} 缩略图" loading="lazy" class="card-img" data-src="${escapeAttr(item.thumbnail_url)}" data-thread-id="${escapeAttr(String(item.thread_id))}" data-channel-id="${item.channel_id != null ? escapeAttr(String(item.channel_id)) : ''}"></div>`
			: "";
		const excerptText = limitText(item.first_message_excerpt||"", hasThumbnail ? 500 : 800);
		const excerptHtml = `<div class="excerpt markdown-content">${renderMarkdown(excerptText)}</div>`;
		const channelName = state.availableChannels.get(String(item.channel_id)) || `频道 ${item.channel_id}`;
		const created = fmtDate(item.created_at);
		const active = fmtDate(item.last_active_at);
		const authorDisplayName = author.display_name || author.global_name || author.name || "未知作者";
		const authorUsername = author.name || "";
		const authorTooltip = authorUsername
			? `点击搜索${authorUsername}的所有作品`
			: "点击搜索该作者的所有作品";
		const guildId = window.GUILD_ID;
		
		return `
		<article class="${cardClassName}" tabindex="0">
			<div class="${mediaClassName}">${mediaImgHtml}${excerptHtml}</div>
			<div class="card-body">
				<h2 class="card-title" title="${escapeAttr(item.title)}">${escapeHtml(item.title)}</h2>
				<div class="card-meta">
					<span class="badge" title="频道"><span class="dot"></span>${escapeHtml(channelName)}</span>
					<span class="badge badge-author" title="${escapeAttr(authorTooltip)}" data-author="${escapeAttr(authorUsername)}">👤 ${escapeHtml(authorDisplayName)}</span>
					<span class="badge" title="发布时间 ${new Date(item.created_at).toLocaleString()}">🕒 ${escapeHtml(created)}</span>
					<span class="badge" title="最近活跃 ${new Date(item.last_active_at).toLocaleString()}">🔥 ${escapeHtml(active)}</span>
					<span class="badge" title="回复">💬 ${escapeHtml(item.reply_count||0)}</span>
					<span class="badge" title="反应">⭐ ${escapeHtml(item.reaction_count||0)}</span>
				</div>
				<div class="tags">${(item.tags||[]).map(t=>`<span class="tag"># ${escapeHtml(t)}</span>`).join("")}</div>
			</div>
			<div class="card-actions">
				<div class="left"> </div>
				<div class="right"><a class="link discord-link" href="#" data-guild="${guildId}" data-channel="${item.channel_id}" data-thread="${item.thread_id}">打开原帖 →</a></div>
			</div>
		</article>`;
	}
	
	function limitText(s,n){ if(!s) return ""; return s.length>n? s.slice(0,n-1)+"…" : s; }

	function attachImageErrorHandlers(){
		const images = document.querySelectorAll('img.card-img');
		images.forEach(img=>{
			if(img.dataset.errorListenerAttached === '1') return;
			img.dataset.errorListenerAttached = '1';
			img.addEventListener('error', onCardImageError, {passive: true});
		});
	}

	function onCardImageError(event){
		const img = event.target;
		if(!img || img.dataset.imageRefreshing === '1') return;
		const threadId = img.dataset.threadId;
		if(!threadId) return;
		img.dataset.imageRefreshing = '1';
		img.src = PLACEHOLDER_IMAGE;
		const channelId = img.dataset.channelId || null;
		queueImageRefresh(threadId, channelId, img);
	}

	function queueImageRefresh(threadId, channelId, img){
		const key = String(threadId);
		let entry = state.imageRefreshQueue.get(key);
		if(!entry){
			entry = {
				threadId: threadId,
				channelId: channelId ? channelId : null,
				imgElements: new Set()
			};
			state.imageRefreshQueue.set(key, entry);
		}
		entry.imgElements.add(img);
		scheduleImageRefresh();
	}

	function scheduleImageRefresh(){
		if(state.imageRefreshProcessing) return;
		if(state.imageRefreshTimer) return;
		state.imageRefreshTimer = setTimeout(flushImageRefreshQueue, IMAGE_REFRESH_DEBOUNCE);
	}

	async function flushImageRefreshQueue(){
		if(state.imageRefreshTimer){
			clearTimeout(state.imageRefreshTimer);
			state.imageRefreshTimer = null;
		}
		if(state.imageRefreshProcessing){
			scheduleImageRefresh();
			return;
		}

		const queueEntries = Array.from(state.imageRefreshQueue.values());
		state.imageRefreshQueue = new Map();
		if(queueEntries.length === 0) return;

		const entryMap = new Map(queueEntries.map(entry => [String(entry.threadId), entry]));
		const payload = {
			items: queueEntries.map(entry => ({
				thread_id: entry.threadId,
				channel_id: entry.channelId ?? undefined
			}))
		};

		state.imageRefreshProcessing = true;
		try{
			const res = await fetch(window.AUTH_URL + '/fetch-images', {
				method: 'POST',
				credentials: 'include',
				headers: {
					'Content-Type': 'application/json',
					...authHeaders()
				},
				body: JSON.stringify(payload)
			});
			if(!res || !res.ok){
				console.error('刷新封面失败:', res ? res.status : 'unknown');
				entryMap.forEach(entry=>{
					entry.imgElements.forEach(img=>{
						img.dataset.imageRefreshing = '0';
					});
				});
				return;
			}
			const data = await res.json();
			handleImageRefreshResponse(data, entryMap);
		}catch(error){
			console.error('刷新封面请求异常:', error);
			entryMap.forEach(entry=>{
				entry.imgElements.forEach(img=>{
					img.dataset.imageRefreshing = '0';
				});
			});
		}finally{
			state.imageRefreshProcessing = false;
			if(state.imageRefreshQueue.size){
				scheduleImageRefresh();
			}
		}
	}

	function handleImageRefreshResponse(data, entryMap){
		if(!data || !Array.isArray(data.results)){
			entryMap.forEach(entry=>{
				entry.imgElements.forEach(img=>{
					img.dataset.imageRefreshing = '0';
				});
			});
			return;
		}

		data.results.forEach(result=>{
			const key = String(result.thread_id);
			const entry = entryMap.get(key);
			console.log(key, entry)
			if(!entry) return;
			const updatedUrl = result && result.updated && result.thumbnail_url ? result.thumbnail_url : null;
			entry.imgElements.forEach(img=>{
				img.dataset.imageRefreshing = '0';
				if(updatedUrl){
					const finalUrl = updatedUrl.includes('?')
						? `${updatedUrl}&_ts=${Date.now()}`
						: `${updatedUrl}?_ts=${Date.now()}`;
					img.src = finalUrl;
					img.setAttribute('data-src', updatedUrl);
				} else {
					img.remove();
				}
			});
			if(updatedUrl){
				applyThumbnailToState(result.thread_id, updatedUrl);
			}
			entryMap.delete(key);
		});

		entryMap.forEach(entry=>{
			entry.imgElements.forEach(img=>{
				img.dataset.imageRefreshing = '0';
			});
		});

		attachImageErrorHandlers();
	}

	function applyThumbnailToState(threadId, newUrl){
		const numericId = threadId;
		const updateList = list=>{
			if(!Array.isArray(list)) return;
			list.forEach(item=>{
				const candidate = item.thread_id ?? item.id ?? item.threadId;
				if(candidate != null && candidate === numericId){
					item.thumbnail_url = newUrl;
				}
			});
		};
		updateList(state.filtered);
		updateList(state.follows);
	}

	function renderPagination(page, total){
		const btn = (p, label, disabled=false, current=false)=>`<button class="page-btn" ${disabled?"disabled":""} ${current?"aria-current=\"page\"":""} data-page="${p}">${label}</button>`;
		const items = [];
		items.push(btn(Math.max(1,page-1), "上一页", page<=1));
		const windowSize = 5; 
		const start = Math.max(1, page - Math.floor(windowSize/2)); 
		const end = Math.min(total, start + windowSize - 1);
		for(let i=start;i<=end;i++) items.push(btn(i, i, false, i===page));
		items.push(btn(Math.min(total,page+1), "下一页", page>=total));
		el.pagination.innerHTML = items.join("");
	}

	/** 事件绑定 **/
	function bindEvents(){
		// 搜索按钮
		el.searchBtn.addEventListener('click', ()=>{
			if(state.viewMode === 'follows'){
				// 关注列表模式：客户端过滤
				state.followsPage = 1;
				state.followsQuery = el.keyword.value;
				applyFollowsFilter();
				renderFollowsInMain();
			} else {
				// 搜索模式：API搜索
				state.page=1;
				state.query=el.keyword.value;
				syncAndSearch();
			}
		});

		// 关键词输入防抖
		el.keyword.addEventListener('input', debounce(()=>{
			if(state.viewMode === 'follows'){
				// 关注列表模式：客户端过滤
				state.followsPage = 1;
				state.followsQuery = el.keyword.value;
				applyFollowsFilter();
				renderFollowsInMain();
			} else {
				// 搜索模式：API搜索
				state.page=1;
				state.query=el.keyword.value;
				syncAndSearch(true);
			}
		}, 250));

		// 时间筛选改变
		el.timeFrom.addEventListener('change', ()=>{
			state.timeFrom = el.timeFrom.value ? new Date(el.timeFrom.value) : null;
			if(state.viewMode === 'follows'){
				state.followsPage = 1;
				applyFollowsFilter();
				renderFollowsInMain();
			} else {
				state.page = 1;
				syncAndSearch();
			}
		});

		el.timeTo.addEventListener('change', ()=>{
			state.timeTo = el.timeTo.value ? new Date(el.timeTo.value) : null;
			if(state.viewMode === 'follows'){
				state.followsPage = 1;
				applyFollowsFilter();
				renderFollowsInMain();
			} else {
				state.page = 1;
				syncAndSearch();
			}
		});

		// 排序改变
		el.sort.addEventListener('change', ()=>{
			state.sort = el.sort.value;
			if(state.viewMode === 'follows'){
				state.followsPage = 1;
				applyFollowsFilter();
				renderFollowsInMain();
			} else {
				state.page = 1;
				syncAndSearch();
			}
		});

		// 每页数量改变
		el.perPage.addEventListener('change', ()=>{
			const newPerPage = +el.perPage.value || 24;
			if(state.viewMode === 'follows'){
				state.followsPerPage = newPerPage;
				state.followsPage = 1;
				renderFollowsInMain();
			} else {
				state.perPage = newPerPage;
				state.page = 1;
				syncAndSearch();
			}
		});

		// 帖子打开方式改变
		if(el.openMode){
			el.openMode.addEventListener('change', ()=>{
				const value = el.openMode.value === 'web' ? 'web' : 'app';
				state.openMode = value;
				try{
					window.localStorage.setItem('open_mode', value);
				}catch{}
			});
		}

		// 标签逻辑改变
		el.tagLogic.addEventListener('change', ()=>{
			state.tagLogic = el.tagLogic.value;
			if(state.viewMode === 'follows'){
				// 关注模式下标签逻辑固定为 AND，不需要处理
				// 但为了一致性，仍然更新状态
				state.followsPage = 1;
				applyFollowsFilter();
				renderFollowsInMain();
			} else {
				state.page = 1;
				syncAndSearch();
			}
		});

		// 分页点击
		el.pagination.addEventListener('click', (e)=>{
			const b = e.target.closest('button[data-page]');
			if(!b) return;
			const p = +b.getAttribute('data-page');
			if(!isNaN(p)) {
				if(state.viewMode === 'follows'){
					// 关注模式：更新关注列表页码
					state.followsPage = p;
					renderFollowsInMain();
					writeToURL(true);
				} else {
					// 搜索模式：更新搜索页码
					state.page = p;
					syncAndSearch();
				}
			}
		});
		
		// 频道列表点击
		el.channelList.addEventListener('click', (e)=>{
			const item = e.target.closest('.channel-item');
			if(!item) return;
			
			const channelId = item.getAttribute('data-channel-id') || null;
			state.selectedChannel = channelId;
			state.page = 1;
			state.tagStates.clear(); // 切换频道时清空标签选择
			state.viewMode = 'search'; // 切换回搜索模式
			updateBannerVisibility();
			
			// 更新UI
			document.querySelectorAll('.channel-item').forEach(el => el.classList.remove('active'));
			item.classList.add('active');
			
			syncAndSearch();
		});

		// 标签模式切换
		if(el.tagModeSwitch){
			el.tagModeSwitch.addEventListener('change', ()=>{
				state.tagMode = el.tagModeSwitch.checked ? 'excluded' : 'included';
			});
		}
		
		// 标签胶囊点击
		el.tagPills.addEventListener('click', (e)=>{
			const pill = e.target.closest('.tag-pill');
			if(!pill) return;
			
			const tag = pill.getAttribute('data-tag');
			if(tag){
				if(state.viewMode === 'follows'){
					// 关注列表模式：客户端过滤
					cycleFollowsTagState(tag);
					state.followsPage = 1;
					applyFollowsFilter();
					renderFollowsInMain();
				} else {
					// 搜索模式：API搜索
					cycleTagState(tag);
					state.page = 1;
					syncAndSearch();
				}
			}
		});

		// 侧边栏导航按钮
		document.querySelectorAll('.nav-btn').forEach(btn => {
			btn.addEventListener('click', ()=>{
				const panel = btn.getAttribute('data-panel');
				switchPanel(panel);
			});
		});

		// 抽屉菜单切换
		if(el.drawerToggle){
			el.drawerToggle.addEventListener('click', ()=>{
				el.sidebar.classList.toggle('open');
			});

			// 点击外部关闭抽屉
			document.addEventListener('click', (e)=>{
				if(window.innerWidth > 720) return;
				if(!el.sidebar.contains(e.target) && !el.drawerToggle.contains(e.target)){
					el.sidebar.classList.remove('open');
				}
			});
		}
		
		// 关注列表事件委托
		if(el.followsContent){
			el.followsContent.addEventListener('click', (e)=>{
				// 取消关注按钮
				const unfollowBtn = e.target.closest('.btn-unfollow');
				if(unfollowBtn){
					const threadId = unfollowBtn.getAttribute('data-thread-id');
					if(threadId){
						unfollowThread(threadId);
					}
					return;
				}
				
				// Discord链接
				const discordLink = e.target.closest('.discord-link');
				if(discordLink){
					e.preventDefault();
					const guild = discordLink.getAttribute('data-guild');
					const channel = discordLink.getAttribute('data-channel');
					const thread = discordLink.getAttribute('data-thread');
					openDiscordLink(guild, channel, thread);
					return;
				}
			});
		}
		
		// 结果区域事件委托
		el.results.addEventListener('click', (e)=>{
			// 点击作者跳转搜索
			const authorBadge = e.target.closest('.badge-author');
			if(authorBadge){
				const authorUsername = (authorBadge.getAttribute('data-author') || '').trim();
				if(authorUsername){
					state.query = `author:${authorUsername}`;
					el.keyword.value = state.query;
					state.page = 1;
					syncAndSearch();
					window.scrollTo({top:0, behavior:'smooth'});
				}
				return;
			}
			
			// 点击标签（这里暂时不做处理，因为现在标签在侧边栏）
			
			// 点击图片弹出大图
			const img = e.target.closest('.card-img');
			if(img){
				const src = img.getAttribute('data-src');
				if(src) openImagePopup(src);
				return;
			}
			
			// 点击 Discord 链接
			const discordLink = e.target.closest('.discord-link');
			if(discordLink){
				e.preventDefault();
				const guild = discordLink.getAttribute('data-guild');
				const channel = discordLink.getAttribute('data-channel');
				const thread = discordLink.getAttribute('data-thread');
				openDiscordLink(guild, channel, thread);
				return;
			}
			
			// 取消关注按钮（关注列表视图）
			const unfollowBtn = e.target.closest('.btn-unfollow');
			if(unfollowBtn && !unfollowBtn.classList.contains('disabled')){
				const threadId = unfollowBtn.getAttribute('data-thread-id');
				const authorId = unfollowBtn.getAttribute('data-author-id');
				if(threadId){
					unfollowThread(threadId, authorId);
				}
				return;
			}
		});
		
		// 浏览器前进后退
		window.addEventListener('popstate', ()=>{
			readFromURL();
			hydrateControls();
			updateBannerVisibility();
			fetchSearchResults();
		});
	}
	
	/** Discord 链接跳转 **/
	function openDiscordLink(guild, channel, thread){
		const safeGuild = guild ? String(guild) : '';
		const safeChannel = channel && channel !== 'null' && channel !== 'undefined' ? String(channel) : '';
		const safeThread = thread && thread !== 'null' && thread !== 'undefined' ? String(thread) : '';
		const segments = [];
		if(safeGuild) segments.push(safeGuild);
		if(safeThread) segments.push(safeThread);
		const path = segments.join('/');
		const appUrl = path ? `discord://-/channels/${path}` : 'discord://-/channels';
		const webUrl = path ? `https://discord.com/channels/${path}` : 'https://discord.com/channels';

		if(state.openMode === 'web' || !path){
			window.open(webUrl, '_blank', 'noopener,noreferrer');
			return;
		}

		const iframe = document.createElement('iframe');
		iframe.style.display = 'none';
		iframe.src = appUrl;
		document.body.appendChild(iframe);

		let opened = false;
		const timeout = setTimeout(()=>{
			if(!opened){
				window.open(webUrl, '_blank', 'noopener,noreferrer');
			}
			document.body.removeChild(iframe);
		}, 1500);

		const onBlur = ()=>{
			opened = true;
			clearTimeout(timeout);
			setTimeout(()=> document.body.removeChild(iframe), 100);
			window.removeEventListener('blur', onBlur);
		};
		window.addEventListener('blur', onBlur);

		window.location.href = appUrl;
	}

	
	/** 图片弹出层 **/
	function openImagePopup(src){
		const popup = document.createElement('div');
		popup.className = 'image-popup';
		popup.innerHTML = `
			<div class="popup-backdrop"></div>
			<div class="popup-content">
				<img src="${escapeAttr(src)}" alt="大图预览">
				<button class="popup-close" aria-label="关闭">✕</button>
			</div>
		`;
		document.body.appendChild(popup);
		
		const close = ()=>{ popup.remove(); };
		popup.querySelector('.popup-backdrop').addEventListener('click', close);
		popup.querySelector('.popup-close').addEventListener('click', close);
		document.addEventListener('keydown', function onEsc(e){
			if(e.key==='Escape'){
				close();
				document.removeEventListener('keydown', onEsc);
			}
		});
	}

	function hydrateControls(){
		el.keyword.value = state.query;
		el.sort.value = state.sort;
		el.perPage.value = String(state.perPage);
		if(el.openMode){
			el.openMode.value = state.openMode;
		}
		el.tagLogic.value = state.tagLogic;
		el.timeFrom.value = state.timeFrom ? toISODate(state.timeFrom) : "";
		el.timeTo.value = state.timeTo ? toISODate(state.timeTo) : "";
	}
	
	function toISODate(d){
		const x = new Date(d);
		x.setHours(0,0,0,0);
		return x.toISOString().slice(0,10);
	}

	function syncAndSearch(replace=false){
		writeToURL(replace);
		fetchSearchResults();
	}

	/** 登录 **/
	async function login(){
		window.location.href = window.AUTH_URL + "/auth/login";
	}

	/** 退出登录 **/
	async function logout(){
		try{
			window.localStorage.removeItem('auth_token');
			window.AUTH_TOKEN = null;
			window.location.href = window.AUTH_URL + "/auth/logout";
		}catch(e){
			console.error('退出登录失败:', e);
			alert('退出登录失败，请稍后重试');
		}
	}

	/** 加载关注列表 **/
	async function loadFollows(){
		if(!state.authed) return;
		
		state.loading = true;
		showLoadingPlaceholders();
		
		try{
			const res = await fetch(window.AUTH_URL + '/follows/', {
				credentials: 'include',
				headers: authHeaders()
			});
			
			if(res && res.ok){
				const data = await res.json();
				state.follows = data.threads || [];
				state.followsTotal = data.total || 0;
				
				// 提取所有唯一的tags
				extractFollowsTags();
				
				// 应用筛选和排序
				applyFollowsFilter();
			}else{
				state.follows = [];
				state.followsTotal = 0;
				state.followsAvailableTags = [];
				state.filtered = [];
				state.total = 0;
			}
		}catch(e){
			console.error('加载关注列表失败:', e);
			state.follows = [];
			state.followsTotal = 0;
			state.followsAvailableTags = [];
			state.filtered = [];
			state.total = 0;
		}
		
		state.loading = false;
		renderFollowsInMain();
	}
	
	/** 从关注列表提取所有唯一tags **/
	function extractFollowsTags(){
		const tagsSet = new Set();
		state.follows.forEach(thread => {
			if(thread.tags && Array.isArray(thread.tags)){
				thread.tags.forEach(tag => tagsSet.add(tag));
			}
		});
		state.followsAvailableTags = Array.from(tagsSet).sort();
	}
	
	/** 应用关注列表筛选 **/
	function applyFollowsFilter(){
		let filtered = state.follows;
		
		// 关键词搜索
		if(state.followsQuery){
			const query = state.followsQuery.toLowerCase();
			filtered = filtered.filter(thread => {
				const title = (thread.title || '').toLowerCase();
				const excerpt = (thread.first_message_excerpt || '').toLowerCase();
				return title.includes(query) || excerpt.includes(query);
			});
		}
		
		// Tag筛选
		const includeTags = [];
		const excludeTags = [];
		state.followsTagStates.forEach((status, tag) => {
			if(status === 'included') includeTags.push(tag);
			else if(status === 'excluded') excludeTags.push(tag);
		});
		
		if(includeTags.length > 0 || excludeTags.length > 0){
			filtered = filtered.filter(thread => {
				const threadTags = thread.tags || [];
				
				// 排除标签：只要包含任意排除标签就过滤掉
				if(excludeTags.length > 0){
					const hasExcluded = excludeTags.some(tag => threadTags.includes(tag));
					if(hasExcluded) return false;
				}
				
				// 包含标签：必须包含所有指定标签
				if(includeTags.length > 0){
					const hasAllIncluded = includeTags.every(tag => threadTags.includes(tag));
					if(!hasAllIncluded) return false;
				}
				
				return true;
			});
		}
		
		// 时间筛选
		if(state.timeFrom){
			const fromTime = state.timeFrom.getTime();
			filtered = filtered.filter(thread => {
				const createdTime = new Date(thread.created_at).getTime();
				return createdTime >= fromTime;
			});
		}
		
		if(state.timeTo){
			const toTime = state.timeTo.getTime();
			filtered = filtered.filter(thread => {
				const createdTime = new Date(thread.created_at).getTime();
				return createdTime <= toTime;
			});
		}
		
		// 排序：按最近更新时间排序（没有更新时间则用发帖时间）
		filtered.sort((a, b) => {
			const aUpdateTime = a.latest_update_at ? new Date(a.latest_update_at).getTime() : new Date(a.created_at).getTime();
			const bUpdateTime = b.latest_update_at ? new Date(b.latest_update_at).getTime() : new Date(b.created_at).getTime();
			
			// 根据排序方式决定升序还是降序
			if(state.sort === 'created_asc'){
				return aUpdateTime - bUpdateTime; // 升序
			} else {
				return bUpdateTime - aUpdateTime; // 降序（默认）
			}
		});
		
		state.filtered = filtered;
		state.total = filtered.length;
	}
	
	/** 在主界面渲染关注列表 **/
	function renderFollowsInMain(){
		const total = state.total;
		const totalFollows = state.followsTotal;
		const pages = Math.max(1, Math.ceil(total / state.followsPerPage));
		if(state.followsPage > pages && pages > 0) state.followsPage = pages;
		
		// 更新搜索框显示当前查询
		el.keyword.value = state.followsQuery;
		
		// 更新tag pills显示
		updateTagPills();
		
		// 更新统计信息
		const filterInfo = total !== totalFollows ? ` (筛选后 ${total} 个)` : '';
		el.stats.textContent = `共 ${totalFollows} 个关注${filterInfo} · 第 ${state.followsPage}/${pages} 页`;
		
		if(totalFollows === 0){
			el.results.innerHTML = '<div class="auth-required"><div class="auth-card"><h3>📌 暂无关注的帖子</h3><p>加入帖子后会自动添加到关注列表</p></div></div>';
			el.pagination.innerHTML = '';
			return;
		}
		
		if(total === 0){
			el.results.innerHTML = '<div class="auth-required"><div class="auth-card"><h3>🔍 没有符合条件的帖子</h3><p>尝试调整搜索条件或标签筛选</p></div></div>';
			el.pagination.innerHTML = '';
			return;
		}
		
		// 分页
		const start = (state.followsPage - 1) * state.followsPerPage;
		const end = start + state.followsPerPage;
		const pagedThreads = state.filtered.slice(start, end);
		
		// 渲染关注卡片
		el.results.innerHTML = pagedThreads.map(thread => renderFollowCard(thread)).join("");
		attachImageErrorHandlers();
		
		// 渲染分页
		renderFollowsPagination(state.followsPage, pages);
		
		window.scrollTo({top: 0, behavior: 'smooth'});
	}
	
	/** 渲染单个关注卡片 **/
	function renderFollowCard(thread){
		const channelName = state.availableChannels.get(String(thread.channel_id)) || `频道 ${thread.channel_id}`;
		const created = fmtDate(thread.created_at);
		const active = fmtDate(thread.last_active_at);
		const hasUpdate = thread.has_update;
		const updateBadge = hasUpdate ? '<span class="update-badge">🔔 有更新</span>' : '';
		const guildId = window.GUILD_ID;
		const hasThumbnail = Boolean(thread.thumbnail_url);
		const cardClassParts = ['card'];
		if(hasUpdate) cardClassParts.push('has-update-border');
		if(!hasThumbnail) cardClassParts.push('card--no-thumb');
		const mediaClassName = hasThumbnail ? 'card-media' : 'card-media card-media--no-thumb';
		const mediaImgHtml = hasThumbnail
			? `<div class="media-img"><img src="${escapeAttr(thread.thumbnail_url)}" alt="${escapeAttr(thread.title)} 缩略图" loading="lazy" class="card-img" data-src="${escapeAttr(thread.thumbnail_url)}" data-thread-id="${escapeAttr(String(thread.thread_id))}" data-channel-id="${thread.channel_id != null ? escapeAttr(String(thread.channel_id)) : ''}"></div>`
			: "";
		const excerptText = limitText(thread.first_message_excerpt||"", hasThumbnail ? 500 : 800);
		const excerptHtml = `<div class="excerpt markdown-content">${renderMarkdown(excerptText)}</div>`;
		
		// 检查是否是用户自己的帖子（使用字符串比较避免精度问题）
		const isOwnThread = state.user && String(thread.author_id) === String(state.user.id);
		const unfollowBtn = isOwnThread
			? '<span class="btn-unfollow disabled" title="不能取消关注自己的帖子">取消关注</span>'
			: `<button class="btn-unfollow" data-thread-id="${escapeAttr(String(thread.thread_id))}" data-author-id="${escapeAttr(String(thread.author_id))}">取消关注</button>`;
		
		// 只要有 latest_update_link 就显示"查看最新版"按钮
		const viewUpdateBtn = thread.latest_update_link
			? `<a class="btn-link" href="${escapeAttr(thread.latest_update_link)}" target="_blank" rel="noopener">查看最新版</a>`
			: '';
		
		return `
		<article class="${cardClassParts.join(' ')}" tabindex="0">
			<div class="${mediaClassName}">${mediaImgHtml}${excerptHtml}</div>
			<div class="card-body">
				<div class="follow-header-inline">
					<h2 class="card-title" title="${escapeAttr(thread.title)}">${escapeHtml(thread.title)}</h2>
					${updateBadge}
				</div>
				<div class="card-meta">
					<span class="badge"><span class="dot"></span>${escapeHtml(channelName)}</span>
					<span class="badge">🕒 ${escapeHtml(created)}</span>
					<span class="badge">🔥 ${escapeHtml(active)}</span>
					<span class="badge">💬 ${escapeHtml(thread.reply_count||0)}</span>
					<span class="badge">⭐ ${escapeHtml(thread.reaction_count||0)}</span>
				</div>
			</div>
			<div class="card-actions">
				<div class="left"></div>
				<div class="right follow-actions-inline">
					${unfollowBtn}
					${viewUpdateBtn}
					<button class="btn-link discord-link" data-guild="${guildId}" data-channel="${thread.channel_id}" data-thread="${thread.thread_id}">打开原帖</button>
				</div>
			</div>
		</article>`;
	}
	
	/** 根据模式切换关注列表tag状态 **/
	function cycleFollowsTagState(tag){
		const current = state.followsTagStates.get(tag) || null;
		const mode = state.tagMode; // 使用全局的tag模式
		
		if(current === mode){
			// 如果已经是当前模式，则取消选择
			state.followsTagStates.delete(tag);
		} else {
			// 否则设置为当前模式
			state.followsTagStates.set(tag, mode);
		}
	}
	
	/** 渲染关注列表分页 **/
	function renderFollowsPagination(page, total){
		if(total <= 1){
			el.pagination.innerHTML = '';
			return;
		}
		
		const btn = (p, label, disabled=false, current=false)=>`<button class="page-btn follows-page-btn" ${disabled?"disabled":""} ${current?"aria-current=\"page\"":""} data-page="${p}">${label}</button>`;
		const items = [];
		items.push(btn(Math.max(1,page-1), "上一页", page<=1));
		const windowSize = 5;
		const start = Math.max(1, page - Math.floor(windowSize/2));
		const end = Math.min(total, start + windowSize - 1);
		for(let i=start;i<=end;i++) items.push(btn(i, i, false, i===page));
		items.push(btn(Math.min(total,page+1), "下一页", page>=total));
		el.pagination.innerHTML = items.join("");
		
		// 绑定分页点击事件
		el.pagination.querySelectorAll('.follows-page-btn').forEach(btn => {
			btn.addEventListener('click', ()=>{
				const p = +btn.getAttribute('data-page');
				if(!isNaN(p)){
					state.followsPage = p;
					renderFollowsInMain();
				}
			});
		});
	}
	
	/** 取消关注 **/
	async function unfollowThread(threadId, authorId){
		// 检查是否是自己的帖子
		if(state.user && authorId && authorId === state.user.id){
			alert('不能取消关注自己的帖子');
			return;
		}
		
		if(!confirm('确定要取消关注此帖吗？')) return;
		
		try{
			const res = await fetch(window.AUTH_URL + `/follows/${threadId}`, {
				method: 'DELETE',
				credentials: 'include',
				headers: authHeaders()
			});
			
			if(res && res.ok){
				// 重新加载关注列表
				await loadFollows();
				// 更新未读数量
				await updateUnreadCount();
			}else{
				const data = await res.json().catch(() => ({}));
				alert(data.detail || '取消关注失败');
			}
		}catch(e){
			console.error('取消关注失败:', e);
			alert('取消关注失败');
		}
	}
	
	/** 标记关注列表已查看 **/
	async function markFollowsViewed(){
		if(!state.authed) return;
		
		try{
			await fetch(window.AUTH_URL + '/follows/mark-viewed', {
				method: 'POST',
				credentials: 'include',
				headers: authHeaders()
			});
			
			// 更新未读数量
			await updateUnreadCount();
		}catch(e){
			console.error('标记已查看失败:', e);
		}
	}
	
	/** 更新未读数量 **/
	async function updateUnreadCount(){
		if(!state.authed) return;
		
		try{
			const res = await fetch(window.AUTH_URL + '/follows/unread-count', {
				credentials: 'include',
				headers: authHeaders()
			});
			
			if(res && res.ok){
				const data = await res.json();
				state.unreadCount = data.unread_count || 0;
				updateUnreadBadge();
			}
		}catch(e){
			console.error('更新未读数量失败:', e);
		}
	}
	
	/** 更新未读徽章显示 **/
	function updateUnreadBadge(){
		if(state.unreadCount > 0){
			el.followsBadge.textContent = state.unreadCount > 99 ? '99+' : state.unreadCount;
			el.followsBadge.classList.remove('hidden');
		}else{
			el.followsBadge.classList.add('hidden');
		}
	}
		/** Banner轮播相关函数 **/
	function updateBannerCarousel(newBanners){
		// 检查新banner列表是否与当前列表不同
		const bannersChanged = !arraysEqual(
			state.bannerCarousel.map(b => b.thread_id),
			newBanners.map(b => b.thread_id)
		);
		
		if(bannersChanged){
			// 检查当前显示的banner是否还在新列表中
			const currentBanner = state.bannerCarousel[state.currentBannerIndex];
			let newIndex = 0;
			
			if(currentBanner){
				const foundIndex = newBanners.findIndex(b => b.thread_id === currentBanner.thread_id);
				if(foundIndex !== -1){
					// 当前banner仍在列表中，保持显示
					newIndex = foundIndex;
				}
			}
			
			state.bannerCarousel = newBanners;
			state.currentBannerIndex = newIndex;
			renderBanner();
		}else{
			// 列表未变化，只更新数据但不改变索引
			state.bannerCarousel = newBanners;
		}
	}
	
	function arraysEqual(a, b){
		if(a.length !== b.length) return false;
		for(let i = 0; i < a.length; i++){
			if(a[i] !== b[i]) return false;
		}
		return true;
	}
	
	function renderBanner(){
		const bannerSection = document.getElementById('bannerCarousel');
		if(!bannerSection) return;
	
		if(state.bannerAutoPlay){
			clearInterval(state.bannerAutoPlay);
			state.bannerAutoPlay = null;
		}
	
		if(state.bannerCarousel.length === 0){
			bannerSection.innerHTML = '<div class="banner-placeholder"><p>🎉 欢迎使用 Odysseia 论坛搜索</p></div>';
			return;
		}
	
		const guildId = window.GUILD_ID;
		let track = bannerSection.querySelector('.banner-track');
		const needsRebuild = !track || track.children.length !== state.bannerCarousel.length;
	
		if(needsRebuild){
			const slidesHtml = state.bannerCarousel.map((item, idx) => `
				<div class="banner-slide${idx === state.currentBannerIndex ? ' is-active' : ''}" data-index="${idx}" aria-hidden="${idx === state.currentBannerIndex ? 'false' : 'true'}">
					<div class="banner-image-wrapper">
						<img src="${escapeAttr(item.cover_image_url)}"
							 alt="${escapeAttr(item.title)}"
							 class="banner-image"
							 loading="lazy">
					</div>
					<div class="banner-overlay">
						<div class="banner-content">
							<h2 class="banner-title">${escapeHtml(item.title)}</h2>
							<a href="#" class="banner-link discord-link"
							   data-guild="${guildId}"
							   data-channel="${item.channel_id}"
							   data-thread="${item.thread_id}">
								查看详情 →
							</a>
						</div>
					</div>
				</div>
			`).join('');
	
			const indicatorsHtml = state.bannerCarousel.length > 1
				? state.bannerCarousel.map((_, idx) => `
					<button type="button"
							class="banner-indicator${idx === state.currentBannerIndex ? ' active' : ''}"
							data-index="${idx}"
							aria-label="切换到第 ${idx + 1} 个 Banner"
							${idx === state.currentBannerIndex ? 'aria-current="true"' : 'aria-current="false"'}>
					</button>
				`).join('')
				: '';
	
			bannerSection.innerHTML = `
				<div class="banner-container">
					<div class="banner-track">
						${slidesHtml}
					</div>
					${state.bannerCarousel.length > 1 ? `
					<div class="banner-controls">
						<button class="banner-nav-btn banner-prev" aria-label="上一个" type="button">‹</button>
						<button class="banner-nav-btn banner-next" aria-label="下一个" type="button">›</button>
					</div>
					<div class="banner-indicators">
						${indicatorsHtml}
					</div>
					` : ''}
				</div>
			`;
	
			track = bannerSection.querySelector('.banner-track');
	
			if(state.bannerCarousel.length > 1){
				const prevBtn = bannerSection.querySelector('.banner-prev');
				const nextBtn = bannerSection.querySelector('.banner-next');
	
				if(prevBtn){
					prevBtn.addEventListener('click', () => navigateBanner(-1));
				}
	
				if(nextBtn){
					nextBtn.addEventListener('click', () => navigateBanner(1));
				}
	
				bannerSection.querySelectorAll('.banner-indicator').forEach(indicator => {
					indicator.addEventListener('click', (e) => {
						const index = parseInt(e.currentTarget.getAttribute('data-index'));
						if(!isNaN(index) && index !== state.currentBannerIndex){
							state.currentBannerIndex = index;
							renderBanner();
						}
					});
				});
			}
	
			bannerSection.querySelectorAll('.discord-link').forEach(link => {
				link.addEventListener('click', (e) => {
					e.preventDefault();
					const target = e.currentTarget;
					const guild = target.getAttribute('data-guild');
					const channel = target.getAttribute('data-channel');
					const thread = target.getAttribute('data-thread');
					openDiscordLink(guild, channel, thread);
				});
			});
		}
	
		if(track){
			track.style.transform = `translateX(-${state.currentBannerIndex * 100}%)`;
		}
	
		bannerSection.querySelectorAll('.banner-slide').forEach((slide, idx) => {
			const isActive = idx === state.currentBannerIndex;
			slide.classList.toggle('is-active', isActive);
			slide.setAttribute('aria-hidden', isActive ? 'false' : 'true');
		});
	
		bannerSection.querySelectorAll('.banner-indicator').forEach((indicator, idx) => {
			const isActive = idx === state.currentBannerIndex;
			indicator.classList.toggle('active', isActive);
			indicator.setAttribute('aria-current', isActive ? 'true' : 'false');
		});
	
		if(state.bannerCarousel.length > 1){
			state.bannerAutoPlay = setInterval(() => navigateBanner(1), 5000);
		}
	}
	
	function updateBannerVisibility(){
		const bannerSection = document.getElementById('bannerCarousel');
		if(!bannerSection) return;
	
		if(state.viewMode === 'follows'){
			bannerSection.classList.add('hidden');
			if(state.bannerAutoPlay){
				clearInterval(state.bannerAutoPlay);
				state.bannerAutoPlay = null;
			}
		}else{
			bannerSection.classList.remove('hidden');
			renderBanner();
		}
	}
	
	function navigateBanner(direction){
		if(state.bannerCarousel.length === 0) return;
		
		state.currentBannerIndex += direction;
		
		// 循环处理
		if(state.currentBannerIndex < 0){
			state.currentBannerIndex = state.bannerCarousel.length - 1;
		}else if(state.currentBannerIndex >= state.bannerCarousel.length){
			state.currentBannerIndex = 0;
		}
		
		renderBanner();
	}

	/** 检查认证 **/
	async function checkAuth(){
		try{
			const res = await fetch(window.AUTH_URL + '/auth/checkauth', {
				credentials:'include',
				headers: authHeaders()
			});
			if(res && res.ok){
				const data = await res.json();
				state.authed = data.loggedIn !== false;
				state.user = data.user || null;
				state.unreadCount = data.unread_count || 0;
				
				// 更新未读徽章
				updateUnreadBadge();
				
				// 更新用户信息显示
				if(state.user){
					el.userName.textContent = state.user.global_name || state.user.username || '用户';
					if(state.user.avatar){
						const avatarUrl = `https://cdn.discordapp.com/avatars/${state.user.id}/${state.user.avatar}.png?size=128`;
						el.userAvatar.src = avatarUrl;
						el.userAvatar.alt = state.user.username;
					} else {
						el.userAvatar.src = `https://cdn.discordapp.com/embed/avatars/${(parseInt(state.user.id) >> 22) % 6}.png`;
					}
				} else {
					// 未登录时显示默认状态
					el.userName.textContent = '未登录';
					el.userAvatar.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Ccircle cx="50" cy="50" r="50" fill="%23333"%3E%3C/circle%3E%3Ctext x="50" y="65" font-size="50" text-anchor="middle" fill="%23999"%3E?%3C/text%3E%3C/svg%3E';
					el.userAvatar.alt = '未登录';
				}
			}else{
				state.authed = false;
				// 未登录时显示默认状态
				el.userName.textContent = '未登录';
				el.userAvatar.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Ccircle cx="50" cy="50" r="50" fill="%23333"%3E%3C/circle%3E%3Ctext x="50" y="65" font-size="50" text-anchor="middle" fill="%23999"%3E?%3C/text%3E%3C/svg%3E';
				el.userAvatar.alt = '未登录';
			}
		}catch(e){
			console.error('检查认证失败:', e);
			state.authed = false;
			el.userName.textContent = '未登录';
			el.userAvatar.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"%3E%3Ccircle cx="50" cy="50" r="50" fill="%23333"%3E%3C/circle%3E%3Ctext x="50" y="65" font-size="50" text-anchor="middle" fill="%23999"%3E?%3C/text%3E%3C/svg%3E';
			el.userAvatar.alt = '未登录';
		}
	}

	/** 启动 **/
	(async function init(){
		readFromURL();
		await checkAuth();
		await initChannels();
		hydrateControls();
		updateBannerVisibility();
		
		if(state.authed){
			// 根据viewMode决定初始加载内容
			if(state.viewMode === 'follows'){
				// 切换到关注列表面板
				switchPanel('follows');
			} else {
				await fetchSearchResults();
			}
		}else{
			render();
		}
		
		bindEvents();
	})();
})();
