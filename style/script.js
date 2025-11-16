const app = {
	state: {
		token: localStorage.getItem('auth_token'),
		user: null,
		view: 'search',
		channelId: null,
		query: '',
		dateStart: null, dateEnd: null,
		sortMethod: 'comprehensive', sortOrder: 'desc',
		limit: 20,
		tagMode: 'include', tagLogic: 'and',
		includedTags: new Set(), excludedTags: new Set(), availableTags: [],
		results: [], banners: [], totalResults: 0, unreadCount: 0,
		isLoading: false, sidebarOpen: false,
		failedImages: null, imageRefreshTimer: null, isRefreshingImages: false
	},

	init() {
		this.handleAuthHash();
		this.renderChannels();
		this.renderUserArea();
		this.setupEventListeners();
		if (this.state.token) this.checkAuth();
		this.executeSearch();
		window.addEventListener('resize', () => { if (window.innerWidth >= 768) this.toggleSidebar(false); });
	},

	// --- Mobile Detail Overlay Logic ---
	openMobileDetail(post) {
		if (window.innerWidth >= 768) return; // Desktop uses hover

		const overlay = document.getElementById('mobile-detail-overlay');
		const card = document.getElementById('mobile-detail-card');

		// Generate Full Content
		const user = post.author || {};
		const authorAvatar = user.avatar ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` : `https://cdn.discordapp.com/embed/avatars/0.png`;
		const coverImg = post.thumbnail_url || `https://placehold.co/600x400/2f3136/72767d?text=No+Image`;
		const webLink = `https://discord.com/channels/${window.GUILD_ID || '@me'}/${post.channel_id}/${post.thread_id}`;
		const appLink = `discord://discord.com/channels/${window.GUILD_ID || '@me'}/${post.channel_id}/${post.thread_id}`;
		const authorDisplayName = user.global_name || user.username || 'Unknown';
		const authorUsername = user.username || '';
		const encodedAuthorUsername = encodeURIComponent(authorUsername);
		const authorNameHtml = authorUsername
			? `<span class="text-xs text-discord-primary truncate max-w-[80px] cursor-pointer hover:text-white transition-colors" data-username="${encodedAuthorUsername}" onclick="app.handleAuthorClick(event, this.dataset.username)">${authorDisplayName}</span>`
			: `<span class="text-xs text-gray-400 truncate max-w-[80px]">${authorDisplayName}</span>`;

		card.innerHTML = `
                    <!-- Top: Close Button -->
                    <button class="absolute top-3 right-3 z-20 bg-black/50 text-white rounded-full p-1.5 backdrop-blur-sm" onclick="app.closeMobileDetail()">
                        <span class="material-symbols-outlined text-lg">close</span>
                    </button>
                    
                    <!-- 1. Image Section (Prioritized, Contain Mode) -->
                    <div class="card-image-container w-full relative flex-shrink-0 border-b border-white/10">
                        <img src="${coverImg}" class="card-img w-full h-full object-contain" onerror="app.handleImageError(event, '${post.thread_id}', '${post.channel_id || ""}')">
                    </div>

                    <!-- 2. Scrollable Content -->
                    <div class="content-scroll-area">
                        <div class="flex flex-wrap gap-1.5 mb-3">
                             ${(post.tags || []).map(t => `<span class="text-[10px] bg-discord-sidebar text-discord-muted px-2 py-1 rounded border border-white/5">#${t}</span>`).join('')}
                        </div>
                        <h3 class="text-white font-bold text-lg mb-3 leading-snug">${post.title}</h3>
                        <div class="md-content text-sm text-gray-300 mb-6">
                            ${this.parseMarkdown(post.first_message_excerpt, true)}
                        </div>
                    </div>

                    <!-- 3. Fixed Bottom Actions (Button Row) -->
                    <div class="p-4 border-t border-white/10 bg-discord-element flex items-center justify-between flex-shrink-0">
                        <div class="flex items-center gap-2">
                            <img src="${authorAvatar}" class="w-6 h-6 rounded-full">
                            ${authorNameHtml}
                        </div>
                        <div class="flex items-center gap-2">
                            <a href="${appLink}" class="bg-discord-primary text-white px-3 py-1.5 rounded text-xs font-bold flex items-center gap-1 shadow">
                                <span class="material-symbols-outlined text-xs">open_in_new</span> APP
                            </a>
                            <a href="${webLink}" target="_blank" class="bg-discord-sidebar text-white px-3 py-1.5 rounded text-xs font-bold flex items-center gap-1 border border-white/10">
                                <span class="material-symbols-outlined text-xs">public</span> WEB
                            </a>
                        </div>
                    </div>
                `;

		overlay.classList.remove('hidden');
		// Trigger Reflow
		void overlay.offsetWidth;
		overlay.classList.add('active');
		document.body.style.overflow = 'hidden'; // Lock background scroll
	},

	closeMobileDetail(e) {
		if (e) e.stopPropagation();
		const overlay = document.getElementById('mobile-detail-overlay');
		overlay.classList.remove('active');
		setTimeout(() => {
			overlay.classList.add('hidden');
			document.body.style.overflow = '';
		}, 300);
	},

	// --- Render Results (Grid) ---
	renderResults() {
		const grid = document.getElementById('results-grid');
		document.getElementById('loading-spinner').classList.add('hidden');
		document.getElementById('result-stats').innerText = `找到 ${this.state.totalResults} 结果`;
		document.getElementById('load-more-btn').classList.toggle('hidden', this.state.results.length >= this.state.totalResults || this.state.results.length === 0);

		if (!this.state.results.length) {
			grid.innerHTML = `<div class="col-span-full text-center py-12 text-discord-muted"><span class="material-symbols-outlined text-5xl mb-4 opacity-50">search_off</span><p>没有找到相关帖子</p></div>`;
			return;
		}

		grid.innerHTML = this.state.results.map((post, index) => {
			// Store post data in DOM for easy retrieval
			const postJson = encodeURIComponent(JSON.stringify(post));

			const user = post.author || {};
			const authorName = user.global_name || user.username || "Unknown";
			const authorAvatar = user.avatar ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` : `https://cdn.discordapp.com/embed/avatars/0.png`;
			const authorUsername = user.username || "";
			const encodedAuthorUsername = encodeURIComponent(authorUsername);
			const authorLabelHtml = authorUsername
				? `<span class="text-[10px] text-discord-primary truncate max-w-[60px] cursor-pointer hover:text-white transition-colors" data-username="${encodedAuthorUsername}" onclick="app.handleAuthorClick(event, this.dataset.username)">${authorName}</span>`
				: `<span class="text-[10px] text-gray-400 truncate max-w-[60px]">${authorName}</span>`;
			const coverImg = post.thumbnail_url || `https://placehold.co/600x300/2f3136/72767d?text=No+Image`;
			const webLink = `https://discord.com/channels/${window.GUILD_ID || '@me'}/${post.channel_id}/${post.thread_id}`;
			const appLink = `discord://discord.com/channels/${window.GUILD_ID || '@me'}/${post.channel_id}/${post.thread_id}`;

			let badgeHtml = (this.state.view === 'follows' && post.has_update) ? `<span class="absolute top-2 right-2 bg-discord-red text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-md z-20">NEW</span>` : '';

			// Desktop Hover Action Buttons
			const desktopActions = `
                        <div class="desktop-actions hidden gap-2 mt-3 pt-3 border-t border-white/10 justify-end">
                             <a href="${appLink}" class="bg-discord-primary hover:bg-discord-hover text-white px-3 py-1 rounded text-xs font-bold transition-colors">APP</a>
                             <a href="${webLink}" target="_blank" class="bg-discord-sidebar hover:bg-gray-700 text-white px-3 py-1 rounded text-xs font-bold border border-white/10 transition-colors">WEB</a>
                        </div>
                    `;

			return `
                    <div class="card-wrapper" onclick='app.openMobileDetail(JSON.parse(decodeURIComponent("${postJson}")))' style="--stack-index: ${20 - (index % 10)};"> <!-- Decreasing z-index for stacking context safety -->
                        <div class="card-inner group cursor-pointer">
                            ${badgeHtml}
                            <!-- Image -->
                            <div class="card-image-container overflow-hidden">
                                <img src="${coverImg}" class="card-img" onerror="app.handleImageError(event, '${post.thread_id}', '${post.channel_id || ""}')">
                            </div>
                            
                            <!-- Content -->
                            <div class="p-3 md:p-4 flex flex-col flex-1 min-h-0 bg-[#202225]">
                                <div class="flex flex-wrap gap-1 mb-2 flex-shrink-0">
                                    ${(post.tags || []).slice(0, 2).map(t => `<span class="text-[10px] bg-discord-sidebar text-discord-muted px-1.5 py-0.5 rounded border border-white/5">#${t}</span>`).join('')}
                                </div>

                                <h3 class="text-white font-bold text-sm md:text-base leading-tight mb-2 line-clamp-2 group-hover:text-discord-primary transition-colors">
                                    ${post.title}
                                </h3>
                                
                                <div class="md-content text-xs text-discord-muted mb-2 line-clamp-3 flex-1">
                                    ${this.parseMarkdown(post.first_message_excerpt)}
                                </div>

                                <!-- Footer Info -->
                                <div class="flex items-center justify-between pt-2 border-t border-white/5 mt-auto opacity-80 flex-shrink-0">
                                    <div class="flex items-center gap-2">
                                        <img src="${authorAvatar}" class="w-4 h-4 rounded-full">
                                        ${authorLabelHtml}
                                    </div>
                                    <div class="flex items-center gap-2 text-discord-muted text-[10px]">
                                        <span class="flex items-center gap-0.5"><span class="material-symbols-outlined text-[12px]">chat</span> ${post.reply_count}</span>
                                        <span class="flex items-center gap-0.5"><span class="material-symbols-outlined text-[12px]">favorite</span> ${post.reaction_count}</span>
                                    </div>
                                </div>
                                ${desktopActions}
                            </div>
                        </div>
                    </div>
                    `;
		}).join('');
	},

	// --- Helpers ---
	toggleSidebar(show) {
		this.state.sidebarOpen = show;
		const sidebar = document.getElementById('sidebar');
		const backdrop = document.getElementById('sidebar-backdrop');
		if (show) {
			sidebar.classList.remove('-translate-x-full');
			backdrop.classList.remove('hidden');
			setTimeout(() => backdrop.classList.remove('opacity-0'), 10);
		} else {
			sidebar.classList.add('-translate-x-full');
			backdrop.classList.add('opacity-0');
			setTimeout(() => backdrop.classList.add('hidden'), 300);
		}
	},

	handleAuthHash() {
		const m = location.hash.match(/[#&]token=([^&]+)/);
		if (m) { localStorage.setItem('auth_token', m[1]); location.hash = ''; }
	},

	async fetchAPI(endpoint, method, body) {
		const h = { 'Content-Type': 'application/json' };
		if (this.state.token) h['Authorization'] = `Bearer ${this.state.token}`;
		try {
			const r = await fetch(`${window.AUTH_URL}${endpoint}`, { method, headers: h, body: body ? JSON.stringify(body) : null });
			if (r.status === 401) { this.logout(false); return null; }
			if (r.status === 204) return null;
			if (!r.ok) throw new Error(r.status);
			return await r.json();
		} catch (e) {
			if (endpoint.includes('/search') && this.state.results.length === 0) return this.getMockData();
			return null;
		}
	},

	async executeSearch(reset = true) {
		if (reset) { this.state.results = []; }
		this.state.isLoading = true;
		this.renderResults(); // Render partial/loading state
		document.getElementById('loading-spinner').classList.remove('hidden');

		const excludeThreadIds = this.collectLoadedThreadIds();

		const body = {
			channel_ids: this.state.channelId ? [this.state.channelId] : null,
			include_tags: Array.from(this.state.includedTags),
			exclude_tags: Array.from(this.state.excludedTags),
			tag_logic: this.state.tagLogic,
			keywords: document.getElementById('search-input').value || null,
			created_after: document.getElementById('date-start').value || null,
			created_before: document.getElementById('date-end').value || null,
			sort_method: document.getElementById('sort-method').value,
			sort_order: this.state.sortOrder,
			limit: this.state.limit
		};

		if (excludeThreadIds.length) {
			body.exclude_thread_ids = excludeThreadIds;
		}

		const data = await this.fetchAPI('/search', 'POST', body);
		if (data) {
			const incomingResults = Array.isArray(data.results) ? data.results : [];
			const existingIds = reset ? new Set() : new Set(this.state.results.map(post => String(post.thread_id)));
			const dedupedIncoming = incomingResults.filter(post => {
				const id = String(post.thread_id);
				if (!id || existingIds.has(id)) {
					return false;
				}
				existingIds.add(id);
				return true;
			});

			this.state.results = reset ? dedupedIncoming : [...this.state.results, ...dedupedIncoming];
			this.state.totalResults = data.total;
			this.state.availableTags = data.available_tags || [];
			if (reset && data.banner_carousel) this.state.banners = data.banner_carousel;
		}

		this.state.isLoading = false;
		this.renderResults();
		if (this.state.view === 'search') { this.renderTags(); if (reset) this.renderBanner(); }
		if (window.innerWidth < 768) this.toggleSidebar(false);
	},

	loadMore() {
		if (this.state.isLoading) return;
		if (this.state.results.length >= this.state.totalResults) return;
		this.executeSearch(false);
	},

	handleContentScroll() {
		const container = document.getElementById('content-scroll');
		if (!container) return;
		if (this.state.isLoading) return;
		if (!this.state.results.length) return;
		if (this.state.results.length >= this.state.totalResults) return;

		const { scrollTop, clientHeight, scrollHeight } = container;
		const threshold = 200;
		if (scrollTop + clientHeight >= scrollHeight - threshold) {
			this.loadMore();
		}
	},

	handleAuthorClick(event, encodedUsername) {
		if (event) event.stopPropagation();
		if (!encodedUsername) return;

		let username = '';
		try {
			username = decodeURIComponent(encodedUsername);
		} catch (err) {
			username = encodedUsername;
		}
		this.applyAuthorSearch(username);
	},

	applyAuthorSearch(username) {
		const normalized = (username || '').trim();
		if (!normalized) return;

		const searchInput = document.getElementById('search-input');
		if (searchInput) {
			searchInput.value = `author:${normalized}`;
		}

		this.state.includedTags.clear();
		this.state.excludedTags.clear();

		if (window.innerWidth < 768) {
			this.closeMobileDetail();
		}

		if (this.state.view !== 'search') {
			this.switchView('search');
			return;
		}

		this.renderTags();
		this.executeSearch();
	},

	renderTags() {
		const container = document.getElementById('tag-cloud');
		const tags = new Set([...this.state.availableTags, ...this.state.includedTags, ...this.state.excludedTags]);
		if (!tags.size) { container.innerHTML = ''; return; }
		container.innerHTML = Array.from(tags).map(t => {
			let cls = "bg-discord-element border border-transparent text-discord-muted hover:border-gray-500";
			let icon = "";
			if (this.state.includedTags.has(t)) { cls = "tag-include border"; icon = "check"; }
			else if (this.state.excludedTags.has(t)) { cls = "tag-exclude border"; icon = "block"; }
			return `<button onclick="app.handleTagClick('${t}')" class="tag-pill text-xs px-2 py-1 rounded flex items-center gap-1 ${cls}">${icon ? `<span class="material-symbols-outlined text-[12px]">${icon}</span>` : ''}#${t}</button>`;
		}).join('');
	},

	handleTagClick(tag) {
		if (this.state.includedTags.has(tag) || this.state.excludedTags.has(tag)) { this.state.includedTags.delete(tag); this.state.excludedTags.delete(tag); }
		else { this.state.tagMode === 'include' ? this.state.includedTags.add(tag) : this.state.excludedTags.add(tag); }
		this.renderTags(); this.executeSearch();
	},

	setTagMode(m) { this.state.tagMode = m; this.renderTags(); /* Update UI classes omitted for brevity */ },
	setTagLogic(l) { this.state.tagLogic = l; this.executeSearch(); },

	renderChannels() {
		const container = document.getElementById('channel-list-container');
		let html = '';

		// Add "All Channels" button
		const isGlobal = this.state.channelId === null;
		html += `
	           <div class="space-y-1 pb-4">
	               <button onclick="app.selectChannel('global')" class="w-full flex items-center gap-3 px-3 py-2 rounded hover:bg-discord-element transition-colors text-left ${isGlobal ? 'bg-discord-element text-white font-bold' : 'text-discord-muted'}">
	                   <span class="material-symbols-outlined text-sm">apps</span> 全部频道
	               </button>
	           </div>
	       `;

		// Iterate categories
		if (window.CHANNEL_CATEGORIES) {
			window.CHANNEL_CATEGORIES.forEach(category => {
				html += `<div class="mt-4 mb-2 px-3 text-xs font-bold text-discord-muted uppercase">${category.name}</div>`;
				html += `<div class="space-y-1">`;
				category.channels.forEach(c => {
					const isActive = this.state.channelId === c.id;
					const icon = c.icon || 'chat_bubble';
					html += `
	                   <button onclick="app.selectChannel('${c.id}')" class="w-full flex items-center gap-3 px-3 py-2 rounded hover:bg-discord-element transition-colors text-left ${isActive ? 'bg-discord-element text-white font-bold' : 'text-discord-muted'}">
	                       <span class="material-symbols-outlined text-sm">${icon}</span> ${c.name}
	                   </button>`;
				});
				html += `</div>`;
			});
		}

		container.innerHTML = html;
	},
	selectChannel(id) { this.state.channelId = id === 'global' ? null : id; this.renderChannels(); this.executeSearch(); },

	renderUserArea() {
		const el = document.getElementById('user-area');
		if (this.state.user) {
			const url = this.state.user.avatar ? `https://cdn.discordapp.com/avatars/${this.state.user.id}/${this.state.user.avatar}.png` : `https://cdn.discordapp.com/embed/avatars/0.png`;
			el.innerHTML = `<img src="${url}" class="w-8 h-8 rounded-full"><div class="flex-1 min-w-0"><div class="text-xs font-bold text-white truncate">${this.state.user.global_name}</div></div><button onclick="app.logout()" class="text-muted"><span class="material-symbols-outlined">logout</span></button>`;
		} else { el.innerHTML = `<button onclick="app.login()" class="w-full bg-discord-primary text-white py-2 rounded text-sm">Discord 登录</button>`; }
	},
	login() { window.location.href = `${window.AUTH_URL}/auth/login`; },
	logout(r = true) { localStorage.removeItem('auth_token'); this.state.user = null; this.renderUserArea(); if (r) window.location.href = `${window.AUTH_URL}/auth/logout`; },

	renderBanner() {
		const el = document.getElementById('banner-section');
		if (!this.state.banners.length) { el.classList.add('hidden'); return; }
		el.classList.remove('hidden');
		document.getElementById('banner-slides').innerHTML = `<img src="${this.state.banners[0].cover_image_url}" class="w-full h-full object-cover opacity-80">`;
		document.getElementById('banner-title').innerText = this.state.banners[0].title;
	},

	switchView(v) {
		this.state.view = v;
		document.getElementById('nav-search').className = v === 'search' ? 'w-full flex items-center gap-3 px-3 py-2 rounded bg-discord-element text-white' : 'w-full flex items-center gap-3 px-3 py-2 rounded hover:bg-discord-element text-discord-muted';
		document.getElementById('nav-follows').className = v === 'follows' ? 'w-full flex items-center gap-3 px-3 py-2 rounded bg-discord-element text-white relative' : 'w-full flex items-center gap-3 px-3 py-2 rounded hover:bg-discord-element text-discord-muted relative';
		document.getElementById('banner-section').classList.toggle('hidden', v !== 'search');
		document.getElementById('tags-section').classList.toggle('hidden', v !== 'search');
		document.getElementById('view-title').innerText = v === 'search' ? '搜索结果' : '关注列表';
		this.executeSearch();
	},

	checkAuth() { this.fetchAPI('/auth/checkauth', 'GET').then(d => { if (d && d.loggedIn) { this.state.user = d.user; this.renderUserArea(); } }); },
	toggleSortOrder() { this.state.sortOrder = this.state.sortOrder === 'asc' ? 'desc' : 'asc'; this.executeSearch(); },
	setupEventListeners() {
		let typingTimer;
		const searchInput = document.getElementById('search-input');
		if (searchInput) {
			searchInput.addEventListener('input', () => {
				clearTimeout(typingTimer);
				typingTimer = setTimeout(() => this.executeSearch(), 600);
			});
		}
		const contentScroll = document.getElementById('content-scroll');
		if (contentScroll) {
			contentScroll.addEventListener('scroll', () => this.handleContentScroll());
		}
	},

	parseMarkdown(text, expanded = false) {
		if (!text) return "";
		let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
			.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
			.replace(/`([^`]+)`/g, '<code>$1</code>')
			.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>')
			.replace(/\n/g, '<br>');
		if (expanded) {
			html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>').replace(/^## (.*$)/gim, '<h2>$1</h2>');
		}
		return html;
	},

	collectLoadedThreadIds() {
		if (!this.state.results || !this.state.results.length) return [];
		const ids = new Set();
		this.state.results.forEach(post => {
			const rawId = post?.thread_id ?? null;
			if (rawId === null || rawId === undefined) return;
			const normalized = rawId.toString();
			if (normalized.trim().length === 0) return;
			ids.add(normalized);
		});
		return Array.from(ids);
	},

	getMockData() {
		const r = [];
		const imgs = ['https://placehold.co/800x400/202225/5865F2?text=Update+v2.0', 'https://placehold.co/600x800/36393f/3ba55c?text=Mobile+UI', 'https://placehold.co/1200x600/000/fff?text=Screenshot'];
		for (let i = 0; i < 12; i++) {
			r.push({
				thread_id: `mock-${i}`, channel_id: "1001", author_id: "u1",
				title: i % 2 === 0 ? "Discord 门户设计规范讨论 (v3.0 更新)" : "这是一个标题很长很长的测试帖子用于检测换行和截断效果",
				thumbnail_url: imgs[i % imgs.length],
				first_message_excerpt: `这里是测试内容。包含 **粗体**, \`代码\`, 以及 [链接](https://discord.com)。\n\n第二行内容。\n> 引用文本效果`,
				created_at: new Date().toISOString(), reply_count: 12, reaction_count: 34,
				tags: ['design', 'ui', 'fix'], author: { username: "User" + i, global_name: "Designer " + i }
			});
		}
		return { results: r, total: 99, available_tags: ['ui', 'design', 'code'], banner_carousel: [{ title: "Welcome", cover_image_url: "https://placehold.co/1200x400/202225/5865F2" }] };
	},

	handleImageError(event, threadId, channelId) {
		const imgElement = event.target;
		imgElement.onerror = null;
		imgElement.src = 'https://placehold.co/600x300/2f3136/72767d?text=Image+Loading...';
		this.scheduleThumbnailRefresh({ thread_id: threadId, channel_id: channelId || null }, imgElement);
	},

	scheduleThumbnailRefresh(item, imgElement) {
		if (!this.state.failedImages) this.initializeImageRecovery();
		const key = String(item.thread_id);
		const entry = this.state.failedImages.get(key);
		if (entry) {
			entry.elements.add(imgElement);
		} else {
			this.state.failedImages.set(key, { item, elements: new Set([imgElement]) });
		}
	},

	initializeImageRecovery() {
		if (!this.state.failedImages) {
			this.state.failedImages = new Map();
		}
		if (!this.state.imageRefreshTimer) {
			this.state.imageRefreshTimer = setInterval(() => this.flushImageRecoveryQueue(), 5000);
			window.addEventListener('beforeunload', () => {
				if (this.state.imageRefreshTimer) clearInterval(this.state.imageRefreshTimer);
			});
		}
	},

	cleanupImageRecoveryTimer() {
		if (this.state.failedImages && this.state.failedImages.size === 0 && this.state.imageRefreshTimer) {
			clearInterval(this.state.imageRefreshTimer);
			this.state.imageRefreshTimer = null;
		}
	},

	async flushImageRecoveryQueue() {
		if (!this.state.failedImages || this.state.failedImages.size === 0 || this.state.isRefreshingImages) {
			this.cleanupImageRecoveryTimer();
			return;
		}

		const batchEntries = Array.from(this.state.failedImages.entries()).slice(0, 10);
		batchEntries.forEach(([key]) => this.state.failedImages.delete(key));

		const payload = {
		    items: batchEntries.map(([key, entry]) => {
		        const channelValue = entry.item.channel_id;
		        return {
		            thread_id: entry.item.thread_id,
		            channel_id: channelValue !== undefined && channelValue !== null && channelValue !== '' ? channelValue : undefined,
		        };
		    }),
		};

		this.state.isRefreshingImages = true;
		const response = await this.fetchAPI('/fetch-images', 'POST', payload);
		this.state.isRefreshingImages = false;

		if (!response || !Array.isArray(response.results)) {
		    batchEntries.forEach(([key, entry]) => {
		        this.state.failedImages.set(key, entry);
		        entry.elements.forEach(img => {
		            if (!img.dataset.retried) {
		                img.dataset.retried = 'true';
		                img.src = 'https://placehold.co/600x300/2f3136/72767d?text=Retrying...';
		            } else {
		                img.src = 'https://placehold.co/600x300/000/fff?text=Image+Error';
		            }
		        });
		    });
		    this.cleanupImageRecoveryTimer();
		    return;
		}

		const responseMap = new Map(response.results.map(item => [String(item.thread_id), item]));

		batchEntries.forEach(([, entry]) => {
			const key = String(entry.item.thread_id);
			const result = responseMap.get(key);
			entry.elements.forEach(img => {
				if (result && result.thumbnail_url) {
					img.src = result.thumbnail_url;
					this.updateLocalThumbnail(key, result.thumbnail_url);
				} else {
					img.src = 'https://placehold.co/600x300/000/fff?text=Image+Error';
				}
			});
			if (!result || !result.thumbnail_url) {
				this.state.failedImages.set(key, entry);
			}
		});

		this.cleanupImageRecoveryTimer();
	},

	updateLocalThumbnail(threadId, thumbnailUrl) {
		const targetId = String(threadId);
		const result = this.state.results.find(post => String(post.thread_id) === targetId);
		if (result) {
			result.thumbnail_url = thumbnailUrl;
		}
	}
};

document.addEventListener('DOMContentLoaded', () => app.init());