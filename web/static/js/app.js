/**
 * Main application JavaScript
 */

// Global state
let allTeams = [];
let currentTeam = null;
let currentMonth = null;

/**
 * Returns an inline tooltip icon span for use in HTML template literals.
 * @param {string} text - Tooltip content (keep to 1–2 sentences).
 * @param {boolean} [below=false] - Show tooltip below the icon (for top-of-page elements).
 * @returns {string} HTML string.
 */
function tip(text, below = false) {
    const cls = below ? 'tooltip-icon tooltip-below' : 'tooltip-icon';
    const safe = text.replace(/"/g, '&quot;');
    return `<span class="${cls}" data-tooltip="${safe}" role="img" aria-label="More information">ⓘ</span>`;
}

// JS-driven HTML tooltip for elements with data-tooltip-html (supports bullet points etc.)
(function () {
    let bubble = null;
    document.addEventListener('mouseover', e => {
        const icon = e.target.closest('[data-tooltip-html]');
        if (!icon || bubble) return;
        bubble = document.createElement('div');
        bubble.className = 'tooltip-html-bubble';
        bubble.innerHTML = icon.dataset.tooltipHtml;
        document.body.appendChild(bubble);
        const r = icon.getBoundingClientRect();
        const bw = bubble.offsetWidth;
        const bh = bubble.offsetHeight;
        let left = r.left + r.width / 2 - bw / 2;
        left = Math.max(8, Math.min(left, window.innerWidth - bw - 8));
        bubble.style.left = left + 'px';
        bubble.style.top = (r.top - bh - 8) + 'px';
    });
    document.addEventListener('mouseout', e => {
        const icon = e.target.closest('[data-tooltip-html]');
        if (!icon || !bubble) return;
        bubble.remove();
        bubble = null;
    });
})();

function showToast(title, body, type = 'error') {
    const isError = type === 'error';
    const colors = isError
        ? { bg: '#1a0808', border: '#ef4444', title: '#ef4444', text: '#f87171', close: '#f87171' }
        : { bg: '#1a1200', border: '#f59e0b', title: '#f59e0b', text: '#fbbf24', close: '#fbbf24' };

    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 9999;
        max-width: 360px; padding: 16px 20px;
        background: ${colors.bg}; border: 1px solid ${colors.border};
        border-radius: 8px; color: ${colors.text};
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        font-family: Inter, sans-serif; font-size: 0.9rem; line-height: 1.5;
    `;
    toast.innerHTML = `
        <button onclick="this.parentElement.remove()" style="position:absolute;top:10px;right:12px;background:none;border:none;color:${colors.close};font-size:1.1rem;cursor:pointer;line-height:1;" title="Close">&#x2715;</button>
        <strong style="display:block;color:${colors.title};margin-bottom:6px;padding-right:20px;">${title}</strong>
        <span>${body}</span>
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 8000);
}

/**
 * Synchronous version of safeGetElement (for immediate use)
 * @param {string} id - Element ID
 * @returns {HTMLElement|null} - The element or null if not found
 */
function safeGetElementSync(id) {
    try {
        const element = document.getElementById(id);
        return element;
    } catch (error) {
        console.error(`Error getting element '${id}':`, error);
        return null;
    }
}

/**
 * Global error handler for unhandled errors
 */
window.addEventListener('error', (event) => {
    console.error('Global error caught:', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        error: event.error
    });
    
    // Don't show error for missing elements during initialization
    if (event.message && event.message.includes('addEventListener')) {
        console.warn('Event listener error - this may be due to missing DOM elements');
    }
});

/**
 * Global handler for unhandled promise rejections
 */
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded fired - initializing application...');
    
    try {
        // Initialize tabs first
        initializeTabs();
        
        // Initialize each tab with retry logic
        setTimeout(() => {
            try {
                initializeRecommendations();
            } catch (error) {
                console.error('Error initializing recommendations:', error);
            }
        }, 0);
        
        setTimeout(() => {
            try {
                initializeBacktest();
            } catch (error) {
                console.error('Error initializing backtest:', error);
            }
        }, 0);
        
        setTimeout(() => {
            try {
                initializeStats();
            } catch (error) {
                console.error('Error initializing stats:', error);
            }
        }, 0);
        
        setTimeout(() => {
            try {
                initializeSequences();
            } catch (error) {
                console.error('Error initializing sequences:', error);
            }
        }, 0);
        
        // Load teams asynchronously - don't block if it fails
        loadTeamsWithTimeout().catch(error => {
            console.error('Failed to load teams:', error);
            // Don't block the UI - set a default state
            const teamSelect = document.getElementById('team-select');
            if (teamSelect) {
                teamSelect.innerHTML = '<option value="">Error loading teams — please refresh</option>';
                teamSelect.disabled = false;
            }
            showError(`Failed to load teams: ${error.message}. You can still use other tabs.`);
        });
    } catch (error) {
        console.error('Error during initialization:', error);
        showError('Failed to initialize application. Please refresh the page.');
    }
});

