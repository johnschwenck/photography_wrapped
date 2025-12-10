// API base URL
const API_BASE = 'http://localhost:5000/api';

// Utility function to escape HTML
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Progress polling
let progressInterval = null;

function startProgressPolling(taskId, callback) {
    stopProgressPolling();
    
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/progress/${taskId}`);
            const data = await response.json();
            
            updateProgressBar(data.percentage, data.status);
            
            if (data.status === 'complete' || data.status === 'error' || data.percentage >= 100) {
                stopProgressPolling();
                if (callback) callback(data.status);
            }
        } catch (error) {
            console.error('Error polling progress:', error);
        }
    }, 300);
}

function stopProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

function updateProgressBar(percentage, status) {
    const progressFill = document.querySelector('.progress-fill');
    const progressText = document.querySelector('.progress-text');
    
    if (progressFill && progressText) {
        progressFill.style.width = `${percentage}%`;
        progressText.textContent = `${percentage}% - ${status || 'Processing'}`;
    }
}

// Tab management
document.addEventListener('DOMContentLoaded', () => {
    // Tab switching
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.dataset.tab;

            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            button.classList.add('active');
            document.getElementById(`${tabId}-tab`).classList.add('active');
        });
    });

    // Mode selection for extract
    const modeSelect = document.getElementById('mode-select');
    const crawlOptions = document.getElementById('crawl-options');

    modeSelect.addEventListener('change', () => {
        if (modeSelect.value === 'crawl') {
            crawlOptions.style.display = 'block';
        } else {
            crawlOptions.style.display = 'none';
        }
    });



    // Add to queue
    document.getElementById('add-to-queue-btn').addEventListener('click', addToQueue);

    // Extract all from queue
    document.getElementById('extract-all-btn').addEventListener('click', extractAllFromQueue);

    // Analysis tab functionality
    document.getElementById('run-analysis-btn').addEventListener('click', runDatabaseAnalysis);
    document.getElementById('analysis-category-filter').addEventListener('change', updateAnalysisFilterInfo);
    document.getElementById('analysis-group-filter').addEventListener('change', updateAnalysisFilterInfo);
    document.getElementById('select-all-sessions').addEventListener('click', () => selectAllSessions(true));
    document.getElementById('deselect-all-sessions').addEventListener('click', () => selectAllSessions(false));
    
    // Load analysis filters when tab is clicked
    document.querySelector('[data-tab="analyze"]').addEventListener('click', () => {
        setTimeout(() => loadAnalysisFilters(), 100);
    });

    // Database tab functionality
    document.getElementById('refresh-db-btn').addEventListener('click', loadDatabaseOverview);
    document.getElementById('search-session').addEventListener('input', filterDatabaseTable);
    document.getElementById('filter-db-category').addEventListener('input', filterDatabaseTable);
    document.getElementById('filter-db-group').addEventListener('input', filterDatabaseTable);
    
    // Database reset controls
    document.getElementById('reset-all-btn').addEventListener('click', handleResetAll);
    document.getElementById('reset-category-btn').addEventListener('click', () => toggleResetDropdown('category'));
    document.getElementById('reset-group-btn').addEventListener('click', () => toggleResetDropdown('group'));
    document.getElementById('confirm-delete-category').addEventListener('click', () => handleDeleteByFilter('category'));
    document.getElementById('cancel-delete-category').addEventListener('click', () => closeResetDropdown('category'));
    document.getElementById('confirm-delete-group').addEventListener('click', () => handleDeleteByFilter('group'));
    document.getElementById('cancel-delete-group').addEventListener('click', () => closeResetDropdown('group'));
    document.getElementById('select-all-categories').addEventListener('change', (e) => handleSelectAll('category', e.target.checked));
    document.getElementById('select-all-groups').addEventListener('change', (e) => handleSelectAll('group', e.target.checked));
    
    // Add sort handlers for table headers
    document.querySelectorAll('#db-sessions-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => sortDatabaseTable(th.dataset.sort));
    });
    
    // Load database overview when tab is clicked
    document.querySelector('[data-tab="database"]').addEventListener('click', () => {
        setTimeout(() => loadDatabaseOverview(), 100);
    });
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.db-reset-controls')) {
            closeResetDropdown('category');
            closeResetDropdown('group');
        }
    });
});

async function reselectFolder(id) {
    try {
        const response = await fetch(`${API_BASE}/browse-folder`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.success && data.path) {
            const item = extractionQueue.find(i => i.id === id);
            if (item) {
                item.folderPath = data.path;
                renderQueue();
            }
        }
    } catch (error) {
        console.error('Error selecting folder:', error);
        alert('Error opening folder picker');
    }
}

async function getFolderPath(dirHandle) {
    // This function is no longer used with backend picker
    // Kept for backwards compatibility
    if (dirHandle && dirHandle.name) {
        return `[Selected] ${dirHandle.name}`;
    }
    return '[Selected Directory]';
}

// Extraction Queue Management
let extractionQueue = [];
let extractedCategories = new Set();
let extractedGroups = new Set();

window.editQueueItem = function(id) {
    const item = extractionQueue.find(i => i.id === id);
    if (!item) return;

    const queueItemElement = document.querySelector(`[data-id="${id}"]`);
    
    queueItemElement.innerHTML = `
        <div class="queue-item-header">
            <span class="queue-item-mode">${item.mode}</span>
            <div class="queue-item-actions">
                <button onclick="saveQueueItemEdit(${id})" style="background: var(--primary-color); color: var(--secondary-color);">Save</button>
                <button onclick="cancelQueueItemEdit(${id})">Cancel</button>
            </div>
        </div>
        <div class="queue-item-path" style="margin-bottom: 12px;">
            <label style="display: block; margin-bottom: 4px; color: var(--text-secondary); font-size: 0.85em;">Folder Path:</label>
            <input type="text" id="edit-path-${id}" value="${item.folderPath}" style="width: 100%; padding: 8px; background: var(--background); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-family: monospace; font-size: 0.9em;" />
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
            <div>
                <label style="display: block; margin-bottom: 4px; color: var(--text-secondary); font-size: 0.85em;">Category:</label>
                <input type="text" id="edit-category-${id}" value="${item.category}" style="width: 100%; padding: 8px; background: var(--background); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-size: 0.9em;" />
            </div>
            <div>
                <label style="display: block; margin-bottom: 4px; color: var(--text-secondary); font-size: 0.85em;">Group:</label>
                <input type="text" id="edit-group-${id}" value="${item.group}" style="width: 100%; padding: 8px; background: var(--background); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-size: 0.9em;" />
            </div>
        </div>
        ${item.sessionName ? `
        <div style="margin-bottom: 12px;">
            <label style="display: block; margin-bottom: 4px; color: var(--text-secondary); font-size: 0.85em;">Session Name:</label>
            <input type="text" id="edit-session-${id}" value="${item.sessionName}" style="width: 100%; padding: 8px; background: var(--background); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-size: 0.9em;" />
        </div>
        ` : ''}
        ${item.mode === 'crawl' ? `
        <div style="margin-bottom: 12px;">
            <label style="display: block; margin-bottom: 4px; color: var(--text-secondary); font-size: 0.85em;">Target Folder:</label>
            <input type="text" id="edit-target-${id}" value="${item.targetFolder || ''}" style="width: 100%; padding: 8px; background: var(--background); border: 1px solid var(--border-color); border-radius: 4px; color: var(--text-primary); font-size: 0.9em;" />
        </div>
        ` : ''}
        <div>
            <label style="display: flex; align-items: center; color: var(--text-primary); font-size: 0.9em;">
                <input type="checkbox" id="edit-hitrate-${id}" ${item.calculateHitRate ? 'checked' : ''} style="margin-right: 8px;" />
                Calculate Hit Rate
            </label>
        </div>
    `;
}

window.saveQueueItemEdit = function(id) {
    const item = extractionQueue.find(i => i.id === id);
    if (!item) return;

    const newPath = document.getElementById(`edit-path-${id}`).value.trim();
    const newCategory = document.getElementById(`edit-category-${id}`).value.trim();
    const newGroup = document.getElementById(`edit-group-${id}`).value.trim();
    const newHitRate = document.getElementById(`edit-hitrate-${id}`).checked;
    
    if (!newPath) {
        alert('Folder path cannot be empty');
        return;
    }
    
    if (!newCategory) {
        alert('Category cannot be empty');
        return;
    }
    
    if (!newGroup) {
        alert('Group cannot be empty');
        return;
    }
    
    item.folderPath = newPath;
    item.category = newCategory;
    item.group = newGroup;
    item.calculateHitRate = newHitRate;
    
    const sessionInput = document.getElementById(`edit-session-${id}`);
    if (sessionInput) {
        item.sessionName = sessionInput.value.trim();
    }
    
    if (item.mode === 'crawl') {
        const targetInput = document.getElementById(`edit-target-${id}`);
        if (targetInput) {
            const newTarget = targetInput.value.trim();
            if (!newTarget) {
                alert('Target folder cannot be empty for crawl mode');
                return;
            }
            item.targetFolder = newTarget;
        }
    }
    
    renderQueue();
}

window.cancelQueueItemEdit = function(id) {
    renderQueue();
}

window.reselect = function(id) {
    reselectFolder(id);
}

window.removeFromQueue = function(id) {
    extractionQueue = extractionQueue.filter(item => item.id !== id);
    renderQueue();
}

function addToQueue() {
    console.log('addToQueue function called');
    
    const mode = document.getElementById('mode-select').value;
    const folderPath = document.getElementById('folder-path').value.trim();
    const sessionName = document.getElementById('session-name').value.trim();
    const category = document.getElementById('category').value.trim();
    const group = document.getElementById('group').value.trim();
    const calculateHitRate = document.getElementById('calculate-hit-rate').checked;

    console.log('Adding to queue:', { mode, folderPath, category, group });

    if (!folderPath) {
        alert('Please enter a folder path');
        return;
    }
    
    if (!category) {
        alert('Please enter a category');
        return;
    }
    
    if (!group) {
        alert('Please enter a group');
        return;
    }

    const targetFolder = mode === 'crawl' ? document.getElementById('target-folder').value.trim() : null;

    if (mode === 'crawl' && !targetFolder) {
        alert('Please enter a target folder name for crawl mode (e.g., "Edited")');
        return;
    }

    const queueItem = {
        id: Date.now(),
        mode: mode,
        folderPath: folderPath,
        sessionName: sessionName,
        category: category,
        group: group,
        calculateHitRate: calculateHitRate,
        targetFolder: targetFolder
    };

    console.log('Queue item created:', queueItem);

    extractionQueue.push(queueItem);
    renderQueue();
    
    // Clear form for next entry
    document.getElementById('folder-path').value = '';
    document.getElementById('session-name').value = '';
    document.getElementById('category').value = '';
    document.getElementById('group').value = '';
    document.getElementById('calculate-hit-rate').checked = true;
    if (mode === 'crawl') {
        document.getElementById('target-folder').value = '';
    }
    
    console.log('Current queue length:', extractionQueue.length);
}

function renderQueue() {
    const queueContainer = document.getElementById('extraction-queue');
    const extractAllBtn = document.getElementById('extract-all-btn');

    if (extractionQueue.length === 0) {
        queueContainer.innerHTML = '<p class="empty-queue">No folders added yet. Add folders from the left to build your extraction queue.</p>';
        extractAllBtn.style.display = 'none';
        return;
    }

    extractAllBtn.style.display = 'block';

    let html = '';
    extractionQueue.forEach((item, index) => {
        html += `
            <div class="queue-item" data-id="${item.id}">
                <div class="queue-item-header">
                    <span class="queue-item-mode">${item.mode}</span>
                    <div class="queue-item-actions">
                        <button onclick="editQueueItem(${item.id})">Edit</button>
                        <button class="delete-btn" onclick="removeFromQueue(${item.id})">Remove</button>
                    </div>
                </div>
                <div class="queue-item-path" id="path-${item.id}">
                    ${item.folderPath}
                </div>
                <div class="queue-item-details">
                    <div class="queue-item-detail"><strong>Category:</strong> ${item.category}</div>
                    <div class="queue-item-detail"><strong>Group:</strong> ${item.group}</div>
                    ${item.sessionName ? `<div class="queue-item-detail"><strong>Session:</strong> ${item.sessionName}</div>` : ''}
                    ${item.targetFolder ? `<div class="queue-item-detail"><strong>Target Folder:</strong> ${item.targetFolder}</div>` : ''}
                    <div class="queue-item-detail"><strong>Hit Rate:</strong> ${item.calculateHitRate ? 'Yes' : 'No'}</div>
                </div>
            </div>
        `;
    });

    queueContainer.innerHTML = html;
}

async function extractAllFromQueue() {
    if (extractionQueue.length === 0) {
        alert('Queue is empty. Add folders first.');
        return;
    }

    const resultsArea = document.getElementById('extract-results');
    resultsArea.classList.add('visible');
    resultsArea.innerHTML = '<div class="loading">Processing queue</div>';

    let successCount = 0;
    let failCount = 0;
    let results = [];

    for (let i = 0; i < extractionQueue.length; i++) {
        const item = extractionQueue[i];
        
        resultsArea.innerHTML = `<div class="loading">Processing ${i + 1} of ${extractionQueue.length}</div>`;

        try {
            let response;

            if (item.mode === 'single') {
                response = await fetch(`${API_BASE}/extract`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        folder_path: item.folderPath,
                        session_name: item.sessionName,
                        category: item.category,
                        group: item.group,
                        calculate_hit_rate: item.calculateHitRate
                    })
                });
            } else {
                response = await fetch(`${API_BASE}/crawl`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        parent_dir: item.folderPath,
                        target_folder: item.targetFolder,
                        category: item.category,
                        group: item.group,
                        calculate_hit_rate: item.calculateHitRate
                    })
                });
            }

            const data = await response.json();

            if (response.ok) {
                results.push({ success: true, item: item, data: data });
                successCount++;
            } else {
                results.push({ success: false, item: item, error: data.error });
                failCount++;
            }

        } catch (error) {
            results.push({ success: false, item: item, error: error.message });
            failCount++;
        }
    }

    displayQueueResults(results, successCount, failCount);
    
    // Track extracted categories and groups for analysis
    results.forEach(result => {
        if (result.success) {
            extractedCategories.add(result.item.category);
            extractedGroups.add(result.item.group);
        }
    });
    
    // Clear queue after successful extraction
    extractionQueue = [];
    renderQueue();
}

// Analysis Functions - Database Driven
let allCategories = [];
let allGroups = [];
let categoryGroupMap = {};
let allSessions = [];
let previousCategory = '';  // Track previous category selection

async function loadAnalysisFilters() {
    try {
        const response = await fetch(`${API_BASE}/database/categories-groups`);
        const data = await response.json();
        
        if (!response.ok || !data.success) return;
        
        allCategories = data.categories;
        allGroups = data.groups;
        
        // Build category-group mapping and load all sessions
        const dbResponse = await fetch(`${API_BASE}/database/overview`);
        const dbData = await dbResponse.json();
        if (dbResponse.ok && dbData.success) {
            categoryGroupMap = {};
            allSessions = dbData.sessions;
            
            dbData.sessions.forEach(session => {
                const cat = session.category || '';
                const grp = session.group || '';
                if (!categoryGroupMap[cat]) categoryGroupMap[cat] = new Set();
                if (grp) categoryGroupMap[cat].add(grp);
            });
        }
        
        // Populate category filter
        const categoryFilter = document.getElementById('analysis-category-filter');
        categoryFilter.innerHTML = '<option value="">All Categories</option>';
        allCategories.forEach(cat => {
            categoryFilter.innerHTML += `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`;
        });
        
        // Populate group filter (all groups initially)
        updateGroupFilter();
        
        // Show filter info
        updateAnalysisFilterInfo();
        
    } catch (error) {
        console.error('Error loading analysis filters:', error);
    }
}

function updateGroupFilter() {
    const categoryFilter = document.getElementById('analysis-category-filter');
    const groupFilter = document.getElementById('analysis-group-filter');
    const selectedCategory = categoryFilter.value;
    const currentGroupValue = groupFilter.value;  // Save current selection
    
    console.log('Updating group filter for category:', selectedCategory);
    
    groupFilter.innerHTML = '<option value="">All Groups</option>';
    
    if (selectedCategory && categoryGroupMap[selectedCategory]) {
        // Show only groups in selected category
        const groupsInCategory = Array.from(categoryGroupMap[selectedCategory]).sort();
        console.log('Groups in category:', groupsInCategory);
        groupsInCategory.forEach(grp => {
            groupFilter.innerHTML += `<option value="${escapeHtml(grp)}">${escapeHtml(grp)}</option>`;
        });
        
        // Try to restore previous selection if it's still valid
        if (currentGroupValue && groupsInCategory.includes(currentGroupValue)) {
            groupFilter.value = currentGroupValue;
        }
    } else {
        // Show all groups
        allGroups.forEach(grp => {
            groupFilter.innerHTML += `<option value="${escapeHtml(grp)}">${escapeHtml(grp)}</option>`;
        });
        
        // Reset to "All Groups" if we just switched FROM a category TO "All Categories"
        if (previousCategory && !selectedCategory) {
            groupFilter.value = '';
        } else if (currentGroupValue && allGroups.includes(currentGroupValue)) {
            // Otherwise preserve the selection
            groupFilter.value = currentGroupValue;
        }
    }
    
    // Update tracking
    previousCategory = selectedCategory;
    
    console.log('Group filter updated, options count:', groupFilter.options.length);
}

function updateAnalysisFilterInfo() {
    const categoryFilter = document.getElementById('analysis-category-filter');
    const groupFilter = document.getElementById('analysis-group-filter');
    const filterInfo = document.getElementById('analysis-filter-info');
    const sessionContainer = document.getElementById('session-filter-container');
    
    // Update group dropdown based on category selection
    updateGroupFilter();
    
    const category = categoryFilter.value;
    const group = groupFilter.value;
    
    // Show/hide session filter based on group selection
    if (group) {
        updateSessionFilter(category, group);
        sessionContainer.style.display = 'block';
    } else {
        sessionContainer.style.display = 'none';
    }
    
    // Update filter info text
    if (!category && !group) {
        filterInfo.textContent = 'Analyzing entire database';
    } else {
        let parts = [];
        if (category) parts.push(`Category: ${category}`);
        if (group) parts.push(`Group: ${group}`);
        
        const sessionFilter = document.getElementById('analysis-session-filter');
        const selectedSessions = Array.from(sessionFilter.selectedOptions).map(opt => opt.value);
        if (group && sessionFilter.options.length > 0) {
            if (selectedSessions.length === 0) {
                parts.push('all sessions');
            } else if (selectedSessions.length < sessionFilter.options.length) {
                parts.push(`${selectedSessions.length} sessions`);
            }
        }
        
        filterInfo.textContent = `Filtered by ${parts.join(', ')}`;
    }
}

function updateSessionFilter(category, group) {
    const sessionFilter = document.getElementById('analysis-session-filter');
    
    // Filter sessions by category and group
    const filteredSessions = allSessions.filter(session => {
        const matchesCategory = !category || session.category === category;
        const matchesGroup = !group || session.group === group;
        return matchesCategory && matchesGroup;
    });
    
    // Populate session dropdown (nothing selected by default - means "All Sessions")
    sessionFilter.innerHTML = '';
    filteredSessions.forEach(session => {
        const option = document.createElement('option');
        option.value = session.name;
        option.textContent = `${session.name} (${session.total_photos} photos)`;
        option.selected = false;  // Nothing selected = analyze all sessions
        sessionFilter.appendChild(option);
    });
    
    console.log('Session filter updated:', filteredSessions.length, 'sessions');
}

function selectAllSessions(select) {
    const sessionFilter = document.getElementById('analysis-session-filter');
    Array.from(sessionFilter.options).forEach(option => {
        option.selected = select;
    });
    updateAnalysisFilterInfo();
}

async function runDatabaseAnalysis() {
    const categoryFilter = document.getElementById('analysis-category-filter');
    const groupFilter = document.getElementById('analysis-group-filter');
    const sessionFilter = document.getElementById('analysis-session-filter');
    const resultsArea = document.getElementById('analyze-results');
    const progressBar = document.getElementById('progress-bar');
    
    const category = categoryFilter.value || null;
    const group = groupFilter.value || null;
    
    // Get selected sessions if any are specifically selected
    // If none selected, sessions = null means "analyze all sessions in group"
    let sessions = null;
    if (group && sessionFilter.options.length > 0) {
        const selected = Array.from(sessionFilter.selectedOptions).map(opt => opt.value);
        if (selected.length > 0) {
            sessions = selected;
        }
        // If no sessions selected, sessions stays null = analyze entire group
    }
    
    resultsArea.innerHTML = '';
    progressBar.style.display = 'block';
    updateProgressBar(0, 'Starting analysis...');
    
    try {
        const response = await fetch(`${API_BASE}/analyze/database`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, group, sessions })
        });
        
        updateProgressBar(50, 'Processing data...');
        
        const data = await response.json();
        
        if (!response.ok) {
            progressBar.style.display = 'none';
            showError('analyze-results', data.error || 'Analysis failed');
            return;
        }
        
        updateProgressBar(100, 'Complete');
        setTimeout(() => { progressBar.style.display = 'none'; }, 500);
        
        // Log for debugging
        console.log('Analysis response:', data);
        
        displayAnalysisResults(data.analysis);
        
    } catch (error) {
        progressBar.style.display = 'none';
        showError('analyze-results', `Error: ${error.message}`);
    }
}

function runAutoAnalysis() {
    const extractedInfo = document.getElementById('extracted-info');
    const extractedSummary = document.getElementById('extracted-summary');
    
    if (extractedCategories.size === 0 && extractedGroups.size === 0) {
        showError('analyze-results', 'No extracted data found. Please extract metadata first.');
        return;
    }
    
    // Display extracted data summary
    let summaryHtml = '<p><strong>Categories:</strong> ' + Array.from(extractedCategories).join(', ') + '</p>';
    summaryHtml += '<p><strong>Groups:</strong> ' + Array.from(extractedGroups).join(', ') + '</p>';
    summaryHtml += '<p>Click "Run Analysis" to generate statistics for all extracted data.</p>';
    
    extractedSummary.innerHTML = summaryHtml;
    extractedInfo.style.display = 'block';
}

async function runAllAnalyses() {
    const resultsArea = document.getElementById('analyze-results');
    const progressBar = document.getElementById('progress-bar');
    resultsArea.classList.remove('visible');
    resultsArea.innerHTML = '';
    progressBar.style.display = 'block';
    
    const taskId = 'analyze_' + Date.now();
    updateProgressBar(0, 'Starting');
    
    let allResults = [];
    
    try {
        // Analyze each category
        for (const category of extractedCategories) {
            console.log('Analyzing category:', category);
            startProgressPolling(taskId, (status) => {
                progressBar.style.display = 'none';
            });
            
            const response = await fetch(`${API_BASE}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'category',
                    target: category,
                    task_id: taskId
                })
            });

            const data = await response.json();
            console.log('Category analysis response:', data);
            console.log('Category analysis details:', JSON.stringify(data.analysis, null, 2));
            
            if (response.ok && data.analysis) {
                allResults.push({
                    type: 'category',
                    name: category,
                    data: data.analysis
                });
            } else {
                console.error('Category analysis failed:', data);
            }
        }
        
        // Analyze each group
        for (const group of extractedGroups) {
            console.log('Analyzing group:', group);
            const response = await fetch(`${API_BASE}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: 'group',
                    target: group,
                    task_id: taskId
                })
            });

            const data = await response.json();
            console.log('Group analysis response:', data);
            console.log('Group analysis details:', JSON.stringify(data.analysis, null, 2));
            
            if (response.ok && data.analysis) {
                allResults.push({
                    type: 'group',
                    name: group,
                    data: data.analysis
                });
            } else {
                console.error('Group analysis failed:', data);
            }
        }
        
        stopProgressPolling();
        progressBar.style.display = 'none';
        
        displayAllAnalysisResults(allResults);
        
    } catch (error) {
        stopProgressPolling();
        progressBar.style.display = 'none';
        showError('analyze-results', `Error: ${error.message}`);
    }
}

function displayAllAnalysisResults(results) {
    const resultsArea = document.getElementById('analyze-results');
    resultsArea.classList.add('visible');
    
    let html = '<h2 style="margin-bottom: 20px;">Analysis Complete</h2>';
    
    results.forEach(result => {
        const analysis = result.data;
        html += `
            <div class="result-card" style="margin-bottom: 25px;">
                <h3>${result.type.toUpperCase()}: ${result.name}</h3>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-label">Total Photos</div>
                        <div class="stat-value">${analysis.total_photos}</div>
                    </div>
                    ${analysis.hit_rate ? `
                    <div class="stat-item">
                        <div class="stat-label">Hit Rate</div>
                        <div class="stat-value">${analysis.hit_rate.toFixed(1)}%</div>
                    </div>
                    ` : ''}
                    <div class="stat-item">
                        <div class="stat-label">Unique Lenses</div>
                        <div class="stat-value">${Object.keys(analysis.lens_freq).length}</div>
                    </div>
                </div>
        `;
        
        // Top lenses
        if (analysis.lens_freq && Object.keys(analysis.lens_freq).length > 0) {
            html += '<div style="margin-top: 15px;"><h4>Top Lenses</h4><ul>';
            const lenses = Object.entries(analysis.lens_freq)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);
            lenses.forEach(([lens, count]) => {
                html += `<li>${lens}: ${count} photos</li>`;
            });
            html += '</ul></div>';
        }
        
        // Camera bodies
        if (analysis.camera_freq && Object.keys(analysis.camera_freq).length > 0) {
            html += '<div style="margin-top: 15px;"><h4>Camera Bodies</h4><ul>';
            const cameras = Object.entries(analysis.camera_freq)
                .sort((a, b) => b[1] - a[1]);
            cameras.forEach(([camera, count]) => {
                html += `<li>${camera}: ${count} photos</li>`;
            });
            html += '</ul></div>';
        }
        
        html += '</div>';
    });
    
    resultsArea.innerHTML = html;
}

function displayQueueResults(results, successCount, failCount) {
    const resultsArea = document.getElementById('extract-results');

    // Separate results by mode
    const singleFolderResults = results.filter(r => r.item.mode === 'single');
    const batchCrawlResults = results.filter(r => r.item.mode === 'crawl');

    let html = `
        <div class="success-message">
            Queue processed: ${successCount} successful, ${failCount} failed
        </div>
        <div class="stat-grid">
            <div class="stat-item">
                <div class="stat-label">Total Items</div>
                <div class="stat-value">${results.length}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Successful</div>
                <div class="stat-value">${successCount}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Failed</div>
                <div class="stat-value">${failCount}</div>
            </div>
        </div>
    `;

    // Single Folder Extractions
    if (singleFolderResults.length > 0) {
        html += '<h3 style="margin-top: 25px; margin-bottom: 15px; border-bottom: 1px solid var(--secondary); padding-bottom: 10px;">Single Folder Extractions</h3>';
        
        const singleComplete = singleFolderResults.filter(r => r.success);
        const singleFailed = singleFolderResults.filter(r => !r.success);
        
        // Complete section
        if (singleComplete.length > 0) {
            html += '<h4 style="color: var(--success); margin-top: 15px;">✓ Complete</h4>';
            singleComplete.forEach((result, index) => {
                const item = result.item;
                const session = result.data.session;
                html += `
                    <div class="result-card">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <h3>${session.name}</h3>
                                <p><strong>Category:</strong> ${item.category} | <strong>Group:</strong> ${item.group}</p>
                                <p><strong>Path:</strong> ${item.folderPath}</p>
                                <p><strong>Photos:</strong> ${session.total_photos}</p>
                                ${session.hit_rate ? `<p><strong>Hit Rate:</strong> ${session.hit_rate.toFixed(1)}%</p>` : ''}
                            </div>
                            <button class="btn-secondary" onclick="showSingleFolderDetails(${JSON.stringify(session).replace(/"/g, '&quot;')}, ${JSON.stringify(item).replace(/"/g, '&quot;')})">Details</button>
                        </div>
                    </div>
                `;
            });
        }
        
        // Failed section
        if (singleFailed.length > 0) {
            html += '<h4 style="color: var(--error); margin-top: 15px;">✗ Failed</h4>';
            singleFailed.forEach((result, index) => {
                const item = result.item;
                html += `
                    <div class="result-card" style="border-color: var(--error);">
                        <h3 style="color: var(--error);">Failed</h3>
                        <p><strong>Category:</strong> ${item.category} | <strong>Group:</strong> ${item.group}</p>
                        <p><strong>Path:</strong> ${item.folderPath}</p>
                        <p><strong>Error:</strong> ${result.error}</p>
                    </div>
                `;
            });
        }
    }

    // Batch Crawl Extractions
    if (batchCrawlResults.length > 0) {
        html += '<h3 style="margin-top: 25px; margin-bottom: 15px; border-bottom: 1px solid var(--secondary); padding-bottom: 10px;">Batch Crawl Extractions</h3>';
        
        const crawlComplete = batchCrawlResults.filter(r => r.success);
        const crawlFailed = batchCrawlResults.filter(r => !r.success);
        
        // Complete section
        if (crawlComplete.length > 0) {
            html += '<h4 style="color: var(--success); margin-top: 15px;">✓ Complete</h4>';
            crawlComplete.forEach((result, index) => {
                const item = result.item;
                const summary = result.data.summary;
                const sessions = result.data.sessions;
                html += `
                    <div class="result-card">
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div style="flex: 1;">
                                <h3>Crawl: ${item.folderPath}</h3>
                                <p><strong>Category:</strong> ${item.category} | <strong>Group:</strong> ${item.group}</p>
                                <p><strong>Target Folder:</strong> ${item.targetFolder}</p>
                                <p><strong>Sessions Found:</strong> ${summary.total} | <strong>Successful:</strong> ${summary.successful} | <strong>Failed:</strong> ${summary.failed}</p>
                            </div>
                            <button class="btn-secondary" onclick='showCrawlDetails(${JSON.stringify(sessions).replace(/'/g, "\\'")}, ${JSON.stringify(item).replace(/'/g, "\\'")})'>Details</button>
                        </div>
                    </div>
                `;
            });
        }
        
        // Failed section
        if (crawlFailed.length > 0) {
            html += '<h4 style="color: var(--error); margin-top: 15px;">✗ Failed</h4>';
            crawlFailed.forEach((result, index) => {
                const item = result.item;
                html += `
                    <div class="result-card" style="border-color: var(--error);">
                        <h3 style="color: var(--error);">Failed</h3>
                        <p><strong>Category:</strong> ${item.category} | <strong>Group:</strong> ${item.group}</p>
                        <p><strong>Path:</strong> ${item.folderPath}</p>
                        <p><strong>Target Folder:</strong> ${item.targetFolder}</p>
                        <p><strong>Error:</strong> ${result.error}</p>
                    </div>
                `;
            });
        }
    }

    resultsArea.innerHTML = html;
}

async function extractMetadata() {
    const mode = document.getElementById('mode-select').value;
    const folderPath = document.getElementById('folder-path').value.trim();
    const sessionName = document.getElementById('session-name').value.trim();
    const category = document.getElementById('category').value.trim();
    const group = document.getElementById('group').value.trim();
    const calculateHitRate = document.getElementById('calculate-hit-rate').checked;

    if (!folderPath) {
        showError('extract-results', 'Please enter a folder path');
        return;
    }
    
    if (!category) {
        showError('extract-results', 'Please enter a category');
        return;
    }
    
    if (!group) {
        showError('extract-results', 'Please enter a group');
        return;
    }

    const resultsArea = document.getElementById('extract-results');
    resultsArea.classList.add('visible');
    resultsArea.innerHTML = '<div class="loading">Processing</div>';

    try {
        let response;
        
        if (mode === 'single') {
            response = await fetch(`${API_BASE}/extract`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    folder_path: folderPath,
                    session_name: sessionName,
                    category: category,
                    group: group,
                    calculate_hit_rate: calculateHitRate
                })
            });
        } else {
            const targetFolder = document.getElementById('target-folder').value.trim();
            if (!targetFolder) {
                showError('extract-results', 'Please enter a target folder name');
                return;
            }
            response = await fetch(`${API_BASE}/crawl`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    parent_dir: folderPath,
                    target_folder: targetFolder,
                    category: category,
                    group: group,
                    calculate_hit_rate: calculateHitRate
                })
            });
        }

        const data = await response.json();

        if (!response.ok) {
            showError('extract-results', data.error || 'Extraction failed');
            return;
        }

        if (mode === 'single') {
            displaySingleExtractResult(data);
        } else {
            displayCrawlResults(data);
        }

    } catch (error) {
        showError('extract-results', `Error: ${error.message}`);
    }
}

function displaySingleExtractResult(data) {
    const resultsArea = document.getElementById('extract-results');
    const session = data.session;

    resultsArea.innerHTML = `
        <div class="success-message">Successfully extracted metadata</div>
        <div class="result-card">
            <h3>${session.name}</h3>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-label">Session ID</div>
                    <div class="stat-value">${session.id}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Total Photos</div>
                    <div class="stat-value">${session.total_photos}</div>
                </div>
                ${session.hit_rate ? `
                <div class="stat-item">
                    <div class="stat-label">Hit Rate</div>
                    <div class="stat-value">${session.hit_rate.toFixed(1)}%</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">RAW Photos</div>
                    <div class="stat-value">${session.total_raw_photos}</div>
                </div>
                ` : ''}
            </div>
            <p style="margin-top: 15px;"><strong>Category:</strong> ${session.category}</p>
            <p><strong>Group:</strong> ${session.group}</p>
        </div>
    `;
}

function displayCrawlResults(data) {
    const resultsArea = document.getElementById('extract-results');
    const summary = data.summary;
    const sessions = data.sessions;

    let html = `
        <div class="success-message">
            Crawl complete: ${summary.successful} successful, ${summary.failed} failed
        </div>
        <div class="stat-grid">
            <div class="stat-item">
                <div class="stat-label">Total Folders</div>
                <div class="stat-value">${summary.total}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Successful</div>
                <div class="stat-value">${summary.successful}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Failed</div>
                <div class="stat-value">${summary.failed}</div>
            </div>
        </div>
    `;

    if (sessions.length > 0) {
        html += '<h3 style="margin-top: 20px;">Sessions</h3>';
        sessions.forEach(session => {
            if (session.success) {
                html += `
                    <div class="result-card">
                        <h3>${session.session_name}</h3>
                        <p><strong>ID:</strong> ${session.session_id}</p>
                        <p><strong>Photos:</strong> ${session.total_photos}</p>
                        ${session.hit_rate ? `<p><strong>Hit Rate:</strong> ${session.hit_rate.toFixed(1)}%</p>` : ''}
                    </div>
                `;
            } else {
                html += `
                    <div class="result-card" style="border-color: var(--error);">
                        <h3 style="color: var(--error);">Failed</h3>
                        <p><strong>Folder:</strong> ${session.folder}</p>
                        <p><strong>Error:</strong> ${session.error}</p>
                    </div>
                `;
            }
        });
    }

    resultsArea.innerHTML = html;
}

async function analyzeData() {
    const analyzeType = document.getElementById('analyze-type').value;
    const target = document.getElementById('analyze-target').value.trim();

    if (!target) {
        showError('analyze-results', 'Please enter a target');
        return;
    }

    const resultsArea = document.getElementById('analyze-results');
    const progressBar = document.getElementById('progress-bar');
    resultsArea.classList.remove('visible');
    progressBar.style.display = 'block';
    
    const taskId = 'analyze_' + Date.now();
    updateProgressBar(0, 'Starting');

    try {
        if (analyzeType === 'wrapped') {
            const category = document.getElementById('wrapped-category').value.trim();
            
            if (!category) {
                showError('analyze-results', 'Please enter a category for wrapped analysis');
                progressBar.style.display = 'none';
                return;
            }
            
            startProgressPolling(taskId, (status) => {
                progressBar.style.display = 'none';
            });
            
            await generateWrapped(target, category, taskId);
        } else {
            startProgressPolling(taskId, (status) => {
                progressBar.style.display = 'none';
            });
            
            const response = await fetch(`${API_BASE}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    type: analyzeType,
                    target: target,
                    task_id: taskId
                })
            });

            const data = await response.json();

            stopProgressPolling();
            progressBar.style.display = 'none';

            if (!response.ok) {
                showError('analyze-results', data.error || 'Analysis failed');
                return;
            }

            displayAnalysisResults(data.analysis);
        }

    } catch (error) {
        stopProgressPolling();
        progressBar.style.display = 'none';
        showError('analyze-results', `Error: ${error.message}`);
    }
}

