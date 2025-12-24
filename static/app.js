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

// Helper function to extract session name from folder path using smart logic
function extractSessionNameFromPath(folderPath) {
    if (!folderPath) return '';
    
    // Split path and get all parts
    const parts = folderPath.replace(/\\/g, '/').split('/').filter(p => p.trim());
    if (parts.length === 0) return '';
    
    // Date patterns to look for
    const datePatterns = [
        /\d{4}[-_]\d{2}[-_]\d{2}/,  // YYYY-MM-DD or YYYY_MM_DD
        /\d{2}[-_]\d{2}[-_]\d{4}/,  // MM-DD-YYYY or MM_DD_YYYY
        /\d{8}/,                      // YYYYMMDD
        /\d{2}[-_]\d{2}[-_]\d{2}/   // YY-MM-DD or MM-DD-YY
    ];
    
    const genericFolders = ['photos', 'edited', 'raw', 'images', 'jpg', 'jpeg', 'export', 'exported'];
    
    let datePatternFolder = null;
    let nonGenericFolder = null;
    
    // Search from right to left (end of path to beginning)
    for (let i = parts.length - 1; i >= 0; i--) {
        const part = parts[i];
        const partLower = part.toLowerCase();
        
        // Check if folder has a date pattern
        const hasDate = datePatterns.some(pattern => pattern.test(part));
        
        if (hasDate && !datePatternFolder) {
            datePatternFolder = part;
        }
        
        if (!genericFolders.includes(partLower) && !nonGenericFolder) {
            nonGenericFolder = part;
        }
    }
    
    // Use priority order: date pattern > non-generic > endpoint
    const sessionName = datePatternFolder || nonGenericFolder || parts[parts.length - 1];
    return sessionName.replace(/ /g, '_');
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

            // Auto-run analysis when Analysis tab is opened for the first time
            if (tabId === 'analyze' && !currentAnalysisData) {
                runDatabaseAnalysis();
            }
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

    // Date heuristics checkbox - toggle date input
    const dateHeuristicsCheckbox = document.getElementById('use-date-heuristics');
    const filenameDatesCheckbox = document.getElementById('use-filename-dates');
    const sessionDateInput = document.getElementById('session-date');
    
    dateHeuristicsCheckbox.addEventListener('change', () => {
        if (dateHeuristicsCheckbox.checked) {
            sessionDateInput.disabled = true;
            sessionDateInput.style.opacity = '0.5';
            sessionDateInput.style.cursor = 'not-allowed';
        } else {
            sessionDateInput.disabled = false;
            sessionDateInput.style.opacity = '1';
            sessionDateInput.style.cursor = 'text';
        }
    });
    
    // Set initial state (heuristics enabled by default)
    sessionDateInput.disabled = true;
    sessionDateInput.style.opacity = '0.5';
    sessionDateInput.style.cursor = 'not-allowed';

    // Auto-extract session name preview when folder path changes
    const folderPathInput = document.getElementById('folder-path');
    const sessionNameInput = document.getElementById('session-name');
    const autoPreview = document.getElementById('auto-session-name-preview');
    
    folderPathInput.addEventListener('input', () => {
        if (sessionNameInput.value.trim() === '' && folderPathInput.value.trim()) {
            const autoName = extractSessionNameFromPath(folderPathInput.value.trim());
            if (autoName) {
                autoPreview.textContent = `Auto: ${autoName}`;
                autoPreview.style.display = 'block';
            } else {
                autoPreview.style.display = 'none';
            }
        } else {
            autoPreview.style.display = 'none';
        }
    });
    
    sessionNameInput.addEventListener('input', () => {
        if (sessionNameInput.value.trim()) {
            autoPreview.style.display = 'none';
        } else if (folderPathInput.value.trim()) {
            const autoName = extractSessionNameFromPath(folderPathInput.value.trim());
            if (autoName) {
                autoPreview.textContent = `Auto: ${autoName}`;
                autoPreview.style.display = 'block';
            }
        }
    });

    // Add to queue
    document.getElementById('add-to-queue-btn').addEventListener('click', addToQueue);

    // Extract all from queue
    document.getElementById('extract-all-btn').addEventListener('click', extractAllFromQueue);

    // Analysis tab functionality
    document.getElementById('run-analysis-btn').addEventListener('click', runDatabaseAnalysis);

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

// Helper function to check for duplicate sessions
async function checkForDuplicates(category, group, sessionName = '', sessionDate = null) {
    console.log('[DUPLICATE CHECK] Starting check:', { category, group, sessionName, sessionDate });
    try {
        const response = await fetch('/api/check-duplicates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, group, session_name: sessionName, date: sessionDate })
        });
        
        const data = await response.json();
        console.log('[DUPLICATE CHECK] API response:', data);
        
        if (data.similar_sessions && data.similar_sessions.length > 0) {
            // Filter duplicates based on date verification:
            // - If BOTH have dates, they must match (same date = likely duplicate)
            // - If only one or neither has date, consider as potential duplicate
            let matches = data.similar_sessions;
            
            if (sessionDate) {
                matches = matches.filter(s => {
                    // If existing has no date, still flag as potential duplicate
                    if (!s.date) return true;
                    // Both have dates - compare them
                    const existingDate = s.date.split('T')[0];
                    const inputDate = sessionDate.split('T')[0];
                    return existingDate === inputDate;
                });
            }
            
            if (matches.length > 0) {
                console.log('[DUPLICATE CHECK] Found duplicates after filtering:', matches);
                return {
                    hasDuplicates: true,
                    existing: matches[0], // First match
                    input: { 
                        name: data.input_session_name,
                        category: data.input_category, 
                        group: data.input_group,
                        date: sessionDate
                    }
                };
            } else {
                console.log('[DUPLICATE CHECK] No matches after date filtering');
            }
        }
        
        console.log('[DUPLICATE CHECK] No duplicates found');
        return { hasDuplicates: false };
    } catch (error) {
        console.error('[DUPLICATE CHECK] Error:', error);
        return { hasDuplicates: false };
    }
}
// Helper function to show duplicate resolution dialog
async function showDuplicateResolutionDialog(existing, input) {
    return new Promise((resolve) => {
        const existingStr = `"${existing.category}" / "${existing.group}" / "${existing.name}"`;
        const inputStr = `"${input.category}" / "${input.group}" / "${input.name}"`;
        
        // Check if it's an exact match
        const isExactMatch = existing.category === input.category && 
                            existing.group === input.group &&
                            existing.name === input.name;
        
        // Add match percentage if available
        let matchInfo = '';
        if (existing.match_percentage !== undefined) {
            matchInfo = `\nMatch: ${existing.match_percentage}%`;
        }
        
        // Add additional details
        let detailsInfo = '';
        if (existing.total_photos) {
            detailsInfo += `\nPhotos: ${existing.total_photos}`;
            if (existing.hit_rate) {
                detailsInfo += ` | Hit Rate: ${existing.hit_rate.toFixed(1)}%`;
            }
        }
        
        // Add date info if available
        let dateInfo = '';
        if (existing.date || input.date) {
            const existingDate = existing.date ? existing.date.split('T')[0] : 'Not set';
            const inputDate = input.date ? input.date.split('T')[0] : 'Not set';
            const existingSource = existing.date_detected ? ` (${existing.date_detected})` : '';
            dateInfo = `\nExisting date: ${existingDate}${existingSource}\n` +
                      `Your date: ${inputDate}`;
        }
        
        let message;
        if (isExactMatch) {
            message = `⚠️ DUPLICATE SESSION FOUND\n\n` +
                `This session already exists in the database:\n` +
                `${existingStr}${matchInfo}${detailsInfo}\n` +
                dateInfo +
                `\n\nThis will create a duplicate entry.\n\n` +
                `Choose an option:\n` +
                `1 = Continue (allow duplicate)\n` +
                `0 = Cancel`;
        } else {
            message = `⚠️ SIMILAR SESSION FOUND\n\n` +
                `Existing in database: ${existingStr}${matchInfo}${detailsInfo}\n` +
                `Your input: ${inputStr}\n` +
                dateInfo +
                `\n\nThese sessions may be related.\n\n` +
                `Choose an option:\n` +
                `1 = Use YOUR input and update database\n` +
                `2 = Use EXISTING from database\n` +
                `3 = Keep both separate\n` +
                `0 = Cancel`;
        }
        
        const choice = prompt(message);
        
        if (isExactMatch) {
            if (choice === '1') {
                resolve('keep_separate');
            } else {
                resolve('cancel');
            }
        } else {
            if (choice === '1') {
                resolve('rename_existing');
            } else if (choice === '2') {
                resolve('use_existing');
            } else if (choice === '3') {
                resolve('keep_separate');
            } else {
                resolve('cancel');
            }
        }
    });
}

