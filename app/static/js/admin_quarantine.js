function quarantineLogic() {
    return {
        quarantineItems: [],
        isQuarantineLoading: false,

        async fetchQuarantine() {
            this.isQuarantineLoading = true;
            const data = await this.authFetch('/admin/quarantine-list');
            this.quarantineItems = data || [];
            this.isQuarantineLoading = false;
        },

        getQuarantineUrl(path) {
            if (!path) return '';
            return '/static/quarantine/' + path;
        }
    }
}