function displayAnalysisResults(analysis) {
    const resultsArea = document.getElementById('analyze-results');
    resultsArea.classList.add('visible');

    // Debug logging
    console.log('displayAnalysisResults called with:', analysis);
    console.log('analysis.scope:', analysis.scope);
    console.log('analysis.total_photos:', analysis.total_photos);
    console.log('analysis.lens_freq:', analysis.lens_freq);

    // Handle sessions-specific analysis
    if (analysis.scope === 'sessions') {
        let html = `
            <h2 style="margin-bottom: 20px;">Selected Sessions Analysis</h2>
            <div class="result-card">
                <h3>Overview</h3>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-label">Sessions Analyzed</div>
                        <div class="stat-value">${analysis.total_sessions}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Total Photos</div>
                        <div class="stat-value">${analysis.total_photos.toLocaleString()}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">RAW Photos</div>
                        <div class="stat-value">${analysis.total_raw_photos.toLocaleString()}</div>
                    </div>
                    ${analysis.average_hit_rate ? `
                    <div class="stat-item">
                        <div class="stat-label">Average Hit Rate</div>
                        <div class="stat-value">${analysis.average_hit_rate}%</div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        // List sessions
        if (analysis.sessions && analysis.sessions.length > 0) {
            html += '<div class="result-card"><h3>Sessions</h3>';
            analysis.sessions.forEach(session => {
                html += `<p><strong>${escapeHtml(session.name)}:</strong> ${session.total_photos} photos`;
                if (session.hit_rate) html += ` (${session.hit_rate}% hit rate)`;
                html += `</p>`;
            });
            html += '</div>';
        }
        
        resultsArea.innerHTML = html;
        return;
    }

    // Handle database-wide analysis (different structure)
    if (analysis.scope === 'database') {
        let html = `
            <h2 style="margin-bottom: 20px;">Database Analysis</h2>
            <div class="result-card">
                <h3>Overview</h3>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-label">Total Sessions</div>
                        <div class="stat-value">${analysis.total_sessions}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Total Photos</div>
                        <div class="stat-value">${analysis.total_photos.toLocaleString()}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">RAW Photos</div>
                        <div class="stat-value">${analysis.total_raw_photos.toLocaleString()}</div>
                    </div>
                    ${analysis.average_hit_rate ? `
                    <div class="stat-item">
                        <div class="stat-label">Average Hit Rate</div>
                        <div class="stat-value">${analysis.average_hit_rate}%</div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        // Categories breakdown
        if (analysis.categories && Object.keys(analysis.categories).length > 0) {
            html += '<div class="result-card"><h3>Categories</h3>';
            const sortedCats = Object.entries(analysis.categories)
                .sort((a, b) => b[1].photos - a[1].photos);
            sortedCats.forEach(([cat, data]) => {
                html += `<p><strong>${escapeHtml(cat)}:</strong> ${data.sessions} sessions, ${data.photos.toLocaleString()} photos</p>`;
            });
            html += '</div>';
        }
        
        // Groups breakdown
        if (analysis.groups && Object.keys(analysis.groups).length > 0) {
            html += '<div class="result-card"><h3>Groups</h3>';
            const sortedGroups = Object.entries(analysis.groups)
                .sort((a, b) => b[1].photos - a[1].photos);
            sortedGroups.forEach(([grp, data]) => {
                html += `<p><strong>${escapeHtml(grp)}:</strong> ${data.sessions} sessions, ${data.photos.toLocaleString()} photos</p>`;
            });
            html += '</div>';
        }
        
        resultsArea.innerHTML = html;
        return;
    }

    // Handle specific category/group analysis (original format)
    let html = `
        <h2 style="margin-bottom: 20px;">Analysis Complete</h2>
        <div class="result-card">
            <h3>${analysis.name || 'Analysis Results'}</h3>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-label">Total Photos</div>
                    <div class="stat-value">${analysis.total_photos || 0}</div>
                </div>
                ${analysis.hit_rate !== undefined && analysis.hit_rate !== null ? `
                <div class="stat-item">
                    <div class="stat-label">Hit Rate</div>
                    <div class="stat-value">${analysis.hit_rate.toFixed(1)}%</div>
                </div>
                ` : ''}
                <div class="stat-item">
                    <div class="stat-label">Unique Lenses</div>
                    <div class="stat-value">${Object.keys(analysis.lens_freq || {}).length}</div>
                </div>
                ${analysis.camera_freq ? `
                <div class="stat-item">
                    <div class="stat-label">Camera Bodies</div>
                    <div class="stat-value">${Object.keys(analysis.camera_freq).length}</div>
                </div>
                ` : ''}
            </div>
        </div>
    `;

    // Camera Bodies
    if (analysis.camera_freq && Object.keys(analysis.camera_freq).length > 0) {
        html += '<div class="result-card"><h3>Camera Bodies</h3>';
        const cameras = Object.entries(analysis.camera_freq)
            .sort((a, b) => b[1] - a[1]);
        
        cameras.forEach(([camera, count]) => {
            const percentage = ((count / analysis.total_photos) * 100).toFixed(1);
            html += `<p><strong>${camera}:</strong> ${count} photos (${percentage}%)</p>`;
        });
        html += '</div>';
    }

    // Top lenses
    if (analysis.lens_freq && Object.keys(analysis.lens_freq).length > 0) {
        html += '<div class="result-card"><h3>Top Lenses</h3>';
        const lenses = Object.entries(analysis.lens_freq)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        lenses.forEach(([lens, count]) => {
            const percentage = ((count / analysis.total_photos) * 100).toFixed(1);
            html += `<p><strong>${lens}:</strong> ${count} photos (${percentage}%)</p>`;
        });
        html += '</div>';
    }

    // Aperture Stats
    if (analysis.aperture_freq && Object.keys(analysis.aperture_freq).length > 0) {
        html += '<div class="result-card"><h3>Aperture Settings</h3>';
        const apertures = Object.entries(analysis.aperture_freq)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        apertures.forEach(([aperture, count]) => {
            const percentage = ((count / analysis.total_photos) * 100).toFixed(1);
            html += `<p><strong>f/${aperture}:</strong> ${count} photos (${percentage}%)</p>`;
        });
        html += '</div>';
    }

    // Shutter Speed Stats
    if (analysis.shutter_speed_freq && Object.keys(analysis.shutter_speed_freq).length > 0) {
        html += '<div class="result-card"><h3>Shutter Speeds</h3>';
        const shutters = Object.entries(analysis.shutter_speed_freq)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        shutters.forEach(([shutter, count]) => {
            const percentage = ((count / analysis.total_photos) * 100).toFixed(1);
            html += `<p><strong>${shutter}s:</strong> ${count} photos (${percentage}%)</p>`;
        });
        html += '</div>';
    }

    // ISO Stats
    if (analysis.iso_freq && Object.keys(analysis.iso_freq).length > 0) {
        html += '<div class="result-card"><h3>ISO Settings</h3>';
        const isos = Object.entries(analysis.iso_freq)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        isos.forEach(([iso, count]) => {
            const percentage = ((count / analysis.total_photos) * 100).toFixed(1);
            html += `<p><strong>ISO ${iso}:</strong> ${count} photos (${percentage}%)</p>`;
        });
        html += '</div>';
    }

    // Focal Length Stats
    if (analysis.focal_length_freq && Object.keys(analysis.focal_length_freq).length > 0) {
        html += '<div class="result-card"><h3>Focal Lengths</h3>';
        const focals = Object.entries(analysis.focal_length_freq)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);
        
        focals.forEach(([focal, count]) => {
            const percentage = ((count / analysis.total_photos) * 100).toFixed(1);
            html += `<p><strong>${focal}mm:</strong> ${count} photos (${percentage}%)</p>`;
        });
        html += '</div>';
    }

    // Time of Day
    if (analysis.time_of_day_freq && Object.keys(analysis.time_of_day_freq).length > 0) {
        html += '<div class="result-card"><h3>Time of Day</h3>';
        const times = Object.entries(analysis.time_of_day_freq)
            .sort((a, b) => b[1] - a[1]);
        
        times.forEach(([time, count]) => {
            const percentage = ((count / analysis.total_photos) * 100).toFixed(1);
            html += `<p><strong>${time}:</strong> ${count} photos (${percentage}%)</p>`;
        });
        html += '</div>';
    }

    resultsArea.innerHTML = html;
}

