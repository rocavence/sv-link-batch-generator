// StreetVoice sv.link 批次工具 - 前端邏輯

class SVLinkBatchGenerator {
    constructor() {
        this.results = [];
        this.lookupResults = [];
        this.updateData = [];
        this.updateResults = [];
        this.processing = false;
        this.currentTab = 'generate';
        this.initEventListeners();
        this.initUI();
        this.initLineNumbers();
    }

    initEventListeners() {
        // Tab 切換
        document.getElementById('generateTab').addEventListener('click', () => this.switchTab('generate'));
        document.getElementById('lookupTab').addEventListener('click', () => this.switchTab('lookup'));
        document.getElementById('updateTab').addEventListener('click', () => this.switchTab('update'));

        // 批次生成事件
        document.getElementById('processBtn').addEventListener('click', () => this.processUrls());
        document.getElementById('exportCsv').addEventListener('click', () => this.exportCsv());
        document.getElementById('exportQrZip').addEventListener('click', () => this.exportQrZip());

        // 批次反查事件
        document.getElementById('lookupBtn').addEventListener('click', () => this.lookupUrls());
        document.getElementById('lookupExportCsv').addEventListener('click', () => this.exportLookupCsv());

        // 批次修改事件
        document.getElementById('updateLookupBtn').addEventListener('click', () => this.lookupCurrentTargets());
        document.getElementById('updateConfirmBtn').addEventListener('click', () => this.confirmUpdate());
        document.getElementById('updateExecuteBtn').addEventListener('click', () => this.executeBatchUpdate());
        document.getElementById('updateExportCsv').addEventListener('click', () => this.exportUpdateCsv());

        // 輸入驗證
        document.getElementById('apiKey').addEventListener('input', () => this.validateInputs());
        document.getElementById('urlList').addEventListener('input', () => {
            this.validateInputs();
            this.updateLineNumbers();
        });
        document.getElementById('linkList').addEventListener('input', () => this.updateLookupLineNumbers());
        document.getElementById('updateLinkList').addEventListener('input', () => this.updateUpdateLineNumbers());

        // 滾動同步
        document.getElementById('urlList').addEventListener('scroll', (e) => {
            document.getElementById('lineNumbers').scrollTop = e.target.scrollTop;
        });
        document.getElementById('linkList').addEventListener('scroll', (e) => {
            document.getElementById('lookupLineNumbers').scrollTop = e.target.scrollTop;
        });
        document.getElementById('updateLinkList').addEventListener('scroll', (e) => {
            document.getElementById('updateLineNumbers').scrollTop = e.target.scrollTop;
        });

        // Enter 鍵支援
        document.getElementById('apiKey').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.processUrls();
        });
        document.getElementById('lookupApiKey').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.lookupUrls();
        });
        document.getElementById('updateApiKey').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.lookupCurrentTargets();
        });
    }

    initUI() {
        // 隱藏結果和匯出區域
        document.getElementById('results').style.display = 'none';
        document.getElementById('exportSection').style.display = 'none';
        document.getElementById('lookupResults').style.display = 'none';
        document.getElementById('lookupExportSection').style.display = 'none';
        document.getElementById('updateResults').style.display = 'none';
        document.getElementById('updateExportSection').style.display = 'none';
        
        // 預設按鈕狀態
        this.updateProcessButton(false);
    }

    initLineNumbers() {
        this.updateLineNumbers();
        this.updateLookupLineNumbers();
        this.updateUpdateLineNumbers();
    }

    // Tab 切換功能
    switchTab(tab) {
        // 移除所有 active 狀態
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        // 設定新的 active 狀態
        document.getElementById(tab + 'Tab').classList.add('active');
        document.getElementById(tab + 'Content').classList.add('active');
        
        this.currentTab = tab;
        
        // 重置結果區域
        if (tab === 'generate') {
            document.getElementById('results').style.display = 'none';
            document.getElementById('exportSection').style.display = 'none';
        } else if (tab === 'lookup') {
            document.getElementById('lookupResults').style.display = 'none';
            document.getElementById('lookupExportSection').style.display = 'none';
        } else if (tab === 'update') {
            this.resetUpdateFlow();
        }
    }

    // 行號更新功能
    updateLineNumbers() {
        const lines = document.getElementById('urlList').value.split('\n');
        const lineCount = Math.max(lines.length, 1);
        let numbers = '';
        for (let i = 1; i <= lineCount; i++) {
            numbers += i + (i < lineCount ? '\n' : '');
        }
        document.getElementById('lineNumbers').textContent = numbers;
    }

    updateLookupLineNumbers() {
        const lines = document.getElementById('linkList').value.split('\n');
        const lineCount = Math.max(lines.length, 1);
        let numbers = '';
        for (let i = 1; i <= lineCount; i++) {
            numbers += i + (i < lineCount ? '\n' : '');
        }
        document.getElementById('lookupLineNumbers').textContent = numbers;
    }

    updateUpdateLineNumbers() {
        const lines = document.getElementById('updateLinkList').value.split('\n');
        const lineCount = Math.max(lines.length, 1);
        let numbers = '';
        for (let i = 1; i <= lineCount; i++) {
            numbers += i + (i < lineCount ? '\n' : '');
        }
        document.getElementById('updateLineNumbers').textContent = numbers;
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

    // 批次生成功能
    async processUrls() {
        if (!this.validateInputs() || this.processing) {
            return;
        }

        const apiKey = document.getElementById('apiKey').value.trim();
        const urlList = document.getElementById('urlList').value.trim();

        const urls = urlList.split('\n')
            .map(url => url.trim())
            .filter(url => url.length > 0);

        if (urls.length === 0) {
            this.showStatus('請輸入有效的網址清單', 'error');
            return;
        }

        this.processing = true;
        this.setLoading(true);
        this.showProgress(true);
        this.hideResults();
        this.results = [];

        try {
            this.showStatus(`開始處理 ${urls.length} 個網址...`, 'success');

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
                this.displayResults(data.results, data.summary);
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

    // 批次反查功能
    async lookupUrls() {
        const apiKey = document.getElementById('lookupApiKey').value.trim();
        const linkText = document.getElementById('linkList').value.trim();

        if (!apiKey) {
            alert('請輸入 API Key');
            return;
        }

        if (!linkText) {
            alert('請輸入要反查的短網址');
            return;
        }

        const links = linkText.split('\n').filter(link => link.trim());

        if (links.length === 0) {
            alert('請輸入有效的短網址');
            return;
        }

        this.setLookupLoading(true);
        this.showLookupProgress(true);

        try {
            const response = await fetch('/api/lookup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    api_key: apiKey,
                    links: links
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '反查失敗');
            }

            this.lookupResults = data.results;
            this.displayLookupResults(data.results, data.summary);

        } catch (error) {
            alert(`錯誤: ${error.message}`);
            console.error('反查錯誤:', error);
        } finally {
            this.setLookupLoading(false);
            this.showLookupProgress(false);
        }
    }

    // 批次修改功能
    async lookupCurrentTargets() {
        const apiKey = document.getElementById('updateApiKey').value.trim();
        const linkText = document.getElementById('updateLinkList').value.trim();

        if (!apiKey) {
            alert('請輸入 API Key');
            return;
        }

        if (!linkText) {
            alert('請輸入要修改的短網址');
            return;
        }

        const links = linkText.split('\n').filter(link => link.trim());

        if (links.length === 0) {
            alert('請輸入有效的短網址');
            return;
        }

        this.setUpdateLookupLoading(true);
        this.showUpdateLookupProgress(true);

        try {
            const response = await fetch('/api/batch-lookup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    api_key: apiKey,
                    links: links
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '查詢失敗');
            }

            this.updateData = data.results;
            this.showUpdateEditStage();

        } catch (error) {
            alert(`錯誤: ${error.message}`);
            console.error('查詢錯誤:', error);
        } finally {
            this.setUpdateLookupLoading(false);
            this.showUpdateLookupProgress(false);
        }
    }

    showUpdateEditStage() {
        document.getElementById('updateStage1').style.display = 'none';
        document.getElementById('updateStage2').style.display = 'block';
        
        const container = document.getElementById('updateEditContainer');
        let html = `
            <div class="update-edit-header">
                <div class="update-col">短網址</div>
                <div class="update-col">目前目標</div>
                <div class="update-col">新目標</div>
            </div>
        `;

        this.updateData.forEach((item, index) => {
            const shortUrl = item.link;
            const currentTarget = item.success ? item.target : '查詢失敗';
            const statusClass = item.success ? 'success' : 'failed';
            
            html += `
                <div class="update-edit-row ${statusClass}">
                    <div class="update-col short-url">${shortUrl}</div>
                    <div class="update-col current-target">${currentTarget}</div>
                    <div class="update-col new-target">
                        ${item.success ? 
                            `<input type="text" class="update-input" data-index="${index}" placeholder="輸入新的目標網址">` : 
                            '<span class="error-text">無法修改</span>'
                        }
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    confirmUpdate() {
        const inputs = document.querySelectorAll('.update-input');
        const changes = [];

        inputs.forEach(input => {
            const index = parseInt(input.dataset.index);
            const newTarget = input.value.trim();
            
            if (newTarget) {
                const item = this.updateData[index];
                changes.push({
                    index: index,
                    shortUrl: item.link,
                    currentTarget: item.target,
                    newTarget: newTarget,
                    linkId: item.linkId
                });
            }
        });

        if (changes.length === 0) {
            alert('請至少輸入一個新的目標網址');
            return;
        }

        this.showUpdateConfirmStage(changes);
    }

    showUpdateConfirmStage(changes) {
        document.getElementById('updateStage2').style.display = 'none';
        document.getElementById('updateStage3').style.display = 'block';
        
        const container = document.getElementById('updateConfirmList');
        let html = `
            <div class="update-confirm-summary">
                即將修改 ${changes.length} 個短網址：
            </div>
        `;

        changes.forEach((change) => {
            html += `
                <div class="update-confirm-item">
                    <div class="confirm-row">
                        <strong>${change.shortUrl}</strong>
                    </div>
                    <div class="confirm-row">
                        <span class="label">目前：</span>${change.currentTarget}
                    </div>
                    <div class="confirm-row">
                        <span class="label">修改為：</span>${change.newTarget}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
        this.pendingChanges = changes;
    }

    async executeBatchUpdate() {
        const changes = this.pendingChanges;
        
        if (!changes || changes.length === 0) {
            alert('沒有要修改的項目');
            return;
        }

        this.setUpdateExecuteLoading(true);
        this.showUpdateExecuteProgress(true);

        try {
            const response = await fetch('/api/batch-update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    api_key: document.getElementById('updateApiKey').value.trim(),
                    changes: changes
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '修改失敗');
            }

            this.updateResults = data.results;
            this.showUpdateResults(data.results, data.summary);

        } catch (error) {
            alert(`錯誤: ${error.message}`);
            console.error('修改錯誤:', error);
        } finally {
            this.setUpdateExecuteLoading(false);
            this.showUpdateExecuteProgress(false);
        }
    }

    resetUpdateFlow() {
        document.getElementById('updateStage1').style.display = 'block';
        document.getElementById('updateStage2').style.display = 'none';
        document.getElementById('updateStage3').style.display = 'none';
        document.getElementById('updateResults').style.display = 'none';
        document.getElementById('updateExportSection').style.display = 'none';
        this.updateData = [];
        this.updateResults = [];
        this.pendingChanges = null;
    }

    // 載入狀態管理
    setLoading(isLoading) {
        const btn = document.getElementById('processBtn');
        const loading = document.getElementById('loading');
        const btnText = document.getElementById('btnText');

        loading.style.display = isLoading ? 'block' : 'none';
        btnText.textContent = isLoading ? '處理中...' : '開始處理';
        
        this.updateProcessButton(!isLoading);
    }

    setLookupLoading(isLoading) {
        const btn = document.getElementById('lookupBtn');
        const loading = document.getElementById('lookupLoading');
        const btnText = document.getElementById('lookupBtnText');

        btn.disabled = isLoading;
        loading.style.display = isLoading ? 'block' : 'none';
        btnText.textContent = isLoading ? '反查中...' : '開始反查';
    }

    setUpdateLookupLoading(isLoading) {
        const btn = document.getElementById('updateLookupBtn');
        const loading = document.getElementById('updateLookupLoading');
        const btnText = document.getElementById('updateLookupBtnText');

        btn.disabled = isLoading;
        loading.style.display = isLoading ? 'block' : 'none';
        btnText.textContent = isLoading ? '查詢中...' : '查詢當前目標';
    }

    setUpdateExecuteLoading(isLoading) {
        const btn = document.getElementById('updateExecuteBtn');
        const loading = document.getElementById('updateExecuteLoading');
        const text = document.getElementById('updateExecuteBtnText');
        
        btn.disabled = isLoading;
        loading.style.display = isLoading ? 'block' : 'none';
        text.textContent = isLoading ? '修改中...' : '執行修改';
    }

    // 進度條管理
    showProgress(show) {
        const progress = document.getElementById('progress');
        const progressBar = document.getElementById('progressBar');
        
        progress.style.display = show ? 'block' : 'none';
        
        if (show) {
            progressBar.style.width = '30%';
            setTimeout(() => progressBar.style.width = '60%', 500);
            setTimeout(() => progressBar.style.width = '90%', 1000);
        } else {
            progressBar.style.width = '100%';
            setTimeout(() => progressBar.style.width = '0%', 300);
        }
    }

    showLookupProgress(show) {
        const progress = document.getElementById('lookupProgress');
        const progressBar = document.getElementById('lookupProgressBar');
        
        progress.style.display = show ? 'block' : 'none';
        if (show) {
            progressBar.style.width = '0%';
            setTimeout(() => progressBar.style.width = '100%', 100);
        }
    }

    showUpdateLookupProgress(show) {
        const progress = document.getElementById('updateLookupProgress');
        const progressBar = document.getElementById('updateLookupProgressBar');
        
        progress.style.display = show ? 'block' : 'none';
        if (show) {
            progressBar.style.width = '0%';
            setTimeout(() => progressBar.style.width = '100%', 100);
        }
    }

    showUpdateExecuteProgress(show) {
        const progress = document.getElementById('updateExecuteProgress');
        const progressBar = document.getElementById('updateExecuteProgressBar');
        
        progress.style.display = show ? 'block' : 'none';
        if (show) {
            progressBar.style.width = '0%';
            setTimeout(() => progressBar.style.width = '100%', 100);
        }
    }

    // 結果顯示
    displayResults(resultsData, summary) {
        let html = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th style="width: 80px;">狀態</th>
                        <th style="width: 60px;">編號</th>
                        <th>原始網址</th>
                        <th>短網址</th>
                        <th style="width: 90px;">操作</th>
                    </tr>
                </thead>
                <tbody>
        `;

        resultsData.forEach((result, index) => {
            const statusClass = result.success ? 'status-success' : 'status-failed';
            const statusText = result.success ? '成功' : '失敗';
            const copyButton = result.success ? 
                `<button class="copy-btn" onclick="app.copyToClipboard('${result.short}', this)">複製</button>` : 
                '<span style="color: #ccc;">-</span>';
            
            html += `
                <tr>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                    <td><span class="row-number">${index + 1}</span></td>
                    <td class="url-cell original-url">${result.original}</td>
                    <td class="url-cell short-url">${result.short}</td>
                    <td>${copyButton}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        
        const summaryHtml = `
            <div style="display: flex; gap: 20px; justify-content: center; margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <div><span style="color: #6c757d; margin-right: 5px;">總數:</span><span style="font-weight: 600; color: #333;">${summary.total}</span></div>
                <div><span style="color: #6c757d; margin-right: 5px;">成功:</span><span style="font-weight: 600; color: #28a745;">${summary.success}</span></div>
                <div><span style="color: #6c757d; margin-right: 5px;">失敗:</span><span style="font-weight: 600; color: #dc3545;">${summary.failed}</span></div>
            </div>
        `;

        document.getElementById('resultList').innerHTML = summaryHtml + html;
        document.getElementById('results').style.display = 'block';
        document.getElementById('exportSection').style.display = 'block';
    }

    displayLookupResults(resultsData, summary) {
        let html = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th style="width: 80px;">狀態</th>
                        <th style="width: 60px;">編號</th>
                        <th>短網址</th>
                        <th style="width: 100px;">觀看次數</th>
                        <th>目標網址</th>
                        <th style="width: 90px;">操作</th>
                    </tr>
                </thead>
                <tbody>
        `;

        resultsData.forEach((result, index) => {
            const statusClass = result.success ? 'status-success' : 'status-failed';
            const statusText = result.success ? '成功' : '失敗';
            const copyButton = result.success ? 
                `<button class="copy-btn" onclick="app.copyToClipboard('${result.views}', this)">複製</button>` : 
                '<span style="color: #ccc;">-</span>';
            
            html += `
                <tr>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                    <td><span class="row-number">${index + 1}</span></td>
                    <td class="url-cell short-url">${result.link}</td>
                    <td style="text-align: center; font-weight: 600; color: #FF6B6B;">${result.views}</td>
                    <td class="url-cell original-url">${result.target}</td>
                    <td>${copyButton}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        
        const summaryHtml = `
            <div style="display: flex; gap: 20px; justify-content: center; margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <div><span style="color: #6c757d; margin-right: 5px;">總數:</span><span style="font-weight: 600; color: #333;">${summary.total}</span></div>
                <div><span style="color: #6c757d; margin-right: 5px;">成功:</span><span style="font-weight: 600; color: #28a745;">${summary.success}</span></div>
                <div><span style="color: #6c757d; margin-right: 5px;">失敗:</span><span style="font-weight: 600; color: #dc3545;">${summary.failed}</span></div>
            </div>
        `;

        document.getElementById('lookupResultList').innerHTML = summaryHtml + html;
        document.getElementById('lookupResults').style.display = 'block';
        document.getElementById('lookupExportSection').style.display = 'block';
    }

    showUpdateResults(resultsData, summary) {
        document.getElementById('updateStage3').style.display = 'none';
        
        let html = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th style="width: 80px;">狀態</th>
                        <th style="width: 60px;">編號</th>
                        <th>短網址</th>
                        <th>新目標網址</th>
                        <th style="width: 90px;">操作</th>
                    </tr>
                </thead>
                <tbody>
        `;

        resultsData.forEach((result, index) => {
            const statusClass = result.success ? 'status-success' : 'status-failed';
            const statusText = result.success ? '成功' : '失敗';
            const copyButton = result.success ? 
                `<button class="copy-btn" onclick="app.copyToClipboard('${result.shortUrl}', this)">複製</button>` : 
                '<span style="color: #ccc;">-</span>';
            
            html += `
                <tr>
                    <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                    <td><span class="row-number">${index + 1}</span></td>
                    <td class="url-cell short-url">${result.shortUrl}</td>
                    <td class="url-cell original-url">${result.newTarget}</td>
                    <td>${copyButton}</td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        
        const summaryHtml = `
            <div style="display: flex; gap: 20px; justify-content: center; margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <div><span style="color: #6c757d; margin-right: 5px;">總數:</span><span style="font-weight: 600; color: #333;">${summary.total}</span></div>
                <div><span style="color: #6c757d; margin-right: 5px;">成功:</span><span style="font-weight: 600; color: #28a745;">${summary.success}</span></div>
                <div><span style="color: #6c757d; margin-right: 5px;">失敗:</span><span style="font-weight: 600; color: #dc3545;">${summary.failed}</span></div>
            </div>
        `;

        document.getElementById('updateResultList').innerHTML = summaryHtml + html;
        document.getElementById('updateResults').style.display = 'block';
        document.getElementById('updateExportSection').style.display = 'block';
    }

    hideResults() {
        document.getElementById('results').style.display = 'none';
        document.getElementById('exportSection').style.display = 'none';
    }

    // 匯出功能
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
                    results: this.results
                })
            });

            const data = await response.json();

            if (response.ok && data.content) {
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

    async exportLookupCsv() {
        if (!this.lookupResults || this.lookupResults.length === 0) {
            alert('請先進行反查');
            return;
        }

        try {
            const response = await fetch('/api/export/lookup-csv', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    results: this.lookupResults
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '匯出失敗');
            }

            const blob = new Blob([atob(data.content)], { type: data.mimetype });
            this.downloadBlob(blob, data.filename);

        } catch (error) {
            alert(`匯出失敗: ${error.message}`);
        }
    }

    async exportUpdateCsv() {
        if (!this.updateResults || this.updateResults.length === 0) {
            alert('請先進行修改');
            return;
        }

        try {
            const response = await fetch('/api/export/update-csv', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    results: this.updateResults
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '匯出失敗');
            }

            const blob = new Blob([atob(data.content)], { type: data.mimetype });
            this.downloadBlob(blob, data.filename);

        } catch (error) {
            alert(`匯出失敗: ${error.message}`);
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

        // 儲存結果到 sessionStorage 並打開 QR Gallery
        sessionStorage.setItem('qr_results', JSON.stringify(this.results));
        window.open('/qr-gallery', '_blank');
    }

    // 工具函數
    async copyToClipboard(text, button) {
        try {
            await navigator.clipboard.writeText(text);
            const originalText = button.textContent;
            button.textContent = '已複製';
            button.classList.add('copied');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copied');
            }, 2000);
        } catch (err) {
            console.error('複製失敗:', err);
            alert('複製失敗，請手動複製');
        }
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
        
        setTimeout(() => URL.revokeObjectURL(url), 100);
    }

    showStatus(message, type) {
        const statusDiv = document.getElementById('statusMessage');
        
        if (statusDiv) {
            statusDiv.textContent = message;
            statusDiv.className = `status-message status-${type}`;
            statusDiv.style.display = 'block';

            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 5000);
        }
    }
}

// 全域函數
function switchTab(tab) {
    if (window.app) {
        window.app.switchTab(tab);
    }
}

function resetUpdateFlow() {
    if (window.app) {
        window.app.resetUpdateFlow();
    }
}

function backToUpdateStage1() {
    document.getElementById('updateStage2').style.display = 'none';
    document.getElementById('updateStage1').style.display = 'block';
}

function backToUpdateStage2() {
    document.getElementById('updateStage3').style.display = 'none';
    document.getElementById('updateStage2').style.display = 'block';
}

// 初始化應用程式
document.addEventListener('DOMContentLoaded', () => {
    console.log('StreetVoice sv.link 批次工具初始化...');
    
    window.app = new SVLinkBatchGenerator();
    
    console.log('應用程式初始化完成');
});