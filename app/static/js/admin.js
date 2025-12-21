document.addEventListener('alpine:init', () => {
    Alpine.data('adminApp', () => ({
        currentView: 'dashboard',
        reportTab: 'All',
        token: localStorage.getItem('authToken'),
        user: JSON.parse(localStorage.getItem('currentUser') || '{}'),
        isDark: localStorage.getItem('theme') === 'dark',

        toasts: [],

        stats: {},
        currentStatsRange: '7d',

        // Data Users
        keyPeople: [],
        regularUsers: [],
        pagination: { current_page: 1, pages: 1, total: 0 },
        searchQuery: '',

        // Data Lain
        reports: [],
        feedbacks: { positive: [], negative: [], total: 0 },
        feedbackRange: 'all',
        activeFeedbackTab: 'all',
        feedbackPercent: 0,

        // UI States
        activeDropdown: null,
        suspendModalOpen: false,
        selectedReport: null,
        suspendTargetId: null,

        // Forms
        formProfile: { display_name: '', username: '', email: '', avatarFile: null },
        oldPassword: '', newPassword: '',
        pinForm: { old: '', new: '' },

        // Quick Action Forms & Autocomplete
        manageForm: { email: '', role: 'admin' },
        suspendForm: { email: '', days: '3' },
        suggestions: [],
        activeSearch: null,

        articlesList: [],
        articlePage: 1,
        isArticleModalOpen: false,
        articleForm: {
            id: null,
            title: '', category: '', content: '', tags: '',
            source_name: '', source_url: '',
            image: null, preview: null,
            image_url_manual: '',
            is_featured: false
        },
        hasDraft: false,


        confirmModal: {
            show: false,
            title: '',
            message: '',
            type: 'primary', 
            confirmText: 'Ya',
            callback: null
        },

        // Menu Navigasi
        navItems: [
            { id: 'dashboard', label: 'Dashboard', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"></path></svg>' },
            { id: 'users', label: 'Pengguna', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>' },
            { id: 'blacklist', label: 'Blacklist', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>' },
            { id: 'reports', label: 'Laporan', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>' },
            { id: 'feedback', label: 'Feedback', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"></path></svg>' },
            { id: 'articles', label: 'Artikel', icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"></path></svg>' },
            {
                id: 'activity_log',
                label: 'Activity Log',
                icon: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>'
            },
        ],

        timeRanges: [
            { label: 'Hari Ini', val: 'today' }, { label: '7 Hari', val: '7d' }, { label: 'Bulan Ini', val: '30d' },
            { label: 'Tahun Ini', val: '1y' }, { label: '5 Tahun', val: '5y' }, { label: '10 Tahun', val: '10y' }, { label: 'Semua', val: 'all' }
        ],

        // INIT & UTILS
        initApp() {
            if (!this.token) window.location.href = '/admin/login';
            if (this.isDark) document.documentElement.classList.add('dark');
            if (!this.user.display_name) this.user.display_name = "Admin";
            this.formProfile = { ...this.user, avatarFile: null };

            // Load Data Awal
            this.fetchStats();
            this.fetchKeyPeople();
            this.fetchRegularUsers(1);
            this.fetchBannedUsers(1);
            this.fetchReports();
            this.fetchFeedback();
            this.fetchArticles();
            this.fetchLogs();
        },

        ...blacklistLogic(),
        ...activityLogLogic(),


        async authFetch(url, opts = {}) {
            const headers = { 'Authorization': 'Bearer ' + this.token, 'Content-Type': 'application/json', ...opts.headers };
            const res = await fetch(url, { ...opts, headers });

            if (res.status === 403) {
                const data = await res.json().catch(() => ({}));
                alert(data.message || data.error || "Akses ditolak atau Akun Anda telah disuspend.");
                this.logout();
                return null;
            }

            if (res.status === 401) { this.logout(); return null; }
            return res.json();
        },

        toggleTheme() { this.isDark = !this.isDark; document.documentElement.classList.toggle('dark'); localStorage.setItem('theme', this.isDark ? 'dark' : 'light'); },
        logout() { localStorage.removeItem('authToken'); localStorage.removeItem('currentUser'); window.location.href = '/admin/login'; },



        async fetchKeyPeople() {
            this.keyPeople = await this.authFetch('/admin/users/key-people') || [];
        },

        getAvatarUrl(path) {
            if (!path) return '';

            const safePath = String(path).trim();

            if (safePath.startsWith('http') || safePath.startsWith('data:')) {
                return safePath;
            }

            return '/static/uploads/' + safePath;
        },

        showToast(title, message, type = 'success') {
            const id = Date.now();
            this.toasts.push({ id, title, message, type, show: true });
            setTimeout(() => {
                const index = this.toasts.findIndex(t => t.id === id);
                if (index > -1) this.toasts[index].show = false;
                setTimeout(() => {
                    this.toasts = this.toasts.filter(t => t.id !== id);
                }, 300);
            }, 3000);
        },

        askConfirm(title, message, callback, type = 'primary', confirmText = 'Ya') {
            this.confirmModal = {
                show: true,
                title,
                message,
                type,
                confirmText,
                callback
            };
        },

        confirmAction() {
            if (this.confirmModal.callback) {
                this.confirmModal.callback();
            }
            this.confirmModal.show = false;
        },

        get ownersList() { return this.keyPeople.filter(u => u.role === 'owner'); },
        get adminsList() { return this.keyPeople.filter(u => u.role === 'admin'); },

        async fetchRegularUsers(page = 1) {
            const q = encodeURIComponent(this.searchQuery);
            const url = `/admin/users/regular?page=${page}&limit=10&q=${q}`;

            const data = await this.authFetch(url);
            if (data) {
                this.regularUsers = data.users;
                this.pagination = {
                    current_page: data.current_page,
                    pages: data.pages,
                    total: data.total
                };
            }
        },

        changePage(newPage) {
            if (newPage < 1 || newPage > this.pagination.pages) return;
            this.fetchRegularUsers(newPage);
        },

        async searchSuggestions(query, type) {
            this.activeSearch = type;

            if (query.length < 2) {
                this.suggestions = [];
                return;
            }

            const url = `/admin/users/autocomplete?q=${encodeURIComponent(query)}`;
            const data = await this.authFetch(url);

            if (Array.isArray(data)) {
                this.suggestions = data;
            } else {
                this.suggestions = [];
            }
        },

        selectSuggestion(userEmail) {
            if (this.activeSearch === 'manage') {
                this.manageForm.email = userEmail;
            } else if (this.activeSearch === 'suspend') {
                this.suspendForm.email = userEmail;
            }
            this.suggestions = [];
            this.activeSearch = null;
        },
        async quickChangeRole() {
            if (!this.manageForm.email) return this.showToast('Validasi', "Masukkan email user", 'error');

            let targetUser = this.keyPeople.find(u => u.email === this.manageForm.email) ||
                this.regularUsers.find(u => u.email === this.manageForm.email);

            if (!targetUser) return this.showToast('Tidak Ditemukan', "User tidak ditemukan.", 'error');
            if (targetUser.id === this.user.id) return this.showToast('Akses Ditolak', "Tidak bisa mengubah role diri sendiri.", 'error');
            this.askConfirm(
                'Ubah Role',
                `Yakin ingin mengubah ${targetUser.username} menjadi ${this.manageForm.role.toUpperCase()}?`,
                async () => {
                    const res = await this.authFetch('/admin/users/change-role', {
                        method: 'POST', body: JSON.stringify({ user_id: targetUser.id, new_role: this.manageForm.role })
                    });
                    if (res?.message) {
                        this.showToast('Berhasil', res.message);
                        this.manageForm.email = '';
                        this.fetchKeyPeople();
                        this.fetchRegularUsers(this.pagination.current_page);
                    } else if (res?.error) {
                        this.showToast('Gagal', res.error, 'error');
                    }
                }
            );
        },


        get isProfileChanged() {
            if (this.formProfile.avatarFile) return true;
            return this.formProfile.display_name !== this.user.display_name ||
                this.formProfile.username !== this.user.username ||
                this.formProfile.email !== this.user.email;
        },

        async quickSuspend() {
            if (!this.suspendForm.email) return alert("Masukkan email user");

            let targetUser = this.keyPeople.find(u => u.email === this.suspendForm.email) ||
                this.regularUsers.find(u => u.email === this.suspendForm.email);

            if (!targetUser) return this.showToast('Tidak Ditemukan', "User tidak ditemukan.", 'error');

            if (targetUser.role === 'admin' || targetUser.role === 'owner') {
                return this.showToast('Akses Ditolak', "Tidak bisa men-suspend sesama Admin/Owner.", 'error');
            }

            this.suspendTargetId = targetUser.id;
            this.executeSuspend(parseInt(this.suspendForm.days));
            this.suspendForm.email = '';
        },

        async promoteUser(u) {
            this.askConfirm(
                'Promote User',
                `Jadikan ${u.username} sebagai Admin?`,
                async () => {
                    const res = await this.authFetch('/admin/users/change-role', {
                        method: 'POST', body: JSON.stringify({ user_id: u.id, new_role: 'admin' })
                    });
                    if (res?.message) {
                        this.showToast('Berhasil', res.message);
                        this.activeDropdown = null;
                        this.fetchKeyPeople();
                        this.fetchRegularUsers(this.pagination.current_page);
                    } else if (res?.error) {
                        this.showToast('Gagal', res.error, 'error');
                    }
                }
            );
        },

        async deleteUserById(u) {
            const confirmName = prompt(`KETIK 'CONFIRM' untuk menghapus user ${u.username} secara permanen.`);
            if (confirmName !== 'CONFIRM') return this.showToast('Batal', "Penghapusan dibatalkan.", 'error');

            const res = await this.authFetch(`/admin/users/${u.id}`, { method: 'DELETE' });
            if (res?.message) {
                this.showToast('Terhapus', res.message);
                this.activeDropdown = null;
                this.fetchKeyPeople();
                this.fetchRegularUsers(this.pagination.current_page);
            } else if (res?.error) {
                this.showToast('Gagal', res.error, 'error');
            }
        },

        openDirectSuspend(u) {
            this.selectedReport = null;
            this.suspendTargetId = u.id;
            this.suspendModalOpen = true;
            this.activeDropdown = null;
        },

        async unsuspendUser(u) {
            this.askConfirm(
                'Pulihkan Akun',
                `Pulihkan akun ${u.username}?`,
                async () => {
                    const res = await this.authFetch('/admin/users/unsuspend', {
                        method: 'POST', body: JSON.stringify({ user_id: u.id })
                    });

                    if (res?.message) {
                        this.showToast('Dipulihkan', res.message);
                        this.activeDropdown = null;
                        this.fetchKeyPeople();
                        this.fetchRegularUsers(this.pagination.current_page);
                        this.fetchBannedUsers(1);
                    } else if (res?.error) {
                        this.showToast('Gagal', res.error, 'error');
                    }
                }
            );
        },
        async executeSuspend(days) {
            if (!this.suspendTargetId) return alert("Target Error");
            const res = await this.authFetch('/admin/users/suspend', { method: 'POST', body: JSON.stringify({ user_id: this.suspendTargetId, days }) });
            if (res?.message) {
                this.showToast('Hukuman Dijatuhkan', res.message);
                if (this.selectedReport) {
                    this.authFetch(`/admin/reports/${this.selectedReport.id}/resolve`, { method: 'POST', body: JSON.stringify({ action: 'resolved' }) });
                    this.fetchReports();
                }
                this.suspendModalOpen = false;
                this.fetchKeyPeople();
                this.fetchRegularUsers(this.pagination.current_page);
            } else if (res?.error) {
                this.showToast('Gagal', res.error, 'error');
            }
        },

        async connectGoogleAccount() {
            if (!window.firebaseAuth) {
                return this.showToast('Error', "Layanan Google belum siap. Refresh halaman.", 'error');
            }

            try {
                const result = await window.signInWithPopup(window.firebaseAuth, window.googleProvider);
                const idToken = await result.user.getIdToken();
                const res = await fetch('/admin/link-google', {
                    method: 'POST',
                    headers: {
                        'Authorization': 'Bearer ' + this.token,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ token: idToken })
                });

                const data = await res.json();

                if (res.ok) {
                    this.showToast('Sukses', 'Akun Google berhasil dihubungkan!');
                    this.user.google_uid = data.google_uid;
                    this.user.auth_provider = 'google';
                    localStorage.setItem('currentUser', JSON.stringify(this.user));
                } else {
                    this.showToast('Gagal', data.message || "Gagal menghubungkan akun.", 'error');
                }

            } catch (err) {
                console.error(err);
                this.showToast('Gagal', "Terjadi kesalahan saat koneksi Google.", 'error');
            }
        },

        async fetchArticles(page = 1) {
            this.articlePage = page;
            const res = await this.authFetch(`/admin/articles/?page=${page}&limit=10`);
            if (res && res.articles) {
                this.articlesList = res.articles;
            }
        },

        getArticleImg(path) {
            if (!path) return 'https://via.placeholder.com/150?text=No+Image';
            if (path.startsWith('http')) return path;
            return `/static/uploads/articles/${path}`;
        },

        openArticleModal() {
            this.articleForm = {
                id: null,
                title: '', category: '', content: '', tags: '',
                source_name: '', source_url: '',
                image: null, preview: null, image_url_manual: '',
                is_featured: false
            };
            this.hasDraft = false;
            const draft = localStorage.getItem('article_draft');

            if (draft) {
                try {
                    const parsed = JSON.parse(draft);
                    this.articleForm = { ...this.articleForm, ...parsed };
                    this.hasDraft = true;
                } catch (e) {
                    console.error("Draft error", e);
                }
            }

            this.isArticleModalOpen = true;

            this.$nextTick(() => {
                this.$watch('articleForm', (val) => {
                    if (val.id) return;

                    const toSave = {
                        title: val.title,
                        category: val.category,
                        content: val.content,
                        tags: val.tags,
                        source_name: val.source_name,
                        source_url: val.source_url,
                        is_featured: val.is_featured,
                        preview: val.preview
                    };
                    localStorage.setItem('article_draft', JSON.stringify(toSave));
                    this.hasDraft = true;
                }, { deep: true });
            });
        },

        clearDraft(closeModal = true) {
            if (closeModal && !confirm("Hapus semua tulisan?")) return;

            this.articleForm = {
                title: '', category: '', content: '', tags: '',
                source_name: '', source_url: '', // Reset juga
                image: null, preview: null, is_featured: false
            };
            localStorage.removeItem('article_draft');
            this.hasDraft = false;
        },

        handleArticleImage(e) {
            if (e.target.files.length) {
                const file = e.target.files[0];
                this.articleForm.image = file;
                const reader = new FileReader();
                reader.onload = (ev) => { this.articleForm.preview = ev.target.result; };
                reader.readAsDataURL(file);
            }
        },

        formatTagsInput() {
            let val = this.articleForm.tags;
            val = val.replace(/[^a-zA-Z0-9_, ]/g, '');
            val = val.replace(/, +/g, ',');
            val = val.replace(/ +/g, '_');
            this.articleForm.tags = val;
        },

        editArticle(art) {
            this.clearDraft(false); 
            this.articleForm = {
                id: art.id,
                title: art.title,
                category: art.category,
                content: art.content,
                tags: Array.isArray(art.tags) ? art.tags.join(',') : (art.tags || ''),
                source_name: art.source_name || '',
                source_url: art.source_url || '',
                image: null, 
                image_url_manual: '',
                preview: this.getArticleImg(art.image_url),
                is_featured: art.is_featured
            };

            this.isArticleModalOpen = true;
        },

        async submitArticle() {
            if (!this.articleForm.title || !this.articleForm.content) return alert("Judul dan Konten wajib diisi");

            const formData = new FormData();
            formData.append('title', this.articleForm.title);
            formData.append('category', this.articleForm.category);
            formData.append('content', this.articleForm.content);
            formData.append('tags', this.articleForm.tags);
            formData.append('source_name', this.articleForm.source_name);
            formData.append('source_url', this.articleForm.source_url);
            formData.append('is_featured', this.articleForm.is_featured);

            if (this.articleForm.image) {
                formData.append('image', this.articleForm.image);
            } else if (this.articleForm.image_url_manual) {
                formData.append('image_url_manual', this.articleForm.image_url_manual);
            }

            let url = '/admin/articles/';
            if (this.articleForm.id) {
                url = `/admin/articles/${this.articleForm.id}`; 
            }

            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + this.token },
                    body: formData
                });

                const data = await res.json();

                if (res.ok) {
                    this.showToast('Sukses', this.articleForm.id ? 'Artikel diperbarui!' : 'Artikel diterbitkan!');
                    this.isArticleModalOpen = false;
                    this.clearDraft(false);
                    this.fetchArticles();
                } else {
                    alert(data.message || data.error);
                }
            } catch (e) {
                alert("Terjadi kesalahan jaringan.");
            }
        },

        async deleteArticle(id) {
            if (!confirm("Hapus artikel ini?")) return;
            const res = await this.authFetch(`/admin/articles/${id}`, { method: 'DELETE' });
            if (res?.message) {
                this.showToast('Terhapus', res.message);
                this.fetchArticles(this.articlePage);
            }
        },
        setFeedbackRange(range) { this.feedbackRange = range; this.fetchFeedback(); },
        async fetchFeedback() {
            const url = `/admin/feedbacks?range=${this.feedbackRange}`;
            const data = await this.authFetch(url);
            if (data) {
                this.feedbacks = data;
                const total = (data.positive.length + data.negative.length);
                this.feedbackPercent = total > 0 ? Math.round((data.positive.length / total) * 100) : 0;
                if (data.counts) setTimeout(() => this.renderFeedbackPageChart(data.counts), 100);
            }
        },
        get currentFeedbackList() {
            if (this.activeFeedbackTab === 'positive') return this.feedbacks.positive || [];
            if (this.activeFeedbackTab === 'negative') return this.feedbacks.negative || [];
            const all = [...(this.feedbacks.positive || []), ...(this.feedbacks.negative || [])];
            return all.sort((a, b) => b.id - a.id);
        },
        renderFeedbackPageChart(counts) {
            const ctx = document.getElementById('feedbackPageChart');
            if (!ctx) return;
            if (window.feedbackChartInstance) window.feedbackChartInstance.destroy();
            window.feedbackChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: { labels: ['Positif', 'Negatif'], datasets: [{ data: counts, backgroundColor: ['#10b981', '#f43f5e'], borderWidth: 0, hoverOffset: 4 }] },
                options: { responsive: true, maintainAspectRatio: false, cutout: '75%', plugins: { legend: { display: false }, tooltip: { enabled: true } } }
            });
        },

        // DASHBOARD CHARTS
        setStatsRange(range) { this.currentStatsRange = range; this.fetchStats(); },
        async fetchStats() {
            const tzOffset = new Date().getTimezoneOffset();
            const url = `/admin/stats?range=${this.currentStatsRange}&tz_offset=${tzOffset}`;
            this.stats = await this.authFetch(url) || {};
            if (this.stats.chart_data) setTimeout(() => this.renderCharts(this.stats.chart_data), 100);
        },
        renderCharts(data) {
            if (!data) return;
            const commonOptions = { responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false }, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false }, ticks: { color: '#9ca3af', font: { size: 10 } } }, y: { beginAtZero: true, suggestedMax: 5, grid: { color: 'rgba(156, 163, 175, 0.1)', borderDash: [5, 5] }, ticks: { color: '#9ca3af', font: { size: 10 }, stepSize: 1, precision: 0 } } } };
            const charts = [{ id: 'chartUsers', type: 'line', label: 'User Baru', data: data.users, color: '#3b82f6', bg: 'rgba(59, 130, 246, 0.1)' }, { id: 'chartPosts', type: 'bar', label: 'Postingan', data: data.posts, color: '#10b981', bg: '#10b981' }, { id: 'chartReports', type: 'line', label: 'Laporan', data: data.reports, color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' }];
            charts.forEach(c => { const ctx = document.getElementById(c.id); if (ctx) { if (window['my' + c.id]) window['my' + c.id].destroy(); window['my' + c.id] = new Chart(ctx, { type: c.type, data: { labels: data.labels, datasets: [{ label: c.label, data: c.data, borderColor: c.type === 'line' ? c.color : undefined, backgroundColor: c.bg, fill: c.type === 'line', tension: 0.4, borderRadius: 4 }] }, options: commonOptions }); } });

            const ctxSent = document.getElementById('chartSentiment');
            if (ctxSent && this.stats.sentiment_data) {
                if (window.myChartSent) window.myChartSent.destroy();
                window.myChartSent = new Chart(ctxSent, { type: 'doughnut', data: { labels: ['Positif', 'Negatif'], datasets: [{ data: this.stats.sentiment_data, backgroundColor: ['#22c55e', '#ef4444'], borderWidth: 0 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } });
            }
        },

        // REPORTS
        async fetchReports() { this.reports = await this.authFetch('/admin/reports') || []; },
        get filteredReports() { return this.reportTab === 'All' ? this.reports : this.reports.filter(r => r.target_type === this.reportTab); },
        openSuspendModal(r) { this.selectedReport = r; this.suspendTargetId = r.target_user_id; this.suspendModalOpen = true; },
        async resolveReport(id, action) {
            this.askConfirm(
                'Selesaikan Laporan',
                "Tandai laporan ini sebagai selesai?",
                async () => {
                    await this.authFetch(`/admin/reports/${id}/resolve`, {
                        method: 'POST', body: JSON.stringify({ action })
                    });
                    this.fetchReports();
                }
            );
        },
        // SETTINGS
        handleFileSelect(e) {
            if (e.target.files.length) {
                const file = e.target.files[0];
                this.formProfile.avatarFile = file;
                const reader = new FileReader();
                reader.onload = (e) => { this.user.avatar_url = e.target.result; };
                reader.readAsDataURL(file);
            }
        },
        async updateProfile() {
            const formData = new FormData();
            formData.append('display_name', this.formProfile.display_name);
            formData.append('username', this.formProfile.username);
            formData.append('email', this.formProfile.email);
            if (this.formProfile.avatarFile) formData.append('avatar', this.formProfile.avatarFile);

            try {
                const res = await fetch('/admin/update-profile', {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + this.token },
                    body: formData
                });
                const data = await res.json();

                if (res.ok) {
                    this.showToast('Berhasil', data.message); // TOAST
                    this.user = data.user;
                    localStorage.setItem('currentUser', JSON.stringify(data.user));
                    this.formProfile.avatarFile = null;
                } else {
                    this.showToast('Gagal', data.message || data.error, 'error'); // TOAST
                }
            } catch (e) {
                this.showToast('Error', 'Gagal update profil', 'error');
            }
        },



        async changePassword() {
            if (!this.newPassword || this.newPassword.length < 6) {
                return this.showToast('Perhatian', "Password baru minimal 6 karakter!", 'error');
            }

            if (this.user.auth_provider !== 'google' && !this.oldPassword) {
                return this.showToast('Perhatian', "Masukkan password lama Anda.", 'error');
            }

            const res = await this.authFetch('/admin/change-password', {
                method: 'POST',
                body: JSON.stringify({
                    old_password: this.oldPassword,
                    new_password: this.newPassword
                })
            });

            if (res?.message) {
                this.showToast('Berhasil', res.message);
                this.newPassword = '';
                this.oldPassword = '';
                this.user.auth_provider = 'email';
                localStorage.setItem('currentUser', JSON.stringify(this.user));
            } else if (res?.error) {
                this.showToast('Gagal', res.error, 'error');
            }
        },

        async updatePin() {
            if (this.pinForm.new.length !== 6) return this.showToast('Error', "PIN Baru harus 6 digit angka", 'error');
            if (isNaN(this.pinForm.new)) return this.showToast('Error', "PIN harus berupa angka", 'error');

            const res = await this.authFetch('/admin/update-pin', {
                method: 'POST',
                body: JSON.stringify({ old_pin: this.pinForm.old, new_pin: this.pinForm.new })
            });

            if (res?.message) {
                this.showToast('Berhasil', res.message);
                this.pinForm.old = '';
                this.pinForm.new = '';
            } else if (res?.error) {
                this.showToast('Gagal', res.error, 'error');
            }
        },

        async deleteAccount() {
            const confirmation = prompt("KETIK 'DELETE' (kapital) untuk menghapus akun Anda secara permanen:");
            if (confirmation !== 'DELETE') return this.showToast('Batal', "Penghapusan dibatalkan.", 'error');

            if (!confirm("Apakah Anda benar-benar yakin?")) return;

            const res = await this.authFetch('/admin/delete-account', { method: 'DELETE' });

            if (res?.message) {
                alert(res.message);
                this.logout();
            } else if (res?.error) {
                this.showToast('Gagal', res.error, 'error');
            }
        },
    }));
}
);