async function generateWrapped(group, category, taskId) {
    const resultsArea = document.getElementById('analyze-results');
    const progressBar = document.getElementById('progress-bar');

    try {
        const response = await fetch(`${API_BASE}/wrapped`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                category: category,
                group: group,
                task_id: taskId
            })
        });

        const data = await response.json();

        stopProgressPolling();
        progressBar.style.display = 'none';

        if (!response.ok) {
            showError('analyze-results', data.error || 'Wrapped generation failed');
            return;
        }

        if (!data.wrapped) {
            showError('analyze-results', data.message || 'No data found');
            return;
        }

        displayWrappedResults(data.wrapped);

    } catch (error) {
        progressBar.style.display = 'none';
        showError('analyze-results', `Error: ${error.message}`);
    }
}

function displayWrappedResults(wrapped) {
    const resultsArea = document.getElementById('analyze-results');
    resultsArea.classList.add('visible');

    let html = `
        <h2 style="margin-bottom: 20px;">Analysis Complete</h2>
        <div class="wrapped-card">
            <h3>${wrapped.category.toUpperCase()} ${wrapped.group.toUpperCase()}</h3>
            <p>Total Sessions: ${wrapped.total_sessions}</p>
        </div>
    `;

    if (wrapped.sessions && wrapped.sessions.length > 0) {
        html += '<div class="result-card"><h3>All Sessions</h3>';
        
        const sessionsWithHitRate = wrapped.sessions.filter(s => s.hit_rate != null);
        if (sessionsWithHitRate.length > 0) {
            const avgHitRate = sessionsWithHitRate.reduce((sum, s) => sum + s.hit_rate, 0) / sessionsWithHitRate.length;
            html += `<p><strong>Average Hit Rate:</strong> ${avgHitRate.toFixed(1)}%</p>`;
        }

        const totalPhotos = wrapped.sessions.reduce((sum, s) => sum + s.total_photos, 0);
        html += `<p><strong>Total Photos:</strong> ${totalPhotos}</p>`;

        html += '</div>';

        html += '<table class="session-table"><thead><tr>';
        html += '<th>Session</th><th>Photos</th><th>Hit Rate</th><th>Date</th>';
        html += '</tr></thead><tbody>';

        wrapped.sessions.forEach(session => {
            html += '<tr>';
            html += `<td>${session.name}</td>`;
            html += `<td>${session.total_photos}</td>`;
            html += `<td>${session.hit_rate ? session.hit_rate.toFixed(1) + '%' : 'N/A'}</td>`;
            html += `<td>${session.date || 'N/A'}</td>`;
            html += '</tr>';
        });

        html += '</tbody></table>';
    }

    if (wrapped.note) {
        html += `<div class="result-card"><p><em>${wrapped.note}</em></p></div>`;
    }

    resultsArea.innerHTML = html;
}

