const app = {
	state: {
		token: localStorage.getItem('auth_token'),
		user: null,
		view: 'search',
		channelId: null,
		query: '',
		dateStart: null, dateEnd: null,
		sortMethod: 'last_active', sortOrder: 'desc',
		limit: 20,
		tagMode: 'include', tagLogic: 'and',
		includedTags: new Set(), excludedTags: new Set(), availableTags: [],
		results: [], banners: [], totalResults: 0, unreadCount: 0,
		isLoading: false, sidebarOpen: false,
		failedImages: null, imageRefreshTimer: null, isRefreshingImages: false,
		followThreads: [], followTotal: 0, followFetched: false,
		followFetchLimit: 10000, followAvailableTags: [], followNeedsRefresh: false
	},
	markingFollows: false,

	getPrimaryThumbnail(post) {
		if (!post) return null;
		if (Array.isArray(post.thumbnail_urls) && post.thumbnail_urls.length) {
			return post.thumbnail_urls.find(url => typeof url === 'string' && url.length) || null;
		}
		if (typeof post.thumbnail_url === 'string' && post.thumbnail_url.length) {
			return post.thumbnail_url;
		}
		return null;
	},

	normalizeThumbnailList(thumbnailUrls) {
		if (Array.isArray(thumbnailUrls)) {
			return thumbnailUrls.filter(url => typeof url === 'string' && url.length);
		}
		if (typeof thumbnailUrls === 'string' && thumbnailUrls.length) {
			return [thumbnailUrls];
		}
		return [];
	},

	getPlaceholderImage(size = '600x300') {
		return `https://placehold.co/${size}/2f3136/72767d?text=No+Image`;
	},

	// 生成多图智能排版 HTML（用于卡片默认状态）
	renderMultiImageGrid(thumbnailUrls, threadId) {
		const urls = this.normalizeThumbnailList(thumbnailUrls);
		const count = urls.length;
		
		if (count === 0) {
			return `<img src="${this.getPlaceholderImage()}" class="card-img single-img" onerror="app.handleImageError(event, '${threadId}', '')">`;
		}
		
		if (count === 1) {
			return `<img src="${urls[0]}" class="card-img single-img" onerror="app.handleImageError(event, '${threadId}', '')">`;
		}
		
		if (count === 2) {
			return `
				<div class="multi-img-grid grid-2">
					<div class="img-cell"><img src="${urls[0]}" onerror="this.src='${this.getPlaceholderImage('300x300')}'"></div>
					<div class="img-cell"><img src="${urls[1]}" onerror="this.src='${this.getPlaceholderImage('300x300')}'"></div>
				</div>`;
		}
		
		if (count === 3) {
			return `
				<div class="multi-img-grid grid-3">
					<div class="img-cell img-main"><img src="${urls[0]}" onerror="this.src='${this.getPlaceholderImage('400x400')}'"></div>
					<div class="img-cell"><img src="${urls[1]}" onerror="this.src='${this.getPlaceholderImage('200x200')}'"></div>
					<div class="img-cell"><img src="${urls[2]}" onerror="this.src='${this.getPlaceholderImage('200x200')}'"></div>
				</div>`;
		}
		
		// 4张及以上：2x2网格，超过4张显示剩余数量
		const displayUrls = urls.slice(0, 4);
		const remaining = count - 4;
		
		return `
			<div class="multi-img-grid grid-4">
				${displayUrls.map((url, idx) => `
					<div class="img-cell${idx === 3 && remaining > 0 ? ' has-more' : ''}">
						<img src="${url}" onerror="this.src='${this.getPlaceholderImage('200x200')}'">
						${idx === 3 && remaining > 0 ? `<div class="more-overlay">+${remaining}</div>` : ''}
					</div>
				`).join('')}
			</div>`;
	},

	// 生成轮播组件 HTML（用于悬停展开/移动端详情）
	renderCarousel(thumbnailUrls, threadId, carouselId) {
		const urls = this.normalizeThumbnailList(thumbnailUrls);
		const count = urls.length;
		
		if (count === 0) {
			return `<img src="${this.getPlaceholderImage('600x400')}" class="card-img carousel-single" onerror="app.handleImageError(event, '${threadId}', '')">`;
		}
		
		if (count === 1) {
			return `<img src="${urls[0]}" class="card-img carousel-single" onerror="app.handleImageError(event, '${threadId}', '')">`;
		}
		
		const dotsHtml = urls.map((_, idx) => 
			`<button class="carousel-dot${idx === 0 ? ' active' : ''}" data-index="${idx}" onclick="app.goToSlide('${carouselId}', ${idx}, event)"></button>`
		).join('');
		
		return `
			<div class="carousel" id="${carouselId}" data-current="0" data-total="${count}">
				<div class="carousel-track">
					${urls.map((url, idx) => `
						<div class="carousel-slide${idx === 0 ? ' active' : ''}" data-index="${idx}">
							<img src="${url}" onerror="this.src='${this.getPlaceholderImage('600x400')}'">
						</div>
					`).join('')}
				</div>
				<button class="carousel-btn carousel-prev" onclick="app.prevSlide('${carouselId}', event)">
					<span class="material-symbols-outlined">chevron_left</span>
				</button>
				<button class="carousel-btn carousel-next" onclick="app.nextSlide('${carouselId}', event)">
					<span class="material-symbols-outlined">chevron_right</span>
				</button>
				<div class="carousel-dots">${dotsHtml}</div>
				<div class="carousel-counter">${1}/${count}</div>
			</div>`;
	},

	// 轮播控制函数
	goToSlide(carouselId, index, event) {
		if (event) event.stopPropagation();
		const carousel = document.getElementById(carouselId);
		if (!carousel) return;
		
		const total = parseInt(carousel.dataset.total);
		const slides = carousel.querySelectorAll('.carousel-slide');
		const dots = carousel.querySelectorAll('.carousel-dot');
		const counter = carousel.querySelector('.carousel-counter');
		
		// 更新当前索引
		carousel.dataset.current = index;
		
		// 更新slide显示
		slides.forEach((slide, i) => {
			slide.classList.toggle('active', i === index);
		});
		
		// 更新dots状态
		dots.forEach((dot, i) => {
			dot.classList.toggle('active', i === index);
		});
		
		// 更新计数器
		if (counter) {
			counter.textContent = `${index + 1}/${total}`;
		}
	},

	prevSlide(carouselId, event) {
		if (event) event.stopPropagation();
		const carousel = document.getElementById(carouselId);
		if (!carousel) return;
		
		const current = parseInt(carousel.dataset.current);
		const total = parseInt(carousel.dataset.total);
		const newIndex = (current - 1 + total) % total;
		this.goToSlide(carouselId, newIndex);
	},

	nextSlide(carouselId, event) {
		if (event) event.stopPropagation();
		const carousel = document.getElementById(carouselId);
		if (!carousel) return;
		
		const current = parseInt(carousel.dataset.current);
		const total = parseInt(carousel.dataset.total);
		const newIndex = (current + 1) % total;
		this.goToSlide(carouselId, newIndex);
	},

	resetFollowState() {
		this.state.followThreads = [];
		this.state.followTotal = 0;
		this.state.followFetched = false;
		this.state.followAvailableTags = [];
		this.state.followNeedsRefresh = true;
		if (this.state.view === 'follows') {
			this.state.results = [];
			this.state.totalResults = 0;
			this.renderResults();
		}
	},

	// --- URL 状态同步 ---
	saveStateToUrl() {
		const params = new URLSearchParams();
		
		// 视图模式
		if (this.state.view !== 'search') {
			params.set('view', this.state.view);
		}
		
		// 频道
		if (this.state.channelId) {
			params.set('channel', this.state.channelId);
		}
		
		// 搜索关键词
		const searchInput = document.getElementById('search-input');
		const query = searchInput?.value?.trim();
		if (query) {
			params.set('q', query);
		}
		
		// 日期范围
		const dateStart = document.getElementById('date-start')?.value;
		const dateEnd = document.getElementById('date-end')?.value;
		if (dateStart) params.set('from', dateStart);
		if (dateEnd) params.set('to', dateEnd);
		
		// 排序
		const sortMethod = document.getElementById('sort-method')?.value;
		if (sortMethod && sortMethod !== 'comprehensive') {
			params.set('sort', sortMethod);
		}
		if (this.state.sortOrder !== 'desc') {
			params.set('order', this.state.sortOrder);
		}
		
		// 标签
		if (this.state.includedTags.size > 0) {
			params.set('tags', Array.from(this.state.includedTags).join(','));
		}
		if (this.state.excludedTags.size > 0) {
			params.set('exclude', Array.from(this.state.excludedTags).join(','));
		}
		
		// 标签逻辑
		if (this.state.tagLogic !== 'and') {
			params.set('logic', this.state.tagLogic);
		}
		
		// 更新 URL（不刷新页面）
		const newUrl = params.toString() ? `${location.pathname}?${params}` : location.pathname;
		history.replaceState(null, '', newUrl);
	},

	loadStateFromUrl() {
		const params = new URLSearchParams(location.search);
		
		// 视图模式
		const view = params.get('view');
		if (view === 'follows') {
			this.state.view = 'follows';
		}
		
		// 频道
		const channel = params.get('channel');
		if (channel) {
			this.state.channelId = channel;
		}
		
		// 搜索关键词
		const query = params.get('q');
		if (query) {
			const searchInput = document.getElementById('search-input');
			if (searchInput) searchInput.value = query;
		}
		
		// 日期范围
		const dateStart = params.get('from');
		const dateEnd = params.get('to');
		if (dateStart) {
			const el = document.getElementById('date-start');
			if (el) el.value = dateStart;
		}
		if (dateEnd) {
			const el = document.getElementById('date-end');
			if (el) el.value = dateEnd;
		}
		
		// 排序
		const sortMethod = params.get('sort');
		if (sortMethod) {
			const el = document.getElementById('sort-method');
			if (el) el.value = sortMethod;
		}
		const sortOrder = params.get('order');
		if (sortOrder === 'asc') {
			this.state.sortOrder = 'asc';
		}
		
		// 标签
		const tags = params.get('tags');
		if (tags) {
			tags.split(',').filter(t => t.trim()).forEach(t => this.state.includedTags.add(t.trim()));
		}
		const exclude = params.get('exclude');
		if (exclude) {
			exclude.split(',').filter(t => t.trim()).forEach(t => this.state.excludedTags.add(t.trim()));
		}
		
		// 标签逻辑
		const logic = params.get('logic');
		if (logic === 'or') {
			this.state.tagLogic = 'or';
		}
	},
	updateFollowBadge() {
		const badge = document.getElementById('sidebar-badge');
		if (!badge) return;
		if (this.state.unreadCount > 0) {
			badge.textContent = Math.min(this.state.unreadCount, 99).toString();
			badge.classList.remove('hidden');
		} else {
			badge.classList.add('hidden');
		}
	},
	async refreshUnreadCount() {
		if (!this.state.token) {
			this.state.unreadCount = 0;
			this.updateFollowBadge();
			return;
		}
		const data = await this.fetchAPI('/follows/unread-count', 'GET');
		if (data && typeof data.unread_count === 'number') {
			this.state.unreadCount = data.unread_count;
		} else {
			this.state.unreadCount = 0;
		}
		this.updateFollowBadge();
	},
	async markFollowsViewed() {
		if (!this.state.token || this.markingFollows || this.state.unreadCount === 0) return;
		this.markingFollows = true;
		try {
			await this.fetchAPI('/follows/mark-viewed', 'POST', {});
			this.state.unreadCount = 0;
			this.updateFollowBadge();
			this.state.followThreads = this.state.followThreads.map(thread => ({
				...thread,
				has_update: false,
				last_viewed_at: new Date().toISOString()
			}));
		} catch (err) {
			console.warn('标记关注已读失败', err);
		} finally {
			this.markingFollows = false;
		}
	},

	async removeFollow(threadId, event) {
		if (event) event.stopPropagation();
		if (!this.state.token) return;
		
		try {
			const response = await this.fetchAPI(`/follows/${threadId}`, 'DELETE');
			if (response) {
				// 从本地列表中移除
				this.state.followThreads = this.state.followThreads.filter(
					t => String(t.thread_id) !== String(threadId)
				);
				this.state.followTotal = Math.max(0, this.state.followTotal - 1);
				
				// 如果当前在关注视图，更新显示
				if (this.state.view === 'follows') {
					this.applyFollowFilters();
					this.renderResults();
				}
				
				this.showToast('已取消关注');
			}
		} catch (err) {
			console.error('取消关注失败', err);
			this.showToast('取消关注失败');
		}
	},
	async fetchFollowThreads(force = false) {
		if (!this.state.token) {
			this.resetFollowState();
			return;
		}
		if (this.state.followFetched && !force && !this.state.followNeedsRefresh) {
			return;
		}
		const limit = this.state.followFetchLimit || 10000;
		try {
			const data = await this.fetchAPI(`/follows?limit=${limit}&offset=0`, 'GET');
			if (!data) return;
			const threads = Array.isArray(data.threads) ? data.threads : [];
			this.state.followThreads = threads.map(thread => ({
				...thread,
				thread_id: thread.thread_id != null ? String(thread.thread_id) : thread.thread_id,
				channel_id: thread.channel_id != null ? String(thread.channel_id) : thread.channel_id,
				tags: Array.isArray(thread.tags) ? thread.tags : []
			}));
			this.state.followTotal = data.total ?? this.state.followThreads.length;
			const tagSet = new Set();
			this.state.followThreads.forEach(t => (t.tags || []).forEach(tag => tagSet.add(tag)));
			this.state.followAvailableTags = Array.from(tagSet);
			this.state.followFetched = true;
			this.state.followNeedsRefresh = false;
		} catch (err) {
			console.error('获取关注列表失败', err);
			this.state.followNeedsRefresh = true;
		}
	},
	applyFollowFilters() {
		const threads = Array.isArray(this.state.followThreads) ? [...this.state.followThreads] : [];
		const searchInput = document.getElementById('search-input');
		const keywordRaw = (searchInput?.value || '').trim().toLowerCase();
		let authorQuery = null;
		const keywordTokens = [];
		if (keywordRaw.length) {
			keywordRaw.split(/\s+/).forEach(token => {
				if (token.startsWith('author:')) {
					authorQuery = token.slice(7);
				} else {
					keywordTokens.push(token);
				}
			});
		}
		const includeTags = Array.from(this.state.includedTags);
		const excludeTags = Array.from(this.state.excludedTags);
		const selectedChannel = this.state.channelId ? String(this.state.channelId) : null;
		const dateStartValue = document.getElementById('date-start')?.value || null;
		const dateEndValue = document.getElementById('date-end')?.value || null;
		const dateStart = dateStartValue ? new Date(dateStartValue) : null;
		const dateEnd = dateEndValue ? new Date(dateEndValue) : null;

		const filtered = threads.filter(thread => {
			const tags = Array.isArray(thread.tags) ? thread.tags : [];
			const matchesInclude = includeTags.length === 0
				|| (this.state.tagLogic === 'and'
					? includeTags.every(tag => tags.includes(tag))
					: includeTags.some(tag => tags.includes(tag)));
			if (!matchesInclude) return false;

			const matchesExclude = excludeTags.length === 0 || excludeTags.every(tag => !tags.includes(tag));
			if (!matchesExclude) return false;

			if (selectedChannel && String(thread.channel_id) !== selectedChannel) return false;

			const createdAt = thread.created_at ? new Date(thread.created_at) : null;
			if (dateStart && (!createdAt || createdAt < dateStart)) return false;
			if (dateEnd && (!createdAt || createdAt > dateEnd)) return false;

			if (authorQuery) {
				const author = thread.author || {};
				const authorName = (author.username || author.global_name || '').toLowerCase();
				if (!authorName.includes(authorQuery.toLowerCase())) return false;
			}

			if (keywordTokens.length) {
				const haystack = [
					thread.title,
					thread.first_message_excerpt,
					tags.join(' ')
				].join(' ').toLowerCase();
				const matchesKeywords = keywordTokens.every(token => haystack.includes(token));
				if (!matchesKeywords) return false;
			}

			return true;
		});

		const sortMethod = document.getElementById('sort-method')?.value || 'comprehensive';
		const sortOrder = this.state.sortOrder === 'asc' ? 'asc' : 'desc';
		filtered.sort((a, b) => {
			const va = this.getFollowSortValue(a, sortMethod);
			const vb = this.getFollowSortValue(b, sortMethod);
			return sortOrder === 'asc' ? va - vb : vb - va;
		});

		this.state.results = filtered;
		this.state.totalResults = filtered.length;
		if (this.state.view === 'follows') {
			this.renderTags();
		}
		return filtered;
	},
	getFollowSortValue(thread, method) {
		const createdAt = thread.created_at ? new Date(thread.created_at).getTime() : 0;
		const lastActive = thread.last_active_at ? new Date(thread.last_active_at).getTime() : createdAt;
		const latestUpdate = thread.latest_update_at ? new Date(thread.latest_update_at).getTime() : lastActive;
		switch (method) {
			case 'created_at':
				return createdAt;
			case 'last_active':
				return lastActive;
			case 'reply_count':
				return thread.reply_count ?? 0;
			case 'reaction_count':
				return thread.reaction_count ?? 0;
			default:
				return latestUpdate;
		}
	},

	init() {
		this.handleAuthHash();
		this.loadStateFromUrl(); // 从 URL 恢复状态
		this.renderChannels();
		this.renderUserArea();
		this.updateSortOrderIcon(); // 更新排序图标
		this.setupEventListeners();
		this.setupBannerScrollObserver(); // 设置banner滚动监听
		this.renderBannerScopeOptions(); // 渲染banner申请范围选项
		
		// 更新视图导航状态
		if (this.state.view === 'follows') {
			document.getElementById('nav-search').className = 'w-full flex items-center gap-3 px-3 py-2 rounded hover:bg-discord-element text-discord-muted';
			document.getElementById('nav-follows').className = 'w-full flex items-center gap-3 px-3 py-2 rounded bg-discord-element text-white relative';
			document.getElementById('banner-section').classList.add('hidden');
			document.getElementById('view-title').innerText = '关注列表';
		}
		
		// 恢复banner折叠状态
		if (this.bannerCollapsed) {
			document.getElementById('banner-section')?.classList.add('collapsed');
		}
		
		if (this.state.token) {
			this.checkAuth();
		} else {
			// 没有 token，跳转到登录页面
			this.redirectToLogin();
			return;
		}
		this.executeSearch();
		window.addEventListener('resize', () => { if (window.innerWidth >= 768) this.toggleSidebar(false); });
		window.addEventListener('popstate', () => {
			this.loadStateFromUrl();
			this.renderChannels();
			this.updateSortOrderIcon();
			this.executeSearch();
		});
	},

	renderBannerScopeOptions() {
		const scopeSelect = document.getElementById('banner-scope');
		if (!scopeSelect) return;
		
		// 清空现有选项
		scopeSelect.innerHTML = '<option value="">请选择展示范围</option>';
		
		// 添加全频道选项
		const globalOption = document.createElement('option');
		globalOption.value = 'global';
		globalOption.textContent = '🌐 全频道（最多3个）';
		scopeSelect.appendChild(globalOption);
		
		// 添加各频道选项
		if (window.CHANNEL_CATEGORIES) {
			window.CHANNEL_CATEGORIES.forEach(category => {
				const optgroup = document.createElement('optgroup');
				optgroup.label = category.name;
				
				category.channels.forEach(channel => {
					const option = document.createElement('option');
					option.value = channel.id;
					option.textContent = `📋 ${channel.name}（最多5个）`;
					optgroup.appendChild(option);
				});
				
				scopeSelect.appendChild(optgroup);
			});
		}
	},

	// --- Detail Overlay Logic (统一移动端和桌面端) ---
	openMobileDetail(post) {
		const overlay = document.getElementById('mobile-detail-overlay');
		const card = document.getElementById('mobile-detail-card');

		// Generate Full Content
		const user = post.author || {};
		const authorAvatar = user.avatar_url || (user.avatar ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` : `https://cdn.discordapp.com/embed/avatars/0.png`);
		
		// 关注列表优先使用 latest_update_link
		const defaultWebLink = `https://discord.com/channels/${window.GUILD_ID || '@me'}/${post.thread_id}`;
		const defaultAppLink = `discord://discord.com/channels/${window.GUILD_ID || '@me'}/${post.thread_id}`;
		const webLink = (this.state.view === 'follows' && post.latest_update_link) ? post.latest_update_link : defaultWebLink;
		const appLink = (this.state.view === 'follows' && post.latest_update_link) ? post.latest_update_link.replace('https://discord.com', 'discord://discord.com') : defaultAppLink;
		
		const authorDisplayName = user.global_name || user.name || user.username || 'Unknown';
		const authorUsername = user.name || user.username || '';
		const encodedAuthorUsername = encodeURIComponent(authorUsername);
		const authorNameHtml = authorUsername
			? `<span class="text-xs text-discord-primary truncate max-w-[80px] cursor-pointer hover:text-white transition-colors" data-username="${encodedAuthorUsername}" onclick="app.handleAuthorClick(event, this.dataset.username)">${authorDisplayName}</span>`
			: `<span class="text-xs text-gray-400 truncate max-w-[80px]">${authorDisplayName}</span>`;
		
		// 取消关注按钮（仅在关注列表视图显示）
		const unfollowBtn = this.state.view === 'follows'
			? `<button onclick="app.removeFollow('${post.thread_id}', event); app.closeMobileDetail();" class="bg-discord-red/20 hover:bg-discord-red text-discord-red hover:text-white px-3 py-1.5 rounded text-xs font-bold border border-discord-red/30 transition-colors flex items-center gap-1">
					<span class="material-symbols-outlined text-xs">remove_circle</span> 取消关注
			   </button>`
			: '';

		// 生成轮播组件
		const detailCarouselId = `detail-carousel-${post.thread_id}`;
		const carouselHtml = this.renderCarousel(post.thumbnail_urls, post.thread_id, detailCarouselId);

		card.innerHTML = `
                    <!-- Top: Close Button -->
                    <button class="absolute top-3 right-3 z-20 bg-black/50 text-white rounded-full p-1.5 backdrop-blur-sm" onclick="app.closeMobileDetail()">
                        <span class="material-symbols-outlined text-lg">close</span>
                    </button>
                    
                    <!-- 1. Image Section with Carousel -->
                    <div class="card-image-container detail-carousel-container w-full relative flex-shrink-0 border-b border-white/10">
                        ${carouselHtml}
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
                    <div class="p-4 border-t border-white/10 bg-discord-element flex flex-col gap-3 flex-shrink-0">
                        <div class="flex items-center justify-between">
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
                        ${unfollowBtn ? `<div class="flex justify-center">${unfollowBtn}</div>` : ''}
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
		const spinner = document.getElementById('loading-spinner');
		if (spinner) spinner.classList.add('hidden');
		document.getElementById('result-stats').innerText = `找到 ${this.state.totalResults} 结果`;
		const loadMoreBtn = document.getElementById('load-more-btn');
		if (loadMoreBtn) {
			const hideLoadMore = this.state.view !== 'search' || this.state.results.length === 0 || this.state.results.length >= this.state.totalResults;
			loadMoreBtn.classList.toggle('hidden', hideLoadMore);
		}

		if (!this.state.results.length) {
			grid.innerHTML = `<div class="col-span-full text-center py-12 text-discord-muted"><span class="material-symbols-outlined text-5xl mb-4 opacity-50">search_off</span><p>没有找到相关帖子</p></div>`;
			return;
		}

		grid.innerHTML = this.state.results.map((post, index) => {
			// Store post data in DOM for easy retrieval
			const postJson = encodeURIComponent(JSON.stringify(post));

			const user = post.author || {};
			const authorName = user.global_name || user.name || user.username || "Unknown";
			const authorAvatar = user.avatar_url || (user.avatar ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` : `https://cdn.discordapp.com/embed/avatars/0.png`);
			const authorUsername = user.name || user.username || "";
			const encodedAuthorUsername = encodeURIComponent(authorUsername);
			const authorLabelHtml = authorUsername
				? `<span class="text-[10px] text-discord-primary truncate max-w-[60px] cursor-pointer hover:text-white transition-colors" data-username="${encodedAuthorUsername}" onclick="app.handleAuthorClick(event, this.dataset.username)">${authorName}</span>`
				: `<span class="text-[10px] text-gray-400 truncate max-w-[60px]">${authorName}</span>`;
			
			// 关注列表优先使用 latest_update_link
			const defaultWebLink = `https://discord.com/channels/${window.GUILD_ID || '@me'}/${post.thread_id}`;
			const defaultAppLink = `discord://discord.com/channels/${window.GUILD_ID || '@me'}/${post.thread_id}`;
			const webLink = (this.state.view === 'follows' && post.latest_update_link) ? post.latest_update_link : defaultWebLink;
			const appLink = (this.state.view === 'follows' && post.latest_update_link) ? post.latest_update_link.replace('https://discord.com', 'discord://discord.com') : defaultAppLink;

			let badgeHtml = (this.state.view === 'follows' && post.has_update) ? `<span class="absolute top-2 right-2 bg-discord-red text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-md z-20">NEW</span>` : '';

			// 生成多图排版（默认状态）
			const multiImageHtml = this.renderMultiImageGrid(post.thumbnail_urls, post.thread_id);
			// 生成轮播（悬停状态，桌面端）
			const carouselId = `carousel-${post.thread_id}-${index}`;
			const carouselHtml = this.renderCarousel(post.thumbnail_urls, post.thread_id, carouselId);
			const imageCount = this.normalizeThumbnailList(post.thumbnail_urls).length;

			// Desktop Hover Action Buttons
			const unfollowBtn = this.state.view === 'follows' 
				? `<button onclick="app.removeFollow('${post.thread_id}', event)" class="bg-discord-red/20 hover:bg-discord-red text-discord-red hover:text-white px-3 py-1 rounded text-xs font-bold border border-discord-red/30 hover:border-discord-red transition-colors">取消关注</button>`
				: '';
			const desktopActions = `
                        <div class="desktop-actions hidden gap-2 mt-3 pt-3 border-t border-white/10 justify-end">
                             ${unfollowBtn}
                             <a href="${appLink}" class="bg-discord-primary hover:bg-discord-hover text-white px-3 py-1 rounded text-xs font-bold transition-colors">APP</a>
                             <a href="${webLink}" target="_blank" class="bg-discord-sidebar hover:bg-gray-700 text-white px-3 py-1 rounded text-xs font-bold border border-white/10 transition-colors">WEB</a>
                        </div>
                    `;

			return `
                    <div class="card-wrapper" onclick='app.openMobileDetail(JSON.parse(decodeURIComponent("${postJson}")))' style="--stack-index: ${20 - (index % 10)};"> <!-- Decreasing z-index for stacking context safety -->
                        <div class="card-inner group cursor-pointer">
                            ${badgeHtml}
                            <!-- Image Container with Multi-Image Grid (default) and Carousel (hover) -->
                            <div class="card-image-container overflow-hidden">
                            	<div class="card-img-default">${multiImageHtml}</div>
                            	<div class="card-img-hover">${carouselHtml}</div>
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
		console.log(m)
		if (m) {
			localStorage.setItem('auth_token', m[1]);
			location.hash = '';
			this.state.token = m[1];
			this.resetFollowState();
		}
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
			return null;
		}
	},

	async executeSearch(reset = true) {
		// 保存当前结果，以便请求失败时恢复
		const previousResults = this.state.results;
		const previousTotal = this.state.totalResults;
		
		if (reset) { this.state.results = []; }
		this.state.isLoading = true;
		this.renderResults(); // Render partial/loading state
		const spinner = document.getElementById('loading-spinner');
		if (spinner) spinner.classList.remove('hidden');

		if (this.state.view === 'follows') {
			await this.fetchFollowThreads();
			this.applyFollowFilters();
			await this.markFollowsViewed();
			this.state.isLoading = false;
			if (spinner) spinner.classList.add('hidden');
			this.renderResults();
			if (window.innerWidth < 768) this.toggleSidebar(false);
			if (reset) this.saveStateToUrl(); // 保存状态到 URL
			return;
		}

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
		} else if (reset) {
			// 请求失败时恢复原有结果
			this.state.results = previousResults;
			this.state.totalResults = previousTotal;
		}

		this.state.isLoading = false;
		this.renderResults();
		if (this.state.view === 'search') { this.renderTags(); if (reset) this.renderBanner(); }
		if (window.innerWidth < 768) this.toggleSidebar(false);
		if (reset) this.saveStateToUrl(); // 保存状态到 URL
	},

	loadMore() {
		if (this.state.view === 'follows') return;
		if (this.state.isLoading) return;
		if (this.state.results.length >= this.state.totalResults) return;
		this.executeSearch(false);
	},

	handleContentScroll() {
		if (this.state.view === 'follows') return;
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

		if (this.state.view === 'follows') {
			this.renderTags();
			this.applyFollowFilters();
			this.renderResults();
			return;
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
		const tagsSection = document.getElementById('tags-section');
		const baseTags = this.state.view === 'follows' ? this.state.followAvailableTags : this.state.availableTags;
		const tags = new Set([...(baseTags || []), ...this.state.includedTags, ...this.state.excludedTags]);
		
		// 当没有可用标签时隐藏整个 tags-section
		if (!tags.size) {
			container.innerHTML = '';
			if (tagsSection) tagsSection.classList.add('hidden');
			return;
		}
		
		// 有标签时显示 tags-section
		if (tagsSection) tagsSection.classList.remove('hidden');
		
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
		this.renderTags();
		if (this.state.view === 'follows') {
			this.applyFollowFilters();
			this.renderResults();
			this.saveStateToUrl();
		} else {
			this.executeSearch();
		}
	},

	setTagMode(m) {
		this.state.tagMode = m;
		this.renderTags();
		/* Update UI classes omitted for brevity */
		if (this.state.view === 'follows') {
			this.applyFollowFilters();
			this.renderResults();
			this.saveStateToUrl();
		} else {
			this.executeSearch();
		}
	},
	setTagLogic(l) {
		this.state.tagLogic = l;
		if (this.state.view === 'follows') {
			this.applyFollowFilters();
			this.renderResults();
			this.saveStateToUrl();
		} else {
			this.executeSearch();
		}
	},

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
	selectChannel(id) {
		this.state.channelId = id === 'global' ? null : id;
		this.renderChannels();
		if (this.state.view === 'follows') {
			this.applyFollowFilters();
			this.renderResults();
			this.saveStateToUrl();
		} else {
			this.executeSearch();
		}
	},

	renderUserArea() {
		const el = document.getElementById('user-area');
		if (this.state.user) {
			const url = this.state.user.avatar ? `https://cdn.discordapp.com/avatars/${this.state.user.id}/${this.state.user.avatar}.png` : `https://cdn.discordapp.com/embed/avatars/0.png`;
			el.innerHTML = `<img src="${url}" class="w-8 h-8 rounded-full"><div class="flex-1 min-w-0"><div class="text-xs font-bold text-white truncate">${this.state.user.global_name}</div></div><button onclick="app.logout()" class="text-muted"><span class="material-symbols-outlined">logout</span></button>`;
		} else { el.innerHTML = `<button onclick="app.login()" class="w-full bg-discord-primary text-white py-2 rounded text-sm">Discord 登录</button>`; }
	},
	login() { window.location.href = `${window.AUTH_URL}/auth/login`; },
	logout(r = true) {
		localStorage.removeItem('auth_token');
		this.state.token = null;
		this.state.user = null;
		this.resetFollowState();
		this.state.unreadCount = 0;
		this.updateFollowBadge();
		this.renderUserArea();
		if (r) window.location.href = `${window.AUTH_URL}/auth/logout`;
	},

	// Banner状态
	bannerCollapsed: localStorage.getItem('banner_collapsed') === 'true',
	currentBannerIndex: 0,
	bannerAutoplayTimer: null,

	renderBanner() {
		const el = document.getElementById('banner-section');
		const sidebarBanner = document.getElementById('sidebar-banner');
		
		// 如果已折叠，确保元素状态正确
		if (this.bannerCollapsed) {
			el.classList.add('collapsed');
		}
		
		// 准备banner数据
		let banners = this.state.banners || [];
		if (!banners.length) {
			// 使用默认banner占位
			banners = [{
				title: '欢迎来到类脑索引',
				cover_image_url: 'banner.png',
				thread_id: null
			}];
		}
		
		el.classList.remove('hidden');
		
		// 渲染轮播内容（包含模糊背景层）
		const slidesHtml = banners.map((banner, idx) => `
			<div class="banner-slide ${idx === 0 ? 'active' : ''}" data-index="${idx}">
				<div class="banner-blur-bg" style="background-image: url('${banner.cover_image_url}')"></div>
				<img src="${banner.cover_image_url}" onerror="this.src='banner.png'; this.previousElementSibling.style.backgroundImage='url(banner.png)'">
			</div>
		`).join('');
		
		const dotsHtml = banners.length > 1 ? `
			<div class="banner-dots">
				${banners.map((_, idx) => `
					<button class="banner-dot ${idx === 0 ? 'active' : ''}" data-index="${idx}" onclick="app.goToBannerSlide(${idx})"></button>
				`).join('')}
			</div>
		` : '';
		
		const navButtons = banners.length > 1 ? `
			<button class="banner-nav-btn banner-prev" onclick="app.prevBannerSlide()">
				<span class="material-symbols-outlined">chevron_left</span>
			</button>
			<button class="banner-nav-btn banner-next" onclick="app.nextBannerSlide()">
				<span class="material-symbols-outlined">chevron_right</span>
			</button>
		` : '';
		
		document.getElementById('banner-slides').innerHTML = slidesHtml;
		document.getElementById('banner-title').innerText = banners[0].title;
		
		// 添加导航按钮和指示点
		const container = el.querySelector('.banner-container');
		
		// 移除旧的导航元素
		container.querySelectorAll('.banner-dots, .banner-nav-btn').forEach(e => e.remove());
		
		// 添加新的导航元素
		if (dotsHtml) container.insertAdjacentHTML('beforeend', dotsHtml);
		if (navButtons) container.insertAdjacentHTML('beforeend', navButtons);
		
		// 启动自动轮播
		this.startBannerAutoplay();
		
		// 更新侧边栏迷你banner
		this.updateSidebarBanner();
		
		// 更新跳转按钮显示状态
		this.updateBannerLinks();
	},

	startBannerAutoplay() {
		this.stopBannerAutoplay();
		const banners = this.state.banners || [];
		if (banners.length <= 1) return;
		
		this.bannerAutoplayTimer = setInterval(() => {
			this.nextBannerSlide();
		}, 5000);
	},

	stopBannerAutoplay() {
		if (this.bannerAutoplayTimer) {
			clearInterval(this.bannerAutoplayTimer);
			this.bannerAutoplayTimer = null;
		}
	},

	goToBannerSlide(index) {
		const banners = this.state.banners || [];
		if (!banners.length) return;
		
		this.currentBannerIndex = index;
		const slides = document.querySelectorAll('#banner-slides .banner-slide');
		const dots = document.querySelectorAll('.banner-dots .banner-dot');
		const titleEl = document.getElementById('banner-title');
		
		slides.forEach((slide, i) => slide.classList.toggle('active', i === index));
		dots.forEach((dot, i) => dot.classList.toggle('active', i === index));
		if (titleEl && banners[index]) {
			titleEl.innerText = banners[index].title;
		}
		
		// 同步更新侧边栏banner
		this.updateSidebarBannerSlide(index);
		
		// 更新跳转按钮显示状态
		this.updateBannerLinks();
		
		// 重启自动播放计时器
		this.startBannerAutoplay();
	},

	prevBannerSlide() {
		const banners = this.state.banners || [];
		if (!banners.length) return;
		const newIndex = (this.currentBannerIndex - 1 + banners.length) % banners.length;
		this.goToBannerSlide(newIndex);
	},

	nextBannerSlide() {
		const banners = this.state.banners || [];
		if (!banners.length) return;
		const newIndex = (this.currentBannerIndex + 1) % banners.length;
		this.goToBannerSlide(newIndex);
	},

	openCurrentBannerApp() {
		const banners = this.state.banners || [];
		const current = banners[this.currentBannerIndex];
		if (!current || !current.thread_id) return;
		
		const appLink = `discord://discord.com/channels/${window.GUILD_ID || '@me'}/${current.thread_id}`;
		window.location.href = appLink;
	},

	openCurrentBannerWeb() {
		const banners = this.state.banners || [];
		const current = banners[this.currentBannerIndex];
		if (!current || !current.thread_id) return;
		
		const webLink = `https://discord.com/channels/${window.GUILD_ID || '@me'}/${current.thread_id}`;
		window.open(webLink, '_blank');
	},

	updateBannerLinks() {
		const banners = this.state.banners || [];
		const current = banners[this.currentBannerIndex];
		const hasLink = current && current.thread_id;
		
		// 主 Banner 跳转按钮
		const bannerLinks = document.getElementById('banner-links');
		if (bannerLinks) {
			bannerLinks.classList.toggle('hidden', !hasLink);
		}
		
		// 侧边栏 Banner 跳转按钮
		const sidebarAppBtn = document.getElementById('sidebar-banner-app-btn');
		const sidebarWebBtn = document.getElementById('sidebar-banner-web-btn');
		if (sidebarAppBtn) {
			sidebarAppBtn.classList.toggle('hidden', !hasLink);
		}
		if (sidebarWebBtn) {
			sidebarWebBtn.classList.toggle('hidden', !hasLink);
		}
	},

	toggleBannerCollapse() {
		this.bannerCollapsed = !this.bannerCollapsed;
		localStorage.setItem('banner_collapsed', this.bannerCollapsed);
		
		const el = document.getElementById('banner-section');
		el.classList.toggle('collapsed', this.bannerCollapsed);
		
		// 折叠时停止自动播放
		if (this.bannerCollapsed) {
			this.stopBannerAutoplay();
		} else {
			this.startBannerAutoplay();
		}
	},

	// 侧边栏Banner状态
	sidebarBannerClosed: false,
	sidebarBannerDragging: false,
	sidebarBannerDragOffset: { x: 0, y: 0 },

	closeSidebarBanner() {
		const el = document.getElementById('sidebar-banner');
		if (el) {
			el.classList.add('closing');
			this.sidebarBannerClosed = true;
			setTimeout(() => {
				el.classList.remove('visible', 'closing');
			}, 200);
		}
	},

	updateSidebarBanner() {
		const sidebarBanner = document.getElementById('sidebar-banner');
		if (!sidebarBanner) return;
		
		const banners = this.state.banners || [];
		if (!banners.length) {
			// 使用默认banner
			banners.push({
				title: '欢迎来到类脑索引',
				cover_image_url: 'banner.png',
				thread_id: null
			});
		}
		
		// 渲染侧边栏banner
		const sidebarSlidesHtml = banners.map((banner, idx) => `
			<div class="sidebar-banner-slide ${idx === this.currentBannerIndex ? 'active' : ''}" data-index="${idx}"
				 onclick="${banner.thread_id ? `app.openCurrentBannerWeb()` : ''}"
				 style="${banner.thread_id ? 'cursor: pointer;' : ''}">
				<img src="${banner.cover_image_url}" class="w-full h-full object-cover" onerror="this.src='banner.png'">
			</div>
		`).join('');
		
		sidebarBanner.querySelector('.sidebar-banner-slides').innerHTML = sidebarSlidesHtml;
		sidebarBanner.querySelector('.sidebar-banner-title').innerText = banners[this.currentBannerIndex]?.title || '欢迎';
		
		// 更新跳转按钮显示状态
		this.updateBannerLinks();
	},

	setupSidebarBannerDrag() {
		const sidebarBanner = document.getElementById('sidebar-banner');
		if (!sidebarBanner) return;
		
		const dragHandle = sidebarBanner.querySelector('.sidebar-banner-drag-handle');
		if (!dragHandle) return;
		
		const startDrag = (e) => {
			// 阻止选中文本
			e.preventDefault();
			
			this.sidebarBannerDragging = true;
			sidebarBanner.classList.add('dragging');
			
			const rect = sidebarBanner.getBoundingClientRect();
			const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
			const clientY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
			
			this.sidebarBannerDragOffset = {
				x: clientX - rect.left,
				y: clientY - rect.top
			};
			
			document.addEventListener('mousemove', onDrag);
			document.addEventListener('mouseup', stopDrag);
			document.addEventListener('touchmove', onDrag, { passive: false });
			document.addEventListener('touchend', stopDrag);
		};
		
		const onDrag = (e) => {
			if (!this.sidebarBannerDragging) return;
			
			e.preventDefault();
			
			const clientX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
			const clientY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
			
			let newX = clientX - this.sidebarBannerDragOffset.x;
			let newY = clientY - this.sidebarBannerDragOffset.y;
			
			// 限制在视口范围内
			const bannerWidth = sidebarBanner.offsetWidth;
			const bannerHeight = sidebarBanner.offsetHeight;
			const maxX = window.innerWidth - bannerWidth;
			const maxY = window.innerHeight - bannerHeight;
			
			newX = Math.max(0, Math.min(newX, maxX));
			newY = Math.max(0, Math.min(newY, maxY));
			
			sidebarBanner.style.left = newX + 'px';
			sidebarBanner.style.top = newY + 'px';
			sidebarBanner.style.right = 'auto';
		};
		
		const stopDrag = () => {
			this.sidebarBannerDragging = false;
			sidebarBanner.classList.remove('dragging');
			
			document.removeEventListener('mousemove', onDrag);
			document.removeEventListener('mouseup', stopDrag);
			document.removeEventListener('touchmove', onDrag);
			document.removeEventListener('touchend', stopDrag);
		};
		
		dragHandle.addEventListener('mousedown', startDrag);
		dragHandle.addEventListener('touchstart', startDrag, { passive: false });
	},

	updateSidebarBannerSlide(index) {
		const sidebarBanner = document.getElementById('sidebar-banner');
		if (!sidebarBanner) return;
		
		const slides = sidebarBanner.querySelectorAll('.sidebar-banner-slide');
		const titleEl = sidebarBanner.querySelector('.sidebar-banner-title');
		const banners = this.state.banners || [];
		
		slides.forEach((slide, i) => slide.classList.toggle('active', i === index));
		if (titleEl && banners[index]) {
			titleEl.innerText = banners[index].title;
		}
	},

	setupBannerScrollObserver() {
		const bannerSection = document.getElementById('banner-section');
		const sidebarBanner = document.getElementById('sidebar-banner');
		
		if (!bannerSection || !sidebarBanner) return;
		
		const observer = new IntersectionObserver((entries) => {
			entries.forEach(entry => {
				// 当主banner不可见时，显示侧边栏banner（如果没有被用户关闭）
				const isMainVisible = entry.isIntersecting;
				const isInSearchView = this.state.view === 'search';
				
				if (!isMainVisible && isInSearchView && !this.bannerCollapsed && !this.sidebarBannerClosed) {
					sidebarBanner.classList.add('visible');
				} else {
					sidebarBanner.classList.remove('visible');
				}
			});
		}, {
			threshold: 0.1,
			rootMargin: '-50px 0px 0px 0px'
		});
		
		observer.observe(bannerSection);
		
		// 设置拖动功能
		this.setupSidebarBannerDrag();
	},

	// Banner申请相关
	openBannerApplicationModal() {
		const modal = document.getElementById('banner-application-modal');
		if (modal) {
			modal.classList.remove('hidden');
			modal.classList.add('active');
			document.body.style.overflow = 'hidden';
		}
	},

	closeBannerApplicationModal() {
		const modal = document.getElementById('banner-application-modal');
		if (modal) {
			modal.classList.remove('active');
			setTimeout(() => {
				modal.classList.add('hidden');
				document.body.style.overflow = '';
			}, 300);
		}
	},

	async submitBannerApplication(event) {
		event.preventDefault();
		
		const threadIdInput = document.getElementById('banner-thread-id');
		const coverUrlInput = document.getElementById('banner-cover-url');
		const scopeSelect = document.getElementById('banner-scope');
		const submitBtn = document.getElementById('banner-submit-btn');
		
		const threadId = threadIdInput.value.trim();
		const coverUrl = coverUrlInput.value.trim();
		const scope = scopeSelect.value;
		
		// 验证
		if (!threadId || !coverUrl || !scope) {
			this.showBannerApplicationError('请填写所有必填字段');
			return;
		}
		
		if (!/^\d{17,20}$/.test(threadId)) {
			this.showBannerApplicationError('帖子ID必须是17-20位数字');
			return;
		}
		
		if (!coverUrl.startsWith('http://') && !coverUrl.startsWith('https://')) {
			this.showBannerApplicationError('封面图链接必须以http://或https://开头');
			return;
		}
		
		// 禁用提交按钮
		submitBtn.disabled = true;
		submitBtn.innerHTML = '<span class="material-symbols-outlined animate-spin">progress_activity</span> 提交中...';
		
		try {
			const response = await this.fetchAPI('/banner/apply', 'POST', {
				thread_id: threadId,
				cover_image_url: coverUrl,
				target_scope: scope
			});
			
			if (response && response.success) {
				this.closeBannerApplicationModal();
				this.showToast('✅ Banner申请已提交，等待审核');
				// 清空表单
				threadIdInput.value = '';
				coverUrlInput.value = '';
				scopeSelect.value = '';
			} else {
				this.showBannerApplicationError(response?.message || '提交失败，请重试');
			}
		} catch (error) {
			this.showBannerApplicationError('网络错误，请重试');
		} finally {
			submitBtn.disabled = false;
			submitBtn.innerHTML = '<span class="material-symbols-outlined">send</span> 提交申请';
		}
	},

	showBannerApplicationError(message) {
		const errorEl = document.getElementById('banner-application-error');
		if (errorEl) {
			errorEl.textContent = message;
			errorEl.classList.remove('hidden');
			setTimeout(() => errorEl.classList.add('hidden'), 5000);
		}
	},

	showToast(message) {
		// 创建临时toast提示
		const toast = document.createElement('div');
		toast.className = 'fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-discord-element text-white px-4 py-2 rounded-lg shadow-lg z-50 transition-opacity duration-300';
		toast.textContent = message;
		document.body.appendChild(toast);
		
		setTimeout(() => {
			toast.style.opacity = '0';
			setTimeout(() => toast.remove(), 300);
		}, 3000);
	},

	switchView(v) {
		this.state.view = v;
		document.getElementById('nav-search').className = v === 'search' ? 'w-full flex items-center gap-3 px-3 py-2 rounded bg-discord-element text-white' : 'w-full flex items-center gap-3 px-3 py-2 rounded hover:bg-discord-element text-discord-muted';
		document.getElementById('nav-follows').className = v === 'follows' ? 'w-full flex items-center gap-3 px-3 py-2 rounded bg-discord-element text-white relative' : 'w-full flex items-center gap-3 px-3 py-2 rounded hover:bg-discord-element text-discord-muted relative';
		document.getElementById('banner-section').classList.toggle('hidden', v !== 'search');
		const showTags = (v === 'search' || v === 'follows');
		document.getElementById('tags-section').classList.toggle('hidden', !showTags);
		document.getElementById('view-title').innerText = v === 'search' ? '搜索结果' : '关注列表';
		this.executeSearch();
	},

	checkAuth() {
		this.fetchAPI('/auth/checkauth', 'GET').then(d => {
			if (d && d.loggedIn) {
				this.state.user = d.user;
				this.state.followNeedsRefresh = true;
				this.renderUserArea();
				this.refreshUnreadCount();
			} else {
				// 未登录，跳转到登录页面
				this.redirectToLogin();
			}
		}).catch(() => {
			// 请求失败，跳转到登录页面
			this.redirectToLogin();
		});
	},

	redirectToLogin() {
		// 保存当前页面 URL 以便登录后返回
		const currentUrl = window.location.href;
		const loginUrl = `login.html?redirect=${encodeURIComponent(currentUrl)}`;
		window.location.href = loginUrl;
	},
	toggleSortOrder() {
		this.state.sortOrder = this.state.sortOrder === 'asc' ? 'desc' : 'asc';
		this.updateSortOrderIcon();
		if (this.state.view === 'follows') {
			this.applyFollowFilters();
			this.renderResults();
			this.saveStateToUrl();
		} else {
			this.executeSearch();
		}
	},

	updateSortOrderIcon() {
		const btn = document.getElementById('sort-order-btn');
		if (!btn) return;
		const icon = btn.querySelector('.material-symbols-outlined');
		if (icon) {
			icon.textContent = this.state.sortOrder === 'asc' ? 'arrow_upward' : 'arrow_downward';
		}
	},
	setupEventListeners() {
		let typingTimer;
		const searchInput = document.getElementById('search-input');
		if (searchInput) {
			searchInput.addEventListener('input', () => {
				clearTimeout(typingTimer);
				typingTimer = setTimeout(() => {
					if (this.state.view === 'follows') {
						this.applyFollowFilters();
						this.renderResults();
					} else {
						this.executeSearch();
					}
				}, 600);
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
		const imgs = [
			'https://placehold.co/800x400/202225/5865F2?text=Image+1',
			'https://placehold.co/600x800/36393f/3ba55c?text=Image+2',
			'https://placehold.co/1200x600/000/fff?text=Image+3',
			'https://placehold.co/400x400/ed4245/fff?text=Image+4',
			'https://placehold.co/500x300/4752c4/fff?text=Image+5',
			'https://placehold.co/300x500/3ba55c/fff?text=Image+6'
		];
		for (let i = 0; i < 12; i++) {
			// 根据索引生成不同数量的图片来测试各种布局
			const imageCount = (i % 6) + 1; // 1-6张图
			const postImages = imgs.slice(0, imageCount);
			
			r.push({
				thread_id: `mock-${i}`, channel_id: "1001", author_id: "u1",
				title: i % 2 === 0 ? "Discord 门户设计规范讨论 (v3.0 更新)" : "这是一个标题很长很长的测试帖子用于检测换行和截断效果",
				thumbnail_urls: postImages,
				first_message_excerpt: `这里是测试内容。包含 **粗体**, \`代码\`, 以及 [链接](https://discord.com)。\n\n第二行内容。\n> 引用文本效果\n\n此帖包含 ${imageCount} 张图片。`,
				created_at: new Date().toISOString(), reply_count: 12, reaction_count: 34,
				tags: ['design', 'ui', 'fix'], author: { username: "User" + i, global_name: "Designer " + i }
			});
		}
		return { results: r, total: 99, available_tags: ['ui', 'design', 'code'], banner_carousel: [{ title: "Welcome", cover_image_url: "https://placehold.co/1200x400/202225/5865F2" }] };
	},

	handleImageError(event, threadId, channelId) {
		const imgElement = event.target;
		imgElement.onerror = null;
		imgElement.src = this.getPlaceholderImage();
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
			
			// 检查是否有错误
			if (result && result.error != null) {
				// 有错误，从failedImages移除（不再重试）
				// 根据错误类型显示不同占位图
				const errorPlaceholder = result.error === 'no_image_found' 
					? this.getPlaceholderImage() 
					: 'https://placehold.co/600x300/000/fff?text=Image+Error';
				entry.elements.forEach(img => {
					img.src = errorPlaceholder;
				});
				// 不重新加入 failedImages，停止重试
				return;
			}
			
			entry.elements.forEach(img => {
				const nextUrl = this.getPrimaryThumbnail(result) || this.getPlaceholderImage();
				img.src = nextUrl;
				if (result && result.thumbnail_urls && result.thumbnail_urls.length) {
					this.updateLocalThumbnail(key, result.thumbnail_urls);
				} else {
					img.src = 'https://placehold.co/600x300/000/fff?text=Image+Error';
				}
			});
			if (!result || !result.thumbnail_urls || !result.thumbnail_urls.length) {
				this.state.failedImages.set(key, entry);
			}
		});

		this.cleanupImageRecoveryTimer();
	},

	updateLocalThumbnail(threadId, thumbnailUrls) {
		const targetId = String(threadId);
		const normalized = this.normalizeThumbnailList(thumbnailUrls);
		if (!normalized.length) {
			return;
		}
		const result = this.state.results.find(post => String(post.thread_id) === targetId);
		if (result) {
			result.thumbnail_urls = normalized;
			if (result.thumbnail_url && !normalized.includes(result.thumbnail_url)) {
				result.thumbnail_urls.unshift(result.thumbnail_url);
			}
		}
	}
};

document.addEventListener('DOMContentLoaded', () => app.init());