// Helper function to rename existing sessions
async function renameExistingSessions(oldCategory, oldGroup, newCategory, newGroup) {
    try {
        const response = await fetch('/api/database/rename-sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                old_category: oldCategory,
                old_group: oldGroup,
                new_category: newCategory,
                new_group: newGroup
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log(`Renamed ${data.updated_sessions} sessions`);
            alert(`✓ Updated ${data.updated_sessions} existing session(s) to use "${newCategory}" / "${newGroup}"`);
        } else {
            alert('Error renaming sessions: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error renaming sessions:', error);
        alert('Error renaming sessions: ' + error.message);
    }
}

async function addToQueue() {
    console.log('addToQueue function called');
    
    const mode = document.getElementById('mode-select').value;
    const folderPath = document.getElementById('folder-path').value.trim();
    let sessionName = document.getElementById('session-name').value.trim();
    const sessionDate = document.getElementById('session-date').value.trim();
    const useDateHeuristics = document.getElementById('use-date-heuristics').checked;
    const useFilenameDates = document.getElementById('use-filename-dates').checked;
    const category = document.getElementById('category').value.trim();
    const group = document.getElementById('group').value.trim();
    const calculateHitRate = document.getElementById('calculate-hit-rate').checked;

    // If session name is empty, auto-extract from path
    if (!sessionName && folderPath) {
        sessionName = extractSessionNameFromPath(folderPath);
        console.log('Auto-extracted session name:', sessionName);
    }

    console.log('Adding to queue:', { mode, folderPath, category, group, sessionName });

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

    // Check for duplicates before adding to queue (include session name and date for verification)
    console.log('[ADD TO QUEUE] Checking for duplicates...');
    const duplicateCheckResult = await checkForDuplicates(category, group, sessionName, sessionDate || null);
    console.log('[ADD TO QUEUE] Duplicate check result:', duplicateCheckResult);
    
    if (duplicateCheckResult && duplicateCheckResult.hasDuplicates) {
        console.log('[ADD TO QUEUE] Duplicates found, showing dialog...');
        // Show resolution dialog and wait for user choice
        const resolution = await showDuplicateResolutionDialog(
            duplicateCheckResult.existing,
            duplicateCheckResult.input
        );
        console.log('[ADD TO QUEUE] User resolution:', resolution);
        
        if (resolution === 'cancel') {
            return; // User cancelled
        } else if (resolution === 'rename_existing') {
            // Rename all existing sessions to match new input
            await renameExistingSessions(
                duplicateCheckResult.existing.category,
                duplicateCheckResult.existing.group,
                category,
                group
            );
        } else if (resolution === 'use_existing') {
            // Update form to use existing names
            document.getElementById('category').value = duplicateCheckResult.existing.category;
            document.getElementById('group').value = duplicateCheckResult.existing.group;
        }
        // If 'keep_separate', continue with original values
    }

    // Re-read category and group after potential duplicate resolution
    const finalCategory = document.getElementById('category').value.trim();
    const finalGroup = document.getElementById('group').value.trim();

    const queueItem = {
        id: Date.now(),
        mode: mode,
        folderPath: folderPath,
        sessionName: sessionName,
        sessionDate: sessionDate,
        useDateHeuristics: useDateHeuristics,
        useFilenameDates: useFilenameDates,
        category: finalCategory,
        group: finalGroup,
        calculateHitRate: calculateHitRate,
        targetFolder: targetFolder
    };

    console.log('Queue item created:', queueItem);

    extractionQueue.push(queueItem);
    renderQueue();
    
    // Clear form for next entry
    document.getElementById('folder-path').value = '';
    document.getElementById('session-name').value = '';
    document.getElementById('session-date').value = '';
    document.getElementById('use-date-heuristics').checked = true;
    document.getElementById('use-filename-dates').checked = true;
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
                        ${item.sessionDate ? `<div class="queue-item-detail"><strong>Date:</strong> ${item.sessionDate}</div>` : ''}
                        ${!item.sessionDate && item.useDateHeuristics ? `<div class="queue-item-detail"><strong>Date:</strong> Auto-detect</div>` : ''}
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
                        date: item.sessionDate,
                        use_date_heuristics: item.useDateHeuristics,
                        use_filename_dates: item.useFilenameDates,
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

async function runDatabaseAnalysis() {
    const resultsArea = document.getElementById('analyze-results');
    const progressBar = document.getElementById('progress-bar');
    
    // Clear any existing filters - start fresh with full database analysis
    activeFilters = {};
    currentAnalysisData = null;
    
    resultsArea.innerHTML = '';
    progressBar.style.display = 'block';
    updateProgressBar(0, 'Starting analysis...');
    
    try {
        const response = await fetch(`${API_BASE}/analyze/database`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ })
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
        
        // Store the full (unfiltered) analysis as the baseline for labels/options
        currentAnalysisData = data.analysis;
        currentFilteredAnalysisData = data.analysis;
        currentFacetAnalyses = buildDefaultFacetAnalyses(data.analysis);
        
        // Log for debugging
        console.log('Analysis response:', data);
        
        displayAnalysisResults(data.analysis, currentFacetAnalyses);
        
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
                                ${session.date ? `<p><strong>Date:</strong> ${session.date} (${session.date_detected || 'provided'})</p>` : `<p><strong>Date:</strong> Not found</p>`}
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
    let sessionName = document.getElementById('session-name').value.trim();
    const sessionDate = document.getElementById('session-date').value.trim();
    const useDateHeuristics = document.getElementById('use-date-heuristics').checked;
    const useFilenameDates = document.getElementById('use-filename-dates').checked;
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

    // If session name is empty, auto-extract from path
    if (!sessionName && folderPath) {
        sessionName = extractSessionNameFromPath(folderPath);
        console.log('Auto-extracted session name:', sessionName);
    }

    // Check for duplicates before extraction (include session name and date for verification)
    const duplicateCheckResult = await checkForDuplicates(category, group, sessionName, sessionDate || null);
    if (duplicateCheckResult && duplicateCheckResult.hasDuplicates) {
        // Show resolution dialog and wait for user choice
        const resolution = await showDuplicateResolutionDialog(
            duplicateCheckResult.existing,
            duplicateCheckResult.input
        );
        
        if (resolution === 'cancel') {
            return; // User cancelled
        } else if (resolution === 'rename_existing') {
            // Rename all existing sessions to match new input
            await renameExistingSessions(
                duplicateCheckResult.existing.category,
                duplicateCheckResult.existing.group,
                category,
                group
            );
        } else if (resolution === 'use_existing') {
            // Update form and variables to use existing names
            document.getElementById('category').value = duplicateCheckResult.existing.category;
            document.getElementById('group').value = duplicateCheckResult.existing.group;
        }
        // If 'keep_separate', continue with original values
    }

    // Re-read category and group after potential duplicate resolution
    const finalCategory = document.getElementById('category').value.trim();
    const finalGroup = document.getElementById('group').value.trim();

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
                    date_str: sessionDate,
                    use_date_heuristics: useDateHeuristics,
                    use_filename_dates: useFilenameDates,
                    category: finalCategory,
                    group: finalGroup,
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
                    date_str: sessionDate,
                    use_date_heuristics: useDateHeuristics,
                    use_filename_dates: useFilenameDates,
                    category: finalCategory,
                    group: finalGroup,
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
            <p style="margin-top: 15px;"><strong>Session Name:</strong> ${session.name}</p>
            <p><strong>Category:</strong> ${session.category}</p>
            <p><strong>Group:</strong> ${session.group}</p>
            ${session.date ? `<p><strong>Date:</strong> ${session.date} <span style="color: var(--success);">(${session.date_detected || 'provided'})</span></p>` : `<p><strong>Date:</strong> <span style="color: var(--error);">Not found</span></p>`}
            ${session.date_detected && session.date_detected.startsWith('filename') ? `<p style="color: var(--warning); font-size: 0.9em; margin-top: 10px;">💡 Date extracted from filenames. You can adjust this in the Database tab if needed.</p>` : ''}
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

// Helper function to create histogram charts
let chartInstances = [];
let currentAnalysisData = null; // Store the full analysis data
let currentFilteredAnalysisData = null; // Store the analysis matching ALL active filters
let currentFacetAnalyses = null; // Store per-pane facet analyses (all filters except that pane)
let currentPhotoDetailsPhotos = null; // Store the current Photo Details rows for local-only charts
let currentPhotoDetailsVisiblePhotos = null; // Store the Photo Details rows currently shown (after local chart filtering)
let photoDetailsLocalFilters = { day_of_week: [], time_of_day: [] }; // Local-only filters for Photo Details chart/table
let analysisRequestSeq = 0; // Prevent out-of-order async responses from overwriting UI
let analysisAbortController = null; // Abort in-flight analysis requests when filters change quickly
let activeFilters = {}; // Store active filters { filterType: value }
let activeLensType = 'all'; // Track lens type filter: 'all', 'prime', or 'zoom'
let photoDetailsTemporalMode = 'day_of_week'; // 'day_of_week' | 'time_of_day'
let expandedSections = {}; // Track which sections are expanded

function requestChartResize() {
    // Chart.js can compute a tiny/default width if a canvas is created while hidden
    // (e.g., in a collapsed section). Force a reflow after layout/visibility changes.
    const resizeAll = () => {
        chartInstances.forEach(chart => {
            try {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            } catch (e) {
                // ignore
            }
        });
    };

    // Multi-pass: immediate next frame, then again after one more frame, and once after a short delay.
    try {
        if (typeof window.requestAnimationFrame === 'function') {
            window.requestAnimationFrame(() => {
                resizeAll();
                window.requestAnimationFrame(() => {
                    resizeAll();
                });
            });
        } else {
            resizeAll();
        }
        setTimeout(resizeAll, 200);
    } catch (e) {
        // ignore
    }
}

function normalizeToArray(value) {
    if (value === undefined || value === null) return [];
    return Array.isArray(value) ? value : [value];
}

function getPhotoDetailsTimeOfDayBucket(timeOnly) {
    // timeOnly expected like "HH:MM:SS".
    if (!timeOnly || typeof timeOnly !== 'string') return 'Unknown';
    const parts = timeOnly.split(':');
    if (parts.length < 1) return 'Unknown';
    const hour = parseInt(parts[0], 10);
    if (Number.isNaN(hour) || hour < 0 || hour > 23) return 'Unknown';

    if (hour <= 3) return 'Night';
    if (hour <= 11) return 'Morning';
    if (hour <= 18) return 'Afternoon';
    return 'Night';
}

function buildPhotoDetailsTemporalHistogram(photos, mode) {
    const safePhotos = Array.isArray(photos) ? photos : [];

    if (mode === 'time_of_day') {
        const ordered = ['Morning', 'Afternoon', 'Night', 'Unknown'];
        const counts = Object.fromEntries(ordered.map(k => [k, 0]));

        safePhotos.forEach(p => {
            const bucket = getPhotoDetailsTimeOfDayBucket(p && p.time_only);
            counts[bucket] = (counts[bucket] || 0) + 1;
        });

        const labels = ordered;
        return {
            title: 'Photo Details - Time of Day',
            xAxisLabel: 'Time Period',
            labels,
            data: labels.map(l => counts[l]),
            color: 'rgba(251, 146, 60, 0.8)'
        };
    }

    const orderedDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Unknown'];
    const counts = Object.fromEntries(orderedDays.map(k => [k, 0]));

    safePhotos.forEach(p => {
        const raw = p && p.day_of_week;
        const day = (raw && typeof raw === 'string' && raw.trim().length > 0) ? raw.trim() : 'Unknown';
        if (counts[day] === undefined) {
            counts.Unknown += 1;
        } else {
            counts[day] += 1;
        }
    });

    const labels = orderedDays;
    return {
        title: 'Photo Details - Day of Week',
        xAxisLabel: 'Day',
        labels,
        data: labels.map(l => counts[l]),
        color: 'rgba(59, 130, 246, 0.8)'
    };
}

function isFilterValueSelected(filterType, value) {
    const values = normalizeToArray(activeFilters[filterType]);
    return values.some(v => v === value);
}

function setMultiFilterValue(filterType, value) {
    // Toggle value in list; delete key if empty
    const values = normalizeToArray(activeFilters[filterType]);
    const exists = values.some(v => v === value);
    const next = exists ? values.filter(v => v !== value) : [...values, value];
    if (next.length === 0) {
        delete activeFilters[filterType];
    } else {
        activeFilters[filterType] = next;
    }
}

function isMultiSelectGesture(event) {
    // Windows/Linux: Ctrl+Click; macOS: Cmd+Click
    return !!(event && (event.ctrlKey || event.metaKey));
}

function normalizeToUniqueStringArray(values) {
    const arr = normalizeToArray(values).map(v => String(v));
    return Array.from(new Set(arr));
}

function applyLocalSelection(localKey, value, event) {
    // Plain click: select single value, or deselect if already selected.
    // Ctrl/Cmd+click: toggle in multi-selection.
    const cur = normalizeToUniqueStringArray(photoDetailsLocalFilters[localKey]);
    const v = String(value);
    const isSelected = cur.includes(v);

    if (isMultiSelectGesture(event)) {
        const next = isSelected ? cur.filter(x => x !== v) : [...cur, v];
        photoDetailsLocalFilters[localKey] = next;
        return;
    }

    if (isSelected) {
        // deselect
        photoDetailsLocalFilters[localKey] = cur.filter(x => x !== v);
        return;
    }

    photoDetailsLocalFilters[localKey] = [v];
}

function getActivePhotoDetailsLocalKey() {
    return photoDetailsTemporalMode === 'time_of_day' ? 'time_of_day' : 'day_of_week';
}

function applySelection(filterType, value, event) {
    // Default click: single-select (set to exactly one value).
    // Ctrl/Cmd+click: multi-select toggle (add/remove value).
    if (isMultiSelectGesture(event)) {
        setMultiFilterValue(filterType, value);
        return;
    }

    // Plain click:
    // - If value already selected: deselect it (remove from selection; clear filter if last).
    // - If value not selected: replace with single selection.
    const current = normalizeToArray(activeFilters[filterType]);
    const isSelected = current.some(v => v === value);

    if (isSelected) {
        const next = current.filter(v => v !== value);
        if (next.length === 0) {
            delete activeFilters[filterType];
        } else {
            activeFilters[filterType] = next;
        }
        return;
    }

    activeFilters[filterType] = [value];
}

function clearDownstreamFilters(changedFilterType) {
    // Keep hierarchy behavior exactly the same: any change to an upstream filter clears all downstream filters.
    if (changedFilterType === 'category') {
        delete activeFilters.group;
        delete activeFilters.camera;
        delete activeFilters.lens;
        delete activeFilters.lens_type;
        delete activeFilters.aperture;
        delete activeFilters.shutter_speed;
        delete activeFilters.iso;
        delete activeFilters.focal_length;
        delete activeFilters.time_of_day;
    } else if (changedFilterType === 'group') {
        delete activeFilters.camera;
        delete activeFilters.lens;
        delete activeFilters.lens_type;
        delete activeFilters.aperture;
        delete activeFilters.shutter_speed;
        delete activeFilters.iso;
        delete activeFilters.focal_length;
        delete activeFilters.time_of_day;
    } else if (changedFilterType === 'camera') {
        delete activeFilters.lens;
        delete activeFilters.lens_type;
        delete activeFilters.aperture;
        delete activeFilters.shutter_speed;
        delete activeFilters.iso;
        delete activeFilters.focal_length;
        delete activeFilters.time_of_day;
    } else if (changedFilterType === 'lens') {
        delete activeFilters.aperture;
        delete activeFilters.shutter_speed;
        delete activeFilters.iso;
        delete activeFilters.focal_length;
        delete activeFilters.time_of_day;
    }
}

function withoutFilter(filters, filterKey) {
    const next = { ...(filters || {}) };
    delete next[filterKey];
    return next;
}

function buildAnalyzeDatabaseRequestBody(filters, options = null) {
    const cleanFilters = filters || {};
    const body = Object.keys(cleanFilters).length > 0 ? { filters: cleanFilters } : {};
    if (options && typeof options.include_photos === 'boolean') {
        body.include_photos = options.include_photos;
    }
    return body;
}

async function fetchDatabaseAnalysis(filters, options = null) {
    const response = await fetch(`${API_BASE}/analyze/database`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildAnalyzeDatabaseRequestBody(filters, options))
    });

    const data = await response.json();
    if (!response.ok || !data.analysis) {
        throw new Error(data.error || 'Failed to fetch analysis');
    }
    return data.analysis;
}

async function fetchDatabaseFacetedAnalysis(filters, options = null, signal = null) {
    const response = await fetch(`${API_BASE}/analyze/database_faceted`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildAnalyzeDatabaseRequestBody(filters, options)),
        signal
    });

    const data = await response.json();
    if (!response.ok || !data.analysis) {
        throw new Error(data.error || 'Failed to fetch faceted analysis');
    }
    return {
        analysis: data.analysis,
        facets: data.facets || {}
    };
}

async function fetchFacetAnalyses(filters) {
    const facetKeys = [
        'category',
        'group',
        'camera',
        'lens',
        'aperture',
        'shutter_speed',
        'iso',
        'focal_length',
        'time_of_day'
    ];

    const results = await Promise.all(
        facetKeys.map(async (facetKey) => {
            try {
                const facetFilters = withoutFilter(filters, facetKey);
                const analysis = await fetchDatabaseAnalysis(facetFilters, { include_photos: false });
                return [facetKey, analysis];
            } catch (e) {
                console.warn(`Facet fetch failed for ${facetKey}:`, e);
                return [facetKey, null];
            }
        })
    );

    return Object.fromEntries(results);
}

function buildDefaultFacetAnalyses(analysis) {
    return {
        category: analysis,
        group: analysis,
        camera: analysis,
        lens: analysis,
        aperture: analysis,
        shutter_speed: analysis,
        iso: analysis,
        focal_length: analysis,
        time_of_day: analysis
    };
}

function renderCategoryHitRateChartIfVisible() {
    const sectionEl = document.getElementById('category-hitrate-content');
    if (!sectionEl || sectionEl.style.display === 'none') return;
    if (!currentAnalysisData || !currentAnalysisData.metadata || !currentAnalysisData.metadata.categories) return;

    const categoriesWithHitRate = Object.entries(currentAnalysisData.metadata.categories)
        .filter(([cat, data]) => data.hit_rate !== null && data.hit_rate !== undefined);
    if (categoriesWithHitRate.length === 0) return;

    const sortedCategoryHitRates = categoriesWithHitRate.sort((a, b) => b[1].hit_rate - a[1].hit_rate);
    const categoryHitRateMetadata = sortedCategoryHitRates.map(([cat, data]) => ({
        name: cat,
        type: 'Category',
        finalEdits: (data.hit_rate_photos !== undefined && data.hit_rate_photos !== null) ? data.hit_rate_photos : data.photos,
        totalPhotos: data.raw_photos
    }));

    const categoryColors = sortedCategoryHitRates.map(([cat]) => {
        const isSelected = normalizeToArray(activeFilters.category).includes(cat);
        return isSelected ? 'rgba(34, 197, 94, 0.8)' : 'rgba(34, 197, 94, 0.3)';
    });

    createHistogramChart(
        'chart-category-hitrate',
        sortedCategoryHitRates.map(c => c[0]),
        sortedCategoryHitRates.map(c => c[1].hit_rate),
        'Hit Rate by Category',
        'Category',
        activeFilters.category ? categoryColors : 'rgba(34, 197, 94, 0.8)',
        'category',
        sortedCategoryHitRates.map(c => c[0]),
        true,
        categoryHitRateMetadata
    );
}