// Database overview state
let dbData = {
    sessions: [],
    filteredSessions: [],
    sortColumn: 'date',
    sortDirection: 'desc'
};

async function loadDatabaseOverview() {
    const summaryContent = document.getElementById('db-summary-content');
    const tbody = document.getElementById('db-sessions-tbody');
    
    summaryContent.innerHTML = '<p>Loading...</p>';
    tbody.innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center;">Loading...</td></tr>';

    try {
        const response = await fetch(`${API_BASE}/database/overview`);
        const data = await response.json();

        if (!response.ok) {
            summaryContent.innerHTML = `<p style="color: var(--error);">Error: ${data.error || 'Failed to load database'}</p>`;
            return;
        }

        // Display summary
        displayDatabaseSummary(data.summary);
        
        // Store sessions data
        dbData.sessions = data.sessions;
        dbData.filteredSessions = [...data.sessions];
        
        // Sort and display
        sortDatabaseTable(dbData.sortColumn, true);

    } catch (error) {
        summaryContent.innerHTML = `<p style="color: var(--error);">Error: ${error.message}</p>`;
        tbody.innerHTML = `<tr><td colspan="7" style="padding: 20px; text-align: center; color: var(--error);">Error loading database</td></tr>`;
    }
}

function displayDatabaseSummary(summary) {
    const summaryContent = document.getElementById('db-summary-content');
    
    let html = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px;">
            <div>
                <strong style="font-size: 2em; color: var(--primary);">${summary.total_sessions}</strong>
                <p style="margin: 5px 0 0 0;">Total Sessions</p>
            </div>
            <div>
                <strong style="font-size: 2em; color: var(--primary);">${summary.total_photos.toLocaleString()}</strong>
                <p style="margin: 5px 0 0 0;">Total Photos</p>
            </div>
        </div>
    `;
    
    if (summary.categories.length > 0) {
        html += '<div style="margin-bottom: 15px;"><strong>Categories:</strong><br>';
        summary.categories.forEach(cat => {
            html += `<span style="margin-right: 15px;">• ${cat.name}: ${cat.sessions} sessions, ${cat.photos.toLocaleString()} photos</span>`;
        });
        html += '</div>';
    }
    
    if (summary.groups.length > 0) {
        html += '<div><strong>Groups:</strong><br>';
        summary.groups.forEach(grp => {
            html += `<span style="margin-right: 15px;">• ${grp.name}: ${grp.sessions} sessions, ${grp.photos.toLocaleString()} photos</span>`;
        });
        html += '</div>';
    }
    
    summaryContent.innerHTML = html;
}

function filterDatabaseTable() {
    const searchTerm = document.getElementById('search-session').value.toLowerCase();
    const categoryFilter = document.getElementById('filter-db-category').value.toLowerCase();
    const groupFilter = document.getElementById('filter-db-group').value.toLowerCase();
    
    dbData.filteredSessions = dbData.sessions.filter(session => {
        const matchesSearch = !searchTerm || session.name.toLowerCase().includes(searchTerm);
        const matchesCategory = !categoryFilter || session.category.toLowerCase().includes(categoryFilter);
        const matchesGroup = !groupFilter || session.group.toLowerCase().includes(groupFilter);
        
        return matchesSearch && matchesCategory && matchesGroup;
    });
    
    renderDatabaseTable();
}

function sortDatabaseTable(column, skipToggle = false) {
    // Toggle sort direction if clicking same column
    if (!skipToggle && dbData.sortColumn === column) {
        dbData.sortDirection = dbData.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        dbData.sortColumn = column;
        if (skipToggle) {
            dbData.sortDirection = column === 'date' ? 'desc' : 'asc';
        } else {
            dbData.sortDirection = 'asc';
        }
    }
    
    // Sort filtered sessions
    dbData.filteredSessions.sort((a, b) => {
        let aVal, bVal;
        
        switch (column) {
            case 'name':
                aVal = a.name.toLowerCase();
                bVal = b.name.toLowerCase();
                break;
            case 'category':
                aVal = a.category.toLowerCase();
                bVal = b.category.toLowerCase();
                break;
            case 'group':
                aVal = a.group.toLowerCase();
                bVal = b.group.toLowerCase();
                break;
            case 'photos':
                aVal = a.total_photos;
                bVal = b.total_photos;
                break;
            case 'raw':
                aVal = a.total_raw_photos;
                bVal = b.total_raw_photos;
                break;
            case 'hitrate':
                aVal = a.hit_rate ?? -1;
                bVal = b.hit_rate ?? -1;
                break;
            case 'date':
                aVal = a.date || '';
                bVal = b.date || '';
                break;
            default:
                return 0;
        }
        
        if (aVal < bVal) return dbData.sortDirection === 'asc' ? -1 : 1;
        if (aVal > bVal) return dbData.sortDirection === 'asc' ? 1 : -1;
        return 0;
    });
    
    renderDatabaseTable();
}

function renderDatabaseTable() {
    const tbody = document.getElementById('db-sessions-tbody');
    
    if (dbData.filteredSessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center;">No sessions found</td></tr>';
        return;
    }
    
    tbody.innerHTML = dbData.filteredSessions.map(session => `
        <tr>
            <td style="padding: 12px;">${escapeHtml(session.name)}</td>
            <td style="padding: 12px;">${escapeHtml(session.category)}</td>
            <td style="padding: 12px;">${escapeHtml(session.group)}</td>
            <td style="padding: 12px; text-align: right;">${session.total_photos}</td>
            <td style="padding: 12px; text-align: right;">${session.total_raw_photos}</td>
            <td style="padding: 12px; text-align: right;">${session.hit_rate !== null ? session.hit_rate + '%' : 'N/A'}</td>
            <td style="padding: 12px;">${session.date || 'N/A'}</td>
        </tr>
    `).join('');
}

// Database Reset Functions
async function handleResetAll() {
    if (!confirm('⚠️ WARNING: This will permanently delete ALL data from the database!\n\nThis includes:\n- All sessions\n- All photos\n- All analyses\n- All lenses\n\nThis action CANNOT be undone.\n\nAre you absolutely sure?')) {
        return;
    }
    
    // Double confirmation for safety
    if (!confirm('Final confirmation: Delete everything?')) {
        return;
    }
    
    const resetBtn = document.getElementById('reset-all-btn');
    resetBtn.disabled = true;
    resetBtn.textContent = 'Deleting...';
    
    try {
        const response = await fetch(`${API_BASE}/database/reset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ confirm: true })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            alert(`✅ Database reset complete!\n\nDeleted:\n- ${data.deleted.sessions} sessions\n- ${data.deleted.photos} photos\n- ${data.deleted.lenses} lenses\n- ${data.deleted.analyses} analyses`);
            loadDatabaseOverview();
        } else {
            alert(`❌ Error: ${data.error || 'Failed to reset database'}`);
        }
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    } finally {
        resetBtn.disabled = false;
        resetBtn.textContent = 'Reset All Data';
    }
}

