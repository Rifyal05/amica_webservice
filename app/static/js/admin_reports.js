function reportsLogic() {
    return {
        reports: [], 
        activeReportTab: 'post', 
        
        evidenceModal: { 
            show: false, 
            data: null, 
            reason: '', 
            processing: false,
            hasActionTaken: false
        },

        setReportTab(type) {
            this.activeReportTab = type;
            this.fetchReports();
        },

        async fetchReports() {
            const url = `/admin/reports?type=${this.activeReportTab}`;
            const data = await this.authFetch(url);
            this.reports = Array.isArray(data) ? data : [];
        },

        openEvidence(group) {
            this.evidenceModal.data = JSON.parse(JSON.stringify(group));
            this.evidenceModal.reason = (group.reasons && group.reasons[0]) ? group.reasons[0] : 'Melanggar Pedoman Komunitas';
            this.evidenceModal.show = true;
            this.evidenceModal.processing = false;
            this.evidenceModal.hasActionTaken = false;
        },

        closeEvidence() {
            this.evidenceModal.show = false;
            this.evidenceModal.data = null;
            if (this.evidenceModal.hasActionTaken) {
                this.fetchReports();
            }
        },

        async actQuarantinePost() {
            if (!this.evidenceModal.data) return;
            this.evidenceModal.processing = true;

            const res = await this.authFetch('/admin/reports/action/quarantine-post', {
                method: 'POST',
                body: JSON.stringify({
                    target_id: this.evidenceModal.data.target_id,
                    reason: this.evidenceModal.reason
                })
            });

            this.evidenceModal.processing = false;
            if (res?.message) {
                this.showToast('Sukses', res.message);
                this.evidenceModal.hasActionTaken = true;
                this.closeEvidence();
            } else {
                this.showToast('Gagal', res?.error || 'Terjadi kesalahan', 'error');
            }
        },

        async actSanitizeUser(field) {
            if (!this.evidenceModal.data) return;
            if (!confirm(`Yakin ingin mereset ${field.toUpperCase()} user ini?`)) return;

            this.evidenceModal.processing = true;
            const res = await this.authFetch('/admin/reports/action/sanitize-user', {
                method: 'POST',
                body: JSON.stringify({
                    target_id: this.evidenceModal.data.target_id,
                    fields: [field],
                    reason: this.evidenceModal.reason
                })
            });

            this.evidenceModal.processing = false;
            if (res?.message) {
                this.showToast('Sukses', res.message);
                this.evidenceModal.hasActionTaken = true;

                if (field === 'avatar') this.evidenceModal.data.preview.avatar_url = null;
                if (field === 'banner') this.evidenceModal.data.preview.banner_url = null;
                if (field === 'bio') this.evidenceModal.data.preview.bio = '[Dibersihkan oleh Admin]';
                if (field === 'display_name') this.evidenceModal.data.preview.display_name = 'Amica User';
                if (field === 'username') this.evidenceModal.data.preview.username = 'user_reset...';
            } else {
                this.showToast('Gagal', res?.error, 'error');
            }
        },

        async actDeleteComment() {
            if (!this.evidenceModal.data) return;
            this.evidenceModal.processing = true;

            const res = await this.authFetch('/admin/reports/action/delete-comment', {
                method: 'POST',
                body: JSON.stringify({
                    target_id: this.evidenceModal.data.target_id,
                    reason: this.evidenceModal.reason
                })
            });

            this.evidenceModal.processing = false;
            if (res?.message) {
                this.showToast('Sukses', res.message);
                this.evidenceModal.hasActionTaken = true;
                this.closeEvidence();
            } else {
                this.showToast('Gagal', res?.error, 'error');
            }
        },

        async actDismiss() {
            if (!this.evidenceModal.data) return;
            this.evidenceModal.processing = true;

            const res = await this.authFetch('/admin/reports/action/dismiss-group', {
                method: 'POST',
                body: JSON.stringify({
                    target_id: this.evidenceModal.data.target_id,
                    target_type: this.evidenceModal.data.target_type
                })
            });

            this.evidenceModal.processing = false;
            if (res?.message) {
                this.showToast('Info', res.message);
                this.evidenceModal.hasActionTaken = true;
                this.closeEvidence();
            } else {
                this.showToast('Gagal', res?.error, 'error');
            }
        }
    }
}