/**
 * Tab navigation
 */
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Track which tabs have been loaded to avoid duplicate API calls
    const loadedTabs = new Set();

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.dataset.tab;

            // Update buttons
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update content
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${targetTab}-tab`).classList.add('active');
            
            // Auto-load statistics when stats tab is activated
            if (targetTab === 'stats' && !loadedTabs.has('stats')) {
                loadedTabs.add('stats');
                loadStatistics();
            }
            
            // Auto-load sequences when sequences tab is activated
            if (targetTab === 'sequences' && !loadedTabs.has('sequences')) {
                loadedTabs.add('sequences');
                loadSequences();
            }
        });
    });

    // Seed initial load for the default active tab (Statistics)
    loadedTabs.add('stats');
    loadStatistics();
}

/**
 * Initialize recommendations tab
 */
function initializeRecommendations() {
    try {
        const teamSelect = safeGetElementSync('team-select', 0);
        const monthSelect = safeGetElementSync('month-select', 0);
        const getRecommendationsBtn = safeGetElementSync('get-recommendations-btn', 0);

        if (!teamSelect || !monthSelect || !getRecommendationsBtn) {
            console.error('Recommendations tab elements not found:', {
                teamSelect: !!teamSelect,
                monthSelect: !!monthSelect,
                getRecommendationsBtn: !!getRecommendationsBtn
            });
            // Retry with delay
            setTimeout(() => {
                initializeRecommendations();
            }, 100);
            return;
        }

        // Helper function to load months for a team
        const loadMonthsForTeam = async (teamName) => {
            if (!teamName) {
                monthSelect.innerHTML = '<option value="">Select a team first</option>';
                monthSelect.disabled = true;
                getRecommendationsBtn.disabled = true;
                return;
            }

            currentTeam = teamName;
            showLoading(true);
            try {
                const data = await apiClient.getTeamMonths(teamName);
                monthSelect.innerHTML = '';
                
                if (data.months && data.months.length > 0) {
                    data.months.forEach(month => {
                        const option = document.createElement('option');
                        option.value = month;
                        option.textContent = formatMonth(month);
                        monthSelect.appendChild(option);
                    });
                    monthSelect.disabled = false;
                    
                    // Auto-select first month to enable the button
                    monthSelect.value = data.months[0];
                    monthSelect.dispatchEvent(new Event('change'));
                } else {
                    monthSelect.innerHTML = '<option value="">No months available</option>';
                    monthSelect.disabled = true;
                }
            } catch (error) {
                showError(error.message);
            } finally {
                showLoading(false);
            }
        };

        // Team selection
        try {
            teamSelect.addEventListener('change', async () => {
                await loadMonthsForTeam(teamSelect.value);
            });
        } catch (error) {
            console.error('Error attaching event listener to team select:', error);
        }

        // Month selection
        try {
            monthSelect.addEventListener('change', () => {
                currentMonth = parseInt(monthSelect.value);
                getRecommendationsBtn.disabled = !currentMonth;
            });
        } catch (error) {
            console.error('Error attaching event listener to month select:', error);
        }

        // Get recommendations button
        try {
            getRecommendationsBtn.addEventListener('click', async () => {
                if (!currentTeam || !currentMonth) return;
                await loadRecommendations(currentTeam, currentMonth);
            });
            console.log('Recommendations tab initialized successfully');
        } catch (error) {
            console.error('Error attaching event listener to get recommendations button:', error);
        }
    } catch (error) {
        console.error('Error in initializeRecommendations:', error);
    }
}

/**
 * Initialize backtest tab
 */
function initializeBacktest() {
    try {
        const runBacktestBtn = safeGetElementSync('run-backtest-btn', 0);
        
        if (!runBacktestBtn) {
            // Retry with a small delay
            setTimeout(() => {
                const btn = document.getElementById('run-backtest-btn');
                if (btn) {
                    console.log('run-backtest-btn found on retry');
                    try {
                        btn.addEventListener('click', async () => {
                            await runBacktest();
                        });
                    } catch (error) {
                        console.error('Error attaching event listener to run-backtest-btn:', error);
                    }
                } else {
                    console.error('run-backtest-btn not found after retry');
                }
            }, 100);
            return;
        }

        try {
            runBacktestBtn.addEventListener('click', async () => {
                await runBacktest();
            });
            console.log('Backtest button initialized successfully');
        } catch (error) {
            console.error('Error attaching event listener to run-backtest-btn:', error);
        }
        
        // Initialize optimal configuration button
        const findOptimalBtn = safeGetElementSync('find-optimal-btn');
        if (findOptimalBtn) {
            findOptimalBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Find optimal button clicked');
                await findOptimalConfig();
            });
            console.log('Find optimal button initialized successfully');
        } else {
            console.error('find-optimal-btn not found during initialization');
            // Retry with a small delay
            setTimeout(() => {
                const btn = document.getElementById('find-optimal-btn');
                if (btn) {
                    console.log('find-optimal-btn found on retry');
                    btn.addEventListener('click', async (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        console.log('Find optimal button clicked (retry handler)');
                        await findOptimalConfig();
                    });
                } else {
                    console.error('find-optimal-btn not found after retry');
                }
            }, 100);
        }
        
        // Initialize view latest results button
        const viewLatestResultsBtn = safeGetElementSync('view-latest-results-btn');
        if (viewLatestResultsBtn) {
            viewLatestResultsBtn.addEventListener('click', async () => {
                await viewLatestResults();
            });
            console.log('View latest results button initialized successfully');
        }
        
        // Initialize upload results button
        const uploadResultsBtn = safeGetElementSync('upload-results-btn');
        const uploadResultsInput = safeGetElementSync('upload-results-input');
        if (uploadResultsBtn && uploadResultsInput) {
            uploadResultsBtn.addEventListener('click', () => {
                uploadResultsInput.click();
            });
            uploadResultsInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (file) {
                    await uploadResults(file);
                    // Reset input so same file can be selected again
                    e.target.value = '';
                }
            });
            console.log('Upload results button initialized successfully');
        }
        
        // Add event listeners for configuration sliders
        const configSliders = [
            { id: 'config-top-n', valueId: 'config-top-n-value' },
            { id: 'config-similarity-weight', valueId: 'config-similarity-weight-value', 
              secondaryId: 'config-sequence-weight-value', secondaryCalc: (v) => (1 - v).toFixed(2) },
            { id: 'config-k-similar', valueId: 'config-k-similar-value' },
            { id: 'config-lookahead-months', valueId: 'config-lookahead-months-value' },
            { id: 'config-recent-months', valueId: 'config-recent-months-value' },
            { id: 'config-min-similarity', valueId: 'config-min-similarity-value' }
        ];
        
        configSliders.forEach(({ id, valueId, secondaryId, secondaryCalc }) => {
            const slider = document.getElementById(id);
            const valueDisplay = document.getElementById(valueId);
            const secondaryDisplay = secondaryId ? document.getElementById(secondaryId) : null;
            
            if (slider && valueDisplay) {
                slider.addEventListener('input', () => {
                    const value = parseFloat(slider.value);
                    if (id === 'config-similarity-weight') {
                        valueDisplay.textContent = value.toFixed(2);
                        if (secondaryDisplay && secondaryCalc) {
                            secondaryDisplay.textContent = secondaryCalc(value);
                        }
                    } else if (id === 'config-min-similarity') {
                        valueDisplay.textContent = value.toFixed(2);
                    } else {
                        valueDisplay.textContent = Math.round(value);
                    }
                });
            }
        });
    } catch (error) {
        console.error('Error in initializeBacktest:', error);
    }
}

/**
 * Initialize statistics tab
 * Note: Statistics are now auto-loaded when the tab is opened (see initializeTabs)
 */
function initializeStats() {
    // Statistics are now auto-loaded when the tab is activated
    // This function is kept for compatibility but no longer sets up button listeners
    console.log('Statistics tab initialized (auto-load on tab open)');
}

/**
 * Initialize sequences tab
 * Note: Sequences are now auto-loaded when the tab is opened (see initializeTabs)
 */
function initializeSequences() {
    // Sequences are now auto-loaded when the tab is activated
    // This function is kept for compatibility but no longer sets up button listeners
    console.log('Sequences tab initialized (auto-load on tab open)');
}

/**
 * Load teams with timeout
 */
async function loadTeamsWithTimeout(timeoutMs = 10000) {
    return Promise.race([
        loadTeams(),
        new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Team loading timed out after 10 seconds')), timeoutMs)
        )
    ]);
}

/**
 * Load teams
 */
async function loadTeams() {
    const teamSelect = document.getElementById('team-select');
    
    if (!teamSelect) {
        console.error('Team loading elements not found');
        return;
    }
    
    teamSelect.innerHTML = '<option value="">Loading...</option>';
    teamSelect.disabled = true;
    showLoading(true);

    try {
        console.log('Loading all teams...');
        allTeams = await apiClient.getTeams();
        teamSelect.innerHTML = '';
        allTeams.forEach(team => {
            const option = document.createElement('option');
            option.value = team.name;
            option.textContent = `${team.name} (${team.num_months} months of data)`;
            teamSelect.appendChild(option);
        });

        teamSelect.disabled = false;
        console.log('Teams loaded successfully');
        
        // If no team is selected, select the first one
        // Then trigger month loading for the selected team
        if (!teamSelect.value && allTeams.length > 0) {
            teamSelect.value = allTeams[0].name;
        }
        
        // Check if a team is selected and trigger month loading
        if (teamSelect.value) {
            // Trigger change event to load months for the selected team
            teamSelect.dispatchEvent(new Event('change'));
        }
    } catch (error) {
        console.error('Error loading teams:', error);
        showError(`Failed to load teams: ${error.message}`);
        teamSelect.innerHTML = '<option value="">Error loading teams</option>';
        teamSelect.disabled = false; // Enable so user can try again
    } finally {
        showLoading(false);
    }
}

/**
 * Load recommendations
 */
async function loadRecommendations(team, month) {
    const resultsDiv = document.getElementById('recommendations-results');
    resultsDiv.classList.add('hidden');
    showLoading(true);

    try {
        // Explicitly pass optimized defaults to ensure correct values are used
        const data = await apiClient.getRecommendations(team, month, 2, 19);
        displayRecommendations(data);
    } catch (error) {
        showError(error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Build a single-line verdict badge summarising prediction accuracy.
 */
function buildVerdictLine(data) {
    if (!data.validation) return '';
    const v = data.validation;

    if (v.accuracy !== null && v.accuracy !== undefined) {
        const validatedRecs = data.recommendations.filter(r => r.validated);
        const unvalidatedRecs = data.recommendations.filter(r => !r.validated);

        if (v.validated_count === v.total_recommendations) {
            const names = validatedRecs.map(r => r.practice).join(' and ');
            return `<div class="verdict-line verdict-hit">✓ Prediction correct: ${v.validated_count}/${v.total_recommendations} — ${names} ${v.validated_count === 1 ? 'was' : 'were'} adopted</div>`;
        } else if (v.validated_count > 0) {
            const hitNames = validatedRecs.map(r => r.practice).join(' and ');
            const missNames = unvalidatedRecs.map(r => r.practice).join(' and ');
            return `<div class="verdict-line verdict-partial">~ Partial: ${v.validated_count}/${v.total_recommendations} — ${hitNames} matched; ${missNames} was not adopted</div>`;
        } else {
            const actualNames = (v.actual_improvements || []).map(i => i.practice).join(' and ');
            return `<div class="verdict-line verdict-miss">✗ Missed: 0/${v.total_recommendations}${actualNames ? ` — team actually improved ${actualNames}` : ''}</div>`;
        }
    }

    // No improvements occurred in the validation window
    let monthsText = formatMonth(v.next_month);
    if (v.month_after) monthsText += `, ${formatMonth(v.month_after)}`;
    if (v.month_after_2) monthsText += `, ${formatMonth(v.month_after_2)}`;
    return `<div class="verdict-line verdict-nodata">— No practice changes in validation window (${monthsText}); accuracy not computed</div>`;
}

/**
 * Display recommendations
 */
function displayRecommendations(data) {
    const resultsDiv = document.getElementById('recommendations-results');
    resultsDiv.classList.remove('hidden');

    // Check for API errors
    if (data.error) {
        let errorMsg = data.error;
        if (data.details) {
            errorMsg += ` ${data.details}`;
        }
        showError(errorMsg);
        resultsDiv.innerHTML = `<div class="error-message">${errorMsg}</div>`;
        return;
    }

    // Business value mapping for common practices
    const businessValueMap = {
        "CI/CD": "Faster deployment cycles, reduced manual errors, improved time-to-market",
        "Test Automation": "Higher code quality, faster feedback loops, reduced regression bugs",
        "TDD": "Better design, fewer bugs in production, improved code maintainability",
        "Code Review": "Knowledge sharing, early bug detection, improved code quality",
        "DoD": "Clear acceptance criteria, reduced rework, faster delivery",
        "Sprint Planning": "Better team alignment, realistic commitments, improved predictability",
        "Daily Standup": "Improved communication, early problem detection, team coordination",
        "Retrospective": "Continuous improvement, team learning, process optimization",
        "Product Backlog": "Prioritized work, clear roadmap, stakeholder alignment",
        "User Stories": "User-focused development, clear requirements, better communication"
    };

    const verdictLine = buildVerdictLine(data);

    let html = `
        <div class="recommendations-header">
            <h3>Top ${data.recommendations.length} Recommendations for ${data.team}</h3>
            <p class="month-info">Predicting for month: ${formatMonth(data.month)}</p>
            ${verdictLine}
            <p class="debug-info" style="font-size: 0.85em; color: #666; margin-top: 5px;">
                Requested: top_n=${data.recommendations.length} (optimized default: 2)
            </p>
        </div>
    `;

    // Add prominent warning if team didn't improve anything
    if (data.validation && data.validation.actual_improvements && data.validation.actual_improvements.length === 0) {
        let validationMonthsText = formatMonth(data.validation.next_month);
        if (data.validation.month_after) {
            validationMonthsText += `, ${formatMonth(data.validation.month_after)}`;
        }
        if (data.validation.month_after_2) {
            validationMonthsText += `, and ${formatMonth(data.validation.month_after_2)}`;
        }
        
        html += `
            <div style="background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.4); border-left: 3px solid #f59e0b; border-radius: 6px; color: #d4b896; margin-bottom: 20px; padding: 14px 16px;">
                <strong style="color: #f59e0b;">⚠ Team Status:</strong> This team (${data.team}) did not improve any practices in the validation window (${validationMonthsText})
                <p style="margin-top: 8px; margin-bottom: 0; font-size: 0.875em; opacity: 0.8;">
                    Note: This is informational, not a model failure. Teams don't always improve practices every month.
                </p>
            </div>
        `;
    }

    html += `
        <div class="info-box">
            <strong>Understanding the Output:</strong>
            <ul>
                <li><strong>Current Level:</strong> Your team's maturity level (0-3 scale: 0=Not implemented, 1=Basic, 2=Intermediate, 3=Mature)</li>
                <li><strong>Recommendation Score:</strong> Range 0.0-1.0 (higher = stronger recommendation, more evidence)</li>
                <li><strong>Score combines:</strong> Similar teams' improvements (60%) + Natural sequences (40%)</li>
            </ul>
            <details class="score-explanation">
                <summary><strong>Click to see detailed explanation of how scores are calculated</strong></summary>
                <div class="explanation-content">
                    <h4>How Recommendation Scores Work</h4>
                    <p>The recommendation score combines two powerful signals:</p>
                    
                    <div class="explanation-section">
                        <h5>1. Similar Teams' Improvements (60% weight, default)</h5>
                        <ul>
                            <li>The system compares your team's current state against <strong>ALL teams at ALL past months</strong></li>
                            <li>It finds the <strong>19 most similar teams across all historical data</strong> (default, configurable; not just same month)</li>
                            <li>It looks at <strong>what those similar teams improved</strong> in their next 1-3 months (checks up to 3 months ahead)</li>
                            <li>Each improvement is weighted by:
                                <ul>
                                    <li>How similar that team is to yours (higher similarity = more weight)</li>
                                    <li>How much they improved (bigger improvement = more weight)</li>
                                </ul>
                            </li>
                            <li><strong>Example:</strong> If 3 similar teams improved 'CI/CD' and they're 85% similar to you, this practice gets a high score</li>
                            <li><strong>Why this works:</strong> Teams with similar profiles face similar challenges. If they succeeded with a practice, you likely will too.</li>
                        </ul>
                    </div>
                    
                    <div class="explanation-section">
                        <h5>2. Natural Sequences (40% weight, default)</h5>
                        <ul>
                            <li>The system learns patterns from <strong>ALL teams' improvement history</strong></li>
                            <li>It identifies which practices typically follow others</li>
                            <li><strong>Example patterns learned:</strong>
                                <ul>
                                    <li>Teams that improved 'CI/CD' → often improve 'Test Automation' next (60% of cases)</li>
                                    <li>Teams that improved 'DoD' → often improve 'Code Review' next (55% of cases)</li>
                                </ul>
                            </li>
                            <li>If your team improved a practice in the <strong>last 3 months</strong> (default), related practices get boosted</li>
                            <li><strong>Why this works:</strong> Practices build on each other logically. CI/CD enables automated testing, so Test Automation naturally follows.</li>
                        </ul>
                    </div>
                    
                    <div class="explanation-section">
                        <h5>3. Combining the Signals</h5>
                        <ul>
                            <li>Both components are <strong>normalized separately</strong> (each divided by its maximum value) before combining</li>
                            <li>Then they're combined with weighted average:
                                <div class="formula">Final Score = (Normalized Similarity Score × 0.6) + (Normalized Sequence Score × 0.4)</div>
                                <p style="font-size: 0.9em; color: #666; margin-top: 5px;">Note: The 0.6/0.4 split is the default (configurable via similarity_weight parameter)</p>
                            </li>
                            <li>Practices are then ranked by this combined score</li>
                            <li>The <strong>top 2 practices</strong> (default, configurable; that aren't already at max level) are recommended</li>
                        </ul>
                    </div>
                    
                    <div class="explanation-section">
                        <h5>Why This Hybrid Approach Works</h5>
                        <ul>
                            <li><strong>Similarity alone:</strong> "Teams like you improved X" (good but can be rigid)</li>
                            <li><strong>Sequences alone:</strong> "X usually comes after Y" (good but too generic)</li>
                            <li><strong>Combined:</strong> "Teams like you improved X, AND it fits your natural next step"</li>
                            <li>This gives you both <strong>peer validation</strong> AND <strong>logical progression</strong></li>
                        </ul>
                    </div>
                </div>
            </details>
        </div>

        <div class="recommendations-list">
    `;

    data.recommendations.forEach((rec, index) => {
        const validatedClass = rec.validated ? 'validated' : 'not-validated';
        const validatedText = rec.validated ? 'Validated' : 'Not improved';

        html += `
            <div class="recommendation-item ${validatedClass}">
                <div class="rec-number">${index + 1}</div>
                <div class="rec-content">
                    <h4>${rec.practice}</h4>
                    <div class="rec-details">
                        <div class="rec-detail">
                            <strong>Recommendation Score:</strong>${tip('A weighted composite: similar teams\' improvements (60%) + natural practice sequences (40%). Higher = more evidence from the dataset.')} ${rec.score.toFixed(3)} <span class="score-range">(range: 0.0-1.0, higher = stronger)</span>
                        </div>
                        <div class="rec-detail">
                            <strong>Current Level:</strong>${tip('Your team\'s maturity on this practice. 0 = not implemented, 1 = basic, 2 = intermediate, 3 = mature. Only practices below level 3 are recommended.')} ${rec.level_display || `Level ${rec.level_num} (${rec.level_description})`}
                        </div>
                        <div class="rec-detail">
                            <strong>Why:</strong> 
                            ${rec.why.includes('checked but didn\'t improve') ? 
                                `<span style="color: #856404;">${rec.why}</span>` : 
                                rec.why.includes('no similar teams found') ?
                                `<span style="color: #666; font-style: italic;">${rec.why}</span>` :
                                rec.why
                            }
                            ${rec.similar_teams && rec.similar_teams.length > 0 ? `
                                <ul class="similar-teams-list" style="margin: 8px 0 0 20px; padding: 0;">
                                    <li style="margin: 4px 0; list-style: none; font-size: 0.9em; color: #555;">Similar teams that improved this practice${tip('Cosine similarity of practice maturity profiles across all historical months. Higher % = more similar overall agile state.')}</li>
                                    ${rec.similar_teams.map(st => {
                                        const similarAt = st.similar_at_month || st.month;
                                        const similarAtText = similarAt !== st.month 
                                            ? ` (similar at ${formatMonth(similarAt)})` 
                                            : '';
                                        return `
                                        <li style="margin: 4px 0;">
                                            • <strong>${st.team}</strong>${similarAtText} improved in ${formatMonth(st.month)} 
                                            <span style="color: #666; font-size: 0.9em;">(${(st.similarity * 100).toFixed(0)}% similar)</span>
                                        </li>
                                    `;
                                    }).join('')}
                                </ul>
                            ` : rec.why.includes('checked but didn\'t improve') ? `
                                <p style="margin: 8px 0 0 0; color: #856404; font-size: 0.9em; font-style: italic;">
                                    Note: Similar teams were evaluated but didn't improve this practice. Recommendation is based on sequence patterns only.
                                </p>
                            ` : ''}
                        </div>
                        ${data.validation ? `
                            <div class="rec-detail validation-status">
                                <strong>Validation:</strong>${tip('Checked against actual data: did the team improve this practice in the 1–3 months after the prediction? \'Validated\' means the prediction came true.')} ${rec.improved_in_months ? 
                                    (rec.improved_in_months.length === 3 
                                        ? `${validatedText} in month ${formatMonth(rec.improved_in_months[0])}, ${formatMonth(rec.improved_in_months[1])}, AND ${formatMonth(rec.improved_in_months[2])}`
                                        : rec.improved_in_months.length === 2 
                                        ? `${validatedText} in month ${formatMonth(rec.improved_in_months[0])} AND ${formatMonth(rec.improved_in_months[1])}`
                                        : `${validatedText} in month ${formatMonth(rec.improved_in_months[0])}`)
                                    : `${validatedText} in month ${formatMonth(data.validation.next_month)}${data.validation.month_after ? `, ${formatMonth(data.validation.month_after)}` : ''}${data.validation.month_after_2 ? `, or ${formatMonth(data.validation.month_after_2)}` : ''}`}
                            </div>
                        ` : ''}
                        ${businessValueMap[rec.practice] ? `
                            <div class="rec-detail" style="background: #f0f4ff; padding: 10px; border-radius: 4px; margin-top: 8px;">
                                <strong>💡 Why This Matters:</strong> ${businessValueMap[rec.practice]}
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    });

    html += `</div>`;

    // Always show Validation Summary section when validation data exists
    if (data.validation) {
        let validationMonthsText = `Month ${formatMonth(data.validation.next_month)}`;
        if (data.validation.month_after) {
            validationMonthsText += `, ${formatMonth(data.validation.month_after)}`;
        }
        if (data.validation.month_after_2) {
            validationMonthsText += `, and ${formatMonth(data.validation.month_after_2)}`;
        }
        
        html += `
            <div class="validation-summary">
                <h4>Validation Summary (${validationMonthsText}):</h4>
                <p><strong>Practices that improved:</strong> ${data.validation.actual_improvements ? data.validation.actual_improvements.length : 0}</p>
        `;

        // Show improvements list if any improvements occurred
        if (data.validation.actual_improvements && data.validation.actual_improvements.length > 0) {
            html += `
                <ul class="improvements-list">
            `;

            data.validation.actual_improvements.forEach(imp => {
                const wasRecommended = data.recommendations.some(r => r.practice === imp.practice);
                const status = wasRecommended ? 'Recommended' : 'Not recommended';
                let improvedInText = '';
                if (imp.improved_in && imp.improved_in.length === 3) {
                    improvedInText = ` (improved in ${formatMonth(imp.improved_in[0])}, ${formatMonth(imp.improved_in[1])}, AND ${formatMonth(imp.improved_in[2])})`;
                } else if (imp.improved_in && imp.improved_in.length === 2) {
                    improvedInText = ` (improved in ${formatMonth(imp.improved_in[0])} AND ${formatMonth(imp.improved_in[1])})`;
                } else if (imp.improved_in && imp.improved_in.length === 1) {
                    improvedInText = ` (improved in ${formatMonth(imp.improved_in[0])})`;
                }
                html += `
                    <li>
                        <strong>${imp.practice}:</strong> +${imp.improvement_pct.toFixed(1)}%${improvedInText} ${status}
                    </li>
                `;
            });

            html += `
                </ul>
            `;
        } else {
            // No improvements occurred - show clear message
            html += `
                <p style="color: #856404; font-style: italic; margin-top: 8px;">
                    No practices improved in the validation window (${validationMonthsText}).
                </p>
            `;
        }
        
        // Show accuracy based on what happened
        if (data.validation.accuracy !== null && data.validation.accuracy !== undefined) {
            // Accuracy was calculated (both improvements and recommendations exist)
            html += `
                <p class="accuracy-info" style="margin-top: 15px;">
                    <strong>Recommendation Accuracy:</strong> ${data.validation.validated_count}/${data.validation.total_recommendations} = ${(data.validation.accuracy * 100).toFixed(1)}%
                </p>
            `;
        } else if (data.validation.total_recommendations === 0) {
            // Improvements occurred but no recommendations were generated
            html += `
                <p class="accuracy-info" style="color: #666; font-style: italic; margin-top: 15px;">
                    <strong>Recommendation Accuracy:</strong> Not calculated (no recommendations were generated)
                </p>
                <p style="color: #666; font-size: 0.9em; margin-top: 8px;">
                    Note: The system couldn't generate recommendations (all practices may be at max level, or no similar teams/sequences found).
                </p>
            `;
        } else {
            // No improvements occurred (but recommendations were generated)
            html += `
                <p class="accuracy-info" style="color: #666; font-style: italic; margin-top: 15px;">
                    <strong>Recommendation Accuracy:</strong> Not calculated (no improvements occurred in validation window)
                </p>
                <p style="color: #666; font-size: 0.9em; margin-top: 8px;">
                    Note: This is not a model failure - it just means the team didn't improve anything in the validation window.
                </p>
            `;
        }
        
        html += `
            </div>
        `;
    }

    // Display practice maturity profile
    if (data.practice_profile) {
        html += `
            <div class="practice-profile">
                <h4>Current Practice Maturity Profile</h4>
        `;
        
        const levels = [
            { key: 'level_0', name: 'Not implemented', num: 0 },
            { key: 'level_1', name: 'Basic level', num: 1 },
            { key: 'level_2', name: 'Intermediate level', num: 2 },
            { key: 'level_3', name: 'Advanced level', num: 3 }
        ];
        
        levels.forEach(level => {
            const practices = data.practice_profile[level.key] || [];
            if (practices.length > 0) {
                const totalPractices = Object.values(data.practice_profile).flat().length;
                const percentage = totalPractices > 0 ? (practices.length / totalPractices) * 100 : 0;
                const levelPercentage = (level.num / 3) * 100;

                html += `
                    <div class="practice-level">
                        <h5>Level ${level.num} (${level.name}): ${practices.length} practices</h5>
                        <div class="maturity-bar-container" style="background: #e0e0e0; border-radius: 4px; height: 8px; margin: 10px 0;">
                            <div class="maturity-bar-fill" style="background: linear-gradient(90deg, #f59e0b, #d97706); width: ${levelPercentage}%; height: 100%; border-radius: 4px;"></div>
                        </div>
                        <div class="practice-list">${practices.join(', ')}</div>
                    </div>
                `;
            }
        });
        
        html += `
            </div>
        `;
    }

    resultsDiv.innerHTML = html;
}

/**
 * Run backtest
 */
/**
 * Get configuration from UI controls
 */
function getBacktestConfig() {
    return {
        top_n: parseInt(document.getElementById('config-top-n').value) || 2,
        k_similar: parseInt(document.getElementById('config-k-similar').value) || 19,
        similarity_weight: parseFloat(document.getElementById('config-similarity-weight').value) || 0.6,
        similar_teams_lookahead_months: parseInt(document.getElementById('config-lookahead-months').value) || 3,
        recent_improvements_months: parseInt(document.getElementById('config-recent-months').value) || 3,
        min_similarity_threshold: parseFloat(document.getElementById('config-min-similarity').value) || 0.75
    };
}

/**
 * Toggle configuration section visibility
 */
function toggleConfigSection(sectionId) {
    const section = document.getElementById(sectionId);
    const toggle = document.getElementById(sectionId + '-toggle');
    
    if (section.style.display === 'none') {
        section.style.display = 'block';
        toggle.textContent = '▼';
    } else {
        section.style.display = 'none';
        toggle.textContent = '▶';
    }
}

async function runBacktest() {
    const resultsDiv = document.getElementById('backtest-results');
    resultsDiv.classList.add('hidden');
    showLoading(true);

    try {
        console.log('Running backtest validation...');
        const config = getBacktestConfig();
        console.log('Backtest validation config:', config);
        const data = await apiClient.runBacktest(null, config);
        console.log('Backtest validation response:', data);
        
        // Validate response structure
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid response from backtest validation API');
        }
        
        if (!data.per_month_results) {
            console.warn('Warning: per_month_results missing from response');
        }
        
        displayBacktestResults(data);
    } catch (error) {
        console.error('Error running backtest validation:', error);
        showError(`Failed to run backtest validation: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

/**
 * Display backtest results
 */
/**
 * Renders one column of the "Supplementary Rank-Aware Metrics" panel: model value vs.
 * random baseline vs. improvement factor, for a single metric (Precision@N, Recall@N, or MRR).
 * @param {string} label - Metric name shown as the column heading.
 * @param {number} modelValue - Model's overall value for this metric (0-1).
 * @param {number} baselineValue - Matching random-baseline value for this metric (0-1).
 * @param {number} factor - modelValue / baselineValue, as already computed by the API.
 * @param {string} tipText - Tooltip explaining the metric.
 * @returns {string} HTML string for one metric column.
 */
function renderRankMetricCard(label, modelValue, baselineValue, factor, tipText) {
    const isMrr = label === 'MRR';
    const formatValue = (v) => isMrr ? (v || 0).toFixed(2) : `${((v || 0) * 100).toFixed(1)}%`;
    const color = (modelValue || 0) >= (baselineValue || 0) ? '#28a745' : '#dc3545';
    return `
        <div style="text-align: center; flex: 1; min-width: 140px;">
            <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">${label} ${tip(tipText)}</div>
            <div style="font-size: 1.8em; font-weight: bold; color: #f59e0b;">${formatValue(modelValue)}</div>
            <div style="font-size: 0.8em; color: #8a8785; margin-top: 4px;">vs random ${formatValue(baselineValue)}</div>
            <div style="font-size: 0.95em; font-weight: bold; color: ${color}; margin-top: 4px;">${(baselineValue || 0) > 0 ? (factor || 0).toFixed(2) + '×' : '—'}</div>
        </div>
    `;
}

function displayBacktestResults(data) {
    const resultsDiv = document.getElementById('backtest-results');
    resultsDiv.classList.remove('hidden');

    // Validate required fields
    if (!data.total_predictions && data.total_predictions !== 0) {
        console.error('Missing total_predictions in backtest validation results');
        showError('Could not display backtest results. Please try again.');
        return;
    }

    // Build per-month results table
    let perMonthTable = '';
    if (data.per_month_results && Array.isArray(data.per_month_results) && data.per_month_results.length > 0) {
        perMonthTable = `
            <div class="per-month-results" style="margin-top: 30px;">
                <h4>Per-Month Results</h4>
                <div class="table-outer">
                <table class="results-table" style="width: 100%;">
                    <thead>
                        <tr>
                            <th>Month ${tip('The month being predicted. The model uses only data from prior months to make predictions for this month.')}</th>
                            <th>Training Months ${tip('Historical months the model trained on before predicting this month. Grows with each row as more history becomes available.')}</th>
                            <th>Predictions ${tip('Total practice recommendations generated across all tested teams for this month. Each team receives top-N recommendations.')}</th>
                            <th>Correct ${tip('Recommendations that matched an actual practice improvement made by the team within the 3-month validation window following this month.')}</th>
                            <th>Monthly Accuracy ${tip('Correct ÷ Predictions for this month only. The Overall Accuracy shown above is the simple average of this column — each month counted equally, regardless of how many teams it had.')}</th>
                            <th>Popularity Baseline ${tip('Accuracy of a naive heuristic that always recommends the top-N globally most-improved practices (learned from the same past months as the model), ignoring the target team\'s own state. A stronger sanity check than random selection.')}</th>
                            <th>Precision@N ${tip('Correct recommendations ÷ recommendations made (top_n). Unlike Monthly Accuracy, this is penalized when only some of the N recommendations were right. Higher = fewer wasted suggestions.')}</th>
                            <th>Recall@N ${tip('Correct recommendations ÷ practices actually improved. Capped at top_n ÷ actual improvements, so a low value can reflect that cap rather than a weaker model. Higher = better coverage of what teams actually improved.')}</th>
                            <th>MRR ${tip('Mean Reciprocal Rank: 1.0 if the first recommendation was correct, 0.5 if the second was the first hit, 0 if none were correct. Rewards ranking the right answer first. Higher = correct answer ranks closer to the top.')}</th>
                            <th>Teams Tested ${tip('Teams that had at least one improvement in the 3-month validation window. Teams with zero improvements are excluded - their absence is not a model failure.')}</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        data.per_month_results.forEach(r => {
            const trainRange = (r.train_months && r.train_months.length > 0)
                ? `${formatMonth(r.train_months[0])} to ${formatMonth(r.train_months[r.train_months.length - 1])}`
                : 'N/A';
            perMonthTable += `
                        <tr>
                            <td><strong>${formatMonth(r.month || 0)}</strong></td>
                            <td>${(r.train_months || []).length} months<br><small>${trainRange}</small></td>
                            <td>${r.predictions || 0}</td>
                            <td>${r.correct || 0}</td>
                            <td><strong>${((r.accuracy || 0) * 100).toFixed(1)}%</strong></td>
                            <td>${((r.popularity_accuracy || 0) * 100).toFixed(1)}%</td>
                            <td>${((r.precision || 0) * 100).toFixed(1)}%</td>
                            <td>${((r.recall || 0) * 100).toFixed(1)}%</td>
                            <td>${(r.mrr || 0).toFixed(2)}</td>
                            <td>${r.teams_tested || 0}</td>
                        </tr>
            `;
        });

        const totalPredictions = data.total_predictions || 0;
        const totalCorrect = data.correct_predictions || 0;
        const rawRatio = totalPredictions > 0 ? (totalCorrect / totalPredictions * 100).toFixed(1) : '—';
        const overallAvg = ((data.overall_accuracy || 0) * 100).toFixed(1);
        const overallPopularityAvg = ((data.overall_popularity_baseline || 0) * 100).toFixed(1);
        const overallPrecisionAvg = ((data.overall_precision || 0) * 100).toFixed(1);
        const overallRecallAvg = ((data.overall_recall || 0) * 100).toFixed(1);
        const overallMrrAvg = (data.overall_mrr || 0).toFixed(2);
        const totalTeamsTested = data.per_month_results.reduce((sum, r) => sum + (r.teams_tested || 0), 0);

        perMonthTable += `
                        <tr style="border-top: 2px solid var(--primary-500); background: rgba(245,158,11,0.06);">
                            <td><strong>Total</strong></td>
                            <td style="color: #8a8785; text-align: center;">—</td>
                            <td><strong>${totalPredictions}</strong></td>
                            <td><strong>${totalCorrect}</strong></td>
                            <td>
                                <strong style="color: var(--primary-500);">${overallAvg}%</strong>
                                <span style="color: #8a8785; font-size: 0.78em; margin-left: 4px;">avg of above</span>
                                <div style="font-size: 0.8em; color: #8a8785; margin-top: 2px;">${rawRatio}% if ${totalCorrect}÷${totalPredictions}</div>
                            </td>
                            <td><strong>${overallPopularityAvg}%</strong></td>
                            <td><strong>${overallPrecisionAvg}%</strong></td>
                            <td><strong>${overallRecallAvg}%</strong></td>
                            <td><strong>${overallMrrAvg}</strong></td>
                            <td><strong>${totalTeamsTested}</strong></td>
                        </tr>
        `;

        perMonthTable += `
                    </tbody>
                </table>
                </div>
            </div>
        `;
    }

    // Calculate improvement gap
    const modelAccuracy = (data.overall_accuracy || 0) * 100;
    const randomBaseline = (data.random_baseline || 0) * 100;
    const improvementGap = modelAccuracy - randomBaseline;
    const gapColor = improvementGap > 0 ? '#28a745' : '#dc3545';

    const popularityBaseline = (data.overall_popularity_baseline || 0) * 100;
    const popularityGap = modelAccuracy - popularityBaseline;
    const popularityGapColor = popularityGap > 0 ? '#28a745' : '#dc3545';
    
    const html = `
        <div class="backtest-results">
            <h3>Backtest Validation Results (Rolling Window)</h3>
            
            <!-- Model vs Random Comparison -->
            <div class="accuracy-comparison" style="margin: 30px 0; padding: 20px; background: #1e1d1a; border-radius: 8px; border: 1px solid #3a3835;">
                <h4 style="margin-top: 0; text-align: center;">Model vs Random Baseline</h4>
                <div style="display: flex; justify-content: space-around; align-items: center; margin: 20px 0;">
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Model Accuracy</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #f59e0b;">${modelAccuracy.toFixed(1)}%</div>
                    </div>
                    <div style="font-size: 2em; color: #6b6865;">vs</div>
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Random Baseline</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #a8a5a3;">${randomBaseline.toFixed(1)}%</div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-around; align-items: flex-start; margin-top: 20px; padding-top: 20px; border-top: 1px solid #3a3835; gap: 10px;">
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Improvement Gap</div>
                        <div style="font-size: 3em; font-weight: bold; color: ${gapColor};">${improvementGap > 0 ? '+' : ''}${improvementGap.toFixed(1)}%</div>
                        <div style="font-size: 0.85em; color: #8a8785; margin-top: 5px;">
                            ${improvementGap > 0 ? 'Model beats random by ' + improvementGap.toFixed(1) + ' percentage points' : 'Model underperforms random by ' + Math.abs(improvementGap).toFixed(1) + ' percentage points'}
                        </div>
                    </div>
                    <div style="width: 1px; background: #3a3835; align-self: stretch;"></div>
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Improvement Factor</div>
                        <div style="font-size: 3em; font-weight: bold; color: ${gapColor};">${randomBaseline > 0 ? (modelAccuracy / randomBaseline).toFixed(2) : '—'}×</div>
                        <div style="font-size: 0.85em; color: #8a8785; margin-top: 5px;">
                            ${randomBaseline > 0 ? 'Model is ' + (modelAccuracy / randomBaseline).toFixed(2) + '× more accurate than random' : 'No random baseline available'}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Model vs Popularity Baseline: a naive heuristic that always recommends whatever
                 improves most often organization-wide, ignoring the target team's own state. -->
            <div class="accuracy-comparison" style="margin: 20px 0; padding: 20px; background: #1e1d1a; border-radius: 8px; border: 1px solid #3a3835;">
                <h4 style="margin-top: 0; text-align: center;">
                    Model vs Popularity Baseline
                    ${tip('A stronger sanity check than random selection: this baseline always recommends the top-N practices that improve most often across the whole organization, ignoring the target team\'s own state and history entirely (learned only from months before the prediction, same as the model). Shows how much value the model\'s personalization specifically adds on top of "know the organization\'s general trends."')}
                </h4>
                <div style="display: flex; justify-content: space-around; align-items: center; margin: 20px 0;">
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Model Accuracy</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #f59e0b;">${modelAccuracy.toFixed(1)}%</div>
                    </div>
                    <div style="font-size: 2em; color: #6b6865;">vs</div>
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Popularity Baseline</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #a8a5a3;">${popularityBaseline.toFixed(1)}%</div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-around; align-items: flex-start; margin-top: 20px; padding-top: 20px; border-top: 1px solid #3a3835; gap: 10px;">
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Improvement Gap</div>
                        <div style="font-size: 3em; font-weight: bold; color: ${popularityGapColor};">${popularityGap > 0 ? '+' : ''}${popularityGap.toFixed(1)}%</div>
                        <div style="font-size: 0.85em; color: #8a8785; margin-top: 5px;">
                            ${popularityGap > 0 ? 'Model beats popularity baseline by ' + popularityGap.toFixed(1) + ' percentage points' : 'Model underperforms popularity baseline by ' + Math.abs(popularityGap).toFixed(1) + ' percentage points'}
                        </div>
                    </div>
                    <div style="width: 1px; background: #3a3835; align-self: stretch;"></div>
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Improvement Factor</div>
                        <div style="font-size: 3em; font-weight: bold; color: ${popularityGapColor};">${popularityBaseline > 0 ? (modelAccuracy / popularityBaseline).toFixed(2) : '—'}×</div>
                        <div style="font-size: 0.85em; color: #8a8785; margin-top: 5px;">
                            ${popularityBaseline > 0 ? 'Model is ' + (modelAccuracy / popularityBaseline).toFixed(2) + '× more accurate than the popularity baseline' : 'No popularity baseline available'}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Supplementary rank-aware metrics: Overall Accuracy above is Hit Rate@N (binary
                 hit/miss, ignores rank, full credit for 1-of-N). These three are stricter. -->
            <div class="accuracy-comparison" style="margin: 20px 0; padding: 20px; background: #1e1d1a; border-radius: 8px; border: 1px solid #3a3835;">
                <h4 style="margin-top: 0; text-align: center;">
                    Supplementary Rank-Aware Metrics
                    ${tip('Overall Accuracy above (Hit Rate@N) is a binary hit/miss per case that ignores recommendation order and gives full credit even if only 1 of N recommendations was correct. These three metrics are stricter: Precision@N penalizes wrong picks, Recall@N measures how much of a team\'s actual improvement activity was captured, and MRR rewards ranking the correct answer first.')}
                </h4>
                <div style="display: flex; justify-content: space-around; gap: 16px; flex-wrap: wrap; margin-top: 16px;">
                    ${renderRankMetricCard(
                        'Precision@N',
                        data.overall_precision,
                        data.random_precision,
                        data.precision_improvement_factor,
                        'Correct recommendations ÷ total recommendations made (top_n). Getting 1 of 2 right scores 0.5 here, vs. 1.0 in Overall Accuracy. Higher = fewer wasted suggestions: more of what we recommend actually gets improved.'
                    )}
                    ${renderRankMetricCard(
                        'Recall@N',
                        data.overall_recall,
                        data.random_recall,
                        data.recall_improvement_factor,
                        'Correct recommendations ÷ practices actually improved. Capped at top_n ÷ actual improvements — a low value can reflect that cap, not necessarily a weaker model. Higher = better coverage: more of what the team really improved was on our list.'
                    )}
                    ${renderRankMetricCard(
                        'MRR',
                        data.overall_mrr,
                        data.random_mrr,
                        data.mrr_improvement_factor,
                        'Mean Reciprocal Rank: 1.0 if the top recommendation was correct, 0.5 if the second was the first hit, 0 if none were. Sensitive to ranking order, unlike Overall Accuracy. Higher = the correct answer ranks closer to the top, not buried further down the list.'
                    )}
                </div>
            </div>

            <div style="margin-top: 14px; font-size: 0.82em; color: #6b6865; text-align: center;">
                Rolling-window cross-validation · 87 teams · 35 practices · 10 months · 655 observations · no future data used${tip('Validation approach: time-series rolling window — model trains on past months and predicts on future months it has never seen. Temporal ordering is strictly enforced so no future data leaks into training. Results are compared against a random-selection baseline to establish statistical significance.')}
            </div>

            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-label">Total Predictions${tip('Number of team/month test cases evaluated across all rolling windows where actual improvement data was available.')}</div>
                    <div class="metric-value">${data.total_predictions || 0}</div>
                    <div class="metric-description">team/month combinations</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Correct Predictions${tip('Test cases where at least one recommended practice was actually adopted by the team within the 1–3 months following the prediction.')}</div>
                    <div class="metric-value">${data.correct_predictions || 0}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Overall Accuracy${tip('Macro average: accuracy is computed per month first (correct ÷ total for that month), then those rates are averaged equally across all months. Each month gets the same weight regardless of how many teams were tested — so a month with 2 teams counts the same as a month with 30 teams.')}</div>
                    <div class="metric-value highlight">${modelAccuracy.toFixed(1)}%</div>
                    <div class="metric-description">macro avg · ${data.per_month_results ? data.per_month_results.length : 0} months</div>
                    <div style="font-size:0.82em;color:#8a8785;margin-top:5px;">raw ratio: ${data.total_predictions > 0 ? ((data.correct_predictions / data.total_predictions) * 100).toFixed(1) + '%' : '—'} (${data.correct_predictions || 0} ÷ ${data.total_predictions || 0})${tip('Raw ratio = total correct ÷ total predictions across all months. Differs from the macro average above because months with more teams carry proportionally more weight — the macro average treats every month equally.')}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Random Baseline${tip('Expected accuracy if practices were chosen randomly: top_n ÷ total_practices. Provides the performance floor to beat.')}</div>
                    <div class="metric-value">${randomBaseline.toFixed(1)}%</div>
                    <div class="metric-description">probability of random success</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Improvement Gap${tip('Model accuracy minus the random baseline, in percentage points. Positive value proves the model adds value beyond chance.')}</div>
                    <div class="metric-value" style="color: ${gapColor};">${improvementGap > 0 ? '+' : ''}${improvementGap.toFixed(1)}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Improvement Factor${tip('Model accuracy ÷ random baseline. A 2× factor means the model is twice as likely as random to recommend what a team will actually adopt.')}</div>
                    <div class="metric-value highlight">${(data.improvement_factor || 0).toFixed(1)}x</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Months Tested</div>
                    <div class="metric-value">${data.per_month_results ? data.per_month_results.length : 0}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Avg Improvements/Case ${tip('Average number of practices a team actually improved within the 3-month validation window. Higher values mean more signal for the model to predict against.')}</div>
                    <div class="metric-value">${(data.avg_improvements_per_case || 0).toFixed(1)}</div>
                </div>
            </div>

            ${perMonthTable}
            
            <div class="info-box" style="margin-top: 20px;">
                <strong>What does "Total Predictions" mean?</strong>
                <p>Total Predictions = ${data.total_predictions} <strong>team/month combinations</strong> where:</p>
                <ul>
                    <li>A team had data in a test month</li>
                    <li>The team actually improved at least one practice in that month</li>
                    <li>We generated recommendations for that team/month</li>
                </ul>
                <p><strong>Example:</strong> If Team "Avengers" improved practices in months 20200906 and 20201005, that counts as <strong>2 predictions</strong> (one per month).</p>
            </div>
        </div>
    `;

    resultsDiv.innerHTML = html;
}

// Global variable to track optimization cancellation
let optimizationAbortController = null;

/**
 * Find optimal configuration
 */
async function findOptimalConfig() {
    // Show confirmation dialog before starting
    console.log('findOptimalConfig called - showing confirmation dialog');
    const confirmed = window.confirm('This operation may take up to an hour to complete. Do you want to continue?');
    console.log('Confirmation result:', confirmed);
    if (!confirmed) {
        console.log('User cancelled optimization');
        return; // User cancelled, exit early
    }
    console.log('User confirmed - proceeding with optimization');
    
    const progressDiv = document.getElementById('optimization-progress');
    const resultsDiv = document.getElementById('optimization-results');
    const progressText = document.getElementById('optimization-progress-text');
    const progressBar = document.getElementById('optimization-progress-bar');
    const cancelBtn = document.getElementById('cancel-optimization-btn');
    
    // Hide previous results, show progress
    resultsDiv.classList.add('hidden');
    progressDiv.classList.remove('hidden');
    showLoading(true);
    
    // Enable cancel button
    let cancellationRequested = false;
    if (cancelBtn) {
        cancelBtn.disabled = false;
        cancelBtn.onclick = async () => {
            if (cancellationRequested) return; // Already cancelling
            cancellationRequested = true;
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Cancelling...';
            
            // Request cancellation on server
            // Don't abort the fetch - let server finish current iteration and return partial results
            try {
                await apiClient.cancelOptimization();
                progressText.textContent = 'Cancellation requested. Finishing current test and returning partial results...';
            } catch (e) {
                console.error('Error cancelling optimization:', e);
            }
        };
    }
    
    try {
        progressText.textContent = 'Starting optimization...';
        progressBar.style.width = '0%';
        
        // Optimized ranges based on impact analysis:
        // Fixed (non-impactful): similarity_weight=0.6
        // Testing: top_n, k_similar, min_similarity_threshold, recent_improvements_months, similar_teams_lookahead_months
        const ranges = {
            min_accuracy: 0.40,
            top_n_range: [2, 3, 4, 5],
            similarity_weight_range: [0.6],  // Single value since fixed (non-impactful parameter)
            k_similar_range: [15, 19, 20],
            min_similarity_threshold_range: [0, 0.5, 0.75],
            recent_improvements_months_range: [1, 2, 3],
            similar_teams_lookahead_months_range: [1, 2, 3],
            fixed_params: {
                similarity_weight: 0.6,  // Fixed: non-impactful parameter (0.6-0.8 produce same results)
            }
        };
        
        // Calculate total combinations for progress tracking (optimized search space)
        const topNCount = 4; // [2, 3, 4, 5]
        const kSimilarCount = 3; // [15, 19, 20]
        const minSimilarityCount = 3; // [0.0, 0.5, 0.75]
        const recentMonthsCount = 3; // [1, 2, 3]
        const lookaheadMonthsCount = 3; // [1, 2, 3]
        const totalCombinations = topNCount * kSimilarCount * minSimilarityCount * recentMonthsCount * lookaheadMonthsCount;
        
        progressText.textContent = `Testing ${totalCombinations} combinations (Optimized Search: fixed non-impactful params, testing time-based params)...`;
        
        // Run optimization - no timeout, rely on cancellation mechanism for stopping
        const data = await apiClient.findOptimalConfig(ranges);
        
        // Hide progress, show results
        progressDiv.classList.add('hidden');
        resultsDiv.classList.remove('hidden');
        
        // Display results (will handle cancelled/partial results in displayOptimizationResults)
        displayOptimizationResults(data, ranges.min_accuracy);
    } catch (error) {
        console.error('Error finding optimal config:', error);
        
        // Check if it was cancelled
        if (error.name === 'AbortError' || error.message.includes('cancelled')) {
            progressText.textContent = 'Optimization cancelled. No partial results available.';
            // Show cancellation message
            setTimeout(() => {
                progressDiv.classList.add('hidden');
                resultsDiv.classList.remove('hidden');
                resultsDiv.innerHTML = `
                    <div class="info-box" style="background: #fff; border: 2px solid #ffc107; color: #856404;">
                        <h3 style="color: #856404;">Warning: Optimization Cancelled</h3>
                        <p style="color: #856404;">The optimization was cancelled before any results were found.</p>
                        <p style="color: #856404;">Please try again or adjust parameters for a faster search.</p>
                    </div>
                `;
            }, 1000);
        } else {
            progressDiv.classList.add('hidden');
            showError(`Failed to find optimal configuration: ${error.message}`);
        }
    } finally {
        showLoading(false);
        if (cancelBtn) {
            cancelBtn.disabled = true;
            cancelBtn.textContent = 'Cancel Optimization';
        }
    }
}

/**
 * Render paginated configurations table
 */
function renderPaginatedConfigurationsTable(allResults) {
    const pageSize = 10;
    let currentPage = 1;
    const totalPages = Math.ceil(allResults.length / pageSize);
    const wrapper = document.getElementById('configurations-table-wrapper');
    
    if (!wrapper) return;
    
    function renderTable() {
        const startIdx = (currentPage - 1) * pageSize;
        const endIdx = Math.min(startIdx + pageSize, allResults.length);
        const pageResults = allResults.slice(startIdx, endIdx);
        
        let tableHtml = `
            <div class="table-outer">
            <table class="results-table" style="width: 100%;">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>top_n</th>
                        <th>sim_weight</th>
                        <th>k_sim</th>
                        <th>min_sim</th>
                        <th>Accuracy</th>
                        <th>Random</th>
                        <th>Gap</th>
                        <th>Improvement Factor</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        pageResults.forEach((r, idx) => {
            const rank = startIdx + idx + 1;
            tableHtml += `
                <tr>
                    <td><strong>${rank}</strong></td>
                    <td>${r.config.top_n}</td>
                    <td>${r.config.similarity_weight.toFixed(2)}</td>
                    <td>${r.config.k_similar}</td>
                    <td>${r.config.min_similarity_threshold.toFixed(2)}</td>
                    <td>${(r.model_accuracy * 100).toFixed(1)}%</td>
                    <td>${(r.random_baseline * 100).toFixed(1)}%</td>
                    <td style="color: ${r.improvement_gap > 0 ? '#28a745' : '#dc3545'};">
                        ${r.improvement_gap > 0 ? '+' : ''}${(r.improvement_gap * 100).toFixed(1)}%
                    </td>
                    <td>${(r.improvement_factor || 0).toFixed(2)}x</td>
                </tr>
            `;
        });
        
        tableHtml += `
                </tbody>
            </table>
            </div>
        `;
        
        // Pagination controls
        const pageInfo = `Showing ${startIdx + 1}-${endIdx} of ${allResults.length}`;
        const prevDisabled = currentPage === 1 ? 'disabled' : '';
        const nextDisabled = currentPage === totalPages ? 'disabled' : '';
        
        tableHtml += `
            <div style="margin-top: 20px; display: flex; justify-content: space-between; align-items: center;">
                <button id="config-prev-btn" class="btn btn-secondary" ${prevDisabled} style="padding: 8px 15px; ${prevDisabled ? 'opacity: 0.5; cursor: not-allowed;' : ''}">
                    Previous
                </button>
                <span style="font-weight: bold;">${pageInfo}</span>
                <button id="config-next-btn" class="btn btn-secondary" ${nextDisabled} style="padding: 8px 15px; ${nextDisabled ? 'opacity: 0.5; cursor: not-allowed;' : ''}">
                    Next
                </button>
            </div>
        `;
        
        wrapper.innerHTML = tableHtml;
        
        // Add event listeners
        const prevBtn = document.getElementById('config-prev-btn');
        const nextBtn = document.getElementById('config-next-btn');
        
        if (prevBtn && currentPage > 1) {
            prevBtn.addEventListener('click', () => {
                if (currentPage > 1) {
                    currentPage--;
                    renderTable();
                }
            });
        }
        
        if (nextBtn && currentPage < totalPages) {
            nextBtn.addEventListener('click', () => {
                if (currentPage < totalPages) {
                    currentPage++;
                    renderTable();
                }
            });
        }
    }
    
    // Initial render
    renderTable();
}

/**
 * Display optimization results
 */
function displayOptimizationResults(data, minAccuracy = 0.40) {
    const resultsDiv = document.getElementById('optimization-results');
    resultsDiv.classList.remove('hidden');
    
    // Show status message if early stopped or cancelled
    let statusMessage = '';
    if (data.cancelled) {
        statusMessage = '<div class="info-box" style="background: #fff; border: 2px solid #ffc107; color: #856404; margin-bottom: 20px;"><strong style="color: #856404;">Warning: Optimization Cancelled</strong><p style="color: #856404;">Showing best configuration found before cancellation.</p></div>';
    } else if (data.early_stopped) {
        statusMessage = `<div class="info-box" style="background: #d4edda; border-color: #28a745; margin-bottom: 20px;"><strong>Early Stop</strong><p>Found excellent solution (gap: ${(data.improvement_gap * 100).toFixed(1)}%) - stopped early to save time.</p></div>`;
    }
    
    // If cancelled and no optimal config, show what was tested
    if (!data.optimal_config) {
        if (data.cancelled) {
            // Show partial results if any were found
            if (data.all_results && data.all_results.length > 0) {
                // Show best result found before cancellation
                const bestResult = data.all_results[0];
                resultsDiv.innerHTML = `
                    ${statusMessage}
                    <div class="info-box" style="background: #fff; border: 2px solid #ffc107; color: #856404; margin-bottom: 20px;">
                        <h3 style="color: #856404;">Warning: Optimization Cancelled</h3>
                        <p style="color: #856404;">Showing best configuration found before cancellation:</p>
                        <p style="color: #856404;"><strong>Combinations tested:</strong> ${data.total_combinations_tested || 0} / ${data.total_combinations_available || data.total_combinations_tested || 0}</p>
                        <p style="color: #856404;"><strong>Valid combinations:</strong> ${data.valid_combinations || 0}</p>
                    </div>
                    <div class="optimization-results">
                        <h3>Best Configuration Found (Before Cancellation)</h3>
                        <div class="info-box" style="margin: 20px 0;">
                            <h4>Configuration:</h4>
                            <ul>
                                <li><strong>Number of Recommendations:</strong> ${bestResult.config.top_n}</li>
                                <li><strong>Similarity Weight:</strong> ${bestResult.config.similarity_weight.toFixed(2)}</li>
                                <li><strong>Number of Similar Teams:</strong> ${bestResult.config.k_similar}</li>
                                <li><strong>Minimum Similarity Threshold:</strong> ${bestResult.config.min_similarity_threshold.toFixed(2)}</li>
                            </ul>
                            <h4>Results:</h4>
                            <ul>
                                <li><strong>Model Accuracy:</strong> ${(bestResult.model_accuracy * 100).toFixed(1)}%</li>
                                <li><strong>Random Baseline:</strong> ${(bestResult.random_baseline * 100).toFixed(1)}%</li>
                                <li><strong>Improvement Gap:</strong> ${(bestResult.improvement_gap * 100).toFixed(1)}%</li>
                            </ul>
                        </div>
                        <button class="btn btn-primary" onclick="applyOptimalConfigFromCancelled(${JSON.stringify(bestResult.config).replace(/"/g, '&quot;')})">Apply This Configuration</button>
                    </div>
                `;
                return;
            } else {
                // No results found before cancellation
                resultsDiv.innerHTML = statusMessage;
                showToast(
                    'Warning: Optimization Cancelled',
                    `The optimization was cancelled before any valid configurations were found.<br>
                     <strong>Combinations tested:</strong> ${data.total_combinations_tested || 0} / ${data.total_combinations_available || data.total_combinations_tested || 0}<br>
                     Please try again or adjust parameters for a faster search.`,
                    'warning'
                );
                return;
            }
        } else {
            // Not cancelled, just no valid configs found
            resultsDiv.innerHTML = statusMessage;
            showToast(
                'Error: No Optimal Configuration Found',
                `No configuration met the minimum accuracy threshold of ${Math.round((minAccuracy || 0.40) * 100)}%.<br>
                 <strong>Combinations tested:</strong> ${data.total_combinations_tested || 0} / ${data.total_combinations_available || data.total_combinations_tested || 0}<br>
                 <strong>Valid combinations:</strong> ${data.valid_combinations || 0}`,
                'error'
            );
            return;
        }
    }
    
    const config = data.optimal_config;
    const modelAccuracy = (data.model_accuracy || 0) * 100;
    const randomBaseline = (data.random_baseline || 0) * 100;
    const improvementGap = data.improvement_gap || 0;
    const gapPercent = improvementGap * 100;
    const gapColor = gapPercent > 0 ? '#28a745' : '#dc3545';
    
    const completionPct = data.total_combinations_available > 0 
        ? ((data.total_combinations_tested || 0) / data.total_combinations_available * 100).toFixed(1)
        : '0.0';
    const statusText = data.cancelled 
        ? 'Cancelled (partial results)' 
        : data.early_stopped 
        ? 'Early stopped' 
        : 'Completed';
    const similarityFilterText = config.min_similarity_threshold > 0
        ? `Only consider teams with ≥${(config.min_similarity_threshold * 100).toFixed(0)}% similarity`
        : 'No similarity filter (consider all teams)';
    
    let configHtml = `
        <div style="background: #1e1d1a; padding: 20px; border-radius: 8px; margin: 15px 0; border: 1px solid #3a3835;">
            <h4 style="margin-top: 0;">Optimization Summary</h4>
            <div style="margin-bottom: 15px;">
                <strong>Iterations:</strong> ${data.total_combinations_tested || 0} / ${data.total_combinations_available || 0} tested (${completionPct}%) - ${statusText}
            </div>
            
            <details style="margin-bottom: 15px;">
                <summary style="cursor: pointer; font-weight: bold; margin-bottom: 10px;">Parameter Ranges Tested</summary>
                <div style="margin: 10px 0; padding-left: 20px; font-size: 0.9em;">
                    <p style="font-weight: bold; margin-top: 10px; color: #a8a5a3;">Fixed Parameters (Non-Impactful):</p>
                    <ul style="margin: 5px 0; padding-left: 20px;">
                        <li><strong>Similarity Weight:</strong> 0.6 (fixed) - Analysis showed 0.6-0.8 produce identical results</li>
                    </ul>
                    <p style="font-weight: bold; margin-top: 15px; color: #28a745;">Optimized Ranges Tested:</p>
                    <ul style="margin: 5px 0; padding-left: 20px;">
                        <li><strong>Number of Recommendations:</strong> [2, 3, 4, 5] - Number of recommendations to generate</li>
                        <li><strong>Number of Similar Teams:</strong> [15, 19, 20] - Number of similar teams to consider (impactful parameter)</li>
                        <li><strong>Minimum Similarity Threshold:</strong> [0.0, 0.5, 0.75] - Filter out low-similarity teams (impactful parameter)</li>
                        <li><strong>Months to Check for Recent Improvements:</strong> [1, 2, 3] - How recent improvements must be to trigger sequence boosts</li>
                        <li><strong>Months to Look Ahead for Similar Teams:</strong> [1, 2, 3] - How far ahead to check for improvements</li>
                    </ul>
                    <p style="margin-top: 10px; font-style: italic; color: #8a8785;">Search space: 4 × 3 × 3 × 3 × 3 = 324 combinations (optimized from 540)</p>
                </div>
            </details>
            
            <h4 style="margin-top: 15px;">Optimal Configuration</h4>
            <ul style="margin: 10px 0; padding-left: 20px;">
                <li><strong>Number of Recommendations:</strong> ${config.top_n} - Generate ${config.top_n} recommendations</li>
                <li><strong>Similarity Weight:</strong> ${config.similarity_weight.toFixed(2)} - ${(config.similarity_weight*100).toFixed(0)}% weight on similar teams, ${((1-config.similarity_weight)*100).toFixed(0)}% on sequences</li>
                <li><strong>Number of Similar Teams:</strong> ${config.k_similar} - Consider ${config.k_similar} most similar teams</li>
                <li><strong>Months to Look Ahead for Similar Teams:</strong> ${config.similar_teams_lookahead_months} - Check ${config.similar_teams_lookahead_months} months ahead for improvements</li>
                <li><strong>Months to Check for Recent Improvements:</strong> ${config.recent_improvements_months} - Consider improvements from last ${config.recent_improvements_months} months</li>
                <li><strong>Minimum Similarity Threshold:</strong> ${config.min_similarity_threshold.toFixed(2)} - ${similarityFilterText}</li>
            </ul>
        </div>
    `;
    
    const html = `
        <div class="optimization-results">
            ${statusMessage}
            <h3>Optimal Configuration Found!</h3>
            
            ${configHtml}
            
            <!-- Results Summary -->
            <div class="accuracy-comparison" style="margin: 30px 0; padding: 20px; background: #1e1d1a; border-radius: 8px; border: 1px solid #3a3835;">
                <h4 style="margin-top: 0; text-align: center;">Optimal Configuration Results</h4>
                <div style="display: flex; justify-content: space-around; align-items: center; margin: 20px 0;">
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Model Accuracy</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #f59e0b;">${modelAccuracy.toFixed(1)}%</div>
                    </div>
                    <div style="font-size: 2em; color: #6b6865;">vs</div>
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Random Baseline</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #a8a5a3;">${randomBaseline.toFixed(1)}%</div>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #3a3835;">
                    <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Improvement Gap</div>
                    <div style="font-size: 3em; font-weight: bold; color: ${gapColor};">${gapPercent > 0 ? '+' : ''}${gapPercent.toFixed(1)}%</div>
                    <div style="font-size: 0.85em; color: #8a8785; margin-top: 5px;">
                        ${gapPercent > 0 ? 'Model beats random by ' + gapPercent.toFixed(1) + ' percentage points' : 'Model underperforms random by ' + Math.abs(gapPercent).toFixed(1) + ' percentage points'}
                    </div>
                </div>
            </div>
            
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-label">Combinations Tested</div>
                    <div class="metric-value">${data.total_combinations_tested || 0}</div>
                    <div class="metric-description">of ${data.total_combinations_available || data.total_combinations_tested || 0} total</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Valid Combinations</div>
                    <div class="metric-value">${data.valid_combinations || 0}</div>
                    <div class="metric-description">met 40% accuracy threshold</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Predictions</div>
                    <div class="metric-value">${data.total_predictions || 0}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Correct Predictions</div>
                    <div class="metric-value">${data.correct_predictions || 0}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Improvement Factor</div>
                    <div class="metric-value highlight">${(data.improvement_factor || 0).toFixed(1)}x</div>
                </div>
            </div>
            
            <div style="margin-top: 20px;">
                <button id="apply-optimal-config-btn" class="btn btn-primary" style="width: 100%; margin-bottom: 10px;">
                    Apply This Configuration to Sliders
                </button>
                ${data.results_file ? `
                    <div style="margin-bottom: 10px; padding: 10px; background: #e7f3ff; border: 1px solid #b3d9ff; border-radius: 4px;">
                        <strong>Results saved:</strong> ${data.results_file}
                    </div>
                ` : ''}
                <button id="download-results-btn" class="btn btn-secondary" style="width: 100%; margin-bottom: 10px;">
                    Download Results as JSON
                </button>
                <button id="view-latest-results-btn" class="btn btn-secondary" style="width: 100%;">
                    View Latest Results
                </button>
            </div>
            
            ${data.all_results && data.all_results.length > 1 ? `
                <div id="configurations-table-container" style="margin-top: 30px;">
                    <h4>All ${data.all_results.length} Configurations</h4>
                    <div id="configurations-table-wrapper"></div>
                </div>
            ` : ''}
        </div>
    `;
    
    resultsDiv.innerHTML = html;
    
    // Render paginated configurations table if results exist
    if (data.all_results && data.all_results.length > 1) {
        renderPaginatedConfigurationsTable(data.all_results);
    }
    
    // Add event listener for apply button
    const applyBtn = document.getElementById('apply-optimal-config-btn');
    if (applyBtn) {
        applyBtn.addEventListener('click', () => {
            applyOptimalConfig(config);
        });
    }
    
    // Add event listener for download button
    const downloadBtn = document.getElementById('download-results-btn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', () => {
            downloadResults(data);
        });
    }
    
    // Add event listener for view latest results button
    const viewLatestBtn = document.getElementById('view-latest-results-btn');
    if (viewLatestBtn) {
        viewLatestBtn.addEventListener('click', async () => {
            await viewLatestResults();
        });
    }
}

/**
 * Download optimization results as JSON file
 */
function downloadResults(data) {
    try {
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const filename = `optimization_results_${timestamp}.json`;
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        console.error('Error downloading results:', error);
        showError('Failed to download results');
    }
}

/**
 * Upload and display optimization results from JSON file
 */
async function uploadResults(file) {
    const resultsDiv = document.getElementById('optimization-results');
    resultsDiv.classList.remove('hidden');
    showLoading(true);
    
    try {
        // Read file as text
        const text = await file.text();
        
        // Parse JSON
        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            throw new Error('Invalid JSON file. Please select a valid optimization results JSON file.');
        }
        
        // Validate required fields
        if (!data.optimal_config && !data.all_results) {
            throw new Error('Invalid optimization results file. Missing required fields.');
        }
        
        // Display results using existing function
        displayOptimizationResults(data);
    } catch (error) {
        console.error('Error uploading results:', error);
        showError(`Failed to upload results: ${error.message}`);
        resultsDiv.innerHTML = `
            <div class="error" style="padding: 20px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px;">
                <h3>Error: Failed to Upload Results</h3>
                <p>${error.message}</p>
                <p>Please ensure you're uploading a valid optimization results JSON file.</p>
            </div>
        `;
    } finally {
        showLoading(false);
    }
}