async function toggleResetDropdown(type) {
    const dropdown = document.getElementById(`${type}-dropdown`);
    const otherDropdown = document.getElementById(type === 'category' ? 'group-dropdown' : 'category-dropdown');
    
    // Close other dropdown
    otherDropdown.style.display = 'none';
    
    // Toggle current dropdown
    if (dropdown.style.display === 'none' || !dropdown.style.display) {
        dropdown.style.display = 'block';
        await loadDropdownOptions(type);
    } else {
        dropdown.style.display = 'none';
    }
}

function closeResetDropdown(type) {
    const dropdown = document.getElementById(`${type}-dropdown`);
    dropdown.style.display = 'none';
}

async function loadDropdownOptions(type) {
    const listContainer = document.getElementById(`${type}-list`);
    listContainer.innerHTML = '<p style="padding: 10px;">Loading...</p>';
    
    try {
        const response = await fetch(`${API_BASE}/database/categories-groups`);
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            listContainer.innerHTML = '<p style="padding: 10px; color: var(--error);">Error loading data</p>';
            return;
        }
        
        const items = type === 'category' ? data.categories : data.groups;
        
        if (items.length === 0) {
            listContainer.innerHTML = `<p style="padding: 10px; color: var(--text-secondary);">No ${type === 'category' ? 'categories' : 'groups'} found</p>`;
            return;
        }
        
        listContainer.innerHTML = items.map(item => `
            <label>
                <input type="checkbox" class="${type}-checkbox" value="${escapeHtml(item)}">
                ${escapeHtml(item)}
            </label>
        `).join('');
        
    } catch (error) {
        listContainer.innerHTML = `<p style="padding: 10px; color: var(--error);">Error: ${error.message}</p>`;
    }
}

