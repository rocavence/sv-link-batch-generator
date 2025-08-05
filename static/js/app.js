// StreetVoice sv.link 批次短網址生成器 - 前端邏輯

class SVLinkBatchGenerator {
    constructor() {
        this.results = [];
        this.processing = false;
        this.initEventListeners();
        this.initUI();
    }

    initEventListeners() {
        // 主要按鈕事件
        document.getElementById('processBtn').addEventListener('click', () => this.processUrls());
        document.getElementById('exportCsv').addEventListener('click', () => this.exportCsv());
        document.getElementById('exportQrZip').addEventListener('click', () => this.exportQrZip());

        // 輸入驗證
        document.getElementById('apiKey').addEventListener('input', () => this.validateInputs());
        document.getElementById('urlList').addEventListener('input', () => this.validateInputs());
    }

    initUI() {
        // 隱藏結果和匯出區域
        document.getElementById('results').style.display = 'none';
        document.getElementById('exportSection').style.display = 'none';
        
        // 預設按鈕狀態
        this.updateProcessButton(false);
    }

    validateInputs() {
        const apiKey = document.getElementById('apiKey').value.trim();
        const urlList = document.getElementById('urlList').value.trim();
        
        const isValid = apiKey.length > 0 && urlList.length > 0;
        this.updateProcessButton(isValid);
        
        return isValid;
    }

    updateProcessButton(enabled) {
        const btn = document.getElementById('processBtn');
        btn.disabled = !enabled || this.processing;
    }

