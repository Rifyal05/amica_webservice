function appealsLogic() {
    return {
        appeals: [],
        async fetchAppeals() {
            const data = await this.authFetch('/admin/appeals');
            if (data) this.appeals = data;
        },
        async processAppeal(app, action) {
            const note = prompt(`Berikan catatan untuk ${action === 'approved' ? 'menyetujui' : 'menolak'} banding ini:`, "");
            if (note === null) return;

            this.askConfirm(
                action === 'approved' ? 'Terima Banding' : 'Tolak Banding',
                `Yakin ingin ${action === 'approved' ? 'menampilkan kembali' : 'menghapus permanen'} postingan ini?`,
                async () => {
                    const res = await this.authFetch(`/admin/appeals/${app.id}/action`, {
                        method: 'POST',
                        body: JSON.stringify({ action: action, admin_note: note })
                    });
                    if (res?.message) {
                        this.showToast('Berhasil', res.message);
                        this.fetchAppeals();
                        this.fetchStats();
                    }
                },
                action === 'approved' ? 'primary' : 'danger'
            );
        }
    }
}