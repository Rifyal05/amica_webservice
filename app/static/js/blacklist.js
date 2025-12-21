const blacklistLogic = () => ({
    bannedList: [],
    bannedPagination: { current_page: 1, pages: 1, total: 0 },
    blacklistQuery: '', 

    async fetchBannedUsers(page = 1) {
        const q = encodeURIComponent(this.blacklistQuery);

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

    async refreshBlacklist() {
        this.showToast('Memuat ulang...', 'Sedang mengambil data terbaru.');
        await this.fetchBannedUsers(this.bannedPagination.current_page);
    }
});