function renderGroupHitRateChartIfVisible() {
    const sectionEl = document.getElementById('group-hitrate-content');
    if (!sectionEl || sectionEl.style.display === 'none') return;
    if (!currentAnalysisData || !currentAnalysisData.metadata || !currentAnalysisData.metadata.groups) return;

    let filteredGroups = Object.entries(currentAnalysisData.metadata.groups);
    const selectedCatsForGroupHitRateChart = normalizeToArray(activeFilters.category);
    if (selectedCatsForGroupHitRateChart.length > 0) {
        filteredGroups = filteredGroups.filter(([grp, data]) => selectedCatsForGroupHitRateChart.includes(data.category));
    }

    const groupsWithHitRate = filteredGroups.filter(([grp, data]) => data.hit_rate !== null && data.hit_rate !== undefined);
    if (groupsWithHitRate.length === 0) return;

    const sortedGroupHitRates = groupsWithHitRate.sort((a, b) => b[1].hit_rate - a[1].hit_rate);
    const groupHitRateMetadata = sortedGroupHitRates.map(([grp, data]) => ({
        name: grp,
        type: 'Group',
        finalEdits: (data.hit_rate_photos !== undefined && data.hit_rate_photos !== null) ? data.hit_rate_photos : data.photos,
        totalPhotos: data.raw_photos
    }));

    const groupColors = sortedGroupHitRates.map(([grp]) => {
        const isSelected = normalizeToArray(activeFilters.group).includes(grp);
        return isSelected ? 'rgba(34, 197, 94, 0.8)' : 'rgba(34, 197, 94, 0.3)';
    });

    createHistogramChart(
        'chart-group-hitrate',
        sortedGroupHitRates.map(g => g[0]),
        sortedGroupHitRates.map(g => g[1].hit_rate),
        'Hit Rate by Group',
        'Group',
        activeFilters.group ? groupColors : 'rgba(34, 197, 94, 0.8)',
        'group',
        sortedGroupHitRates.map(g => g[0]),
        true,
        groupHitRateMetadata
    );
}

