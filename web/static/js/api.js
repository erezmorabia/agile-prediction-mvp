/**
 * API Client for Agile Practice Prediction System
 */

const API_BASE = '';

class APIClient {
    /**
     * Get all teams
     */
    async getTeams() {
        const response = await fetch(`${API_BASE}/api/teams`);
        if (!response.ok) {
            throw new Error(`Failed to fetch teams: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Get teams with improvements
     */
    async getTeamsWithImprovements() {
        const response = await fetch(`${API_BASE}/api/teams/with-improvements`);
        if (!response.ok) {
            throw new Error(`Failed to fetch teams with improvements: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Get months for a team
     */
    async getTeamMonths(teamName) {
        const response = await fetch(`${API_BASE}/api/teams/${encodeURIComponent(teamName)}/months`);
        if (!response.ok) {
            throw new Error(`Failed to fetch months for team: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Get recommendations
     */
    async getRecommendations(team, month, topN = 2, kSimilar = 19) {
        const requestBody = {
            team: team,
            month: month,
            top_n: topN,
            k_similar: kSimilar
        };
        
        // Debug logging to verify what's being sent
        console.log('[Recommendations API] Request payload:', requestBody);
        
        const response = await fetch(`${API_BASE}/api/recommendations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Failed to get recommendations: ${response.statusText}`);
        }
        
        return await response.json();
    }

    /**
     * Run backtest (rolling window approach)
     */
    async runBacktest(trainRatio = null, config = null) {
        const body = {
            train_ratio: trainRatio
        };
        
        if (config) {
            body.config = config;
        }
        
        const response = await fetch(`${API_BASE}/api/backtest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Failed to run backtest: ${response.statusText}`);
        }
        
        return await response.json();
    }

    /**
     * Get system statistics
     */
    async getSystemStats() {
        const response = await fetch(`${API_BASE}/api/stats`);
        if (!response.ok) {
            throw new Error(`Failed to fetch stats: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Get improvement sequences
     */
    async getImprovementSequences() {
        const response = await fetch(`${API_BASE}/api/sequences`);
        if (!response.ok) {
            throw new Error(`Failed to fetch sequences: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Find optimal configuration
     */
    async findOptimalConfig(ranges = {}, signal = null) {
        const fetchOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                min_accuracy: ranges.min_accuracy || 0.40,
                top_n_range: ranges.top_n_range || null,
                similarity_weight_range: ranges.similarity_weight_range || null,
                k_similar_range: ranges.k_similar_range || null,
                similar_teams_lookahead_months_range: ranges.similar_teams_lookahead_months_range || null,
                recent_improvements_months_range: ranges.recent_improvements_months_range || null,
                min_similarity_threshold_range: ranges.min_similarity_threshold_range || null,
                fixed_params: ranges.fixed_params || null
            })
        };
        
        if (signal) {
            fetchOptions.signal = signal;
        }
        
        const response = await fetch(`${API_BASE}/api/optimize`, fetchOptions);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Failed to find optimal config: ${response.statusText}`);
        }
        
        return await response.json();
    }

    /**
     * Cancel optimization
     */
    async cancelOptimization() {
        const response = await fetch(`${API_BASE}/api/optimize/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Failed to cancel optimization: ${response.statusText}`);
        }
        
        return await response.json();
    }

    /**
     * Get latest optimization results
     */
    async getLatestOptimizationResults() {
        const response = await fetch(`${API_BASE}/api/optimize/latest`);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Failed to get latest results: ${response.statusText}`);
        }
        
        return await response.json();
    }
}

// Export singleton instance
const apiClient = new APIClient();