/**
 * View latest optimization results
 */
async function viewLatestResults() {
    const resultsDiv = document.getElementById('optimization-results');
    resultsDiv.classList.remove('hidden');
    showLoading(true);
    
    try {
        const data = await apiClient.getLatestOptimizationResults();
        displayOptimizationResults(data);
    } catch (error) {
        console.error('Error loading latest results:', error);
        if (error.message && error.message.includes('404')) {
            resultsDiv.innerHTML = `
                <div class="info-box" style="background: #fff; border: 2px solid #ffc107; color: #856404;">
                    <h3 style="color: #856404;">Warning: No Results Found</h3>
                    <p style="color: #856404;">No optimization results have been saved yet. Please run an optimization first.</p>
                </div>
            `;
        } else {
            showError(`Failed to load latest results: ${error.message}`);
        }
    } finally {
        showLoading(false);
    }
}

/**
 * Apply optimal configuration from cancelled optimization (handles string parsing)
 */
function applyOptimalConfigFromCancelled(configStr) {
    try {
        const config = typeof configStr === 'string' ? JSON.parse(configStr.replace(/&quot;/g, '"')) : configStr;
        applyOptimalConfig(config);
    } catch (e) {
        console.error('Error parsing config:', e);
        showError('Failed to apply configuration');
    }
}

