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
        statusInfo: '',

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
            this.isChatLoading = true; // Menyalakan animasi bounce di bubble
            this.statusInfo = '';

            const container = document.getElementById('chatContainer');
            this.$nextTick(() => { if (container) container.scrollTop = container.scrollHeight; });

            try {
                const response = await fetch('/api/bot/ask-admin', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${this.token}` },
                    body: JSON.stringify({ message: userMsg })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let firstChunkReceived = false;
                let msgIndex = -1;

                let charBuffer = [];
                let isTyping = false;

                const processBuffer = () => {
                    if (charBuffer.length > 0) {
                        isTyping = true;
                        this.chatHistory[msgIndex].text += charBuffer.shift();
                        if (container) container.scrollTop = container.scrollHeight;
                        setTimeout(processBuffer, 5);
                    } else {
                        isTyping = false;
                    }
                };

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });

                    if (chunk.includes("[STATUS:QUEUED]")) {
                        this.statusInfo = "Semua server penuh, mengantri slot...";
                        continue;
                    }
                    if (chunk.includes("[STATUS:WAITING_LIST]")) {
                        this.statusInfo = "Slot didapat! Menunggu giliran proses AI...";
                        continue;
                    }
                    if (chunk.includes("[STATUS:PROCESSING]")) {
                        this.statusInfo = "Slot kosong ditemukan! Amica sedang berpikir...";
                        continue;
                    }
                    if (chunk === "[HEARTBEAT]") continue;

                    if (!firstChunkReceived) {
                        this.isChatLoading = false;
                        this.statusInfo = "Amica sedang mengetik...";
                        msgIndex = this.chatHistory.push({ role: 'amica', text: '' }) - 1;
                        firstChunkReceived = true;
                    }

                    for (let char of chunk) {
                        charBuffer.push(char);
                    }
                    if (!isTyping) processBuffer();
                }

                // Hilangkan status setelah selesai mengetik
                setTimeout(() => { this.statusInfo = ""; }, 2000);

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