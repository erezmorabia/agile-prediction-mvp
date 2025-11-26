/**
 * Main application JavaScript
 */

// Global state
let allTeams = [];
let currentTeam = null;
let currentMonth = null;

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
                teamSelect.innerHTML = '<option value="">Error loading teams - try unchecking filter or refreshing</option>';
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

    let html = `
        <div class="recommendations-header">
            <h3>Top ${data.recommendations.length} Recommendations for ${data.team}</h3>
            <p class="month-info">Predicting for month: ${formatMonth(data.month)}</p>
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
            <div class="info-box" style="background: #fff3cd; border: 2px solid #ffc107; color: #856404; margin-bottom: 20px; padding: 15px;">
                <strong>⚠️ Team Status:</strong> This team (${data.team}) did not improve any practices in the validation window (${validationMonthsText})
                <p style="margin-top: 8px; margin-bottom: 0; font-size: 0.9em;">
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
                            <strong>Recommendation Score:</strong> ${rec.score.toFixed(3)} <span class="score-range">(range: 0.0-1.0, higher = stronger)</span>
                        </div>
                        <div class="rec-detail">
                            <strong>Current Level:</strong> ${rec.level_display || `Level ${rec.level_num} (${rec.level_description})`}
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
                                <strong>Validation:</strong> ${rec.improved_in_months ? 
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
                            <div class="maturity-bar-fill" style="background: linear-gradient(90deg, #667eea, #764ba2); width: ${levelPercentage}%; height: 100%; border-radius: 4px;"></div>
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
function displayBacktestResults(data) {
    const resultsDiv = document.getElementById('backtest-results');
    resultsDiv.classList.remove('hidden');

    // Validate required fields
    if (!data.total_predictions && data.total_predictions !== 0) {
        console.error('Missing total_predictions in backtest validation results');
        showError('Invalid backtest validation results: missing required fields');
        return;
    }

    // Build per-month results table
    let perMonthTable = '';
    if (data.per_month_results && Array.isArray(data.per_month_results) && data.per_month_results.length > 0) {
        perMonthTable = `
            <div class="per-month-results" style="margin-top: 30px;">
                <h4>Per-Month Results</h4>
                <table class="results-table" style="width: 100%; margin-top: 15px;">
                    <thead>
                        <tr>
                            <th>Month</th>
                            <th>Training Months</th>
                            <th>Predictions</th>
                            <th>Correct</th>
                            <th>Accuracy</th>
                            <th>Teams Tested</th>
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
                            <td>${r.teams_tested || 0}</td>
                        </tr>
            `;
        });
        
        perMonthTable += `
                    </tbody>
                </table>
            </div>
        `;
    }

    // Calculate improvement gap
    const modelAccuracy = (data.overall_accuracy || 0) * 100;
    const randomBaseline = (data.random_baseline || 0) * 100;
    const improvementGap = modelAccuracy - randomBaseline;
    const gapColor = improvementGap > 0 ? '#28a745' : '#dc3545';
    
    const html = `
        <div class="backtest-results">
            <h3>Backtest Validation Results (Rolling Window)</h3>
            
            <!-- Model vs Random Comparison -->
            <div class="accuracy-comparison" style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; border: 2px solid #dee2e6;">
                <h4 style="margin-top: 0; text-align: center;">Model vs Random Baseline</h4>
                <div style="display: flex; justify-content: space-around; align-items: center; margin: 20px 0;">
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Model Accuracy</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #007bff;">${modelAccuracy.toFixed(1)}%</div>
                    </div>
                    <div style="font-size: 2em; color: #666;">vs</div>
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Random Baseline</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #6c757d;">${randomBaseline.toFixed(1)}%</div>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 2px solid #dee2e6;">
                    <div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Improvement Gap</div>
                    <div style="font-size: 3em; font-weight: bold; color: ${gapColor};">${improvementGap > 0 ? '+' : ''}${improvementGap.toFixed(1)}%</div>
                    <div style="font-size: 0.85em; color: #666; margin-top: 5px;">
                        ${improvementGap > 0 ? 'Model beats random by ' + improvementGap.toFixed(1) + ' percentage points' : 'Model underperforms random by ' + Math.abs(improvementGap).toFixed(1) + ' percentage points'}
                    </div>
                </div>
            </div>
            
            <div class="info-box" style="margin-top: 20px; background: #e8f4f8; border-left: 4px solid #667eea;">
                <strong>Academic Validation Methodology:</strong>
                <ul>
                    <li><strong>Approach:</strong> Rolling window backtest (time-series cross-validation)</li>
                    <li><strong>Data Split:</strong> Chronological (train on past months, test on future months)</li>
                    <li><strong>No Data Leakage:</strong> Strict temporal ordering enforced</li>
                    <li><strong>Baseline Comparison:</strong> Random prediction (statistical significance)</li>
                    <li><strong>Dataset:</strong> 87 teams, 35 practices, 10 months (655 observations)</li>
                </ul>
            </div>

            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-label">Total Predictions</div>
                    <div class="metric-value">${data.total_predictions || 0}</div>
                    <div class="metric-description">team/month combinations</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Correct Predictions</div>
                    <div class="metric-value">${data.correct_predictions || 0}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Overall Accuracy</div>
                    <div class="metric-value highlight">${modelAccuracy.toFixed(1)}%</div>
                    <div class="metric-description">average of all months</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Random Baseline</div>
                    <div class="metric-value">${randomBaseline.toFixed(1)}%</div>
                    <div class="metric-description">probability of random success</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Improvement Gap</div>
                    <div class="metric-value" style="color: ${gapColor};">${improvementGap > 0 ? '+' : ''}${improvementGap.toFixed(1)}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Improvement Factor</div>
                    <div class="metric-value highlight">${(data.improvement_factor || 0).toFixed(1)}x</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Months Tested</div>
                    <div class="metric-value">${data.per_month_results ? data.per_month_results.length : 0}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Avg Improvements/Case</div>
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
        displayOptimizationResults(data);
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
            <table class="results-table" style="width: 100%; margin-top: 15px;">
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
function displayOptimizationResults(data) {
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
                resultsDiv.innerHTML = `
                    ${statusMessage}
                    <div class="error" style="padding: 20px; background: #fff; border: 2px solid #ffc107; border-radius: 8px; color: #856404;">
                        <h3 style="color: #856404;">Warning: Optimization Cancelled</h3>
                        <p style="color: #856404;">The optimization was cancelled before any valid configurations were found.</p>
                        <p style="color: #856404;"><strong>Combinations tested:</strong> ${data.total_combinations_tested || 0} / ${data.total_combinations_available || data.total_combinations_tested || 0}</p>
                        <p style="color: #856404;">Please try again or adjust parameters for a faster search.</p>
                    </div>
                `;
                return;
            }
        } else {
            // Not cancelled, just no valid configs found
            resultsDiv.innerHTML = `
                ${statusMessage}
                <div class="error" style="padding: 20px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px;">
                    <h3>Error: No Optimal Configuration Found</h3>
                    <p>No configuration met the minimum accuracy threshold of 40%.</p>
                    <p><strong>Total combinations tested:</strong> ${data.total_combinations_tested || 0} / ${data.total_combinations_available || data.total_combinations_tested || 0}</p>
                    <p><strong>Valid combinations:</strong> ${data.valid_combinations || 0}</p>
                </div>
            `;
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
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0;">
            <h4 style="margin-top: 0;">Optimization Summary</h4>
            <div style="margin-bottom: 15px;">
                <strong>Iterations:</strong> ${data.total_combinations_tested || 0} / ${data.total_combinations_available || 0} tested (${completionPct}%) - ${statusText}
            </div>
            
            <details style="margin-bottom: 15px;">
                <summary style="cursor: pointer; font-weight: bold; margin-bottom: 10px;">Parameter Ranges Tested</summary>
                <div style="margin: 10px 0; padding-left: 20px; font-size: 0.9em;">
                    <p style="font-weight: bold; margin-top: 10px; color: #856404;">Fixed Parameters (Non-Impactful):</p>
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
                    <p style="margin-top: 10px; font-style: italic; color: #666;">Search space: 4 × 3 × 3 × 3 × 3 = 324 combinations (optimized from 540)</p>
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
            <div class="accuracy-comparison" style="margin: 30px 0; padding: 20px; background: #f8f9fa; border-radius: 8px; border: 2px solid #dee2e6;">
                <h4 style="margin-top: 0; text-align: center;">Optimal Configuration Results</h4>
                <div style="display: flex; justify-content: space-around; align-items: center; margin: 20px 0;">
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Model Accuracy</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #007bff;">${modelAccuracy.toFixed(1)}%</div>
                    </div>
                    <div style="font-size: 2em; color: #666;">vs</div>
                    <div style="text-align: center;">
                        <div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Random Baseline</div>
                        <div style="font-size: 2.5em; font-weight: bold; color: #6c757d;">${randomBaseline.toFixed(1)}%</div>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 2px solid #dee2e6;">
                    <div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Improvement Gap</div>
                    <div style="font-size: 3em; font-weight: bold; color: ${gapColor};">${gapPercent > 0 ? '+' : ''}${gapPercent.toFixed(1)}%</div>
                    <div style="font-size: 0.85em; color: #666; margin-top: 5px;">
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
            throw new Error('Invalid response from statistics API: response is not an object');
        }
        
        // Check for required fields
        if (typeof data.num_teams !== 'number') {
            console.error('Missing num_teams in response:', data);
            throw new Error('Invalid response: missing num_teams field');
        }
        
        if (typeof data.num_practices !== 'number') {
            console.error('Missing num_practices in response:', data);
            throw new Error('Invalid response: missing num_practices field');
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
        showError('Invalid statistics data: missing required fields');
        resultsDiv.innerHTML = `
            <div class="error" style="padding: 20px; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px;">
                <h3>Error: Invalid Statistics Data</h3>
                <p>Missing required fields: num_teams or num_practices</p>
                <p style="margin-top: 10px; font-size: 0.9em; color: #666;">
                    Received data: ${JSON.stringify(data, null, 2)}
                </p>
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
                    <strong>Total Observations:</strong> ${(data.total_observations || 0).toLocaleString()}
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
                                    <div style="margin-top: 10px; padding: 8px; background: #f8f9fa; border-left: 3px solid #007bff; font-size: 0.9em;">
                                        <strong>Remarks:</strong> ${remarks.replace(/\n/g, '<br>')}
                                    </div>
                                `;
                            }
                            
                            return `
                                <details class="practice-item" style="margin: 10px 0; padding: 10px; border: 1px solid #dee2e6; border-radius: 4px;">
                                    <summary class="practice-summary">
                                        ${practice}
                                        <span style="color: #666; font-size: 0.85em; font-weight: normal;"> (click to expand/collapse)</span>
                                    </summary>
                                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
                                        <h5 style="margin-top: 0; color: #495057;">Level Definitions:</h5>
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

            ${data.missing_values && data.missing_values.total_missing > 0 ? `
            <div class="stats-section missing-values-section">
                <h4>Missing Values Analysis</h4>
                <div class="missing-values-summary">
                    <p><strong>Total Missing Values:</strong> ${data.missing_values.total_missing.toLocaleString()}</p>
                </div>

                ${data.missing_values.practices_with_missing && data.missing_values.practices_with_missing.length > 0 ? `
                <div class="missing-values-details">
                    <h5>Practices with Missing Values (${data.missing_values.practices_with_missing.length}):</h5>
                    <div class="missing-practices-list">
                        ${data.missing_values.practices_with_missing.slice(0, 10).map(practice => {
                            const info = data.missing_values.by_practice[practice];
                            return `<div class="missing-item">
                                <strong>${practice}:</strong> ${info.count} missing (${info.percentage}%)
                            </div>`;
                        }).join('')}
                        ${data.missing_values.practices_with_missing.length > 10 ? 
                            `<div class="missing-item">... and ${data.missing_values.practices_with_missing.length - 10} more</div>` : ''}
                    </div>
                </div>
                ` : ''}

                ${data.missing_values.months_with_missing && data.missing_values.months_with_missing.length > 0 ? `
                <div class="missing-values-details">
                    <h5>Months with Missing Values (${data.missing_values.months_with_missing.length}):</h5>
                    <div class="missing-months-list">
                        ${data.missing_values.months_with_missing.slice(0, 10).map(month => {
                            const info = data.missing_values.by_month[month];
                            return `<div class="missing-item">
                                <strong>${formatMonth(month)}:</strong> ${info.count} missing (${info.percentage}%)
                            </div>`;
                        }).join('')}
                        ${data.missing_values.months_with_missing.length > 10 ? 
                            `<div class="missing-item">... and ${data.missing_values.months_with_missing.length - 10} more</div>` : ''}
                    </div>
                </div>
                ` : ''}
            </div>
            ` : ''}
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
        showError('Invalid sequences data: missing required fields');
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
                    <strong>Total Transition Patterns:</strong> ${stats.num_transition_types || 0}
                </div>
                <div class="stat-item">
                    <strong>Total Transitions Observed:</strong> ${stats.total_transitions || 0}
                </div>
                <div class="stat-item">
                    <strong>Practices That Improved:</strong> ${stats.practices_that_improved || 0}
                </div>
                <div class="stat-item">
                    <strong>Total Sequences:</strong> ${data.total_sequences || 0}
                </div>
            </div>
            
            <div class="info-box" style="margin-bottom: 20px;">
                <strong>What This Means:</strong>
                <p>The system analyzed <strong>ALL teams and ALL month-to-month transitions</strong> to learn which practices typically follow others when teams improve. Sequences are learned from transitions where multiple practices improved together from one month to the next (e.g., Month X → Month Y).</p>
                <p>All transitions from all historical months are aggregated into one global pattern. <strong>Format:</strong> 'Practice A' → 'Practice B' (occurred X times, Y% probability)</p>
            </div>
            
            <div style="margin-bottom: 20px; display: flex; gap: 10px;">
                <button id="expand-all-sequences" class="btn btn-secondary" style="padding: 8px 15px; font-size: 0.9em;">Expand All</button>
                <button id="collapse-all-sequences" class="btn btn-secondary" style="padding: 8px 15px; font-size: 0.9em;">Collapse All</button>
            </div>
            
            <h4 style="margin-top: 30px;">Improvement Sequences (sorted by frequency):</h4>
            <div id="sequences-list">
    `;
    
    // Generate sequence groups with collapsible sections - show all practices
    html += generateSequenceGroups(sortedPractices, grouped);
    
    html += `
            </div>
            
            <div class="info-box" style="margin-top: 30px;">
                <strong>Interpretation:</strong>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li>These sequences are learned from <strong>ALL month-to-month transitions across ALL teams</strong></li>
                    <li>When a team improves multiple practices from Month X to Month Y, transitions are created between those practices</li>
                    <li>All transitions are aggregated into one global pattern shown here</li>
                    <li>Higher probability = more common pattern across the organization</li>
                    <li>The system uses these patterns to boost recommendations (30% weight)</li>
                </ul>
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
    
    for (const fromPractice of sortedPractices) {
        const transitions = grouped[fromPractice].sort((a, b) => b.count - a.count);
        const avgProb = transitions.reduce((sum, t) => sum + t.probability, 0) / transitions.length;
        
        html += `
            <details class="sequence-group" data-practice="${fromPractice}">
                <summary class="sequence-summary">
                    <span class="sequence-arrow">▶</span>
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
                        <span class="sequence-prob-text">${(transition.probability * 100).toFixed(1)}%</span>
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
    }
    
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

