class GapSightApp {
    constructor() {
        this.apiBase = window.location.origin;
        this.currentData = null;
        this.graph3D = null;
        this.graph2D = null;
        this.isRotating = true;
        this.currentVizMode = '3d';
        this.apiKey = localStorage.getItem('gapsight_api_key') || '';
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadSettings();
    }

    bindEvents() {
        document.getElementById('search-btn').addEventListener('click', () => this.handleSearch());
        document.getElementById('toggle-advanced').addEventListener('click', () => this.toggleAdvanced());
        
        document.getElementById('settings-btn').addEventListener('click', () => this.openSettings());
        document.getElementById('close-settings').addEventListener('click', () => this.closeSettings());
        document.getElementById('save-settings').addEventListener('click', () => this.saveSettings());
        document.querySelector('#settings-modal .modal-overlay').addEventListener('click', () => this.closeSettings());
        
        document.getElementById('close-prompt').addEventListener('click', () => this.closePromptModal());
        document.getElementById('copy-prompt').addEventListener('click', () => this.copyPrompt());
        document.querySelector('#prompt-modal .modal-overlay').addEventListener('click', () => this.closePromptModal());
        
        document.getElementById('close-panel').addEventListener('click', () => this.closeNodePanel());
        
        document.getElementById('zoom-in').addEventListener('click', () => this.zoomIn());
        document.getElementById('zoom-out').addEventListener('click', () => this.zoomOut());
        document.getElementById('reset-view').addEventListener('click', () => this.resetView());
        document.getElementById('toggle-rotation').addEventListener('click', () => this.toggleRotation());
        
        document.getElementById('keyword1').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });
        document.getElementById('keyword2').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });
    }

    loadSettings() {
        const savedKey = localStorage.getItem('gapsight_api_key');
        if (savedKey) {
            document.getElementById('api-key').value = savedKey;
        }
    }

    toggleAdvanced() {
        const panel = document.getElementById('advanced-panel');
        const btn = document.getElementById('toggle-advanced');
        
        panel.classList.toggle('hidden');
        btn.textContent = panel.classList.contains('hidden') ? '高级选项 ▼' : '高级选项 ▲';
    }

    openSettings() {
        document.getElementById('settings-modal').classList.remove('hidden');
    }

    closeSettings() {
        document.getElementById('settings-modal').classList.add('hidden');
    }

    saveSettings() {
        const apiKey = document.getElementById('api-key').value.trim();
        localStorage.setItem('gapsight_api_key', apiKey);
        this.apiKey = apiKey;
        this.showToast('设置已保存');
        this.closeSettings();
    }

    async handleSearch() {
        const keyword1 = document.getElementById('keyword1').value.trim();
        const keyword2 = document.getElementById('keyword2').value.trim();
        
        if (!keyword1) {
            this.showToast('请输入至少一个关键词');
            return;
        }

        const keywords = [keyword1];
        if (keyword2) {
            keywords.push(keyword2);
        }

        const maxPapers = parseInt(document.getElementById('max-papers').value) || 50;
        const yearsBack = parseInt(document.getElementById('years-back').value) || 5;
        const vizMode = document.getElementById('viz-mode').value;

        this.currentVizMode = vizMode;
        this.setLoading(true);

        try {
            const requestBody = {
                keywords: keywords,
                max_papers: maxPapers,
                years_back: yearsBack,
                visualization_mode: vizMode === '3d' ? '3d' : '2d'
            };

            if (this.apiKey) {
                requestBody.api_key = this.apiKey;
            }

            const response = await fetch(`${this.apiBase}/api/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '请求失败');
            }

            this.currentData = await response.json();
            this.renderResults();
            this.showToast(`分析完成: ${this.currentData.total_papers} 篇论文, ${this.currentData.total_entities} 个实体`);

        } catch (error) {
            console.error('Search error:', error);
            this.showToast('错误: ' + error.message);
        } finally {
            this.setLoading(false);
        }
    }

    setLoading(isLoading) {
        const btn = document.getElementById('search-btn');
        const spinner = btn.querySelector('.btn-spinner');
        const btnText = btn.querySelector('.btn-text');
        
        if (isLoading) {
            spinner.classList.remove('hidden');
            btnText.textContent = '分析中...';
            btn.disabled = true;
        } else {
            spinner.classList.add('hidden');
            btnText.textContent = '开始分析';
            btn.disabled = false;
        }
    }

    renderResults() {
        if (!this.currentData) return;

        document.getElementById('welcome-screen').classList.add('hidden');
        document.getElementById('graph-container').classList.remove('hidden');

        document.getElementById('stats-section').classList.remove('hidden');
        document.getElementById('stat-papers').textContent = this.currentData.total_papers;
        document.getElementById('stat-entities').textContent = this.currentData.total_entities;
        document.getElementById('stat-gaps').textContent = this.currentData.gap_pairs.length;

        document.getElementById('graph-info').textContent = 
            `节点: ${this.currentData.nodes.length} | 边: ${this.currentData.edges.length}`;

        this.renderGapList();
        this.renderGraph();
    }

    renderGapList() {
        const gapSection = document.getElementById('gap-section');
        const gapList = document.getElementById('gap-list');
        
        gapSection.classList.remove('hidden');
        gapList.innerHTML = '';

        const topGaps = this.currentData.gap_pairs.slice(0, 10);

        topGaps.forEach((gap, index) => {
            const item = document.createElement('div');
            item.className = 'gap-item';
            item.innerHTML = `
                <div class="gap-item-header">
                    <span class="gap-concepts">
                        <span>${gap.concept1}</span> ↔ <span>${gap.concept2}</span>
                    </span>
                    <span class="gap-score">${(gap.score * 100).toFixed(0)}%</span>
                </div>
                <div class="gap-reason">${gap.reason}</div>
            `;
            
            item.addEventListener('click', () => {
                this.showGapPrompt(gap);
                this.highlightGap(gap);
            });

            gapList.appendChild(item);
        });
    }

    renderGraph() {
        if (this.currentVizMode === '3d') {
            document.getElementById('graph-3d').classList.remove('hidden');
            document.getElementById('graph-2d').classList.add('hidden');
            this.render3DGraph();
        } else {
            document.getElementById('graph-3d').classList.add('hidden');
            document.getElementById('graph-2d').classList.remove('hidden');
            setTimeout(() => this.render2DGraph(), 50);
        }
    }

    render3DGraph() {
        const container = document.getElementById('graph-3d');
        
        if (this.graph3D) {
            this.graph3D._destructor();
        }

        const nodes = this.currentData.nodes.map(n => ({
            id: n.id,
            name: n.label,
            val: n.size,
            group: n.group,
            betweenness: n.betweenness_centrality,
            constraint: n.constraint,
            effectiveSize: n.effective_size
        }));

        const links = this.currentData.edges.map(e => ({
            source: e.source,
            target: e.target,
            value: e.weight,
            isGap: e.is_gap
        }));

        const groupColors = [
            '#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6',
            '#3b82f6', '#14b8a6', '#f97316', '#e11d48', '#a855f7'
        ];

        this.graph3D = ForceGraph3D()(container)
            .graphData({ nodes, links })
            .nodeColor(n => groupColors[n.group % groupColors.length])
            .nodeVal(n => n.val)
            .nodeLabel(n => `${n.name} (中介中心性: ${(n.betweenness * 100).toFixed(1)}%)`)
            .linkColor(l => l.isGap ? '#f59e0b' : 'rgba(100, 116, 139, 0.5)')
            .linkWidth(l => l.isGap ? 3 : Math.max(0.5, Math.log1p(l.value) * 0.5))
            .linkOpacity(l => l.isGap ? 1 : 0.4)
            .onNodeClick(node => this.showNodeDetails(node))
            .onLinkClick(link => this.handleLinkClick(link))
            .backgroundColor('#0f172a');

        this.graph3D.d3Force('charge').strength(-120);
        this.graph3D.d3Force('link').distance(80);

        this.startRotation();
    }

    render2DGraph() {
        const viewport = document.getElementById('graph-2d');
        const container = document.getElementById('svg-2d');
        
        let width = viewport.clientWidth || 800;
        let height = viewport.clientHeight || 600;
        
        if (width < 100) width = 800;
        if (height < 100) height = 600;

        d3.select(container).selectAll('*').remove();

        const svg = d3.select(container)
            .attr('width', width)
            .attr('height', height)
            .attr('viewBox', [0, 0, width, height]);

        const nodes = this.currentData.nodes.map(n => ({
            ...n,
            name: n.label,
            x: Math.random() * width,
            y: Math.random() * height
        }));

        const links = this.currentData.edges.map(e => ({
            ...e
        }));

        const groupColors = [
            '#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6',
            '#3b82f6', '#14b8a6', '#f97316', '#e11d48', '#a855f7'
        ];

        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id(d => d.id).distance(100))
            .force('charge', d3.forceManyBody().strength(-250))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => (d.size || 10) + 8));

        const link = svg.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('stroke', l => l.is_gap ? '#f59e0b' : 'rgba(100, 116, 139, 0.6)')
            .attr('stroke-width', l => l.is_gap ? 3 : Math.max(1, Math.log1p(l.weight) * 0.8))
            .attr('stroke-opacity', l => l.is_gap ? 1 : 0.5)
            .attr('stroke-dasharray', l => l.is_gap ? '8,4' : 'none')
            .style('cursor', l => l.is_gap ? 'pointer' : 'default');

        const node = svg.append('g')
            .attr('class', 'nodes')
            .selectAll('circle')
            .data(nodes)
            .join('circle')
            .attr('r', d => d.size || 10)
            .attr('fill', d => groupColors[d.group % groupColors.length])
            .attr('stroke', '#fff')
            .attr('stroke-width', 1.5)
            .style('cursor', 'pointer')
            .call(this.drag(simulation))
            .on('click', (event, d) => this.showNodeDetails(d))
            .on('mouseenter', function(event, d) {
                d3.select(this).attr('stroke', '#f59e0b').attr('stroke-width', 3);
            })
            .on('mouseleave', function(event, d) {
                d3.select(this).attr('stroke', '#fff').attr('stroke-width', 1.5);
            });

        const labels = svg.append('g')
            .attr('class', 'labels')
            .selectAll('text')
            .data(nodes)
            .join('text')
            .text(d => d.name.length > 12 ? d.name.substring(0, 10) + '...' : d.name)
            .attr('font-size', '11px')
            .attr('fill', '#e2e8f0')
            .attr('text-anchor', 'middle')
            .attr('pointer-events', 'none')
            .attr('font-weight', '500');

        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x || 0)
                .attr('y1', d => d.source.y || 0)
                .attr('x2', d => d.target.x || 0)
                .attr('y2', d => d.target.y || 0);

            node
                .attr('cx', d => d.x || 0)
                .attr('cy', d => d.y || 0);

            labels
                .attr('x', d => d.x || 0)
                .attr('y', d => (d.y || 0) - (d.size || 10) - 6);
        });

        this.graph2D = { simulation, node, link, labels, svg, width, height };
    }

    drag(simulation) {
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        return d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended);
    }

    showNodeDetails(node) {
        const panel = document.getElementById('node-panel');
        const title = document.getElementById('panel-title');
        const content = document.getElementById('panel-content');

        title.textContent = node.name || node.label;

        const betweenness = node.betweenness !== undefined ? 
            (node.betweenness * 100).toFixed(2) + '%' : 
            ((node.betweenness_centrality || 0) * 100).toFixed(2) + '%';
        
        const constraint = node.constraint !== undefined ?
            node.constraint.toFixed(3) :
            (node.constraint || 0.5).toFixed(3);
        
        const effectiveSize = node.effectiveSize !== undefined ?
            node.effectiveSize.toFixed(2) :
            (node.effective_size || 0).toFixed(2);

        content.innerHTML = `
            <div class="panel-section">
                <h5>结构洞指标</h5>
                <div class="metric-row">
                    <span class="metric-label">中介中心性</span>
                    <span class="metric-value">${betweenness}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">约束系数</span>
                    <span class="metric-value">${constraint}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">有效大小</span>
                    <span class="metric-value">${effectiveSize}</span>
                </div>
            </div>
            <div class="panel-section">
                <h5>节点信息</h5>
                <div class="metric-row">
                    <span class="metric-label">社区分组</span>
                    <span class="metric-value">组 ${node.group}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">节点大小</span>
                    <span class="metric-value">${node.val || node.size}</span>
                </div>
            </div>
        `;

        panel.classList.remove('hidden');
    }

    closeNodePanel() {
        document.getElementById('node-panel').classList.add('hidden');
    }

    handleLinkClick(link) {
        if (link.isGap) {
            const gap = this.currentData.gap_pairs.find(
                g => (g.concept1 === link.source && g.concept2 === link.target) ||
                     (g.concept1 === link.target && g.concept2 === link.source)
            );
            if (gap) {
                this.showGapPrompt(gap);
            }
        }
    }

    highlightGap(gap) {
        if (this.currentVizMode === '3d' && this.graph3D) {
            this.graph3D.linkColor(l => {
                if (l.isGap && 
                    ((l.source === gap.concept1 && l.target === gap.concept2) ||
                     (l.source === gap.concept2 && l.target === gap.concept1))) {
                    return '#ef4444';
                }
                return l.isGap ? '#f59e0b' : 'rgba(100, 116, 139, 0.5)';
            });
        }
    }

    async showGapPrompt(gap) {
        const modal = document.getElementById('prompt-modal');
        const title = document.getElementById('prompt-title');
        const content = document.getElementById('prompt-content');

        title.textContent = `研究空白: ${gap.concept1} ↔ ${gap.concept2}`;
        content.innerHTML = '<div style="text-align: center; padding: 40px;">加载中...</div>';

        modal.classList.remove('hidden');

        try {
            const response = await fetch(`${this.apiBase}/api/gap-prompt`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    concept1: gap.concept1,
                    concept2: gap.concept2,
                    keywords: [],
                    papers: []
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.currentPromptText = data.prompt;
                content.textContent = data.prompt;
            } else {
                content.textContent = gap.prompt;
                this.currentPromptText = gap.prompt;
            }
        } catch (error) {
            content.textContent = gap.prompt;
            this.currentPromptText = gap.prompt;
        }
    }

    closePromptModal() {
        document.getElementById('prompt-modal').classList.add('hidden');
    }

    copyPrompt() {
        if (this.currentPromptText) {
            navigator.clipboard.writeText(this.currentPromptText).then(() => {
                this.showToast('提示词已复制到剪贴板');
            }).catch(() => {
                this.showToast('复制失败，请手动选择复制');
            });
        }
    }

    zoomIn() {
        if (this.currentVizMode === '3d' && this.graph3D) {
            const currentZoom = this.graph3D.zoom();
            const newZoom = Math.min(currentZoom * 1.4, 5);
            this.graph3D.zoom(newZoom, 300);
            this.showToast(`放大: ${(newZoom * 100).toFixed(0)}%`);
        } else if (this.graph2D) {
            this.showToast('2D 模式请使用鼠标滚轮缩放');
        }
    }

    zoomOut() {
        if (this.currentVizMode === '3d' && this.graph3D) {
            const currentZoom = this.graph3D.zoom();
            const newZoom = Math.max(currentZoom * 0.7, 0.1);
            this.graph3D.zoom(newZoom, 300);
            this.showToast(`缩小: ${(newZoom * 100).toFixed(0)}%`);
        }
    }

    resetView() {
        if (this.currentVizMode === '3d' && this.graph3D) {
            this.graph3D.zoomToFit(400, 40);
            this.showToast('视图已重置');
        }
    }

    toggleRotation() {
        const btn = document.getElementById('toggle-rotation');
        this.isRotating = !this.isRotating;
        btn.classList.toggle('active', this.isRotating);

        if (this.isRotating) {
            this.startRotation();
        } else {
            this.stopRotation();
        }
    }

    startRotation() {
        if (!this.graph3D || !this.isRotating) return;

        const distance = 400;
        let angle = 0;

        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }

        const rotate = () => {
            if (!this.isRotating) return;

            angle += 0.002;
            this.graph3D.cameraPosition({
                x: distance * Math.sin(angle),
                y: distance * Math.sin(angle * 0.5),
                z: distance * Math.cos(angle)
            });

            this.animationFrame = requestAnimationFrame(rotate);
        };

        rotate();
    }

    stopRotation() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
    }

    showToast(message) {
        const toast = document.getElementById('toast');
        const msgEl = document.getElementById('toast-message');

        msgEl.textContent = message;
        toast.classList.remove('hidden');

        setTimeout(() => {
            toast.classList.add('hidden');
        }, 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.gapsightApp = new GapSightApp();
});