/**
 * Apply optimal configuration to sliders
 */
function applyOptimalConfig(config) {
    // Update all sliders to match optimal config
    const sliders = {
        'config-top-n': config.top_n,
        'config-similarity-weight': config.similarity_weight,
        'config-k-similar': config.k_similar,
        'config-lookahead-months': config.similar_teams_lookahead_months,
        'config-recent-months': config.recent_improvements_months,
        'config-min-similarity': config.min_similarity_threshold
    };
    
    for (const [id, value] of Object.entries(sliders)) {
        const slider = document.getElementById(id);
        if (slider) {
            slider.value = value;
            // Trigger input event to update displayed values
            slider.dispatchEvent(new Event('input'));
        }
    }
    
    // Show success message
    const resultsDiv = document.getElementById('optimization-results');
    const successMsg = document.createElement('div');
    successMsg.style.cssText = 'margin-top: 15px; padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; color: #155724;';
    successMsg.textContent = 'Configuration applied to sliders! You can now run backtest validation with these settings.';
    resultsDiv.appendChild(successMsg);
    
    // Scroll to top of backtest tab
    document.getElementById('backtest-tab').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Load statistics
 */
async function loadStatistics() {
    const resultsDiv = document.getElementById('stats-results');
    if (!resultsDiv) {
        console.error('stats-results div not found');
        return;
    }
    
    resultsDiv.classList.add('hidden');
    showLoading(true);

    try {
        console.log('Loading statistics...');
        const data = await apiClient.getSystemStats();
        console.log('Statistics response:', data);
        
        // Validate response structure
        if (!data || typeof data !== 'object') {
            throw new Error('Could not load statistics. Please refresh the page.');
        }

        // Check for required fields
        if (typeof data.num_teams !== 'number') {
            console.error('Missing num_teams in response:', data);
            throw new Error('Could not load statistics. Please refresh the page.');
        }

        if (typeof data.num_practices !== 'number') {
            console.error('Missing num_practices in response:', data);
            throw new Error('Could not load statistics. Please refresh the page.');
        }
        
        // Ensure arrays exist
        if (!Array.isArray(data.months)) {
            console.warn('months is not an array, defaulting to empty array');
            data.months = [];
        }
        
        if (!Array.isArray(data.practices)) {
            console.warn('practices is not an array, defaulting to empty array');
            data.practices = [];
        }
        
        displayStatistics(data);
    } catch (error) {
        console.error('Error loading statistics:', error);
        const errorMsg = error.message || 'Unknown error occurred';
        showError(`Failed to load statistics: ${errorMsg}`);
        
        // Show error in the results div
        resultsDiv.classList.remove('hidden');
        resultsDiv.innerHTML = `
            <div class="error" style="padding: 20px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px;">
                <h3>Error Loading Statistics</h3>
                <p>${errorMsg}</p>
                <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                    Please check the browser console for more details or try refreshing the page.
                </p>
            </div>
        `;
    } finally {
        showLoading(false);
    }
}

/**
 * Display statistics
 */
function displayStatistics(data) {
    const resultsDiv = document.getElementById('stats-results');
    if (!resultsDiv) {
        console.error('stats-results div not found');
        return;
    }
    
    resultsDiv.classList.remove('hidden');

    // Validate required fields
    if (typeof data.num_teams !== 'number' || typeof data.num_practices !== 'number') {
        console.error('Missing required fields in statistics data:', data);
        showError('Could not load statistics. Please refresh the page.');
        resultsDiv.innerHTML = `
            <div class="error" style="padding: 20px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px;">
                <h3>Could not load statistics</h3>
                <p>Please refresh the page to try again.</p>
            </div>
        `;
        return;
    }
    
    // Ensure arrays exist with defaults
    const months = Array.isArray(data.months) ? data.months : [];
    const practices = Array.isArray(data.practices) ? data.practices : [];
    const practiceDefinitions = data.practice_definitions || {};
    const practiceRemarks = data.practice_remarks || {};

    const html = `
        <div class="stats-results">
            <h3>System Statistics</h3>
            
            <div class="stats-grid">
                <div class="stat-item">
                    <strong>Total Teams:</strong> ${data.num_teams || 0}
                </div>
                <div class="stat-item">
                    <strong>Total Practices:</strong> ${data.num_practices || 0}
                </div>
                <div class="stat-item">
                    <strong>Total Months:</strong> ${data.num_months || 0}
                </div>
                <div class="stat-item">
                    <strong>Total Observations:</strong>${tip('Total team × practice × month data points in the dataset. Each observation is one maturity score for one team in one month.')} ${(data.total_observations || 0).toLocaleString()}
                </div>
            </div>

            <div class="stats-section">
                <h4>Months (${months.length} total):</h4>
                ${months.length > 0 ? `
                    <div class="months-grid">
                        ${months.map(m => {
                            const formatted = formatMonth(m);
                            return `<span class="month-badge" title="${formatted}">${formatted}</span>`;
                        }).join('')}
                    </div>
                ` : '<p style="color: #666; font-style: italic;">No months available</p>'}
            </div>

            <div class="stats-section">
                <h4>Practices:</h4>
                <div class="practices-list">
                    ${practices.length > 0 ? practices.map(practice => {
                        const definitions = practiceDefinitions[practice];
                        const remarks = practiceRemarks[practice];
                        
                        if (definitions) {
                            // Practice with definitions - make it expandable
                            const levelNames = {0: 'Level 0 (Not implemented)', 1: 'Level 1 (Basic)', 2: 'Level 2 (Intermediate)', 3: 'Level 3 (Mature)'};
                            let levelsHtml = '';
                            for (const level of [0, 1, 2, 3]) {
                                if (definitions[level]) {
                                    levelsHtml += `
                                        <div style="margin: 8px 0; padding-left: 20px;">
                                            <strong>${levelNames[level]}:</strong> ${definitions[level]}
                                        </div>
                                    `;
                                }
                            }
                            
                            let remarksHtml = '';
                            if (remarks) {
                                remarksHtml = `
                                    <div style="margin-top: 10px; padding: 8px; background: #1a1916; border-left: 3px solid #f59e0b; font-size: 0.9em;">
                                        <strong>Remarks:</strong> ${remarks.replace(/\n/g, '<br>')}
                                    </div>
                                `;
                            }
                            
                            return `
                                <details class="practice-item" style="margin: 10px 0; padding: 10px; border: 1px solid #3a3835; border-radius: 4px;">
                                    <summary class="practice-summary">
                                        ${practice}
                                        <span style="color: #6b6865; font-size: 0.85em; font-weight: normal;"> (click to expand/collapse)</span>
                                    </summary>
                                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #3a3835;">
                                        <h5 style="margin-top: 0; color: #e8e5e2;">Level Definitions:</h5>
                                        ${levelsHtml}
                                        ${remarksHtml}
                                    </div>
                                </details>
                            `;
                        } else {
                            // Practice without definitions - simple list item
                            return `<div style="margin: 5px 0; padding: 5px;">${practice}</div>`;
                        }
                    }).join('') : '<p style="color: #666; font-style: italic;">No practices available</p>'}
                </div>
            </div>

            ${data.missing_values && data.missing_values.total_missing > 0 ? (() => {
                const mv = data.missing_values;
                const totalCells = data.total_observations * data.num_practices;
                const completeness = totalCells > 0 ? ((totalCells - mv.total_missing) / totalCells * 100).toFixed(1) : null;

                const topPractice = mv.practices_with_missing && mv.practices_with_missing[0];
                const topInfo = topPractice ? mv.by_practice[topPractice] : null;
                const topShare = topInfo ? Math.round(topInfo.count / mv.total_missing * 100) : 0;
                const otherPractices = mv.practices_with_missing ? mv.practices_with_missing.slice(1) : [];
                const maxOtherPct = otherPractices.length > 0
                    ? Math.max(...otherPractices.map(p => parseFloat(mv.by_practice[p].percentage))).toFixed(1)
                    : null;

                return `
            <div class="stats-section missing-values-section">
                <h4>Data Completeness${tip('Missing values occur when a practice score wasn\'t recorded for a team in a given month. These are excluded from training rather than imputed.')}</h4>
                <div class="missing-values-summary">
                    ${completeness !== null ? `<p><strong>Overall completeness:</strong> ${completeness}%</p>` : ''}
                    ${topShare >= 80 && topPractice ? `<p class="missing-outlier-note">${topShare}% of missing values come from a single practice (<em>${topPractice}</em>)${maxOtherPct !== null ? `; all others ≤ ${maxOtherPct}%` : ''}.</p>` : ''}
                </div>

                ${mv.practices_with_missing && mv.practices_with_missing.length > 0 ? `
                <details class="missing-values-details">
                    <summary>Practices with Missing Values (${mv.practices_with_missing.length})</summary>
                    <div class="missing-practices-list">
                        ${mv.practices_with_missing.slice(0, 10).map(practice => {
                            const info = mv.by_practice[practice];
                            const monthsAffected = info.by_month ? Object.keys(info.by_month).length : null;
                            const label = monthsAffected !== null
                                ? `not recorded in ${monthsAffected} of ${data.num_months} months`
                                : `${info.count} missing (${info.percentage}%)`;
                            return `<div class="missing-item">
                                <strong>${practice}:</strong> ${label}
                            </div>`;
                        }).join('')}
                        ${mv.practices_with_missing.length > 10 ?
                            `<div class="missing-item">... and ${mv.practices_with_missing.length - 10} more</div>` : ''}
                    </div>
                </details>
                ` : ''}

                ${mv.months_with_missing && mv.months_with_missing.length > 0 ? `
                <details class="missing-values-details">
                    <summary>Months with Missing Values (${mv.months_with_missing.length})</summary>
                    <div class="missing-months-list">
                        ${mv.months_with_missing.slice(0, 10).map(month => {
                            const info = mv.by_month[month];
                            return `<div class="missing-item">
                                <strong>${formatMonth(month)}:</strong> ${info.count} missing (${info.percentage}%)
                            </div>`;
                        }).join('')}
                        ${mv.months_with_missing.length > 10 ?
                            `<div class="missing-item">... and ${mv.months_with_missing.length - 10} more</div>` : ''}
                    </div>
                </details>
                ` : ''}
            </div>
            `;
            })() : ''}
        </div>
    `;

    resultsDiv.innerHTML = html;
}

/**
 * Format month (yyyymmdd) for display
 */
function formatMonth(month) {
    const monthStr = month.toString();
    if (monthStr.length === 8) {
        const year = monthStr.substring(0, 4);
        const monthNum = monthStr.substring(4, 6);
        const day = monthStr.substring(6, 8);
        return `${year}-${monthNum}-${day}`;
    }
    return monthStr;
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.classList.remove('hidden');
    } else {
        loading.classList.add('hidden');
    }
}

