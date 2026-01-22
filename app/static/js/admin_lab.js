function aiLabLogic() {
    return {
        labTestCases: [],
        labBenchmarkResults: [],
        labBenchSummary: { avg_mrr: 0, avg_llama: 0, avg_latency: 0 },
        labArticleList: [],
        labMessages: [],
        labChatInput: '',
        labLimitInput: 20,
        labTargetIdInput: '',
        labSearchQuery: '',
        showArticleDropdown: false,
        selectedArticleTitle: 'Semua Artikel (Acak)',
        isLabLoading: false,
        isLabRunningBench: false,
        isLabChatting: false,
        showDetailModal: false,
        showPreviewModal: false,
        selectedDetail: null,
        useLlamaJudge: false,

        initLab() {
            this.loadLabTestCases();
            this.loadLabResults();
            this.loadArticleList();
        },

        async labFetch(url, options = {}) {
            const headers = {
                'Authorization': 'Bearer ' + this.token,
                'Content-Type': 'application/json',
                ...options.headers
            };
            return fetch(url, { ...options, headers });
        },

        async loadArticleList() {
            try {
                const res = await this.labFetch('/admin/ai/article-list');
                const data = await res.json();
                this.labArticleList = Array.isArray(data) ? data : [];
            } catch(e) {}
        },

        selectArticle(id, title) {
            this.labTargetIdInput = id;
            this.selectedArticleTitle = title ? title : 'Semua Artikel (Acak)';
            this.showArticleDropdown = false;
            this.labSearchQuery = '';
        },

        async loadLabResults() {
            try {
                const res = await this.labFetch('/admin/ai/benchmark-results');
                const data = await res.json();
                this.labBenchmarkResults = Array.isArray(data) ? data : [];
                this.calcSummary(); 
            } catch(e) {}
        },

        async loadLabTestCases() {
            try {
                const res = await this.labFetch('/admin/ai/test-cases');
                const data = await res.json();
                this.labTestCases = Array.isArray(data) ? data : [];
            } catch(e) {}
        },

        async generateCases() {
            this.isLabLoading = true;
            try {
                const payload = { limit: parseInt(this.labLimitInput) };
                if(this.labTargetIdInput) payload.target_article_id = this.labTargetIdInput;
                const res = await this.labFetch('/admin/ai/test-cases', {
                    method: 'POST',
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if(data.status === 'success') {
                    this.showToast('Sukses', data.message);
                    this.loadLabTestCases();
                }
            } catch(e) {}
            this.isLabLoading = false;
        },

        async runBenchmark() {
            if(this.isLabRunningBench) return;
            this.isLabRunningBench = true;
            this.labBenchmarkResults = [];
            try {
                const res = await this.labFetch('/admin/ai/run-benchmark', {
                    method: 'POST',
                    body: JSON.stringify({ 
                        limit: this.labTestCases.length,
                        include_llm: this.useLlamaJudge
                    })
                });
                const data = await res.json();
                if(data.status === 'success') {
                    this.showToast('Selesai', 'Benchmark berhasil.');
                    await this.loadLabResults(); 
                }
            } catch(e) { 
                this.showToast('Error', 'Gagal benchmark', 'error'); 
            } finally {
                this.isLabRunningBench = false;
            }
        },

        async clearHistory() {
            if(!confirm("Hapus data?")) return;
            try {
                const res = await this.labFetch('/admin/ai/benchmark-results', { method: 'DELETE' });
                if(res.ok) {
                    this.labBenchmarkResults = [];
                    this.labBenchSummary = { avg_mrr: 0, avg_llama: 0, avg_latency: 0 };
                    this.showToast('Sukses', 'Bersih');
                }
            } catch(e) {}
        },

        async sendManualChat() {
            if(!this.labChatInput.trim()) return;
            const txt = this.labChatInput;
            
            // 1. PUSH PESAN USER
            this.labMessages.push({ id: Date.now(), role: 'user', text: txt, isLoading: false });
            this.labChatInput = '';
            this.isLabChatting = true;
            this.scrollToBottom();

            // 2. LANGSUNG PUSH PESAN AI (LOADING) SEBELUM FETCH
            // Ini membuat bubble loading langsung muncul tanpa menunggu server
            const aiMsgId = Date.now() + 1;
            this.labMessages.push({ id: aiMsgId, role: 'ai', text: '', isLoading: true });
            this.scrollToBottom();

            // Index pesan terakhir (pesan AI yg baru dibuat)
            const idx = this.labMessages.length - 1;

            try {
                const res = await this.labFetch('/admin/ai/ask-admin', {
                    method: 'POST',
                    body: JSON.stringify({ message: txt })
                });
                
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                
                while(true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    
                    if (chunk.includes('"type":') || chunk.includes('{"type":') || chunk.trim().startsWith('{')) {
                        continue;
                    }

                    if (this.labMessages[idx].isLoading && chunk.trim().length > 0) {
                        this.labMessages[idx].isLoading = false;
                    }
                    
                    this.labMessages[idx].text += chunk;
                    this.scrollToBottom();
                }
            } catch(e) {
                // Jika error, update pesan AI yang sudah dibuat tadi
                if (this.labMessages[idx]) {
                     this.labMessages[idx].isLoading = false;
                     this.labMessages[idx].text = "[Error: Gagal terhubung ke server]";
                }
            }
            this.isLabChatting = false;
        },

        scrollToBottom() {
            this.$nextTick(() => { 
                const b = document.getElementById('manualChatBox'); 
                if(b) b.scrollTop = b.scrollHeight; 
            });
        },

        openDetail(result) {
            this.selectedDetail = result;
            this.showDetailModal = true;
        },

        openPreview() {
            this.showPreviewModal = true;
        },

        calcSummary() {
            if(!this.labBenchmarkResults.length) {
                this.labBenchSummary = { avg_mrr: 0, avg_llama: 0, avg_latency: 0 };
                return;
            }
            let tM = 0, tL = 0, tA = 0, countLlama = 0;
            this.labBenchmarkResults.forEach(r => {
                tM += r.mrr_score;
                tA += r.latency;
                if(r.llama_score > 0) {
                    tL += r.llama_score;
                    countLlama++;
                }
            });
            const n = this.labBenchmarkResults.length;
            this.labBenchSummary = { 
                avg_mrr: (tM / n).toFixed(2), 
                avg_llama: countLlama > 0 ? (tL / countLlama).toFixed(1) : 0, 
                avg_latency: (tA / n).toFixed(2) 
            };
        },

        renderMarkdown(text) {
            if (!text) return '';
            let html = text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            const linkRegex = /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g;
            html = html.replace(linkRegex, `
                <a href="$2" target="_blank" class="inline-flex items-center gap-2 px-3 py-1.5 mt-2 mb-1 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-bold hover:bg-indigo-500/20 transition decoration-none">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    $1
                </a>
            `);
            return html.replace(/\n/g, '<br>');
        }
    }
}