function handleSelectAll(type, checked) {
    const checkboxes = document.querySelectorAll(`.${type}-checkbox`);
    checkboxes.forEach(cb => cb.checked = checked);
}

async function handleDeleteByFilter(type) {
    const checkboxes = document.querySelectorAll(`.${type}-checkbox:checked`);
    const selected = Array.from(checkboxes).map(cb => cb.value);
    
    if (selected.length === 0) {
        alert(`Please select at least one ${type} to delete.`);
        return;
    }
    
    const typeName = type === 'category' ? 'categories' : 'groups';
    if (!confirm(`⚠️ Are you sure you want to delete all sessions from these ${typeName}?\n\n${selected.join(', ')}\n\nThis will permanently delete all associated photos and cannot be undone.`)) {
        return;
    }
    
    const confirmBtn = document.getElementById(`confirm-delete-${type}`);
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Deleting...';
    
    try {
        const response = await fetch(`${API_BASE}/database/delete-${type}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [typeName]: selected })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            alert(`✅ ${data.message}`);
            closeResetDropdown(type);
            loadDatabaseOverview();
        } else {
            alert(`❌ Error: ${data.error || 'Failed to delete'}`);
        }
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Delete Selected';
    }
}

function renderDatabaseTable() {
    const tbody = document.getElementById('db-sessions-tbody');
    const showingCount = document.getElementById('db-showing-count');
    const totalCount = document.getElementById('db-total-count');
    
    if (dbData.filteredSessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="padding: 20px; text-align: center;">No sessions match your filters</td></tr>';
        showingCount.textContent = '0';
        totalCount.textContent = dbData.sessions.length;
        return;
    }
    
    let html = '';
    dbData.filteredSessions.forEach(session => {
        html += '<tr style="border-bottom: 1px solid var(--border-color);">';
        html += `<td style="padding: 10px;">${session.name}</td>`;
        html += `<td style="padding: 10px;">${session.category || '-'}</td>`;
        html += `<td style="padding: 10px;">${session.group || '-'}</td>`;
        html += `<td style="padding: 10px; text-align: right;">${session.total_photos}</td>`;
        html += `<td style="padding: 10px; text-align: right;">${session.total_raw_photos || '-'}</td>`;
        html += `<td style="padding: 10px; text-align: right;">${session.hit_rate !== null ? session.hit_rate + '%' : '-'}</td>`;
        html += `<td style="padding: 10px;">${session.date || '-'}</td>`;
        html += '</tr>';
    });
    
    tbody.innerHTML = html;
    showingCount.textContent = dbData.filteredSessions.length;
    totalCount.textContent = dbData.sessions.length;
    
    // Update sort indicators in headers
    document.querySelectorAll('#db-sessions-table th[data-sort]').forEach(th => {
        const arrow = dbData.sortDirection === 'asc' ? ' ▲' : ' ▼';
        const text = th.textContent.replace(/[▲▼]/g, '').trim();
        th.textContent = th.dataset.sort === dbData.sortColumn ? text + arrow : text;
    });
}

function displaySessions(sessions) {
    const resultsArea = document.getElementById('sessions-results');

    if (sessions.length === 0) {
        resultsArea.innerHTML = '<div class="result-card"><p>No sessions found</p></div>';
        return;
    }

    let html = `
        <div class="success-message">Found ${sessions.length} session(s)</div>
        <table class="session-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Group</th>
                    <th>Photos</th>
                    <th>Hit Rate</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
    `;

    sessions.forEach(session => {
        html += '<tr>';
        html += `<td>${session.id}</td>`;
        html += `<td>${session.name}</td>`;
        html += `<td>${session.category}</td>`;
        html += `<td>${session.group}</td>`;
        html += `<td>${session.total_photos}</td>`;
        html += `<td>${session.hit_rate ? session.hit_rate.toFixed(1) + '%' : 'N/A'}</td>`;
        html += `<td>${session.date || 'N/A'}</td>`;
        html += '</tr>';
    });

    html += '</tbody></table>';
    resultsArea.innerHTML = html;
}

function showError(areaId, message) {
    const area = document.getElementById(areaId);
    area.classList.add('visible');
    area.innerHTML = `<div class="error-message">${message}</div>`;
}

// Detail modal functions
window.showSingleFolderDetails = function(session, item) {
    const modal = document.getElementById('details-modal');
    const title = document.getElementById('modal-title');
    const body = document.getElementById('modal-body');
    
    title.textContent = 'Single Folder Extraction Details';
    
    let html = `
        <div class="result-card">
            <h3>${session.name}</h3>
            <p><strong>Category:</strong> ${item.category}</p>
            <p><strong>Group:</strong> ${item.group}</p>
            <p><strong>Path:</strong> ${item.folderPath}</p>
            ${item.sessionName ? `<p><strong>Session Name:</strong> ${item.sessionName}</p>` : ''}
            <p><strong>Session ID:</strong> ${session.id}</p>
            <p><strong>Total Photos:</strong> ${session.total_photos}</p>
            ${session.total_raw_photos ? `<p><strong>Total RAW Photos:</strong> ${session.total_raw_photos}</p>` : ''}
            ${session.hit_rate ? `<p><strong>Hit Rate:</strong> ${session.hit_rate.toFixed(1)}%</p>` : ''}
            ${session.date ? `<p><strong>Date:</strong> ${session.date}</p>` : ''}
            <p><strong>Hit Rate Calculation:</strong> ${item.calculateHitRate ? 'Enabled' : 'Disabled'}</p>
        </div>
    `;
    
    body.innerHTML = html;
    modal.style.display = 'block';
}

window.showCrawlDetails = function(sessions, item) {
    const modal = document.getElementById('details-modal');
    const title = document.getElementById('modal-title');
    const body = document.getElementById('modal-body');
    
    title.textContent = 'Batch Crawl Extraction Details';
    
    const successfulSessions = sessions.filter(s => s.success);
    const failedSessions = sessions.filter(s => !s.success);
    
    let html = `
        <div class="result-card">
            <h3>Overview</h3>
            <p><strong>Category:</strong> ${item.category}</p>
            <p><strong>Group:</strong> ${item.group}</p>
            <p><strong>Parent Path:</strong> ${item.folderPath}</p>
            <p><strong>Target Folder:</strong> ${item.targetFolder}</p>
            <p><strong>Total Sessions:</strong> ${sessions.length}</p>
            <p><strong>Successful:</strong> ${successfulSessions.length}</p>
            <p><strong>Failed:</strong> ${failedSessions.length}</p>
            <p><strong>Hit Rate Calculation:</strong> ${item.calculateHitRate ? 'Enabled' : 'Disabled'}</p>
        </div>
    `;
    
    if (successfulSessions.length > 0) {
        html += '<h3 style="color: var(--success);">✓ Successful Sessions</h3>';
        successfulSessions.forEach(session => {
            html += `
                <div class="result-card" style="margin-bottom: 10px;">
                    <h4>${session.session_name}</h4>
                    <p><strong>Session ID:</strong> ${session.session_id}</p>
                    <p><strong>Total Photos:</strong> ${session.total_photos}</p>
                    ${session.hit_rate ? `<p><strong>Hit Rate:</strong> ${session.hit_rate.toFixed(1)}%</p>` : ''}
                </div>
            `;
        });
    }
    
    if (failedSessions.length > 0) {
        html += '<h3 style="color: var(--error);">✗ Failed Sessions</h3>';
        failedSessions.forEach(session => {
            html += `
                <div class="result-card" style="margin-bottom: 10px; border-color: var(--error);">
                    <h4 style="color: var(--error);">Failed</h4>
                    <p><strong>Folder:</strong> ${session.folder}</p>
                    <p><strong>Error:</strong> ${session.error}</p>
                </div>
            `;
        });
    }
    
    body.innerHTML = html;
    modal.style.display = 'block';
}

window.closeDetailsModal = function() {
    document.getElementById('details-modal').style.display = 'none';
}

// Close modal when clicking outside of it
window.onclick = function(event) {
    const modal = document.getElementById('details-modal');
    if (event.target === modal) {
        closeDetailsModal();
    }
}