    async processUrls() {
        if (!this.validateInputs() || this.processing) {
            return;
        }

        const apiKey = document.getElementById('apiKey').value.trim();
        const urlList = document.getElementById('urlList').value.trim();

        // 解析網址列表
        const urls = urlList.split('\n')
            .map(url => url.trim())
            .filter(url => url.length > 0);

        if (urls.length === 0) {
            this.showStatus('請輸入有效的網址清單', 'error');
            return;
        }

        // 檢測重複 URL
        const duplicates = this.findDuplicateUrls(urls);
        if (duplicates.length > 0) {
            const duplicateList = duplicates.join(', ');
            this.showStatus(`⚠️ 偵測到重複網址：${duplicateList}（每個重複網址都會產生新的短網址）`, 'error');
            
            // 等待 3 秒讓使用者看到警告，然後繼續處理
            await new Promise(resolve => setTimeout(resolve, 3000));
        }

        // 開始處理
        this.processing = true;
        this.setLoading(true);
        this.showProgress(true);
        this.hideResults();
        this.results = [];

        try {
            // 顯示處理開始訊息
            this.showStatus(`開始處理 ${urls.length} 個網址...`, 'success');

            // 呼叫 Render API
            const response = await fetch('/api/shorten', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    api_key: apiKey,
                    urls: urls
                })
            });

            const data = await response.json();

            if (response.ok && data.results) {
                this.results = data.results;
                const successCount = this.results.filter(r => r.success).length;
                const totalCount = this.results.length;
                
                this.displayResults();
                this.showStatus(`處理完成！成功生成 ${successCount}/${totalCount} 個短網址`, 'success');
            } else {
                throw new Error(data.error || '處理失敗');
            }

        } catch (error) {
            console.error('處理錯誤:', error);
            this.showStatus(`處理失敗: ${error.message}`, 'error');
        } finally {
            this.processing = false;
            this.setLoading(false);
            this.showProgress(false);
            this.updateProcessButton(true);
        }
    }

    findDuplicateUrls(urls) {
        const urlCounts = {};
        const duplicates = [];
        
        // 計算每個 URL 出現的次數
        urls.forEach(url => {
            const normalizedUrl = url.toLowerCase().trim();
            urlCounts[normalizedUrl] = (urlCounts[normalizedUrl] || 0) + 1;
        });
        
        // 找出重複的 URL
        Object.keys(urlCounts).forEach(url => {
            if (urlCounts[url] > 1) {
                duplicates.push(url);
            }
        });
        
        return duplicates;
    }

    displayResults() {
        const resultsDiv = document.getElementById('results');
        const resultList = document.getElementById('resultList');
        const exportSection = document.getElementById('exportSection');

        // 清空現有結果
        resultList.innerHTML = '';

        // 生成結果項目
        this.results.forEach((result, index) => {
            const item = document.createElement('div');
            item.className = 'result-item';
            
            const originalDiv = document.createElement('div');
            originalDiv.className = 'result-original';
            originalDiv.textContent = `${index + 1}. ${result.original}`;
            
            const shortDiv = document.createElement('div');
            shortDiv.className = 'result-short';
            shortDiv.textContent = result.short;
            
            // 如果成功，設置可點擊連結
            if (result.success && result.short.startsWith('http')) {
                shortDiv.innerHTML = `<a href="${result.short}" target="_blank" style="color: #FF6B6B; text-decoration: none;">${result.short}</a>`;
            }
            
            item.appendChild(originalDiv);
            item.appendChild(shortDiv);
            resultList.appendChild(item);
        });

        // 顯示結果區域
        resultsDiv.style.display = 'block';
        exportSection.style.display = 'block';

        // 滾動到結果區域
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    hideResults() {
        document.getElementById('results').style.display = 'none';
        document.getElementById('exportSection').style.display = 'none';
    }

    async exportCsv() {
        if (this.results.length === 0) {
            this.showStatus('沒有可匯出的數據', 'error');
            return;
        }

        try {
            const response = await fetch('/api/export/csv', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    results: this.results,
                    type: 'csv'
                })
            });

            const data = await response.json();

            if (response.ok && data.content) {
                // 解碼 base64 內容
                const csvContent = atob(data.content);
                const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8-sig;' });
                this.downloadBlob(blob, data.filename || 'sv-link-results.csv');
                this.showStatus('CSV 檔案已下載', 'success');
            } else {
                throw new Error(data.error || '匯出失敗');
            }

        } catch (error) {
            console.error('CSV 匯出錯誤:', error);
            this.showStatus(`CSV 匯出失敗: ${error.message}`, 'error');
        }
    }

    async exportQrZip() {
        if (this.results.length === 0) {
            this.showStatus('沒有可匯出的數據', 'error');
            return;
        }

        const successResults = this.results.filter(r => r.success);
        if (successResults.length === 0) {
            this.showStatus('沒有成功的短網址可生成 QR Code', 'error');
            return;
        }

        try {
            this.showStatus(`正在生成 ${successResults.length} 個 QR Code...`, 'success');
            
            const response = await fetch('/api/qr/zip', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    results: this.results
                })
            });

            const data = await response.json();

            if (response.ok && data.content) {
                // 解碼 base64 內容
                const zipContent = atob(data.content);
                const blob = new Blob([zipContent], { type: 'application/zip' });
                this.downloadBlob(blob, data.filename || 'sv-link-qrcodes.zip');
                this.showStatus(`QR Code ZIP 已下載 (${successResults.length} 個)`, 'success');
            } else {
                throw new Error(data.error || 'QR Code 生成失敗');
            }

        } catch (error) {
            console.error('QR Code ZIP 匯出錯誤:', error);
            this.showStatus(`QR Code 匯出失敗: ${error.message}`, 'error');
        }
    }

    async generateQrSvg(url) {
        return new Promise((resolve, reject) => {
            try {
                // 使用 qrcode.js 生成 SVG
                QRCode.toString(url, {
                    type: 'svg',
                    width: 256,
                    margin: 2,
                    color: {
                        dark: '#FF6B6B',  // 街聲紅色
                        light: '#FFFFFF'  // 白色背景
                    }
                }, (err, svg) => {
                    if (err) {
                        reject(err);
                    } else {
                        resolve(svg);
                    }
                });
            } catch (error) {
                reject(error);
            }
        });
    }

    getFilenameFromUrl(url) {
        // 從 StreetVoice URL 提取藝人名稱
        const match = url.match(/streetvoice\.com\/([^\/\?]+)/);
        if (match) {
            return match[1].replace(/[^a-zA-Z0-9_-]/g, '_');
        }
        
        // 備用方案：使用時間戳
        return `url-${Date.now()}`;
    }

    downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        
        // 清理 URL 物件
        setTimeout(() => URL.revokeObjectURL(url), 100);
    }

    setLoading(isLoading) {
        const btn = document.getElementById('processBtn');
        const loading = document.getElementById('loading');
        const btnText = document.getElementById('btnText');

        loading.style.display = isLoading ? 'block' : 'none';
        btnText.textContent = isLoading ? '處理中...' : '開始處理';
        
        this.updateProcessButton(!isLoading);
    }

    showProgress(show) {
        const progress = document.getElementById('progress');
        const progressBar = document.getElementById('progressBar');
        
        progress.style.display = show ? 'block' : 'none';
        
        if (show) {
            // 模擬進度動畫
            progressBar.style.width = '30%';
            setTimeout(() => {
                progressBar.style.width = '60%';
            }, 500);
            setTimeout(() => {
                progressBar.style.width = '90%';
            }, 1000);
        } else {
            progressBar.style.width = '100%';
            setTimeout(() => {
                progressBar.style.width = '0%';
            }, 300);
        }
    }

    showStatus(message, type) {
        const statusDiv = document.getElementById('statusMessage');
        
        statusDiv.textContent = message;
        statusDiv.className = `status-message status-${type}`;
        statusDiv.style.display = 'block';

        // 自動隱藏狀態訊息
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

// 初始化應用程式
document.addEventListener('DOMContentLoaded', () => {
    console.log('StreetVoice sv.link 批次短網址生成器初始化...');
    
    // 檢查必要的依賴
    if (typeof JSZip === 'undefined') {
        console.warn('JSZip 庫未載入，使用後端 QR Code 生成');
    }
    
    // 啟動應用程式
    new SVLinkBatchGenerator();
    
    console.log('應用程式初始化完成');
});