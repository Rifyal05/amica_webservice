const blacklistLogic = () => ({
    // State
    bannedList: [],
    bannedPagination: { current_page: 1, pages: 1, total: 0 },
    blacklistQuery: '', // State baru untuk search

    // Actions
    async fetchBannedUsers(page = 1) {
        // Encode query agar aman di URL
        const q = encodeURIComponent(this.blacklistQuery);
        
        // Kirim page dan query (q) ke backend
        const data = await this.authFetch(`/admin/users/banned?page=${page}&q=${q}`);
        
        if (data) {
            this.bannedList = data.users;
            this.bannedPagination = {
                current_page: data.current_page,
                pages: data.pages,
                total: data.total
            };
        }
    },

    // Fungsi Refresh (Reset ke halaman 1, query tetap ada atau bisa dikosongkan opsional)
    async refreshBlacklist() {
        this.showToast('Memuat ulang...', 'Sedang mengambil data terbaru.');
        await this.fetchBannedUsers(this.bannedPagination.current_page);
    }
});