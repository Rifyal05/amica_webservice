function proLogic() {
    return {
        proViewMode: 'list',
        proListType: 'pending',
        pros: [],
        proDetail: null,
        isProLoading: false,
        proSearchQuery: '',
        proImageUrls: { str: null, ktp: null, selfie: null },
        activeCheckUrl: null,

        proRejectModal: {
            show: false,
            reason: ''
        },

        initPro() {
            window.addEventListener('view-changed', (e) => {
                if (e.detail === 'professionals') {
                    this.proViewMode = 'list';
                    this.proListType = 'pending';
                    this.proSearchQuery = '';
                    this.fetchPros();
                }
            });

            if (this.currentView === 'professionals') {
                this.fetchPros();
            }
        },

        getFilteredPros() {
            if (!this.proSearchQuery) return this.pros;
            const q = this.proSearchQuery.toLowerCase();
            return this.pros.filter(p =>
                p.full_name.toLowerCase().includes(q) ||
                p.username.toLowerCase().includes(q) ||
                p.str_number.toLowerCase().includes(q)
            );
        },

        async fetchPros() {
            this.isProLoading = true;
            const endpoint = this.proListType === 'pending' ? 'pending' : 'approved';
            try {
                const resp = await fetch(`/api/admin/pro/${endpoint}`, {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                });
                if (resp.ok) {
                    this.pros = await resp.json();
                }
            } catch (err) {
                console.error(err);
            } finally {
                this.isProLoading = false;
            }
        },

        async setProListType(type) {
            this.proListType = type;
            this.proSearchQuery = '';
            await this.fetchPros();
        },

        async loadSecureImage(filename) {
            if (!filename || filename === 'None' || filename.includes('undefined')) return null;
            try {
                const resp = await fetch(`/api/admin/pro/view-document/${filename}`, {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                });
                if (!resp.ok) return null;
                const blob = await resp.blob();
                return URL.createObjectURL(blob);
            } catch (err) { return null; }
        },

        async openProDetail(id) {
            this.isProLoading = true;
            this.proViewMode = 'detail';
            this.activeCheckUrl = null;

            Object.values(this.proImageUrls).forEach(url => url && URL.revokeObjectURL(url));
            this.proImageUrls = { str: null, ktp: null, selfie: null };

            try {
                const resp = await fetch(`/api/admin/pro/detail/${id}`, {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                });
                this.proDetail = await resp.json();

                if (this.proDetail.str_image) this.proImageUrls.str = await this.loadSecureImage(this.proDetail.str_image.split('/').pop());

                if (this.proListType === 'pending') {
                    if (this.proDetail.ktp_image) this.proImageUrls.ktp = await this.loadSecureImage(this.proDetail.ktp_image.split('/').pop());
                    if (this.proDetail.selfie_image) this.proImageUrls.selfie = await this.loadSecureImage(this.proDetail.selfie_image.split('/').pop());
                }
            } catch (err) {
                this.proViewMode = 'list';
            } finally {
                this.isProLoading = false;
            }
        },

        approvePro() {
            this.askConfirm(
                'Konfirmasi Verifikasi',
                `Setujui ${this.proDetail.full_name} sebagai profesional? Data KTP & Selfie akan dihapus otomatis.`,
                async () => {
                    const resp = await fetch(`/api/admin/pro/approve/${this.proDetail.id}`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${this.token}` }
                    });
                    if (resp.ok) {
                        this.showToast('Berhasil', 'Psikolog Terverifikasi!');
                        this.proViewMode = 'list';
                        this.fetchPros();
                    }
                },
                'primary',
                'Ya, Setujui'
            );
        },

        openRejectProModal() {
            this.proRejectModal.reason = '';
            this.proRejectModal.show = true;
        },

        async executeRejectPro() {
            if (!this.proRejectModal.reason) return;
            try {
                const resp = await fetch(`/api/admin/pro/reject/${this.proDetail.id}`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ reason: this.proRejectModal.reason })
                });
                if (resp.ok) {
                    this.proRejectModal.show = false;
                    this.showToast('Ditolak', 'Permohonan berhasil dihapus.');
                    this.proViewMode = 'list';
                    this.fetchPros();
                }
            } catch (err) {
                this.showToast('Gagal', 'Terjadi kesalahan', 'error');
            }
        },

        unverifyPro() {
            this.askConfirm(
                'Cabut Verifikasi',
                `Hapus status profesional ${this.proDetail.full_name}? Dia akan kembali jadi user biasa.`,
                async () => {
                    const resp = await fetch(`/api/admin/pro/revoke/${this.proDetail.id}`, {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${this.token}` }
                    });
                    if (resp.ok) {
                        this.showToast('Dicabut', 'Status profesional ditiadakan.');
                        this.proViewMode = 'list';
                        this.fetchPros();
                    }
                },
                'danger',
                'Ya, Cabut'
            );
        },

        formatProDate(dateString) {
            if (!dateString) return '-';
            try {
                const cleanDate = dateString.replace(/\.\d+/, '').replace(' ', 'T');
                const date = new Date(cleanDate);
                if (isNaN(date.getTime())) return '-';
                return date.toLocaleDateString('id-ID', {
                    day: 'numeric', month: 'long', year: 'numeric',
                    hour: '2-digit', minute: '2-digit'
                });
            } catch (e) { return '-'; }
        }
    }
}