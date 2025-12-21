const activityLogLogic = () => ({
    logsList: [],
    logFilter: '14d',
    logSearch: '',

    async fetchLogs() {
        const q = encodeURIComponent(this.logSearch);
        const data = await this.authFetch(`/admin/activity-logs?filter=${this.logFilter}&q=${q}`);
        if(data) {
            this.logsList = data;
        }
    },

    async revertLog(log) {
        this.askConfirm(
            'Revert Perubahan',
            `Apakah Anda yakin ingin membatalkan aksi ini?\n"${log.description}"`,
            async () => {
                const res = await this.authFetch(`/admin/activity-logs/${log.id}/revert`, { method: 'POST' });
                
                if (res?.message) {
                    this.showToast('Reverted', res.message);
                    this.fetchLogs();
                    this.fetchKeyPeople();
                    this.fetchRegularUsers(1);
                } else if (res?.error) {
                    this.showToast('Gagal', res.error, 'error');
                }
            },
            'danger',
            'Ya, Revert'
        );
    }
});