function createHistogramChart(canvasId, labels, data, chartTitle, xAxisLabel, color, filterType, rawValues, isPercentage = false, hitRateMetadata = null, customClickHandler = null) {
    // Destroy existing chart if it exists
    const existingChart = chartInstances.find(c => c && c.canvas && c.canvas.id === canvasId);
    if (existingChart) {
        existingChart.destroy();
        chartInstances = chartInstances.filter(c => c && c.canvas && c.canvas.id !== canvasId);
    }
    
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.warn(`Canvas not found: ${canvasId}`);
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    // Calculate total for percentages
    const total = data.reduce((sum, val) => sum + val, 0);
    
    // Use consistent color for entire chart (unless color is an array for grouped data)
    const backgroundColor = Array.isArray(color) ? color : data.map(() => color);
    const borderColor = Array.isArray(color) 
        ? color.map(c => c.replace('0.8', '1'))
        : data.map(() => color.replace('0.8', '1'));
    
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Photos',
                data: data,
                backgroundColor: backgroundColor,
                borderColor: borderColor,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    bottom: 30  // Extra padding at bottom for rotated labels
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: chartTitle,
                    color: '#e5e7eb',
                    font: {
                        size: 14,
                        weight: 'bold'
                    },
                    padding: {
                        top: 10,
                        bottom: 15
                    }
                },
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.95)',
                    titleColor: '#e5e7eb',
                    bodyColor: '#e5e7eb',
                    borderColor: '#4b5563',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: false,
                    callbacks: {
                        title: function(context) {
                            // For hit rate charts, show the category/group name in title
                            if (hitRateMetadata && hitRateMetadata[context[0].dataIndex]) {
                                const itemName = hitRateMetadata[context[0].dataIndex].name;
                                const itemType = hitRateMetadata[context[0].dataIndex].type;
                                return `${itemType}: ${itemName}`;
                            }
                            return context[0].label;
                        },
                        label: function(context) {
                            const value = context.parsed.y;
                            if (isPercentage && hitRateMetadata && hitRateMetadata[context.dataIndex]) {
                                // For hit rate charts, show detailed breakdown
                                const meta = hitRateMetadata[context.dataIndex];
                                return [
                                    `Final Edits: ${meta.finalEdits}`,
                                    `Total Photos: ${meta.totalPhotos}`,
                                    `Hit Rate: ${value.toFixed(1)}%`
                                ];
                            } else if (isPercentage) {
                                // For hit rate charts without metadata
                                return `Hit Rate: ${value.toFixed(1)}%`;
                            } else {
                                // For count charts - value is already from filtered analysis
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
                                return `Photos: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: isPercentage ? 'Hit Rate (%)' : 'Freq',
                        color: '#9ca3af',
                        font: {
                            size: 12,
                            weight: 'bold'
                        }
                    },
                    grid: {
                        color: 'rgba(75, 85, 99, 0.2)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#9ca3af',
                        font: {
                            size: 11
                        }
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: xAxisLabel,
                        color: '#9ca3af',
                        font: {
                            size: 12,
                            weight: 'bold'
                        },
                        padding: {
                            top: 20  // Add space between x-axis labels and title
                        }
                    },
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#9ca3af',
                        font: {
                            size: 11
                        },
                        maxRotation: 45,
                        minRotation: 45
                    }
                }
            }
        }
    });
    
    // Add click handler to canvas for filtering (bars and x-axis labels)
    canvas.onclick = (event) => {
        // Skip filtering if no filterType specified (e.g., bucketed zoom ranges)
        if (!filterType && typeof customClickHandler !== 'function') {
            console.log('Filtering disabled for this chart');
            return;
        }
        
        // Try to find a clicked bar first
        const points = chart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, true);
        
        let clickedIndex = -1;
        
        if (points.length > 0) {
            // Clicked on a bar
            clickedIndex = points[0].index;
        } else {
            // Check if clicked on x-axis label area
            const rect = canvas.getBoundingClientRect();
            const x = event.clientX - rect.left;
            const y = event.clientY - rect.top;
            
            // Get chart area dimensions
            const chartArea = chart.chartArea;
            const xScale = chart.scales.x;
            
            // Check if click is in the x-axis label area (below the chart)
            if (y > chartArea.bottom && y < canvas.height) {
                // Find which label was clicked based on x position
                const labelPositions = xScale.ticks.map((tick, i) => ({
                    index: i,
                    x: xScale.getPixelForTick(i)
                }));
                
                // Find closest label
                let closestLabel = null;
                let minDistance = Infinity;
                
                labelPositions.forEach(pos => {
                    const distance = Math.abs(x - pos.x);
                    if (distance < minDistance && distance < 50) { // Within 50px
                        minDistance = distance;
                        closestLabel = pos;
                    }
                });
                
                if (closestLabel !== null) {
                    clickedIndex = closestLabel.index;
                    console.log('Clicked on x-axis label at index:', clickedIndex);
                }
            }
        }
        
        if (clickedIndex >= 0) {
            const clickedValue = rawValues[clickedIndex];

            // Custom click handler (e.g., local-only Photo Details filtering)
            if (typeof customClickHandler === 'function') {
                customClickHandler(clickedValue, event, {
                    index: clickedIndex,
                    label: labels[clickedIndex],
                    value: data[clickedIndex]
                });
                return;
            }

            // Check if this item is disabled (has 0 count)
            if (data[clickedIndex] === 0) {
                console.log('Cannot select disabled item');
                return;
            }
            
            console.log('Clicked on:', filterType, '=', clickedValue);
            console.log('Current filters before toggle:', {...activeFilters});

            // Single-select by default; multi-select only with Ctrl/Cmd+click
            applySelection(filterType, clickedValue, event);
            // Clear downstream filters based on hierarchy (same behavior as before)
            clearDownstreamFilters(filterType);
            
            console.log('Active filters after toggle:', {...activeFilters});
            
            // Re-render with filtered data
            applyFiltersAndRedraw();
        }
    };
    
    chartInstances.push(chart);
    return chart;
}

function buildPhotoDetailsSectionHtml(analysis) {
    // Photo Details Section - show actual photo data
    const safeAnalysis = analysis || {};
    const photos = Array.isArray(safeAnalysis.photos) ? safeAnalysis.photos : [];

    // Keep a reference to the currently-rendered Photo Details base rows for local-only charting.
    currentPhotoDetailsPhotos = photos;

    // Apply local-only filter from the Photo Details temporal chart to the table.
    const activeLocalKey = getActivePhotoDetailsLocalKey();
    const selectedLocalValues = normalizeToUniqueStringArray(photoDetailsLocalFilters[activeLocalKey]);
    const photoDetailsTablePhotos = selectedLocalValues.length === 0
        ? currentPhotoDetailsPhotos
        : currentPhotoDetailsPhotos.filter(p => {
            if (activeLocalKey === 'time_of_day') {
                return selectedLocalValues.includes(String(getPhotoDetailsTimeOfDayBucket(p && p.time_only)));
            }
            const day = (p && p.day_of_week && String(p.day_of_week).trim().length > 0) ? String(p.day_of_week).trim() : 'Unknown';
            return selectedLocalValues.includes(day);
        });

    currentPhotoDetailsVisiblePhotos = photoDetailsTablePhotos;

    let filterDescription = '';
    const activeFiltersList = [];
    if (activeFilters.camera) activeFiltersList.push(`Camera: ${normalizeToArray(activeFilters.camera).join(', ')}`);
    if (activeFilters.lens) activeFiltersList.push(`Lens: ${normalizeToArray(activeFilters.lens).join(', ')}`);
    if (activeFilters.aperture) activeFiltersList.push(`Aperture: f/${normalizeToArray(activeFilters.aperture).join(', f/')}`);
    if (activeFilters.shutter_speed) activeFiltersList.push(`Shutter: ${normalizeToArray(activeFilters.shutter_speed).join(', ')}s`);
    if (activeFilters.iso) activeFiltersList.push(`ISO: ${normalizeToArray(activeFilters.iso).join(', ')}`);
    if (activeFilters.focal_length) activeFiltersList.push(`Focal Length: ${normalizeToArray(activeFilters.focal_length).join(', ')}mm`);

    if (activeFiltersList.length > 0) {
        filterDescription = ` - Filtered (${activeFiltersList.join(', ')})`;
    }

    const localLabel = (photoDetailsTemporalMode === 'time_of_day') ? 'Time of Day' : 'Day of Week';
    const localDescription = selectedLocalValues.length > 0 ? ` - Local (${localLabel}: ${selectedLocalValues.join(', ')})` : '';

    const photoCount = photoDetailsTablePhotos ? photoDetailsTablePhotos.length : 0;

    let html = `<div class="result-card" id="photo-details-card">
        <h3>Photo Details (${photoCount.toLocaleString()} photos)${filterDescription}${localDescription}</h3>
        <div>`;

    if (photoDetailsTablePhotos && photoDetailsTablePhotos.length > 0) {
        html += `
            <div style="max-height: 400px; overflow-y: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">
                    <thead style="position: sticky; top: 0; background: var(--surface); z-index: 1;">
                        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                            <th style="padding: 8px; text-align: left;">Date</th>
                            <th style="padding: 8px; text-align: left;">Day</th>
                            <th style="padding: 8px; text-align: left;">Time</th>
                            <th style="padding: 8px; text-align: left;">Time of Day</th>
                            <th style="padding: 8px; text-align: left;">Category</th>
                            <th style="padding: 8px; text-align: left;">Group</th>
                            <th style="padding: 8px; text-align: left;">Session</th>
                            <th style="padding: 8px; text-align: left;">Camera</th>
                            <th style="padding: 8px; text-align: left;">Lens</th>
                            <th style="padding: 8px; text-align: center;">Aperture</th>
                            <th style="padding: 8px; text-align: center;">SS</th>
                            <th style="padding: 8px; text-align: center;">ISO</th>
                            <th style="padding: 8px; text-align: center;">Focal Length</th>
                            <th style="padding: 8px; text-align: left;">Filename</th>
                            <th style="padding: 8px; text-align: left;">Path</th>
                        </tr>
                    </thead>
                    <tbody>`;

        photoDetailsTablePhotos.forEach((photo, index) => {
            const rowStyle = index % 2 === 0 ? 'background: rgba(255, 255, 255, 0.02);' : '';
            html += `
                        <tr style="${rowStyle}">
                            <td style="padding: 8px;">${escapeHtml(photo.date_only || 'N/A')}</td>
                            <td style="padding: 8px;">${escapeHtml(photo.day_of_week || 'N/A')}</td>
                            <td style="padding: 8px;">${escapeHtml(photo.time_only || 'N/A')}</td>
                            <td style="padding: 8px;">${escapeHtml(getPhotoDetailsTimeOfDayBucket(photo.time_only) || 'Unknown')}</td>
                            <td style="padding: 8px;">${escapeHtml(photo.category || 'Uncategorized')}</td>
                            <td style="padding: 8px;">${escapeHtml(photo.group || 'Ungrouped')}</td>
                            <td style="padding: 8px;">${escapeHtml(photo.session_name || 'N/A')}</td>
                            <td style="padding: 8px;">${escapeHtml(photo.camera || 'Unknown')}</td>
                            <td style="padding: 8px;">${escapeHtml(photo.lens || 'Unknown')}</td>
                            <td style="padding: 8px; text-align: center;">${photo.aperture ? 'f/' + photo.aperture : 'N/A'}</td>
                            <td style="padding: 8px; text-align: center;">${photo.shutter_speed || 'N/A'}</td>
                            <td style="padding: 8px; text-align: center;">${photo.iso || 'N/A'}</td>
                            <td style="padding: 8px; text-align: center;">${photo.focal_length ? photo.focal_length + 'mm' : 'N/A'}</td>
                            <td style="padding: 8px;">${escapeHtml(photo.filename || 'N/A')}</td>
                            <td style="padding: 8px; font-size: 0.85em; color: #9ca3af;">${escapeHtml(photo.file_path || 'N/A')}</td>
                        </tr>`;
        });

        html += `
                    </tbody>
                </table>
            </div>

            <div style="margin-top: 15px;">
                <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 10px;">
                    <span style="color: #9ca3af; font-size: 0.9em;">Photo Details Chart:</span>
                    <button id="btn-photo-temporal-dow" onclick="togglePhotoDetailsTemporalMode('day_of_week')" style="padding: 6px 12px; border: none; border-radius: 6px; cursor: pointer; background: rgba(59, 130, 246, 0.8); color: white;">Day of Week</button>
                    <button id="btn-photo-temporal-tod" onclick="togglePhotoDetailsTemporalMode('time_of_day')" style="padding: 6px 12px; border: none; border-radius: 6px; cursor: pointer; background: rgba(75, 85, 99, 0.5); color: #9ca3af;">Time of Day</button>
                </div>
                <div style="position: relative; height: 500px;">
                    <canvas id="chart-photo-details-temporal"></canvas>
                </div>
            </div>`;
    } else {
        html += `<p style="padding: 10px; color: #9ca3af;">No photos match the current filters.</p>`;
    }

    html += `
        </div>
    </div>`;

    return html;
}

window.rerenderPhotoDetailsSection = function() {
    const analysis = currentFilteredAnalysisData || currentAnalysisData;
    const card = document.getElementById('photo-details-card');
    if (!analysis || !card) return;

    card.outerHTML = buildPhotoDetailsSectionHtml(analysis);

    try {
        updatePhotoDetailsTemporalToggleButtons();
        renderPhotoDetailsTemporalChart();
    } catch (e) {
        console.warn('Photo Details rerender failed:', e);
    }
}

function updatePhotoDetailsTemporalToggleButtons() {
    const dowBtn = document.getElementById('btn-photo-temporal-dow');
    const todBtn = document.getElementById('btn-photo-temporal-tod');

    // Reset
    if (dowBtn) {
        dowBtn.style.background = 'rgba(75, 85, 99, 0.5)';
        dowBtn.style.color = '#9ca3af';
    }
    if (todBtn) {
        todBtn.style.background = 'rgba(75, 85, 99, 0.5)';
        todBtn.style.color = '#9ca3af';
    }

    // Activate
    if (photoDetailsTemporalMode === 'day_of_week') {
        if (dowBtn) {
            dowBtn.style.background = 'rgba(59, 130, 246, 0.8)';
            dowBtn.style.color = 'white';
        }
    } else {
        if (todBtn) {
            todBtn.style.background = 'rgba(251, 146, 60, 0.8)';
            todBtn.style.color = 'white';
        }
    }
}

function renderPhotoDetailsTemporalChart() {
    // Keep chart distribution stable (like other charts): render from the full Photo Details base rows.
    // Local selection dims bars and filters the table, but does not change the chart's underlying counts.
    const sourcePhotos = Array.isArray(currentPhotoDetailsPhotos) ? currentPhotoDetailsPhotos : [];

    // Allow rendering even when empty; Chart.js will show an empty plot.
    const spec = buildPhotoDetailsTemporalHistogram(sourcePhotos, photoDetailsTemporalMode);
    const localKey = getActivePhotoDetailsLocalKey();
    const selected = normalizeToUniqueStringArray(photoDetailsLocalFilters[localKey]);
    const selectedColor = photoDetailsTemporalMode === 'time_of_day' ? 'rgba(251, 146, 60, 0.8)' : 'rgba(59, 130, 246, 0.8)';
    const dimColor = photoDetailsTemporalMode === 'time_of_day' ? 'rgba(251, 146, 60, 0.3)' : 'rgba(59, 130, 246, 0.3)';
    const colors = spec.labels.map(l => {
        if (selected.length === 0) return selectedColor;
        return selected.includes(String(l)) ? selectedColor : dimColor;
    });

    createHistogramChart(
        'chart-photo-details-temporal',
        spec.labels,
        spec.data,
        spec.title,
        spec.xAxisLabel,
        colors,
        null,
        spec.labels,
        false,
        null,
        (clickedValue, event) => {
            const activeKey = getActivePhotoDetailsLocalKey();
            applyLocalSelection(activeKey, clickedValue, event);
            if (typeof window.rerenderPhotoDetailsSection === 'function') {
                window.rerenderPhotoDetailsSection();
            }
        }
    );
}

// Apply active filters and redraw all charts
async function applyFiltersAndRedraw() {
    if (!currentAnalysisData) return;
    
    // If no filters, just redraw with original data
    if (Object.keys(activeFilters).length === 0) {
        displayActiveFilters(); // Clear filter badges
        currentFilteredAnalysisData = currentAnalysisData;
        currentFacetAnalyses = buildDefaultFacetAnalyses(currentAnalysisData);
        displayAnalysisResults(currentAnalysisData, currentFacetAnalyses);
        return;
    }
    
    // Show active filters to user
    displayActiveFilters();
    
    // Fetch filtered data from backend + per-pane facet analyses (faceted counts)
    try {
        const requestId = ++analysisRequestSeq;
        const filtersSnapshot = { ...activeFilters };

        // Cancel any in-flight analysis call
        if (analysisAbortController) {
            analysisAbortController.abort();
        }
        analysisAbortController = new AbortController();

        console.log('Filter request sent:', { filters: filtersSnapshot });

        const { analysis: filteredAnalysis, facets: facetAnalyses } = await fetchDatabaseFacetedAnalysis(
            filtersSnapshot,
            { include_photos: true },
            analysisAbortController.signal
        );

        // Ignore out-of-order responses
        if (requestId !== analysisRequestSeq) {
            return;
        }

        currentFilteredAnalysisData = filteredAnalysis;
        currentFacetAnalyses = facetAnalyses;
        displayAnalysisResults(filteredAnalysis, facetAnalyses);
    } catch (error) {
        if (error && error.name === 'AbortError') {
            return;
        }
        console.error('Error applying filters:', error);
        showError('analyze-results', `Error: ${error.message}`);
    }
}

// Display active filters as badges
function displayActiveFilters() {
    const resultsArea = document.getElementById('analyze-results');
    let filterBadges = '';
    
    if (Object.keys(activeFilters).length > 0) {
        filterBadges = '<div style="margin-bottom: 15px; padding: 10px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border-left: 3px solid rgba(59, 130, 246, 0.8);">';
        filterBadges += '<strong style="color: #e5e7eb;">Active Filters:</strong> ';
        
        const filterLabels = {
            'camera': 'Camera',
            'lens': 'Lens',
            'aperture': 'Aperture',
            'shutter_speed': 'Shutter Speed',
            'iso': 'ISO',
            'focal_length': 'Focal Length',
            'time_of_day': 'Time of Day',
            'category': 'Category',
            'group': 'Group'
        };
        
        const badges = Object.entries(activeFilters).flatMap(([type, value]) => {
            const label = filterLabels[type] || type;
            const values = normalizeToArray(value);
            return values.map(v => {
                const escaped = String(v).replace(/'/g, "\\'");
                return `<span style="display: inline-block; margin: 5px; padding: 5px 10px; background: rgba(59, 130, 246, 0.8); color: white; border-radius: 15px; font-size: 0.9em;">
                    ${label}: ${v} 
                    <button onclick="removeFilter('${type}', '${escaped}')" style="background: none; border: none; color: white; cursor: pointer; font-weight: bold; margin-left: 5px;">×</button>
                </span>`;
            });
        }).join('');
        
        filterBadges += badges;
        filterBadges += '<button onclick="clearAllFilters()" style="margin-left: 10px; padding: 5px 10px; background: rgba(239, 68, 68, 0.8); color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 0.9em;">Clear All</button>';
        filterBadges += '</div>';
        
        // Insert filter badges at the top of results
        const existingBadges = resultsArea.querySelector('.filter-badges');
        if (existingBadges) {
            existingBadges.remove();
        }
        resultsArea.insertAdjacentHTML('afterbegin', `<div class="filter-badges">${filterBadges}</div>`);
    } else {
        const existingBadges = resultsArea.querySelector('.filter-badges');
        if (existingBadges) {
            existingBadges.remove();
        }
    }
}

// Remove a specific filter
window.removeFilter = function(filterType, value = null) {
    if (value === null || value === undefined) {
        delete activeFilters[filterType];
    } else {
        // Remove a single value from a multi-select filter.
        const values = normalizeToArray(activeFilters[filterType]);
        const next = values.filter(v => String(v) !== String(value));
        if (next.length === 0) {
            delete activeFilters[filterType];
        } else {
            activeFilters[filterType] = next;
        }
    }

    // Maintain the same hierarchy behavior: upstream changes clear downstream.
    clearDownstreamFilters(filterType);
    applyFiltersAndRedraw();
}

// Clear all filters
window.clearAllFilters = function() {
    activeFilters = {};
    activeLensType = 'all';
    
    // Reset lens type buttons if they exist
    const allBtn = document.getElementById('btn-all');
    const primeBtn = document.getElementById('btn-prime');
    const zoomBtn = document.getElementById('btn-zoom');
    
    if (allBtn) {
        allBtn.style.background = 'rgba(59, 130, 246, 0.8)';
        allBtn.style.color = 'white';
    }
    if (primeBtn) {
        primeBtn.style.background = 'rgba(75, 85, 99, 0.5)';
        primeBtn.style.color = '#9ca3af';
    }
    if (zoomBtn) {
        zoomBtn.style.background = 'rgba(75, 85, 99, 0.5)';
        zoomBtn.style.color = '#9ca3af';
    }
    
    applyFiltersAndRedraw();
}

// Toggle section visibility (for collapsible sections)
window.toggleSection = function(sectionId) {
    const content = document.getElementById(sectionId);
    const arrowId = sectionId.replace('-content', '-arrow');
    const arrow = document.getElementById(arrowId);
    
    if (content) {
        if (content.style.display === 'none') {
            content.style.display = 'block';
            if (arrow) arrow.style.transform = 'rotate(180deg)';
            expandedSections[sectionId] = true;

            // Lazy-render hit-rate charts on expand (they size wrong when created hidden).
            if (sectionId === 'category-hitrate-content') {
                renderCategoryHitRateChartIfVisible();
            } else if (sectionId === 'group-hitrate-content') {
                renderGroupHitRateChartIfVisible();
            }

            // If charts were created while this section was collapsed, reflow them now.
            requestChartResize();
        } else {
            content.style.display = 'none';
            if (arrow) arrow.style.transform = 'rotate(0deg)';
            expandedSections[sectionId] = false;
        }
    }
}

// Toggle lens type filter
window.toggleLensType = function(type) {
    console.log('toggleLensType called with:', type);
    console.log('activeFilters before:', {...activeFilters});
    
    activeLensType = type;
    
    // Update button styles
    const allBtn = document.getElementById('btn-all');
    const primeBtn = document.getElementById('btn-prime');
    const zoomBtn = document.getElementById('btn-zoom');
    
    console.log('Buttons found:', { allBtn: !!allBtn, primeBtn: !!primeBtn, zoomBtn: !!zoomBtn });
    
    // Reset all buttons to inactive state
    if (allBtn) {
        allBtn.style.background = 'rgba(75, 85, 99, 0.5)';
        allBtn.style.color = '#9ca3af';
    }
    if (primeBtn) {
        primeBtn.style.background = 'rgba(75, 85, 99, 0.5)';
        primeBtn.style.color = '#9ca3af';
    }
    if (zoomBtn) {
        zoomBtn.style.background = 'rgba(75, 85, 99, 0.5)';
        zoomBtn.style.color = '#9ca3af';
    }
    
    // Highlight active button and set filter
    if (type === 'all') {
        if (allBtn) {
            allBtn.style.background = 'rgba(59, 130, 246, 0.8)';
            allBtn.style.color = 'white';
        }
        // Remove lens_type filter
        delete activeFilters.lens_type;
    } else if (type === 'prime') {
        if (primeBtn) {
            primeBtn.style.background = 'rgba(236, 72, 153, 0.8)';
            primeBtn.style.color = 'white';
        }
        // Add lens_type filter
        activeFilters.lens_type = 'prime';
    } else if (type === 'zoom') {
        if (zoomBtn) {
            zoomBtn.style.background = 'rgba(139, 92, 246, 0.8)';
            zoomBtn.style.color = 'white';
        }
        // Add lens_type filter
        activeFilters.lens_type = 'zoom';
    }
    
    console.log('activeFilters after:', {...activeFilters});
    
    applyFiltersAndRedraw();
}

// Toggle Photo Details temporal chart mode (derived only from Photo Details table rows)
window.togglePhotoDetailsTemporalMode = function(mode) {
    photoDetailsTemporalMode = mode === 'time_of_day' ? 'time_of_day' : 'day_of_week';

    // Switching mode changes which local filter applies to the table, so rerender the section.
    if (typeof window.rerenderPhotoDetailsSection === 'function') {
        window.rerenderPhotoDetailsSection();
        return;
    }

    // Fallback (shouldn't happen): just update buttons + chart.
    updatePhotoDetailsTemporalToggleButtons();
    renderPhotoDetailsTemporalChart();
}

function displayAnalysisResults(analysis, facets = null) {
    const resultsArea = document.getElementById('analyze-results');
    resultsArea.classList.add('visible');
    
    // Store analysis data for filtering (only if not already stored)
    if (!currentAnalysisData) {
        currentAnalysisData = analysis;
    }

    const facetAnalyses = facets || currentFacetAnalyses || buildDefaultFacetAnalyses(analysis);
    
    // Display active filters if any
    displayActiveFilters();

    // Debug logging
    console.log('displayAnalysisResults called with:', analysis);
    console.log('analysis.scope:', analysis.scope);
    console.log('analysis.total_photos:', analysis.total_photos);
    console.log('analysis.lens_freq:', analysis.lens_freq);
    console.log('analysis.camera_freq:', analysis.camera_freq);
    console.log('Has filters?', Object.keys(activeFilters).length > 0);

    const formatSelectionLabel = (value, pluralLabel) => {
        const values = normalizeToArray(value);
        if (values.length === 0) return null;
        if (values.length === 1) return String(values[0]);
        return `Multiple ${pluralLabel}`;
    };

    // Determine the title based on query parameters
    let mainTitle = 'Analysis Complete';
    const categoryLabel = formatSelectionLabel(analysis.query_category, 'Categories');
    const groupLabel = formatSelectionLabel(analysis.query_group, 'Groups');
    if (categoryLabel && !groupLabel) {
        mainTitle = `${categoryLabel} - All Groups`;
    } else if (groupLabel && !categoryLabel) {
        mainTitle = groupLabel;
    } else if (categoryLabel && groupLabel) {
        mainTitle = `${categoryLabel} - ${groupLabel}`;
    } else if (!categoryLabel && !groupLabel) {
        mainTitle = 'All Data';
    }

    // Remove old scope-specific handling - treat all analysis the same way
    let html = `
        <h2 style="margin-bottom: 20px;">${mainTitle}</h2>
    `;
    
    // Add clear filters button if filters are active
    if (Object.keys(activeFilters).length > 0) {
        html += `
            <div style="margin-bottom: 15px;">
                <button onclick="clearAllFilters()" style="padding: 10px 20px; background: rgba(239, 68, 68, 0.8); color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 1em; font-weight: bold;">
                    Reset Filters
                </button>
            </div>
        `;
    }
    
    html += `
        <div class="result-card">
            <h3>Overview${categoryLabel ? ' - ' + categoryLabel : ''}</h3>
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
    
    // Show categories breakdown (faceted): baseline options, counts from category facet (all filters except category)
    if (currentAnalysisData && currentAnalysisData.metadata && currentAnalysisData.metadata.categories) {
        const categoryFacet = facetAnalyses.category || analysis;
        const categoryFacetCategories = (categoryFacet.metadata && categoryFacet.metadata.categories) ? categoryFacet.metadata.categories : {};
        html += '<div class="result-card"><h3>Categories</h3>';
        html += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; max-height: 225px; overflow-y: auto;">';
        const sortedCats = Object.entries(currentAnalysisData.metadata.categories)
            .sort((a, b) => b[1].photos - a[1].photos);
        
        // Determine which category to highlight
        const selectedCategories = normalizeToArray(activeFilters.category);
        let highlightCategory = selectedCategories.length > 0 ? selectedCategories[0] : null;

        // If a group is selected but no category, highlight the group's parent category
        const groupToCategory = (currentAnalysisData.metadata && currentAnalysisData.metadata.group_to_category)
            ? currentAnalysisData.metadata.group_to_category
            : ((analysis.metadata && analysis.metadata.group_to_category) ? analysis.metadata.group_to_category : null);
        const selectedGroupsForHighlight = normalizeToArray(activeFilters.group);
        if (!highlightCategory && selectedGroupsForHighlight.length > 0 && groupToCategory) {
            highlightCategory = groupToCategory[selectedGroupsForHighlight[0]];
        }
        
        sortedCats.forEach(([cat, baseData]) => {
            const isActive = selectedCategories.includes(cat) || highlightCategory === cat;
            const activeStyle = isActive ? 'border: 2px solid rgba(59, 130, 246, 0.9); background-color: rgba(59, 130, 246, 0.15);' : 'border: 2px solid transparent;';
            const facetData = categoryFacetCategories[cat];
            const displaySessions = facetData ? facetData.sessions : 0;
            const displayPhotos = facetData ? facetData.photos : 0;
            const dimStyle = displayPhotos === 0 ? 'opacity: 0.3; cursor: not-allowed;' : '';
            html += `<p class="clickable-category" data-category="${escapeHtml(cat)}" style="margin: 0; cursor: pointer; padding: 5px; border-radius: 8px; transition: all 0.2s; ${activeStyle} ${dimStyle}"><strong>${escapeHtml(cat)}:</strong> ${displaySessions} sessions, ${displayPhotos.toLocaleString()} photos</p>`;
        });
        html += '</div></div>';
    }
    
    // Hit Rate by Category - always use currentAnalysisData for full metadata
    if (currentAnalysisData && currentAnalysisData.metadata && currentAnalysisData.metadata.categories) {
        const categoriesWithHitRate = Object.entries(currentAnalysisData.metadata.categories)
            .filter(([cat, data]) => data.hit_rate !== null && data.hit_rate !== undefined);
        
        if (categoriesWithHitRate.length > 0) {
            const chartId = 'chart-category-hitrate';
            const sectionId = 'category-hitrate-content';
            const isExpanded = expandedSections[sectionId] || false;
            const displayStyle = isExpanded ? 'block' : 'none';
            const arrowRotation = isExpanded ? 'rotate(180deg)' : 'rotate(0deg)';
            html += `<div class="result-card">
                <h3 style="cursor: pointer; user-select: none; display: flex; align-items: center; gap: 10px;" onclick="toggleSection('${sectionId}')">
                    <span id="category-hitrate-arrow" style="transition: transform 0.3s; transform: ${arrowRotation};">▼</span>
                    Hit Rate by Category
                </h3>
                <div id="${sectionId}" style="display: ${displayStyle};">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;">
                        <div style="max-height: 400px; overflow-y: auto;">`;
            const sortedCategoryHitRates = categoriesWithHitRate.sort((a, b) => b[1].hit_rate - a[1].hit_rate);
            
            sortedCategoryHitRates.forEach(([cat, data]) => {
                const numerator = (data.hit_rate_photos !== undefined && data.hit_rate_photos !== null) ? data.hit_rate_photos : data.photos;
                html += `<p><strong>${escapeHtml(cat)}:</strong> ${data.hit_rate.toFixed(1)}% (${numerator} / ${data.raw_photos})</p>`;
            });
            html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div></div>`;
        }
    }
    
    // Show groups breakdown (faceted): baseline options, counts from group facet (all filters except group)
    if (currentAnalysisData && currentAnalysisData.metadata && currentAnalysisData.metadata.groups) {
        const groupFacet = facetAnalyses.group || analysis;
        const groupFacetGroups = (groupFacet.metadata && groupFacet.metadata.groups) ? groupFacet.metadata.groups : {};
        html += '<div class="result-card"><h3>Groups</h3>';
        html += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 10px; max-height: 225px; overflow-y: auto;">';
        
        // Filter groups by selected category
        let filteredGroups = Object.entries(currentAnalysisData.metadata.groups);
        const selectedCatsForGroups = normalizeToArray(activeFilters.category);
        if (selectedCatsForGroups.length > 0) {
            filteredGroups = filteredGroups.filter(([grp, data]) => selectedCatsForGroups.includes(data.category));
        }
        
        const sortedGroups = filteredGroups.sort((a, b) => b[1].photos - a[1].photos);
        const selectedGroups = normalizeToArray(activeFilters.group);
        sortedGroups.forEach(([grp, baseData]) => {
            const isActive = selectedGroups.includes(grp);
            const activeStyle = isActive ? 'border: 2px solid rgba(59, 130, 246, 0.9); background-color: rgba(59, 130, 246, 0.15);' : 'border: 2px solid transparent;';
            const facetData = groupFacetGroups[grp];
            const displaySessions = facetData ? facetData.sessions : 0;
            const displayPhotos = facetData ? facetData.photos : 0;
            const dimStyle = displayPhotos === 0 ? 'opacity: 0.3; cursor: not-allowed;' : '';
            html += `<p class="clickable-group" data-group="${escapeHtml(grp)}" style="margin: 0; cursor: pointer; padding: 5px; border-radius: 8px; transition: all 0.2s; ${activeStyle} ${dimStyle}"><strong>${escapeHtml(grp)}:</strong> ${displaySessions} sessions, ${displayPhotos.toLocaleString()} photos</p>`;
        });
        html += '</div></div>';
    }
    
    // Hit Rate by Group - always use currentAnalysisData for full metadata
    if (currentAnalysisData && currentAnalysisData.metadata && currentAnalysisData.metadata.groups) {
        // Filter groups by selected category if one is active
        let filteredGroups = Object.entries(currentAnalysisData.metadata.groups);
        const selectedCatsForGroupHitRate = normalizeToArray(activeFilters.category);
        if (selectedCatsForGroupHitRate.length > 0) {
            filteredGroups = filteredGroups.filter(([grp, data]) => selectedCatsForGroupHitRate.includes(data.category));
        }
        
        const groupsWithHitRate = filteredGroups.filter(([grp, data]) => data.hit_rate !== null && data.hit_rate !== undefined);
        
        if (groupsWithHitRate.length > 0) {
            const chartId = 'chart-group-hitrate';
            const sectionId = 'group-hitrate-content';
            const isExpanded = expandedSections[sectionId] || false;
            const displayStyle = isExpanded ? 'block' : 'none';
            const arrowRotation = isExpanded ? 'rotate(180deg)' : 'rotate(0deg)';
            html += `<div class="result-card">
                <h3 style="cursor: pointer; user-select: none; display: flex; align-items: center; gap: 10px;" onclick="toggleSection('${sectionId}')">
                    <span id="group-hitrate-arrow" style="transition: transform 0.3s; transform: ${arrowRotation};">▼</span>
                    Hit Rate by Group${normalizeToArray(activeFilters.category).length > 0 ? ' - Multiple Categories' : ''}
                </h3>
                <div id="${sectionId}" style="display: ${displayStyle};">
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;">
                        <div style="max-height: 400px; overflow-y: auto;">`;
            const sortedGroupHitRates = groupsWithHitRate.sort((a, b) => b[1].hit_rate - a[1].hit_rate);
            
            sortedGroupHitRates.forEach(([grp, data]) => {
                const numerator = (data.hit_rate_photos !== undefined && data.hit_rate_photos !== null) ? data.hit_rate_photos : data.photos;
                html += `<p><strong>${escapeHtml(grp)}:</strong> ${data.hit_rate.toFixed(1)}% (${numerator} / ${data.raw_photos})</p>`;
            });
            html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div></div>`;
        }
    }

    // Photo Details Section - show actual photo data
    if (analysis.photos !== undefined) {
        html += buildPhotoDetailsSectionHtml(analysis);
    }

    // Camera Bodies - show all from baseline, counts from camera facet (all filters except camera)
    if (currentAnalysisData && currentAnalysisData.camera_freq && Object.keys(currentAnalysisData.camera_freq).length > 0) {
        const cameraFacet = facetAnalyses.camera || analysis;
        const cameraFacetFreq = cameraFacet.camera_freq || {};
        const cameraFacetTotal = cameraFacet.total_photos || 0;
        const chartId = 'chart-cameras';
        html += `<div class="result-card"><h3>Camera Bodies</h3><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;"><div style="max-height: 400px; overflow-y: auto;">`;
        const cameras = Object.entries(currentAnalysisData.camera_freq)
            .sort((a, b) => b[1] - a[1]);
        
        // Check if camera is the deepest filter
        const hasDownstreamFilters = activeFilters.lens || activeFilters.aperture || 
                                     activeFilters.shutter_speed || activeFilters.iso || 
                                     activeFilters.focal_length;
        
        cameras.forEach(([camera, count]) => {
            const isActive = normalizeToArray(activeFilters.camera).includes(camera);
            // Faceted counts: all active filters EXCEPT camera
            const displayCount = cameraFacetFreq[camera] || 0;
            const percentage = displayCount > 0 && cameraFacetTotal > 0 ? ((displayCount / cameraFacetTotal) * 100).toFixed(1) : '0.0';
            
            const activeStyle = isActive ? 'border: 2px solid rgba(59, 130, 246, 0.9); background-color: rgba(59, 130, 246, 0.15);' : 'border: 2px solid transparent;';
            const dimStyle = displayCount === 0 ? 'opacity: 0.3; cursor: not-allowed;' : '';
            html += `<p class="clickable-camera" data-camera="${escapeHtml(camera)}" style="margin: 0; cursor: pointer; padding: 5px; border-radius: 8px; transition: all 0.2s; ${activeStyle} ${dimStyle}"><strong>${camera}:</strong> ${displayCount} photos (${percentage}%)</p>`;
        });
        html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div>`;
    }

    // All lenses - show all from baseline, counts from lens facet (all filters except lens)
    if (currentAnalysisData && currentAnalysisData.lens_freq && Object.keys(currentAnalysisData.lens_freq).length > 0) {
        const lensFacet = facetAnalyses.lens || analysis;
        const lensFacetFreq = lensFacet.lens_freq || {};
        const lensFacetTotal = lensFacet.total_photos || 0;
        const chartId = 'chart-lenses';
        html += `<div class="result-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0;">All Lenses</h3>
                <div style="display: flex; gap: 5px; background: rgba(55, 65, 81, 0.5); border-radius: 5px; padding: 3px;">
                    <button id="btn-all" onclick="toggleLensType('all')" style="padding: 8px 16px; background: rgba(59, 130, 246, 0.8); color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 0.9em; font-weight: bold;">All</button>
                    <button id="btn-prime" onclick="toggleLensType('prime')" style="padding: 8px 16px; background: rgba(75, 85, 99, 0.5); color: #9ca3af; border: none; border-radius: 3px; cursor: pointer; font-size: 0.9em; font-weight: bold;">Prime</button>
                    <button id="btn-zoom" onclick="toggleLensType('zoom')" style="padding: 8px 16px; background: rgba(75, 85, 99, 0.5); color: #9ca3af; border: none; border-radius: 3px; cursor: pointer; font-size: 0.9em; font-weight: bold;">Zoom</button>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;"><div style="max-height: 400px; overflow-y: auto;">`;
        const lenses = Object.entries(currentAnalysisData.lens_freq)
            .sort((a, b) => a[0].localeCompare(b[0])); // Alphabetical order
        
        // Check if lens is the deepest filter
        const hasDownstreamFilters = activeFilters.aperture || activeFilters.shutter_speed || 
                                     activeFilters.iso || activeFilters.focal_length;
        
        lenses.forEach(([lens, count]) => {
            const isActive = normalizeToArray(activeFilters.lens).includes(lens);
            // Faceted counts: all active filters EXCEPT lens
            const displayCount = lensFacetFreq[lens] || 0;
            const percentage = displayCount > 0 && lensFacetTotal > 0 ? ((displayCount / lensFacetTotal) * 100).toFixed(1) : '0.0';
            
            const activeStyle = isActive ? 'border: 2px solid rgba(59, 130, 246, 0.9); background-color: rgba(59, 130, 246, 0.15);' : 'border: 2px solid transparent;';
            const dimStyle = displayCount === 0 ? 'opacity: 0.3; cursor: not-allowed;' : '';
            html += `<p class="clickable-lens" data-lens="${escapeHtml(lens)}" style="margin: 0; cursor: pointer; padding: 5px; border-radius: 8px; transition: all 0.2s; ${activeStyle} ${dimStyle}"><strong>${lens}:</strong> ${displayCount} photos (${percentage}%)</p>`;
        });
        html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div>`;
    }

    // Aperture Stats - show all from baseline, counts from aperture facet (all filters except aperture)
    if (currentAnalysisData && currentAnalysisData.aperture_freq && Object.keys(currentAnalysisData.aperture_freq).length > 0) {
        const apertureFacet = facetAnalyses.aperture || analysis;
        const apertureFacetFreq = apertureFacet.aperture_freq || {};
        const apertureFacetTotal = apertureFacet.total_photos || 0;
        const chartId = 'chart-apertures';
        html += `<div class="result-card"><h3>Aperture Settings</h3><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;"><div style="max-height: 400px; overflow-y: auto;">`;
        const apertures = Object.entries(currentAnalysisData.aperture_freq)
            .sort((a, b) => {
                const aNum = parseFloat(a[0]);
                const bNum = parseFloat(b[0]);
                return aNum - bNum; // Ascending order (smallest to largest)
            });
        
        apertures.forEach(([aperture, count]) => {
            const isActive = normalizeToArray(activeFilters.aperture).includes(aperture);
            const displayCount = apertureFacetFreq[aperture] || 0;
            const isAvailable = displayCount > 0;
            const percentage = isAvailable && apertureFacetTotal > 0 ? ((displayCount / apertureFacetTotal) * 100).toFixed(1) : '0.0';
            const activeStyle = isActive ? 'border: 2px solid rgba(59, 130, 246, 0.9); background-color: rgba(59, 130, 246, 0.15);' : 'border: 2px solid transparent;';
            const dimStyle = !isAvailable ? 'opacity: 0.3; cursor: not-allowed;' : '';
            html += `<p class="clickable-aperture" data-aperture="${escapeHtml(aperture)}" style="margin: 0; cursor: pointer; padding: 5px; border-radius: 8px; transition: all 0.2s; ${activeStyle} ${dimStyle}"><strong>f/${aperture}:</strong> ${displayCount} photos (${percentage}%)</p>`;
        });
        html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div>`;
    }

    // Shutter Speed Stats - show all from baseline, counts from shutter facet (all filters except shutter_speed)
    if (currentAnalysisData && currentAnalysisData.shutter_speed_freq && Object.keys(currentAnalysisData.shutter_speed_freq).length > 0) {
        const shutterFacet = facetAnalyses.shutter_speed || analysis;
        const shutterFacetFreq = shutterFacet.shutter_speed_freq || {};
        const shutterFacetTotal = shutterFacet.total_photos || 0;
        const chartId = 'chart-shutters';
        html += `<div class="result-card"><h3>Shutter Speeds</h3><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;"><div style="max-height: 400px; overflow-y: auto;">`;
        const parseShutterSpeed = (speed) => {
            if (speed.includes('/')) {
                const [num, denom] = speed.split('/').map(Number);
                return num / denom;
            }
            return parseFloat(speed);
        };
        const shutters = Object.entries(currentAnalysisData.shutter_speed_freq)
            .sort((a, b) => parseShutterSpeed(a[0]) - parseShutterSpeed(b[0])); // Ascending order
        
        shutters.forEach(([shutter, count]) => {
            const isActive = normalizeToArray(activeFilters.shutter_speed).includes(shutter);
            const displayCount = shutterFacetFreq[shutter] || 0;
            const isAvailable = displayCount > 0;
            const percentage = isAvailable && shutterFacetTotal > 0 ? ((displayCount / shutterFacetTotal) * 100).toFixed(1) : '0.0';
            const activeStyle = isActive ? 'border: 2px solid rgba(59, 130, 246, 0.9); background-color: rgba(59, 130, 246, 0.15);' : 'border: 2px solid transparent;';
            const dimStyle = !isAvailable ? 'opacity: 0.3; cursor: not-allowed;' : '';
            html += `<p class="clickable-shutter" data-shutter="${escapeHtml(shutter)}" style="margin: 0; cursor: pointer; padding: 5px; border-radius: 8px; transition: all 0.2s; ${activeStyle} ${dimStyle}"><strong>${shutter}s:</strong> ${displayCount} photos (${percentage}%)</p>`;
        });
        html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div>`;
    }

    // ISO Stats - show all from baseline, counts from ISO facet (all filters except iso)
    if (currentAnalysisData && currentAnalysisData.iso_freq && Object.keys(currentAnalysisData.iso_freq).length > 0) {
        const isoFacet = facetAnalyses.iso || analysis;
        const isoFacetFreq = isoFacet.iso_freq || {};
        const isoFacetTotal = isoFacet.total_photos || 0;
        const chartId = 'chart-isos';
        html += `<div class="result-card"><h3>ISO Settings</h3><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;"><div style="max-height: 400px; overflow-y: auto;">`;
        const isos = Object.entries(currentAnalysisData.iso_freq)
            .sort((a, b) => parseInt(a[0]) - parseInt(b[0])); // Ascending order (smallest to largest)
        
        isos.forEach(([iso, count]) => {
            const isActive = normalizeToArray(activeFilters.iso).includes(iso);
            const displayCount = isoFacetFreq[iso] || 0;
            const isAvailable = displayCount > 0;
            const percentage = isAvailable && isoFacetTotal > 0 ? ((displayCount / isoFacetTotal) * 100).toFixed(1) : '0.0';
            const activeStyle = isActive ? 'border: 2px solid rgba(59, 130, 246, 0.9); background-color: rgba(59, 130, 246, 0.15);' : 'border: 2px solid transparent;';
            const dimStyle = !isAvailable ? 'opacity: 0.3; cursor: not-allowed;' : '';
            html += `<p class="clickable-iso" data-iso="${escapeHtml(iso)}" style="margin: 0; cursor: pointer; padding: 5px; border-radius: 8px; transition: all 0.2s; ${activeStyle} ${dimStyle}"><strong>ISO ${iso}:</strong> ${displayCount} photos (${percentage}%)</p>`;
        });
        html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div>`;
    }

    // Focal Length Stats - show all from baseline, counts from focal length facet (all filters except focal_length)
    if (currentAnalysisData && currentAnalysisData.focal_length_freq && Object.keys(currentAnalysisData.focal_length_freq).length > 0) {
        const focalFacet = facetAnalyses.focal_length || analysis;
        const focalFacetFreq = focalFacet.focal_length_freq || {};
        const focalFacetTotal = focalFacet.total_photos || 0;
        // Separate primes and zooms, bucket zooms by 10mm
        const primes = {};
        const zoomBuckets = {};
        
        Object.entries(currentAnalysisData.focal_length_freq).forEach(([focal, count]) => {
            const focalNum = parseFloat(focal);
            
            // Check if it's a "prime" focal length (common primes: 14, 16, 20, 24, 28, 35, 40, 50, 85, 100, 105, 135, 200, 300, 400, 500, 600)
            const commonPrimes = [14, 16, 20, 24, 28, 35, 40, 50, 85, 100, 105, 135, 200, 300, 400, 500, 600];
            if (commonPrimes.includes(focalNum)) {
                primes[focal] = count;
            } else {
                // Bucket zooms by 10mm ranges
                const bucketStart = Math.floor(focalNum / 10) * 10;
                const bucketEnd = bucketStart + 9;
                const bucketKey = `${bucketStart}-${bucketEnd}mm`;
                zoomBuckets[bucketKey] = (zoomBuckets[bucketKey] || 0) + count;
            }
        });
        
        // Check if we should show primes (show if "all" or "prime" is selected)
        const showPrimes = !activeFilters.lens_type || activeFilters.lens_type === 'prime';
        // Check if we should show zooms (show if "all" or "zoom" is selected)
        const showZooms = !activeFilters.lens_type || activeFilters.lens_type === 'zoom';
        
        // Display primes
        if (Object.keys(primes).length > 0 && showPrimes) {
            const chartId = 'chart-primes';
            html += `<div class="result-card"><h3>Prime Focal Lengths</h3><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;"><div style="max-height: 400px; overflow-y: auto;">`;
            const sortedPrimes = Object.entries(primes)
                .sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]));

            const selectedFocals = normalizeToArray(activeFilters.focal_length);
            
            sortedPrimes.forEach(([focal, count]) => {
                const focalDisplay = parseInt(focal); // Remove decimals for primes
                const isActive = selectedFocals.includes(focal);
                const displayCount = focalFacetFreq[focal] || 0;
                const isAvailable = displayCount > 0;
                const percentage = isAvailable && focalFacetTotal > 0 ? ((displayCount / focalFacetTotal) * 100).toFixed(1) : '0.0';
                const activeStyle = isActive ? 'border: 2px solid rgba(59, 130, 246, 0.9); background-color: rgba(59, 130, 246, 0.15);' : 'border: 2px solid transparent;';
                const dimStyle = !isAvailable ? 'opacity: 0.3; cursor: not-allowed;' : '';
                html += `<p class="clickable-focal" data-focal="${escapeHtml(focal)}" style="margin: 0; cursor: pointer; padding: 5px; border-radius: 8px; transition: all 0.2s; ${activeStyle} ${dimStyle}"><strong>${focalDisplay}mm:</strong> ${displayCount} photos (${percentage}%)</p>`;
            });
            html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div>`;
        }
        
        // Display zoom ranges
        if (Object.keys(zoomBuckets).length > 0 && showZooms) {
            const chartId = 'chart-zooms';
            html += `<div class="result-card"><h3>Zoom Focal Lengths (10mm buckets)</h3><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;"><div style="max-height: 400px; overflow-y: auto;">`;
            
            // Also calculate zoom buckets from focal-length facet data
            const filteredZoomBuckets = {};
            if (focalFacetFreq) {
                Object.entries(focalFacetFreq).forEach(([focal, count]) => {
                    const focalNum = parseFloat(focal);
                    const commonPrimes = [14, 16, 20, 24, 28, 35, 40, 50, 85, 100, 105, 135, 200, 300, 400, 500, 600];
                    if (!commonPrimes.includes(focalNum)) {
                        const bucketStart = Math.floor(focalNum / 10) * 10;
                        const bucketEnd = bucketStart + 9;
                        const bucketKey = `${bucketStart}-${bucketEnd}mm`;
                        filteredZoomBuckets[bucketKey] = (filteredZoomBuckets[bucketKey] || 0) + count;
                    }
                });
            }
            
            const sortedZooms = Object.entries(zoomBuckets)
                .sort((a, b) => {
                    const aStart = parseInt(a[0].split('-')[0]);
                    const bStart = parseInt(b[0].split('-')[0]);
                    return aStart - bStart;
                });
            
            sortedZooms.forEach(([range, count]) => {
                const isAvailable = filteredZoomBuckets[range];
                const displayCount = isAvailable ? filteredZoomBuckets[range] : 0;
                const percentage = isAvailable && focalFacetTotal > 0 ? ((filteredZoomBuckets[range] / focalFacetTotal) * 100).toFixed(1) : '0.0';
                const dimStyle = !isAvailable ? 'opacity: 0.3; cursor: not-allowed;' : '';
                html += `<p style="margin: 0; padding: 5px; ${dimStyle}"><strong>${range}:</strong> ${displayCount} photos (${percentage}%)</p>`;
            });
            html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div>`;
        }
    }

    // Time of Day - show all from baseline, counts from time facet (all filters except time_of_day)
    if (currentAnalysisData && currentAnalysisData.time_of_day_freq && Object.keys(currentAnalysisData.time_of_day_freq).length > 0) {
        const timeFacet = facetAnalyses.time_of_day || analysis;
        const timeFacetFreq = timeFacet.time_of_day_freq || {};
        const timeFacetTotal = timeFacet.total_photos || 0;
        const chartId = 'chart-timeofday';
        html += `<div class="result-card"><h3>Time of Day</h3><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: start;"><div style="max-height: 400px; overflow-y: auto;">`;
        const times = Object.entries(currentAnalysisData.time_of_day_freq)
            .sort((a, b) => b[1] - a[1]);
        
        times.forEach(([time, count]) => {
            const displayCount = timeFacetFreq[time] || 0;
            const isAvailable = displayCount > 0;
            const percentage = isAvailable && timeFacetTotal > 0 ? ((displayCount / timeFacetTotal) * 100).toFixed(1) : '0.0';
            const isActive = normalizeToArray(activeFilters.time_of_day).includes(time);
            const activeStyle = isActive ? 'border: 2px solid rgba(59, 130, 246, 0.9); background-color: rgba(59, 130, 246, 0.15); border-radius: 8px;' : '';
            const dimStyle = !isAvailable ? 'opacity: 0.3; cursor: not-allowed;' : '';
            html += `<p class="clickable-time" data-time="${escapeHtml(time)}" style="margin: 0; cursor: pointer; padding: 5px; transition: all 0.2s; ${activeStyle} ${dimStyle}"><strong>${time}:</strong> ${displayCount} photos (${percentage}%)</p>`;
        });
        html += `</div><div><canvas id="${chartId}" style="height: 350px;"></canvas></div></div></div>`;
    }

    // Destroy all existing charts before setting new HTML
    chartInstances.forEach(chart => {
        if (chart) {
            try {
                chart.destroy();
            } catch (e) {
                console.warn('Error destroying chart:', e);
            }
        }
    });
    chartInstances = [];
    
    resultsArea.innerHTML = html;
    
    // Render all charts after HTML is inserted
    setTimeout(() => {
        // Photo Details temporal chart (derived ONLY from Photo Details rows)
        if (typeof window.togglePhotoDetailsTemporalMode === 'function') {
            try {
                window.togglePhotoDetailsTemporalMode(photoDetailsTemporalMode);
            } catch (e) {
                console.warn('Photo Details temporal toggle restore failed:', e);
            }
        }

        // Hit-rate charts live in collapsible sections: only render when visible to avoid wrong initial sizing.
        renderCategoryHitRateChartIfVisible();
        renderGroupHitRateChartIfVisible();
        
        if (currentAnalysisData && currentAnalysisData.camera_freq && Object.keys(currentAnalysisData.camera_freq).length > 0) {
            const cameras = Object.entries(currentAnalysisData.camera_freq).sort((a, b) => b[1] - a[1]);

            const cameraFacet = facetAnalyses.camera || analysis;
            const cameraFacetFreq = cameraFacet.camera_freq || {};

            const cameraData = cameras.map(([cam, count]) => {
                return cameraFacetFreq[cam] || 0;
            });
            const cameraColors = cameras.map(([cam, count]) => {
                if (activeFilters.camera) {
                    const isSelected = normalizeToArray(activeFilters.camera).includes(cam);
                    return isSelected ? 'rgba(59, 130, 246, 0.8)' : 'rgba(59, 130, 246, 0.3)';
                }
                return 'rgba(59, 130, 246, 0.8)';
            });
            createHistogramChart('chart-cameras', cameras.map(c => c[0]), cameraData, 'Camera Bodies', 'Camera Model', cameraColors, 'camera', cameras.map(c => c[0]));
        }
        if (currentAnalysisData && currentAnalysisData.lens_freq && Object.keys(currentAnalysisData.lens_freq).length > 0) {
            const lenses = Object.entries(currentAnalysisData.lens_freq).sort((a, b) => a[0].localeCompare(b[0]));

            const lensFacet = facetAnalyses.lens || analysis;
            const lensFacetFreq = lensFacet.lens_freq || {};

            const lensData = lenses.map(([lens, count]) => {
                return lensFacetFreq[lens] || 0;
            });
            const lensColors = lenses.map(([lens, count]) => {
                if (activeFilters.lens) {
                    const isSelected = normalizeToArray(activeFilters.lens).includes(lens);
                    return isSelected ? 'rgba(147, 51, 234, 0.8)' : 'rgba(147, 51, 234, 0.3)';
                }
                return 'rgba(147, 51, 234, 0.8)';
            });
            createHistogramChart('chart-lenses', lenses.map(l => l[0]), lensData, 'All Lenses', 'Lens', lensColors, 'lens', lenses.map(l => l[0]));
        }
        if (currentAnalysisData && currentAnalysisData.aperture_freq && Object.keys(currentAnalysisData.aperture_freq).length > 0) {
            const apertures = Object.entries(currentAnalysisData.aperture_freq)
                .sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]));

            const apertureFacet = facetAnalyses.aperture || analysis;
            const apertureFacetFreq = apertureFacet.aperture_freq || {};
            
            const apertureData = apertures.map(([aperture, count]) => {
                return apertureFacetFreq[aperture] || 0;
            });
            const apertureColors = apertures.map(([aperture, count]) => {
                if (activeFilters.aperture) {
                    const isSelected = normalizeToArray(activeFilters.aperture).includes(aperture);
                    return isSelected ? 'rgba(59, 130, 246, 0.8)' : 'rgba(59, 130, 246, 0.3)';
                }
                return 'rgba(59, 130, 246, 0.8)';
            });
            createHistogramChart('chart-apertures', apertures.map(a => `f/${a[0]}`), apertureData, 'Aperture Settings', 'Aperture', apertureColors, 'aperture', apertures.map(a => a[0]));
        }
        if (currentAnalysisData && currentAnalysisData.shutter_speed_freq && Object.keys(currentAnalysisData.shutter_speed_freq).length > 0) {
            const parseShutterSpeed = (speed) => {
                if (speed.includes('/')) {
                    const [num, denom] = speed.split('/').map(Number);
                    return num / denom;
                }
                return parseFloat(speed);
            };
            const shutters = Object.entries(currentAnalysisData.shutter_speed_freq)
                .sort((a, b) => parseShutterSpeed(a[0]) - parseShutterSpeed(b[0]));

            const shutterFacet = facetAnalyses.shutter_speed || analysis;
            const shutterFacetFreq = shutterFacet.shutter_speed_freq || {};
            
            const shutterData = shutters.map(([shutter, count]) => {
                return shutterFacetFreq[shutter] || 0;
            });
            const shutterColors = shutters.map(([shutter, count]) => {
                if (activeFilters.shutter_speed) {
                    const isSelected = normalizeToArray(activeFilters.shutter_speed).includes(shutter);
                    return isSelected ? 'rgba(168, 85, 247, 0.8)' : 'rgba(168, 85, 247, 0.3)';
                }
                return 'rgba(168, 85, 247, 0.8)';
            });
            createHistogramChart('chart-shutters', shutters.map(s => `${s[0]}s`), shutterData, 'Shutter Speeds', 'Shutter Speed', shutterColors, 'shutter_speed', shutters.map(s => s[0]));
        }
        if (currentAnalysisData && currentAnalysisData.iso_freq && Object.keys(currentAnalysisData.iso_freq).length > 0) {
            const isos = Object.entries(currentAnalysisData.iso_freq)
                .sort((a, b) => parseInt(a[0]) - parseInt(b[0]));

            const isoFacet = facetAnalyses.iso || analysis;
            const isoFacetFreq = isoFacet.iso_freq || {};
            
            const isoData = isos.map(([iso, count]) => {
                return isoFacetFreq[iso] || 0;
            });
            const isoColors = isos.map(([iso, count]) => {
                if (activeFilters.iso) {
                    const isSelected = normalizeToArray(activeFilters.iso).includes(iso);
                    return isSelected ? 'rgba(14, 165, 233, 0.8)' : 'rgba(14, 165, 233, 0.3)';
                }
                return 'rgba(14, 165, 233, 0.8)';
            });
            createHistogramChart('chart-isos', isos.map(i => `ISO ${i[0]}`), isoData, 'ISO Settings', 'ISO', isoColors, 'iso', isos.map(i => i[0]));
        }
        if (currentAnalysisData && currentAnalysisData.focal_length_freq && Object.keys(currentAnalysisData.focal_length_freq).length > 0) {
            const focalFacet = facetAnalyses.focal_length || analysis;
            const focalFacetFreq = focalFacet.focal_length_freq || {};
            const primes = {};
            const zoomBuckets = {};
            const commonPrimes = [14, 16, 20, 24, 28, 35, 40, 50, 85, 100, 105, 135, 200, 300, 400, 500, 600];
            
            Object.entries(currentAnalysisData.focal_length_freq).forEach(([focal, count]) => {
                const focalNum = parseFloat(focal);
                if (commonPrimes.includes(focalNum)) {
                    primes[focal] = count;
                } else {
                    const bucketStart = Math.floor(focalNum / 10) * 10;
                    const bucketEnd = bucketStart + 9;
                    const bucketKey = `${bucketStart}-${bucketEnd}mm`;
                    zoomBuckets[bucketKey] = (zoomBuckets[bucketKey] || 0) + count;
                }
            });
            
            if (Object.keys(primes).length > 0) {
                const sortedPrimes = Object.entries(primes).sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]));
                
                const primeData = sortedPrimes.map(([focal, count]) => {
                    return focalFacetFreq[focal] || 0;
                });
                const primeColors = sortedPrimes.map(([focal, count]) => {
                    if (activeFilters.focal_length) {
                        const isSelected = normalizeToArray(activeFilters.focal_length).includes(focal);
                        return isSelected ? 'rgba(236, 72, 153, 0.8)' : 'rgba(236, 72, 153, 0.3)';
                    }
                    return 'rgba(236, 72, 153, 0.8)';
                });
                createHistogramChart('chart-primes', sortedPrimes.map(p => `${parseInt(p[0])}mm`), primeData, 'Prime Focal Lengths', 'Focal Length', primeColors, 'focal_length', sortedPrimes.map(p => p[0]));
            }
            if (Object.keys(zoomBuckets).length > 0) {
                const sortedZooms = Object.entries(zoomBuckets)
                    .sort((a, b) => {
                        const aStart = parseInt(a[0].split('-')[0]);
                        const bStart = parseInt(b[0].split('-')[0]);
                        return aStart - bStart;
                    });

                // Build zoom buckets from the focal-length facet (so focal_length selection doesn't collapse buckets)
                const filteredZoomBuckets = {};
                if (focalFacetFreq) {
                    Object.entries(focalFacetFreq).forEach(([focal, count]) => {
                        const focalNum = parseFloat(focal);
                        if (!commonPrimes.includes(focalNum)) {
                            const bucketStart = Math.floor(focalNum / 10) * 10;
                            const bucketEnd = bucketStart + 9;
                            const bucketKey = `${bucketStart}-${bucketEnd}mm`;
                            filteredZoomBuckets[bucketKey] = (filteredZoomBuckets[bucketKey] || 0) + count;
                        }
                    });
                }

                const zoomData = sortedZooms.map(([bucket]) => filteredZoomBuckets[bucket] || 0);
                createHistogramChart('chart-zooms', sortedZooms.map(z => z[0]), zoomData, 'Zoom Focal Lengths (10mm buckets)', 'Focal Length Range', 'rgba(139, 92, 246, 0.8)', null, sortedZooms.map(z => z[0]));
            }
        }
        if (currentAnalysisData && currentAnalysisData.time_of_day_freq && Object.keys(currentAnalysisData.time_of_day_freq).length > 0) {
            const times = Object.entries(currentAnalysisData.time_of_day_freq).sort((a, b) => b[1] - a[1]);

            const timeFacet = facetAnalyses.time_of_day || analysis;
            const timeFacetFreq = timeFacet.time_of_day_freq || {};
            
            const timeData = times.map(([time, count]) => {
                return timeFacetFreq[time] || 0;
            });
            const timeColors = times.map(([time, count]) => {
                if (activeFilters.time_of_day) {
                    const isSelected = normalizeToArray(activeFilters.time_of_day).includes(time);
                    return isSelected ? 'rgba(251, 146, 60, 0.8)' : 'rgba(251, 146, 60, 0.3)';
                }
                return 'rgba(251, 146, 60, 0.8)';
            });
            createHistogramChart('chart-timeofday', times.map(t => t[0]), timeData, 'Time of Day', 'Time Period', timeColors, 'time_of_day', times.map(t => t[0]));
        }

        // Second-pass reflow: helps when charts were created before final layout.
        requestChartResize();
        
        // Restore lens type button states after HTML re-render
        updateLensTypeButtons();
        
        // Add single-click handlers for categories and groups
        document.querySelectorAll('.clickable-category').forEach(elem => {
            const category = elem.getAttribute('data-category');
            const isActive = category ? normalizeToArray(activeFilters.category).includes(category) : false;
            const isDisabled = elem.style.opacity === '0.3';
            
            elem.addEventListener('click', (event) => {
                if (category && !isDisabled) {
                    applySelection('category', category, event);
                    clearDownstreamFilters('category');
                    applyFiltersAndRedraw();
                }
            });
            
            // Hover effect - only if not active
            elem.addEventListener('mouseenter', () => {
                if (!(category && normalizeToArray(activeFilters.category).includes(category)) && !isDisabled) {
                    elem.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                }
            });
            elem.addEventListener('mouseleave', () => {
                if (!(category && normalizeToArray(activeFilters.category).includes(category)) && !isDisabled) {
                    elem.style.backgroundColor = 'transparent';
                }
            });
        });
        
        document.querySelectorAll('.clickable-group').forEach(elem => {
            const group = elem.getAttribute('data-group');
            const isActive = group ? normalizeToArray(activeFilters.group).includes(group) : false;
            const isDisabled = elem.style.opacity === '0.3';
            
            elem.addEventListener('click', (event) => {
                if (group && !isDisabled) {
                    applySelection('group', group, event);
                    clearDownstreamFilters('group');
                    applyFiltersAndRedraw();
                }
            });
            
            // Hover effect - only if not active
            elem.addEventListener('mouseenter', () => {
                if (!(group && normalizeToArray(activeFilters.group).includes(group)) && !isDisabled) {
                    elem.style.backgroundColor = 'rgba(147, 51, 234, 0.1)';
                }
            });
            elem.addEventListener('mouseleave', () => {
                if (!(group && normalizeToArray(activeFilters.group).includes(group)) && !isDisabled) {
                    elem.style.backgroundColor = 'transparent';
                }
            });
        });

        document.querySelectorAll('.clickable-time').forEach(elem => {
            const time = elem.getAttribute('data-time');
            const isActive = time ? normalizeToArray(activeFilters.time_of_day).includes(time) : false;
            const isDisabled = elem.style.opacity === '0.3';

            elem.addEventListener('click', (event) => {
                if (time && !isDisabled) {
                    applySelection('time_of_day', time, event);
                    applyFiltersAndRedraw();
                }
            });

            elem.addEventListener('mouseenter', () => {
                if (!(time && normalizeToArray(activeFilters.time_of_day).includes(time)) && !isDisabled) {
                    elem.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                }
            });
            elem.addEventListener('mouseleave', () => {
                if (!(time && normalizeToArray(activeFilters.time_of_day).includes(time)) && !isDisabled) {
                    elem.style.backgroundColor = 'transparent';
                }
            });
        });
        
        // Add click handlers for camera bodies
        document.querySelectorAll('.clickable-camera').forEach(elem => {
            const camera = elem.getAttribute('data-camera');
            const isActive = camera ? normalizeToArray(activeFilters.camera).includes(camera) : false;
            const isDisabled = elem.style.opacity === '0.3';
            
            elem.addEventListener('click', (event) => {
                if (camera && !isDisabled) {
                    applySelection('camera', camera, event);
                    clearDownstreamFilters('camera');
                    applyFiltersAndRedraw();
                }
            });
            
            elem.addEventListener('mouseenter', () => {
                if (!(camera && normalizeToArray(activeFilters.camera).includes(camera)) && !isDisabled) {
                    elem.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                }
            });
            elem.addEventListener('mouseleave', () => {
                if (!(camera && normalizeToArray(activeFilters.camera).includes(camera)) && !isDisabled) {
                    elem.style.backgroundColor = 'transparent';
                }
            });
        });
        
        // Add click handlers for lenses
        document.querySelectorAll('.clickable-lens').forEach(elem => {
            const lens = elem.getAttribute('data-lens');
            const isActive = lens ? normalizeToArray(activeFilters.lens).includes(lens) : false;
            const isDisabled = elem.style.opacity === '0.3';
            
            elem.addEventListener('click', (event) => {
                if (lens && !isDisabled) {
                    applySelection('lens', lens, event);
                    clearDownstreamFilters('lens');
                    applyFiltersAndRedraw();
                }
            });
            
            elem.addEventListener('mouseenter', () => {
                if (!(lens && normalizeToArray(activeFilters.lens).includes(lens)) && !isDisabled) {
                    elem.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                }
            });
            elem.addEventListener('mouseleave', () => {
                if (!(lens && normalizeToArray(activeFilters.lens).includes(lens)) && !isDisabled) {
                    elem.style.backgroundColor = 'transparent';
                }
            });
        });
        
        // Add click handlers for apertures
        document.querySelectorAll('.clickable-aperture').forEach(elem => {
            const aperture = elem.getAttribute('data-aperture');
            const isActive = aperture ? normalizeToArray(activeFilters.aperture).includes(aperture) : false;
            const isDisabled = elem.style.opacity === '0.3';
            
            elem.addEventListener('click', (event) => {
                if (aperture && !isDisabled) {
                    applySelection('aperture', aperture, event);
                    applyFiltersAndRedraw();
                }
            });
            
            elem.addEventListener('mouseenter', () => {
                if (!(aperture && normalizeToArray(activeFilters.aperture).includes(aperture)) && !isDisabled) {
                    elem.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                }
            });
            elem.addEventListener('mouseleave', () => {
                if (!(aperture && normalizeToArray(activeFilters.aperture).includes(aperture)) && !isDisabled) {
                    elem.style.backgroundColor = 'transparent';
                }
            });
        });
        
        // Add click handlers for shutter speeds
        document.querySelectorAll('.clickable-shutter').forEach(elem => {
            const shutter = elem.getAttribute('data-shutter');
            const isActive = shutter ? normalizeToArray(activeFilters.shutter_speed).includes(shutter) : false;
            const isDisabled = elem.style.opacity === '0.3';
            
            elem.addEventListener('click', (event) => {
                if (shutter && !isDisabled) {
                    applySelection('shutter_speed', shutter, event);
                    applyFiltersAndRedraw();
                }
            });
            
            elem.addEventListener('mouseenter', () => {
                if (!(shutter && normalizeToArray(activeFilters.shutter_speed).includes(shutter)) && !isDisabled) {
                    elem.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                }
            });
            elem.addEventListener('mouseleave', () => {
                if (!(shutter && normalizeToArray(activeFilters.shutter_speed).includes(shutter)) && !isDisabled) {
                    elem.style.backgroundColor = 'transparent';
                }
            });
        });
        
        // Add click handlers for ISO settings
        document.querySelectorAll('.clickable-iso').forEach(elem => {
            const iso = elem.getAttribute('data-iso');
            const isActive = iso ? normalizeToArray(activeFilters.iso).includes(iso) : false;
            const isDisabled = elem.style.opacity === '0.3';
            
            elem.addEventListener('click', (event) => {
                if (iso && !isDisabled) {
                    applySelection('iso', iso, event);
                    applyFiltersAndRedraw();
                }
            });
            
            elem.addEventListener('mouseenter', () => {
                if (!(iso && normalizeToArray(activeFilters.iso).includes(iso)) && !isDisabled) {
                    elem.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                }
            });
            elem.addEventListener('mouseleave', () => {
                if (!(iso && normalizeToArray(activeFilters.iso).includes(iso)) && !isDisabled) {
                    elem.style.backgroundColor = 'transparent';
                }
            });
        });
        
        // Add click handlers for focal lengths
        document.querySelectorAll('.clickable-focal').forEach(elem => {
            const focal = elem.getAttribute('data-focal');
            const isActive = focal ? normalizeToArray(activeFilters.focal_length).includes(focal) : false;
            const isDisabled = elem.style.opacity === '0.3';
            
            elem.addEventListener('click', (event) => {
                if (focal && !isDisabled) {
                    applySelection('focal_length', focal, event);
                    applyFiltersAndRedraw();
                }
            });
            
            elem.addEventListener('mouseenter', () => {
                if (!(focal && normalizeToArray(activeFilters.focal_length).includes(focal)) && !isDisabled) {
                    elem.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                }
            });
            elem.addEventListener('mouseleave', () => {
                if (!(focal && normalizeToArray(activeFilters.focal_length).includes(focal)) && !isDisabled) {
                    elem.style.backgroundColor = 'transparent';
                }
            });
        });
    }, 100);
}

