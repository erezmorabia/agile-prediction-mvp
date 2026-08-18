/**
 * Main application JavaScript
 */

// Global state
let allTeams = [];
let currentTeam = null;
let currentMonth = null;

/** Return the team's latest recorded snapshot before a prediction month. */
function baselineMonthForPrediction(teamName, predictionMonth) {
    const team = allTeams.find(candidate => candidate.name === teamName);
    if (!team || !Array.isArray(team.months)) return null;
    return team.months.filter(month => month < predictionMonth).at(-1) || null;
}

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
                        const baselineMonth = baselineMonthForPrediction(teamName, month);
                        const option = document.createElement('option');
                        option.value = month;
                        option.dataset.baselineMonth = baselineMonth || '';
                        option.textContent = baselineMonth
                            ? `Baseline: ${formatMonth(baselineMonth)} → Recommend for: ${formatMonth(month)}`
                            : `Recommend for: ${formatMonth(month)}`;
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
                initializeBacktest();
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
        const data = await apiClient.getRecommendations(team, month);
        displayRecommendations(data);
    } catch (error) {
        showError(error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Render the audit box describing the global policy selected for this prediction month
 * (similarity / sequence / popularity weights, popularity recency, peer pool, and how
 * many prior completed months it was selected from).
 */
function policyAuditHtml(policy) {
    if (!policy) return '';
    const simPct = Math.round(policy.similarity_weight * 100);
    const seqPct = Math.round(policy.sequence_weight * 100);
    const popPct = Math.round(policy.popularity_weight * 100);
    const recencyPct = Math.round(policy.popularity_recency_weight * 100);
    const peerInfo = policy.is_bootstrap
        ? 'N/A (bootstrap policy — similarity carries 0% weight)'
        : `${policy.peer_count} teams, min similarity ${(policy.min_similarity * 100).toFixed(0)}%`;
    const priorMonths = (policy.completed_prior_months || []).length;

    return `
        <div class="policy-audit-box" style="background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.3); border-radius: 6px; padding: 12px 16px; margin: 12px 0;">
            <strong>Selected policy for this month:</strong>${policy.is_bootstrap ? ' <span style="color:#f59e0b;">Bootstrap (no completed prior months yet)</span>' : ''}
            <ul style="margin: 8px 0 0 18px; padding: 0; font-size: 0.9em;">
                <li>Similarity ${simPct}% · Sequence ${seqPct}% · Popularity ${popPct}%</li>
                <li>Popularity recency: ${recencyPct}% recent / ${100 - recencyPct}% historical</li>
                <li>Peer pool: ${peerInfo}</li>
                <li>Fixed component windows: 2 observed snapshots (similarity look-ahead and sequence recency)</li>
                ${!policy.is_bootstrap ? `<li>Selected from ${priorMonths} completed prior month(s)${policy.mean_prior_hit_rate != null ? `, mean HR@2 ${(policy.mean_prior_hit_rate * 100).toFixed(1)}%` : ''}</li>` : ''}
            </ul>
        </div>
    `;
}

/**
 * Build a single-line verdict badge summarising recommendation validation.
 */
function buildVerdictLine(data) {
    if (!data.validation) return '';
    const v = data.validation;

    if (v.accuracy !== null && v.accuracy !== undefined) {
        const validatedRecs = data.recommendations.filter(r => r.validated);
        const unvalidatedRecs = data.recommendations.filter(r => !r.validated);

        if (v.validated_count === v.total_recommendations) {
            const names = validatedRecs.map(r => r.practice).join(' and ');
            return `<div class="verdict-line verdict-hit">✓ Recommendation aligned with a later improvement: ${v.validated_count}/${v.total_recommendations} — ${names} improved in the outcome window</div>`;
        } else if (v.validated_count > 0) {
            const hitNames = validatedRecs.map(r => r.practice).join(' and ');
            const missNames = unvalidatedRecs.map(r => r.practice).join(' and ');
            return `<div class="verdict-line verdict-partial">~ Partial alignment: ${v.validated_count}/${v.total_recommendations} — ${hitNames} matched a later improvement; ${missNames} did not improve in the outcome window</div>`;
        } else {
            const actualNames = (v.actual_improvements || []).map(i => i.practice).join(' and ');
            return `<div class="verdict-line verdict-miss">✗ Missed: 0/${v.total_recommendations}${actualNames ? ` — team actually improved ${actualNames}` : ''}</div>`;
        }
    }

    // No improvements occurred in the validation window
    let monthsText = formatMonth(v.next_month);
    if (v.month_after) monthsText += `, ${formatMonth(v.month_after)}`;
    if (v.month_after_2) monthsText += `, ${formatMonth(v.month_after_2)}`;
    return `<div class="verdict-line verdict-nodata">— No practice improvements in the outcome window (${monthsText}); recommendation alignment is not computed</div>`;
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

    // Team has fewer than two non-maxed candidate practices - no recommendations possible
    if (data.message) {
        resultsDiv.innerHTML = `
            <div class="recommendations-header">
                <h3>Recommendations for ${data.team}</h3>
                <p class="month-info">Baseline snapshot: ${formatMonth(baselineMonthForPrediction(data.team, data.month) || 0)} → recommendation month: ${formatMonth(data.month)}</p>
            </div>
            <div class="error-message">${escapeHtml(data.message)}</div>
            ${policyAuditHtml(data.selected_policy)}
        `;
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
            <p class="month-info">Baseline snapshot: ${formatMonth(baselineMonthForPrediction(data.team, data.month) || 0)} → likely next practices for recommendation month: ${formatMonth(data.month)}</p>
            ${verdictLine}
            ${data.no_similar_teams_found ? '<p style="color:#8a8785;font-size:0.9em;margin-top:6px;">No comparable team was found for this baseline — recommendations rely on sequence and popularity evidence only.</p>' : ''}
        </div>
        ${policyAuditHtml(data.selected_policy)}
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
                <li><strong>Current Level:</strong> Your team's maturity level (0–3 scale: 0 = Not implemented, 1 = Basic, 2 = Intermediate, 3 = Mature)</li>
                <li><strong>Recommendation Score:</strong> Range 0.0-1.0 (higher = stronger recommendation, more evidence)</li>
                <li><strong>Score blends three sources</strong> — similarity, sequence, and time-aware popularity — using this month's selected policy shown above.</li>
            </ul>
            <details class="score-explanation">
                <summary><strong>Click to see detailed explanation of how scores are calculated</strong></summary>
                <div class="explanation-content">
                    <h4>How Recommendation Scores Work</h4>
                    <p>For every recommendation month, the system selects one global policy from earlier prediction months whose outcomes have already closed, then blends three evidence sources using that policy's weights (see the box above for this month's actual weights):</p>

                    <div class="explanation-section">
                        <h5>1. Similarity</h5>
                        <ul>
                            <li>The system compares your team's baseline profile against <strong>all team snapshots strictly before that baseline</strong></li>
                            <li>Considers a peer's improvements in the <strong>two observed snapshots</strong> after it looked similar to you (fixed window, never varies)</li>
                            <li>Each improvement is weighted by:
                                <ul>
                                    <li>How similar that team is to yours (higher similarity = more weight)</li>
                                    <li>How much they improved (bigger improvement = more weight)</li>
                                </ul>
                            </li>
                            <li><strong>Why this works:</strong> Teams with similar profiles face similar challenges. If they succeeded with a practice, you likely will too.</li>
                        </ul>
                    </div>

                    <div class="explanation-section">
                        <h5>2. Practice Transition Model (Sequence)</h5>
                        <ul>
                            <li>The system learns patterns from <strong>all teams' improvement history before this baseline</strong></li>
                            <li>It identifies which practices typically follow others at the next improvement-bearing step</li>
                            <li><strong>Evidence:</strong> Open the Sequences tab to inspect the observed transition counts and conditional frequencies for the currently loaded organizational dataset</li>
                            <li>Triggered by what your team improved in its own <strong>two preceding observed snapshots</strong> (fixed window, never varies)</li>
                        </ul>
                    </div>

                    <div class="explanation-section">
                        <h5>3. Time-Aware Popularity</h5>
                        <ul>
                            <li>Organization-wide practice-improvement frequency, restricted to practices you haven't already mastered</li>
                            <li>Combines all-time popularity with the single most recent organization-wide transition into your baseline, weighted by the policy's recency setting</li>
                        </ul>
                    </div>

                    <div class="explanation-section">
                        <h5>4. Combining the Signals</h5>
                        <ul>
                            <li>Each of the three components is <strong>normalized separately</strong> before combining</li>
                            <li>Then combined with a weighted sum:
                                <div class="formula">Final Score = similarity_weight × Similarity + sequence_weight × Sequence + popularity_weight × Popularity</div>
                                <p style="font-size: 0.9em; color: #666; margin-top: 5px;">The weights are selected once per recommendation month (not per team) from the mean alignment rate of earlier completed months — see the policy box above for this month's actual weights.</p>
                            </li>
                            <li>Practices are then ranked by this combined score</li>
                            <li>The <strong>top 2 eligible practices</strong> (not already at max level) are recommended — always exactly two</li>
                        </ul>
                    </div>

                    <div class="explanation-section">
                        <h5>Why This Approach Works</h5>
                        <ul>
                            <li><strong>Core idea:</strong> Learn from observed organizational behavior, walk-forward only, to identify likely next practices for a specific team.</li>
                            <li><strong>Similarity evidence:</strong> "Teams like you improved X"</li>
                            <li><strong>Transition evidence:</strong> "X often followed Y at the next improvement-bearing step"</li>
                            <li><strong>Popularity evidence:</strong> "X is what most teams are improving right now"</li>
                            <li>The blend weights are chosen from what actually worked in earlier months, not fixed in advance.</li>
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
                            <strong>Recommendation Score:</strong>${tip('A weighted blend of similarity, sequence, and time-aware popularity evidence, using this month\'s selected policy. Higher = more evidence from the dataset.')} ${rec.score.toFixed(3)} <span class="score-range">(range: 0.0-1.0, higher = stronger)</span>
                        </div>
                        <div class="rec-detail">
                            <strong>Current Level:</strong>${tip('Your team\'s maturity on this practice. 0 = not implemented, 1 = basic, 2 = intermediate, 3 = mature. Only practices below maturity level 3 are eligible for recommendation.')} ${rec.level_display || `Level ${rec.level_num} (${rec.level_description})`}
                        </div>
                        <div class="rec-detail">
                            <strong>Why:</strong>
                            ${rec.why.includes('No comparable team was found') ?
                                `<span style="color: #a8a5a3; font-style: italic;">${rec.why}</span>` :
                                rec.why
                            }
                            ${rec.similar_teams && rec.similar_teams.length > 0 ? `
                                <ul class="similar-teams-list" style="margin: 8px 0 0 20px; padding: 0;">
                                    <li style="margin: 4px 0; list-style: none; font-size: 0.9em; color: #555;">Comparable teams that improved this practice${tip('Cosine similarity of practice maturity profiles at historical snapshots before your baseline. Higher % = a more comparable maturity profile.')}</li>
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
                            ` : ''}
                        </div>
                        ${data.validation ? `
                            <div class="rec-detail validation-status">
                                <strong>Validation:</strong>${tip('Checked against actual data: did the team improve this practice in the outcome window—the recommendation month and the following two recorded snapshots? \'Validated\' means the recommendation aligned with an observed improvement.')} ${rec.improved_in_months ?
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
                    <strong>Recommendation Alignment:</strong> ${data.validation.validated_count}/${data.validation.total_recommendations} = ${(data.validation.accuracy * 100).toFixed(1)}%
                </p>
            `;
        } else if (data.validation.total_recommendations === 0) {
            // Improvements occurred but no recommendations were generated
            html += `
                <p class="accuracy-info" style="color: #666; font-style: italic; margin-top: 15px;">
                    <strong>Recommendation Alignment:</strong> Not calculated (no recommendations were generated)
                </p>
                <p style="color: #666; font-size: 0.9em; margin-top: 8px;">
                    Note: The system couldn't generate recommendations (all practices may be at max level, or no similar teams/sequences found).
                </p>
            `;
        } else {
            // No improvements occurred (but recommendations were generated)
            html += `
                <p class="accuracy-info" style="color: #666; font-style: italic; margin-top: 15px;">
                    <strong>Recommendation Alignment:</strong> Not calculated (no improvements occurred in the outcome window)
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
            { key: 'level_3', name: 'Mature level', num: 3 }
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
async function runBacktest() {
    const resultsDiv = document.getElementById('backtest-results');
    const runBtn = document.getElementById('run-backtest-btn');
    resultsDiv.classList.add('hidden');
    startBacktestProgress();
    if (runBtn) runBtn.disabled = true;

    try {
        console.log('Running backtest validation...');
        const data = await apiClient.runBacktest();
        console.log('Backtest validation response:', data);

        if (!data || typeof data !== 'object') {
            throw new Error('Invalid response from backtest validation API');
        }

        displayBacktestResults(data);
    } catch (error) {
        console.error('Error running backtest validation:', error);
        showError(`Failed to run backtest validation: ${error.message}`);
    } finally {
        stopBacktestProgress();
        if (runBtn) runBtn.disabled = false;
    }
}

/**
 * Format an improvement factor, or an em-dash when the value is null/non-positive
 * (e.g. a scope with zero qualifying months, or a zero baseline).
 */
function formatFactor(value) {
    return (value === null || value === undefined || value <= 0) ? '—' : `${value.toFixed(2)}×`;
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

/**
 * Render the two accuracy-comparison boxes and the rank-aware metrics/summary grid for
 * one scope (primary or sensitivity). Renders a "not enough completed months" notice
 * instead of misleading 0% figures when the scope has zero qualifying months.
 */
function renderScopeSummary(scope, label) {
    if (!scope || scope.months_included === 0) {
        return `
            <div class="accuracy-comparison" style="margin: 20px 0; padding: 20px; background: #1e1d1a; border-radius: 8px; border: 1px solid #3a3835;">
                <h4 style="margin-top: 0; text-align: center;">${label}</h4>
                <p style="text-align: center; color: #8a8785;">Not enough completed months to report this scope.</p>
            </div>
        `;
    }

    const modelAccuracy = (scope.overall_accuracy || 0) * 100;
    const randomBaseline = (scope.random_baseline || 0) * 100;
    const improvementGap = modelAccuracy - randomBaseline;
    const gapColor = improvementGap >= 0 ? '#28a745' : '#dc3545';

    const popularityAccuracy = (scope.time_aware_popularity_accuracy || 0) * 100;
    const blendGap = modelAccuracy - popularityAccuracy;
    const blendGapColor = blendGap >= 0 ? '#28a745' : '#dc3545';

    return `
        <div class="accuracy-comparison" style="margin: 20px 0; padding: 20px; background: #1e1d1a; border-radius: 8px; border: 1px solid #3a3835;">
            <h4 style="margin-top: 0; text-align: center;">${label} — Blend vs Random Baseline</h4>
            <div style="display: flex; justify-content: space-around; align-items: center; margin: 20px 0;">
                <div style="text-align: center;">
                    <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Blend Alignment (Hit Rate@2)</div>
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
                </div>
                <div style="width: 1px; background: #3a3835; align-self: stretch;"></div>
                <div style="text-align: center; flex: 1;">
                    <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Improvement Factor</div>
                    <div style="font-size: 3em; font-weight: bold; color: ${gapColor};">${formatFactor(scope.improvement_factor)}</div>
                </div>
            </div>
        </div>

        <div class="accuracy-comparison" style="margin: 20px 0; padding: 20px; background: #1e1d1a; border-radius: 8px; border: 1px solid #3a3835;">
            <h4 style="margin-top: 0; text-align: center;">
                ${label} — Blend vs Time-Aware Popularity
                ${tip('Time-aware popularity is independently selected each month under the same walk-forward rule as the blend, restricted to 0% similarity / 0% sequence, on the same evaluable cases. This isolates what the blend adds beyond organization-wide trends. Exploratory result, not a claim of proven superiority.')}
            </h4>
            <div style="display: flex; justify-content: space-around; align-items: center; margin: 20px 0;">
                <div style="text-align: center;">
                    <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Blend Alignment (Hit Rate@2)</div>
                    <div style="font-size: 2.5em; font-weight: bold; color: #f59e0b;">${modelAccuracy.toFixed(1)}%</div>
                </div>
                <div style="font-size: 2em; color: #6b6865;">vs</div>
                <div style="text-align: center;">
                    <div style="font-size: 0.9em; color: #8a8785; margin-bottom: 5px;">Time-Aware Popularity</div>
                    <div style="font-size: 2.5em; font-weight: bold; color: #a8a5a3;">${popularityAccuracy.toFixed(1)}%</div>
                </div>
            </div>
            <div style="text-align: center; margin-top: 10px;">
                <span style="font-size: 1.3em; font-weight: bold; color: ${blendGapColor};">${blendGap > 0 ? '+' : ''}${blendGap.toFixed(1)} pp</span>
            </div>
        </div>

        <div class="accuracy-comparison" style="margin: 20px 0; padding: 20px; background: #1e1d1a; border-radius: 8px; border: 1px solid #3a3835;">
            <h4 style="margin-top: 0; text-align: center;">
                ${label} — Supplementary Rank-Aware Metrics
                ${tip('Overall Accuracy above (Hit Rate@N) is a binary hit/miss per case that ignores recommendation order and gives full credit even if only 1 of N recommendations was correct. These three metrics are stricter: Precision@N penalizes wrong picks, Recall@N measures how much of a team\'s actual improvement activity was captured, and MRR rewards ranking the correct answer first.')}
            </h4>
            <div style="display: flex; justify-content: space-around; gap: 16px; flex-wrap: wrap; margin-top: 16px;">
                ${renderRankMetricCard(
                    'Precision@N',
                    scope.overall_precision,
                    scope.random_precision,
                    scope.precision_improvement_factor,
                    'Correct recommendations ÷ total recommendations made (top_n). Getting 1 of 2 right scores 0.5 here, vs. 1.0 in Overall Accuracy.'
                )}
                ${renderRankMetricCard(
                    'Recall@N',
                    scope.overall_recall,
                    scope.random_recall,
                    scope.recall_improvement_factor,
                    'Correct recommendations ÷ practices actually improved. Capped at top_n ÷ actual improvements.'
                )}
                ${renderRankMetricCard(
                    'MRR',
                    scope.overall_mrr,
                    scope.random_mrr,
                    scope.mrr_improvement_factor,
                    'Mean Reciprocal Rank of the first correct recommendation. Sensitive to ranking order, unlike Overall Accuracy.'
                )}
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric">
                <div class="metric-label">Months Included</div>
                <div class="metric-value">${scope.months_included}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Total Recommendations Evaluated${tip('Number of evaluable team/month cases in this scope.')}</div>
                <div class="metric-value">${scope.total_predictions}</div>
                <div class="metric-description">team/month combinations</div>
            </div>
            <div class="metric">
                <div class="metric-label">Validated Cases</div>
                <div class="metric-value">${scope.correct_predictions}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Overall Alignment (Hit Rate@2)${tip('Macro average: the hit rate is computed per month first, then those rates are averaged equally across all months.')}</div>
                <div class="metric-value highlight">${modelAccuracy.toFixed(1)}%</div>
            </div>
            <div class="metric">
                <div class="metric-label">Avg Improvements/Case</div>
                <div class="metric-value">${scope.avg_improvements_per_case != null ? scope.avg_improvements_per_case.toFixed(1) : '—'}</div>
            </div>
        </div>
    `;
}

function displayBacktestResults(data) {
    const resultsDiv = document.getElementById('backtest-results');
    resultsDiv.classList.remove('hidden');

    if (!data || !data.primary || !data.sensitivity) {
        console.error('Missing primary/sensitivity in backtest validation results');
        showError('Could not display backtest results. Please try again.');
        return;
    }

    // Per-month table: every prediction month, tagged Primary or Sensitivity
    let perMonthTable = '';
    if (data.per_month_results && Array.isArray(data.per_month_results) && data.per_month_results.length > 0) {
        perMonthTable = `
            <div class="per-month-results" style="margin-top: 30px;">
                <h4>Per-Month Results</h4>
                <div class="table-outer">
                <table class="results-table" style="width: 100%;">
                    <thead>
                        <tr>
                            <th>Recommendation Month ${tip('The month for which likely next practices are identified. The model uses only data from prior months.')}</th>
                            <th>Scope ${tip('Primary months have a complete 3-snapshot outcome window and feed the primary aggregate. Sensitivity-only months have a truncated window and are reported separately, never mixed into the primary figures.')}</th>
                            <th>Evaluable Cases ${tip('Team/month cases with a usable baseline, at least two non-maxed candidate practices, and at least one observed improvement in the outcome window.')}</th>
                            <th>Validated Cases</th>
                            <th>Blend Alignment (Hit Rate@2)</th>
                            <th>Time-Aware Popularity ${tip('Independently selected pure-popularity comparison arm (0% similarity / 0% sequence) on the same evaluable cases.')}</th>
                            <th>Diff</th>
                            <th>Precision@N</th>
                            <th>Recall@N</th>
                            <th>MRR</th>
                            <th>Selected Policy ${tip('Peer count, similarity threshold, factor weights, and popularity recency chosen for this month from earlier completed months. Bootstrap = 100% popularity, used before any prior month has a completed outcome window.')}</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        data.per_month_results.forEach(r => {
            const diff = (r.blend_minus_popularity || 0) * 100;
            const diffColor = diff >= 0 ? '#28a745' : '#dc3545';
            const policy = r.selected_policy || {};
            const policyText = policy.is_bootstrap
                ? 'Bootstrap<br><small>100% popularity</small>'
                : `Sim ${Math.round((policy.similarity_weight || 0) * 100)}% · Seq ${Math.round((policy.sequence_weight || 0) * 100)}% · Pop ${Math.round((policy.popularity_weight || 0) * 100)}%<br><small>${policy.peer_count} peers, min sim ${((policy.min_similarity || 0) * 100).toFixed(0)}%, recency ${Math.round((policy.popularity_recency_weight || 0) * 100)}%</small>`;

            perMonthTable += `
                        <tr>
                            <td><strong>${formatMonth(r.month || 0)}</strong></td>
                            <td>${r.full_outcome_window ? 'Primary' : 'Sensitivity'}</td>
                            <td>${r.evaluable_cases || 0}</td>
                            <td>${r.correct || 0}</td>
                            <td><strong>${((r.accuracy || 0) * 100).toFixed(1)}%</strong></td>
                            <td>${((r.time_aware_popularity_accuracy || 0) * 100).toFixed(1)}%</td>
                            <td style="color: ${diffColor};">${diff >= 0 ? '+' : ''}${diff.toFixed(1)} pp</td>
                            <td>${((r.precision || 0) * 100).toFixed(1)}%</td>
                            <td>${((r.recall || 0) * 100).toFixed(1)}%</td>
                            <td>${(r.mrr || 0).toFixed(2)}</td>
                            <td style="font-size: 0.85em;">${policyText}</td>
                        </tr>
            `;
        });

        perMonthTable += `
                    </tbody>
                </table>
                </div>
            </div>
        `;
    }

    const html = `
        <div class="backtest-results">
            <h3>Backtest Validation Results (Rolling Window)</h3>
            <h4 style="margin-top: 30px;">Primary Results <span style="font-size: 0.7em; color: #8a8785;">(months with a complete 3-snapshot outcome window)</span></h4>
            ${renderScopeSummary(data.primary, 'Primary')}

            <h4 style="margin-top: 30px;">Sensitivity Results <span style="font-size: 0.7em; color: #8a8785;">(all recommendation months, including truncated outcome windows — kept separate from the primary aggregate)</span></h4>
            ${renderScopeSummary(data.sensitivity, 'Sensitivity')}

            <div style="margin-top: 14px; font-size: 0.82em; color: #6b6865; text-align: center;">
                Rolling-window cross-validation · no future data used${tip('Validation approach: time-series rolling window. Temporal ordering is strictly enforced so no future data leaks into training or into monthly policy selection.')}
            </div>

            ${perMonthTable}
        </div>
    `;

    resultsDiv.innerHTML = html;
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
const BACKTEST_ESTIMATED_DURATION_MS = 25_000;
const BACKTEST_ESTIMATED_MAX_PROGRESS = 90;
let backtestProgressFrame = null;
let backtestProgressStartedAt = null;

/**
 * Show an explicitly estimated progress indicator while the backtest API request runs.
 * The API returns only once the full backtest completes, so this is intentionally a
 * time-based estimate rather than an assertion of server-side completion percentage.
 */
function startBacktestProgress() {
    const progress = document.getElementById('backtest-progress');
    const fill = document.getElementById('backtest-progress-fill');
    const percent = document.getElementById('backtest-progress-percent');
    const message = document.getElementById('backtest-progress-message');
    const track = progress?.querySelector('[role="progressbar"]');

    showLoading(true);
    if (!progress || !fill || !percent || !message || !track) return;

    if (backtestProgressFrame !== null) {
        cancelAnimationFrame(backtestProgressFrame);
    }

    progress.classList.remove('hidden');
    backtestProgressStartedAt = performance.now();

    const updateProgress = (now) => {
        const elapsed = now - backtestProgressStartedAt;
        const estimatedProgress = Math.min(
            BACKTEST_ESTIMATED_MAX_PROGRESS,
            Math.floor((elapsed / BACKTEST_ESTIMATED_DURATION_MS) * BACKTEST_ESTIMATED_MAX_PROGRESS)
        );
        fill.style.width = `${estimatedProgress}%`;
        percent.textContent = `${estimatedProgress}%`;
        track.setAttribute('aria-valuenow', String(estimatedProgress));

        if (elapsed >= BACKTEST_ESTIMATED_DURATION_MS) {
            message.textContent = 'Finalizing results — the validation is taking a little longer than usual';
        } else if (elapsed >= BACKTEST_ESTIMATED_DURATION_MS * 0.6) {
            message.textContent = 'Scoring recommendations against observed outcomes';
        } else if (elapsed >= BACKTEST_ESTIMATED_DURATION_MS * 0.25) {
            message.textContent = 'Selecting month-specific policies from earlier outcomes';
        } else {
            message.textContent = 'Preparing validation · typically completes in about 25 seconds';
        }

        backtestProgressFrame = requestAnimationFrame(updateProgress);
    };

    backtestProgressFrame = requestAnimationFrame(updateProgress);
}

/** Reset the estimated backtest progress UI after the request completes or fails. */
function stopBacktestProgress() {
    if (backtestProgressFrame !== null) {
        cancelAnimationFrame(backtestProgressFrame);
        backtestProgressFrame = null;
    }

    const progress = document.getElementById('backtest-progress');
    const fill = document.getElementById('backtest-progress-fill');
    const percent = document.getElementById('backtest-progress-percent');
    const track = progress?.querySelector('[role="progressbar"]');

    if (progress) progress.classList.add('hidden');
    if (fill) fill.style.width = '0%';
    if (percent) percent.textContent = '0%';
    if (track) track.setAttribute('aria-valuenow', '0');
    backtestProgressStartedAt = null;
    showLoading(false);
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    const progress = document.getElementById('backtest-progress');
    if (show) {
        // Other API requests share this loader but do not have backtest progress.
        if (progress && backtestProgressStartedAt === null) progress.classList.add('hidden');
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
            <h3>Practice Transition Model Overview</h3>
            
            <div class="stats-grid" style="margin-bottom: 20px;">
                <div class="stat-item">
                    <strong>Source Practices With Transitions:</strong>${tip('Number of practices with at least one observed outgoing transition from a consecutive improvement-bearing step. Same-step improvements do not create an ordered transition.')} ${stats.num_transition_types || 0}
                </div>
                <div class="stat-item">
                    <strong>Total Transitions Observed:</strong>${tip('Raw practice-to-practice transition count summed across all teams and consecutive improvement-bearing steps. More observations provide more evidence for the displayed conditional frequencies.')} ${stats.total_transitions || 0}
                </div>
                <div class="stat-item">
                    <strong>Practices That Improved:</strong> ${stats.practices_that_improved || 0}
                </div>
                <div class="stat-item">
                    <strong>Unique Transition Pairs:</strong>${tip('Number of distinct practice-A → practice-B pairs observed in the currently loaded dataset.')} ${data.total_sequences || 0}
                </div>
            </div>
            
            <div class="info-box" style="margin-bottom: 20px;">
                <strong>What these transitions mean</strong>
                <p>Each row shows how often Practice B improved at the next improvement-bearing step after Practice A improved. The displayed probability is the conditional frequency of that observed transition across the organization; same-step improvements are not treated as ordered transitions.</p>
                <p>The Practice Transition Model contributes <strong>30% of the recommendation score</strong> — the rest comes from similar-team behavior.</p>
            </div>
            
            <div style="margin-bottom: 20px; display: flex; gap: 10px;">
                <button id="expand-all-sequences" class="btn btn-secondary" style="padding: 8px 15px; font-size: 0.9em;">Expand All</button>
                <button id="collapse-all-sequences" class="btn btn-secondary" style="padding: 8px 15px; font-size: 0.9em;">Collapse All</button>
            </div>
            
            <h4 style="margin-top: 30px;">Practice Transitions (sorted by frequency) — ${sortedPractices.length} practices:</h4>
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
                        <span class="sequence-prob-text">${(transition.probability * 100).toFixed(1)}%${tip('Bar color: green ≥ 60%, amber 30–59%, gray < 30%. Higher probability = a more frequently observed transition to this practice at the next improvement-bearing step.')}</span>
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