/**
 * Load and display improvement sequences
 */
async function loadSequences() {
    const resultsDiv = document.getElementById('sequences-results');
    resultsDiv.classList.add('hidden');
    showLoading(true);
    
    try {
        console.log('Loading sequences...');
        const data = await apiClient.getImprovementSequences();
        console.log('Sequences response:', data);
        
        // Validate response structure
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid response from sequences API');
        }
        
        if (!data.sequences && !data.grouped_sequences) {
            console.warn('Warning: sequences or grouped_sequences missing from response');
        }
        
        displaySequences(data);
    } catch (error) {
        console.error('Error loading sequences:', error);
        showError(`Failed to load sequences: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

/**
 * Display improvement sequences
 */
function displaySequences(data) {
    const resultsDiv = document.getElementById('sequences-results');
    resultsDiv.classList.remove('hidden');
    
    // Validate required fields
    if (!data.stats && !data.grouped_sequences) {
        console.error('Missing required fields in sequences data');
        showError('Could not load sequences. Please refresh the page.');
        return;
    }
    
    const stats = data.stats || {};
    const grouped = data.grouped_sequences || {};
    
    // Store original data for filtering
    window.sequencesData = { stats, grouped };
    
    // Sort practices by total transitions
    const sortedPractices = Object.keys(grouped).sort((a, b) => {
        const totalA = grouped[a].reduce((sum, t) => sum + t.count, 0);
        const totalB = grouped[b].reduce((sum, t) => sum + t.count, 0);
        return totalB - totalA;
    });
    
    let html = `
        <div class="sequences-results">
            <h3>Improvement Sequences Overview</h3>
            
            <div class="stats-grid" style="margin-bottom: 20px;">
                <div class="stat-item">
                    <strong>Total Transition Patterns:</strong>${tip('Number of unique practice-A → practice-B pairs learned. Each pair is one distinct Markov transition rule.')} ${stats.num_transition_types || 0}
                </div>
                <div class="stat-item">
                    <strong>Total Transitions Observed:</strong>${tip('Raw co-improvement event count summed across all teams and months. More observations = higher confidence in transition probabilities.')} ${stats.total_transitions || 0}
                </div>
                <div class="stat-item">
                    <strong>Practices That Improved:</strong> ${stats.practices_that_improved || 0}
                </div>
                <div class="stat-item">
                    <strong>Total Sequences:</strong> ${data.total_sequences || 0}
                </div>
            </div>
            
            <div class="info-box" style="margin-bottom: 20px;">
                <strong>What these patterns mean</strong>
                <p>Each row shows how often teams that improved Practice A also improved Practice B in the same month. Probability reflects how consistently this co-occurrence appears across all 87 teams.</p>
                <p>These sequences contribute <strong>30% of the recommendation score</strong> — the rest comes from similar-team behavior.</p>
            </div>
            
            <div style="margin-bottom: 20px; display: flex; gap: 10px;">
                <button id="expand-all-sequences" class="btn btn-secondary" style="padding: 8px 15px; font-size: 0.9em;">Expand All</button>
                <button id="collapse-all-sequences" class="btn btn-secondary" style="padding: 8px 15px; font-size: 0.9em;">Collapse All</button>
            </div>
            
            <h4 style="margin-top: 30px;">Improvement Sequences (sorted by frequency) — ${sortedPractices.length} practices:</h4>
            <div id="sequences-list">
    `;
    
    // Generate sequence groups with collapsible sections - show all practices
    html += generateSequenceGroups(sortedPractices, grouped);
    
    html += `
            </div>
            
        </div>
    `;
    
    resultsDiv.innerHTML = html;
    
    // Attach event listeners for expand/collapse controls
    attachSequenceControls();
}

/**
 * Generate sequence groups HTML with collapsible sections
 */
function generateSequenceGroups(sortedPractices, grouped) {
    let html = '';

    sortedPractices.forEach((fromPractice, index) => {
        const transitions = grouped[fromPractice].sort((a, b) => b.count - a.count);
        const avgProb = transitions.reduce((sum, t) => sum + t.probability, 0) / transitions.length;

        html += `
            <details class="sequence-group" data-practice="${fromPractice}">
                <summary class="sequence-summary">
                    <span class="sequence-arrow">▶</span>
                    <span class="sequence-index">${index + 1}.</span>
                    <span>When '<strong>${fromPractice}</strong>' improved:</span>
                    <span class="sequence-summary-stats">${transitions.length} transitions, avg ${(avgProb * 100).toFixed(1)}% probability</span>
                </summary>
                <ul class="sequence-transitions">
        `;
        
        for (const transition of transitions) {
            const probClass = transition.probability >= 0.6 ? 'sequence-prob-high' 
                           : transition.probability >= 0.3 ? 'sequence-prob-medium' 
                           : 'sequence-prob-low';
            
            html += `
                <li class="sequence-transition ${probClass}" data-prob="${transition.probability}" data-count="${transition.count}" data-to-practice="${transition.to_practice}">
                    <span class="sequence-arrow-visual">→</span>
                    <strong>${transition.to_practice}</strong>
                    <span class="sequence-meta">
                        <span class="sequence-count">${transition.count} times</span>
                        <span class="sequence-prob-text">${(transition.probability * 100).toFixed(1)}%${tip('Bar color: green ≥ 60%, amber 30–59%, gray < 30%. Higher probability = more frequently observed co-improvement across all teams.')}</span>
                        <div class="probability-bar">
                            <div class="probability-fill ${probClass}" style="width: ${transition.probability * 100}%"></div>
                        </div>
                    </span>
                </li>
            `;
        }
        
        html += `
                </ul>
            </details>
        `;
    });

    return html;
}

/**
 * Attach event listeners for sequence expand/collapse controls
 */
function attachSequenceControls() {
    const expandAllBtn = document.getElementById('expand-all-sequences');
    const collapseAllBtn = document.getElementById('collapse-all-sequences');
    
    // Expand all sequences
    if (expandAllBtn) {
        expandAllBtn.addEventListener('click', () => {
            document.querySelectorAll('.sequence-group').forEach(details => {
                details.open = true;
            });
        });
    }
    
    // Collapse all sequences
    if (collapseAllBtn) {
        collapseAllBtn.addEventListener('click', () => {
            document.querySelectorAll('.sequence-group').forEach(details => {
                details.open = false;
            });
        });
    }
}

// ============================================
//   EXAMPLE DATA MODAL
// ============================================

function openExampleModal() {
    const overlay = document.getElementById('example-modal');
    const body = document.getElementById('modal-body');
    const note = document.getElementById('modal-row-note');

    body.innerHTML = '<div class="modal-loading"><div class="spinner"></div><p>Loading dataset…</p></div>';
    note.textContent = '';
    overlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    fetch('/api/example-data')
        .then(r => {
            if (!r.ok) throw new Error(`Server returned ${r.status}`);
            return r.arrayBuffer();
        })
        .then(buf => {
            const wb = XLSX.read(new Uint8Array(buf), { type: 'array' });
            const sheetName = wb.SheetNames[0];
            const ws = wb.Sheets[sheetName];
            const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });

            if (!rows.length) {
                body.innerHTML = '<div class="modal-error">No data found in file.</div>';
                return;
            }

            const headers = rows[0];
            const dataRows = rows.slice(1);
            const MAX_ROWS = 100;
            const display = dataRows.slice(0, MAX_ROWS);

            note.textContent = `Sheet: ${sheetName}  ·  Showing ${display.length} of ${dataRows.length} rows  ·  ${headers.length} columns  ·  Read-only preview`;

            const thead = headers.map(h => `<th>${escapeHtml(String(h ?? ''))}</th>`).join('');
            const tbody = display.map(row => {
                const cells = headers.map((_, i) => `<td>${escapeHtml(String(row[i] ?? ''))}</td>`).join('');
                return `<tr>${cells}</tr>`;
            }).join('');

            body.innerHTML = `
                <div class="excel-table-wrap">
                    <table class="excel-table">
                        <thead><tr>${thead}</tr></thead>
                        <tbody>${tbody}</tbody>
                    </table>
                </div>`;
        })
        .catch(err => {
            body.innerHTML = `<div class="modal-error">Failed to load dataset: ${escapeHtml(err.message)}</div>`;
        });
}

function closeExampleModal() {
    const overlay = document.getElementById('example-modal');
    if (overlay) overlay.classList.add('hidden');
    document.body.style.overflow = '';
}

let _aboutLoaded = false;

function openAboutModal() {
    const overlay = document.getElementById('about-modal');
    const body = document.getElementById('about-modal-body');
    overlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    if (_aboutLoaded) return;

    fetch('/api/docs')
        .then(r => {
            if (!r.ok) throw new Error(`Server returned ${r.status}`);
            return r.text();
        })
        .then(md => {
            _aboutLoaded = true;
            const html = marked.parse(md);
            body.innerHTML = `<div class="docs-content">${html}</div>`;
        })
        .catch(err => {
            body.innerHTML = `<div class="modal-error">Failed to load documentation: ${escapeHtml(err.message)}</div>`;
        });
}

function closeAboutModal() {
    const overlay = document.getElementById('about-modal');
    if (overlay) overlay.classList.add('hidden');
    document.body.style.overflow = '';
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { closeExampleModal(); closeAboutModal(); }
});

/**
 * Show error message
 */
function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = `Error: ${message}`;
    errorDiv.classList.remove('hidden');
    
    setTimeout(() => {
        errorDiv.classList.add('hidden');
    }, 5000);
}