// Helper function to update lens type button states
function updateLensTypeButtons() {
    const allBtn = document.getElementById('btn-all');
    const primeBtn = document.getElementById('btn-prime');
    const zoomBtn = document.getElementById('btn-zoom');
    
    if (!allBtn || !primeBtn || !zoomBtn) return;
    
    // Reset all buttons to inactive state
    allBtn.style.background = 'rgba(75, 85, 99, 0.5)';
    allBtn.style.color = '#9ca3af';
    primeBtn.style.background = 'rgba(75, 85, 99, 0.5)';
    primeBtn.style.color = '#9ca3af';
    zoomBtn.style.background = 'rgba(75, 85, 99, 0.5)';
    zoomBtn.style.color = '#9ca3af';
    
    // Highlight active button based on current state
    if (activeLensType === 'all' || !activeFilters.lens_type) {
        allBtn.style.background = 'rgba(59, 130, 246, 0.8)';
        allBtn.style.color = 'white';
    } else if (activeLensType === 'prime' || activeFilters.lens_type === 'prime') {
        primeBtn.style.background = 'rgba(236, 72, 153, 0.8)';
        primeBtn.style.color = 'white';
    } else if (activeLensType === 'zoom' || activeFilters.lens_type === 'zoom') {
        zoomBtn.style.background = 'rgba(139, 92, 246, 0.8)';
        zoomBtn.style.color = 'white';
    }
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
    sortColumn: 'category',
    sortDirection: 'asc',
    filters: {
        category: '',
        group: ''
    },
    editingSessionId: null
};

