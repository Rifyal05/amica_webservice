function ragLogic() {
    return {
        ragStats: { total: 0, ingested: 0, remaining: 0 },
        ragList: [],
        isSyncing: false,
        isRagModalOpen: false,
        isChatModalOpen: false,
        isWaitMode: false,
        countdown: 0,
        progressMessage: 'Siap sinkronisasi',

        chatInput: '',
        chatHistory: [],
        isChatLoading: false,

        async fetchRagStats() {
            const res = await this.authFetch('/admin/ai/stats');
            this.ragStats = {
                total: res?.total || 0,
                ingested: res?.ingested || 0,
                remaining: res?.remaining || 0
            };
        },

        renderMarkdown(text) {
            if (!text) return '';

            return text
                .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-gray-900 dark:text-white">$1</strong>')

                .replace(/(^|[^\*])\*([^\* \s][^\*]*?[^\* \s])\*(?=[^\*]|$)/g, '$1<em class="italic">$2</em>')

                .replace(/^\* /gm, '• ')

                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" class="text-blue-400 underline font-bold hover:text-blue-300 transition-colors">$1</a>')

                .replace(/\n/g, '<br>');
        },

        async openRagPreview() {
            this.isRagModalOpen = true;
            const res = await this.authFetch('/admin/ai/rag-data');
            this.ragList = res.data || [];
        },

        async startAutoIngest() {
            if (this.ragStats.remaining === 0) return this.showToast('Info', 'Semua data lokal sudah siap.', 'success');

            this.askConfirm('Mulai Proses Lokal?', `Memproses ${this.ragStats.remaining} artikel ke dataset JSONL.`, async () => {
                this.isSyncing = true;
                this.loopIngest();
            });
        },

        async loopIngest() {
            this.progressMessage = `Memproses lokal... Sisa: ${this.ragStats.remaining}`;
            try {
                const res = await this.authFetch('/admin/ai/ingest-auto', { method: 'POST' });
                this.ragStats.remaining = res.remaining;
                this.ragStats.ingested = res.total_ingested;

                if (res.status === 'done') {
                    this.isSyncing = false;
                    this.progressMessage = 'Proses Lokal Selesai!';
                    this.showToast('Sukses', 'Dataset lokal diperbarui.');
                } else if (res.status === 'partial') {
                    setTimeout(() => { this.loopIngest(); }, 1000);
                } else if (res.status === 'rate_limited') {
                    this.startCooldown();
                }
            } catch (e) {
                this.isSyncing = false;
                this.showToast('Error', 'Koneksi terputus.', 'error');
            }
        },

        async syncToCloud() {
            this.askConfirm('Upload ke Cloud?', 'Kirim dataset ke Hugging Face Space?', async () => {
                this.isSyncing = true;
                this.progressMessage = 'Mengunggah ke HF Space...';
                try {
                    const res = await this.authFetch('/admin/ai/sync-cloud', { method: 'POST' });
                    if (res.status === 'success') {
                        this.showToast('Sukses', 'RAG Data untuk Amica berhasil diperbarui di Cloud.');
                    } else {
                        this.showToast('Gagal', res.message, 'error');
                    }
                } catch (e) {
                    this.showToast('Error', 'Gagal terhubung ke server.', 'error');
                } finally {
                    this.isSyncing = false;
                    this.progressMessage = 'Siap sinkronisasi';
                }
            });
        },

        async sendTestChat() {
            if (!this.chatInput.trim() || this.isChatLoading) return;

            const userMsg = this.chatInput;
            this.chatHistory.push({ role: 'user', text: userMsg });
            this.chatInput = '';
            this.isChatLoading = true;

            this.$nextTick(() => {
                const container = document.getElementById('chatContainer');
                if (container) container.scrollTop = container.scrollHeight;
            });

            try {
                const response = await fetch('/api/chats/ask-ai-admin', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${this.token}`
                    },
                    body: JSON.stringify({ message: userMsg })
                });

                const data = await response.json();
                this.isChatLoading = false;

                if (data.status === 'success') {
                    const fullText = data.reply;
                    const msgIndex = this.chatHistory.push({ role: 'amica', text: '' }) - 1;

                    let i = 0;
                    const typeWriter = () => {
                        if (i < fullText.length) {
                            this.chatHistory[msgIndex].text += fullText.charAt(i);
                            i++;

                            const container = document.getElementById('chatContainer');
                            if (container) container.scrollTop = container.scrollHeight;

                            setTimeout(typeWriter, 10);
                        } else {
                            this.chatHistory = [...this.chatHistory];
                        }
                    };
                    typeWriter();

                } else { throw new Error(data.message); }

            } catch (e) {
                this.isChatLoading = false;
                this.chatHistory.push({ role: 'amica', text: "Error: " + e.message });
            }
        },
        startCooldown() {
            this.isWaitMode = true;
            this.countdown = 70;
            const timer = setInterval(() => {
                this.countdown--;
                this.progressMessage = `Limit API! Menunggu: ${this.countdown}s`;
                if (this.countdown <= 0) {
                    clearInterval(timer);
                    this.isWaitMode = false;
                    this.loopIngest();
                }
            }, 1000);
        }
    }
}