async function loadDatabaseOverview() {
    const summaryContent = document.getElementById('db-summary-content');
    const tbody = document.getElementById('db-sessions-tbody');
    
    summaryContent.innerHTML = '<p>Loading...</p>';
    tbody.innerHTML = '<tr><td colspan="8" style="padding: 20px; text-align: center;">Loading...</td></tr>';

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
        // Sort by photo count descending and take top 3
        const topCategories = summary.categories
            .sort((a, b) => b.photos - a.photos)
            .slice(0, 3);
        
        html += '<div style="margin-bottom: 20px;"><strong>Top Categories</strong><br>';
        topCategories.forEach(cat => {
            html += `<div style="margin: 5px 0 0 15px;">${cat.name}: ${cat.sessions} sessions, ${cat.photos.toLocaleString()} photos</div>`;
        });
        html += '</div>';
    }
    
    if (summary.groups.length > 0) {
        // Sort by photo count descending and take top 3
        const topGroups = summary.groups
            .sort((a, b) => b.photos - a.photos)
            .slice(0, 3);
        
        html += '<div style="margin-bottom: 20px;"><strong>Top Groups</strong><br>';
        topGroups.forEach(grp => {
            html += `<div style="margin: 5px 0 0 15px;">${grp.name}: ${grp.sessions} sessions, ${grp.photos.toLocaleString()} photos</div>`;
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
    
    // Sort filtered sessions with multi-level sorting
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
        
        // Primary sort by selected column
        let result = 0;
        if (aVal < bVal) result = dbData.sortDirection === 'asc' ? -1 : 1;
        else if (aVal > bVal) result = dbData.sortDirection === 'asc' ? 1 : -1;
        
        // If equal, apply secondary sorting: category > group > name
        if (result === 0 && column !== 'category') {
            const catCompare = a.category.toLowerCase().localeCompare(b.category.toLowerCase());
            if (catCompare !== 0) return catCompare;
        }
        if (result === 0 && column !== 'group') {
            const groupCompare = a.group.toLowerCase().localeCompare(b.group.toLowerCase());
            if (groupCompare !== 0) return groupCompare;
        }
        if (result === 0 && column !== 'name') {
            return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
        }
        
        return result;
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
        tbody.innerHTML = '<tr><td colspan="8" style="padding: 20px; text-align: center;">No sessions match your filters</td></tr>';
        showingCount.textContent = '0';
        totalCount.textContent = dbData.sessions.length;
        return;
    }
    
    let html = '';
    dbData.filteredSessions.forEach(session => {
        const isEditing = dbData.editingSessionId === session.id;
        html += `<tr id="session-row-${session.id}" style="border-bottom: 1px solid var(--border-color);">`;
        
        if (isEditing) {
            // Edit mode
            html += `<td style="padding: 10px;"><input type="text" id="edit-name-${session.id}" value="${escapeHtml(session.name)}" onkeypress="if(event.key==='Enter')saveSessionEdit(${session.id})" style="width: 100%; padding: 4px; background: var(--background); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 4px;"></td>`;
            html += `<td style="padding: 10px;"><input type="text" id="edit-category-${session.id}" value="${escapeHtml(session.category || '')}" onkeypress="if(event.key==='Enter')saveSessionEdit(${session.id})" style="width: 100%; padding: 4px; background: var(--background); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 4px;"></td>`;
            html += `<td style="padding: 10px;"><input type="text" id="edit-group-${session.id}" value="${escapeHtml(session.group || '')}" onkeypress="if(event.key==='Enter')saveSessionEdit(${session.id})" style="width: 100%; padding: 4px; background: var(--background); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 4px;"></td>`;
            html += `<td style="padding: 10px; text-align: right;">${session.total_photos}</td>`;
            html += `<td style="padding: 10px; text-align: right;"><input type="number" id="edit-raw-${session.id}" value="${session.total_raw_photos || ''}" placeholder="-" onkeypress="if(event.key==='Enter')saveSessionEdit(${session.id})" style="width: 60px; padding: 4px; background: var(--background); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 4px; text-align: right;"></td>`;
            html += `<td style="padding: 10px; text-align: right;">${session.hit_rate !== null ? session.hit_rate + '%' : '-'}</td>`;
            html += `<td style="padding: 10px;">${session.date ? session.date.split('T')[0].split(' ')[0] : '-'}</td>`;
            html += `<td style="padding: 10px; text-align: center;">`;
            html += `<button onclick="saveSessionEdit(${session.id})" style="background: none; border: none; cursor: pointer; color: #4CAF50; font-size: 16px; margin-right: 8px;" title="Save">✓</button>`;
            html += `<button onclick="cancelSessionEdit()" style="background: none; border: none; cursor: pointer; color: #f44336; font-size: 16px;" title="Cancel">✗</button>`;
            html += `</td>`;
        } else {
            // View mode
            html += `<td style="padding: 10px;">${escapeHtml(session.name)}</td>`;
            html += `<td style="padding: 10px;">${escapeHtml(session.category || '-')}</td>`;
            html += `<td style="padding: 10px;">${escapeHtml(session.group || '-')}</td>`;
            html += `<td style="padding: 10px; text-align: right;">${session.total_photos}</td>`;
            html += `<td style="padding: 10px; text-align: right;">${session.total_raw_photos || '-'}</td>`;
            html += `<td style="padding: 10px; text-align: right;">${session.hit_rate !== null ? session.hit_rate + '%' : '-'}</td>`;
            html += `<td style="padding: 10px;">${session.date ? session.date.split('T')[0].split(' ')[0] : '-'}</td>`;
            html += `<td style="padding: 10px; text-align: center; white-space: nowrap;">`;
            html += `<button onclick="showSessionDetails(${session.id})" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); font-size: 16px; padding: 0 8px;" title="Details">ℹ️</button>`;
            html += `<button onclick="editSession(${session.id})" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); font-size: 16px; padding: 0 8px;" title="Edit">✏️</button>`;
            html += `<button onclick="deleteSession(${session.id}, '${escapeHtml(session.name).replace(/'/g, "\\'")}')" style="background: none; border: none; cursor: pointer; color: var(--text-secondary); font-size: 16px; padding: 0 8px;" title="Delete">🗑️</button>`;
            html += `</td>`;
        }
        
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

function showSessionDetails(sessionId) {
    const session = dbData.sessions.find(s => s.id === sessionId);
    if (!session) {
        alert('Session not found');
        return;
    }

    const modal = document.getElementById('details-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalBody = document.getElementById('modal-body');

    modalTitle.textContent = 'Session Details';

    // Format date without timestamp
    let dateDisplay = 'Not found';
    if (session.date) {
        const dateOnly = session.date.split('T')[0].split(' ')[0];
        dateDisplay = `${dateOnly} (${session.date_detected || 'provided'})`;
    }

    modalBody.innerHTML = `
        <div style="padding: 20px; font-family: monospace; line-height: 1.8;">
            <div style="font-size: 1.5em; font-weight: bold; margin-bottom: 20px;">${session.name}</div>
            <div><strong>Category:</strong> ${session.category}</div>
            <div><strong>Group:</strong> ${session.group}</div>
            <div><strong>Session Name:</strong> ${session.name}</div>
            ${session.folder_path ? `<div><strong>Path:</strong> ${session.folder_path}</div>` : ''}
            <div><strong>Session ID:</strong> ${session.id}</div>
            <div><strong>Total Final Edits:</strong> ${session.total_photos}</div>
            ${session.total_raw_photos ? `<div><strong>Total RAW Photos:</strong> ${session.total_raw_photos}</div>` : ''}
            ${session.hit_rate !== null ? `<div><strong>Hit Rate:</strong> ${session.hit_rate.toFixed(1)}%</div>` : ''}
            <div><strong>Date:</strong> ${dateDisplay}</div>
            ${session.hit_rate !== null ? `<div><strong>Hit Rate Calculation:</strong> Enabled</div>` : ''}
        </div>
    `;

    modal.style.display = 'block';
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
            ${session.date ? `<p><strong>Date:</strong> ${session.date} <span style="color: var(--success);">(${session.date_detected || 'provided'})</span></p>` : `<p><strong>Date:</strong> <span style="color: var(--error);">Not found</span></p>`}
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

// Database Session Edit/Delete Functions
function editSession(sessionId) {
    dbData.editingSessionId = sessionId;
    renderDatabaseTable();
}

function cancelSessionEdit() {
    dbData.editingSessionId = null;
    renderDatabaseTable();
}

async function saveSessionEdit(sessionId) {
    const nameInput = document.getElementById(`edit-name-${sessionId}`);
    const categoryInput = document.getElementById(`edit-category-${sessionId}`);
    const groupInput = document.getElementById(`edit-group-${sessionId}`);
    const rawInput = document.getElementById(`edit-raw-${sessionId}`);
    
    const rawValue = rawInput.value.trim();
    const updatedData = {
        name: nameInput.value.trim(),
        category: categoryInput.value.trim() || null,
        group: groupInput.value.trim() || null,
        total_raw_photos: rawValue ? parseInt(rawValue) : null
    };
    
    if (!updatedData.name) {
        alert('Session name cannot be empty');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/database/session/${sessionId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updatedData)
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            dbData.editingSessionId = null;
            await loadDatabaseOverview(); // Reload to get updated data
        } else {
            alert(`Failed to update session: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        alert(`Error updating session: ${error.message}`);
    }
}

async function deleteSession(sessionId, sessionName) {
    if (!confirm(`Are you sure you want to delete "${sessionName}"?\n\nThis will permanently remove the session and all its photo metadata.`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/database/session/${sessionId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            await loadDatabaseOverview(); // Reload to get updated data
        } else {
            alert(`Failed to delete session: ${data.error || 'Unknown error'}`);
        }
    } catch (error) {
        alert(`Error deleting session: ${error.message}`);
    }
}
