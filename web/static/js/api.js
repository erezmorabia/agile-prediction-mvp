/**
 * API Client for Agile Practice Recommendation System
 */

const API_BASE = '';

class APIClient {
    /**
     * Get all teams
     */
    async getTeams() {
        const response = await fetch(`${API_BASE}/api/teams`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Failed to fetch teams: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Get teams with improvements
     */
    async getTeamsWithImprovements() {
        const response = await fetch(`${API_BASE}/api/teams/with-improvements`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Failed to fetch teams with improvements: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Get months for a team
     */
    async getTeamMonths(teamName) {
        const response = await fetch(`${API_BASE}/api/teams/${encodeURIComponent(teamName)}/months`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Failed to fetch months for team: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Get recommendations. The primary flow always returns exactly two
     * recommendations, chosen by that month's globally selected policy - there is no
     * per-request tuning.
     */
    async getRecommendations(team, month) {
        const requestBody = {
            team: team,
            month: month,
            top_n: 2
        };

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
     * Run the backtest. No model parameters are accepted - the monthly policy is the
     * only configuration authority.
     */
    async runBacktest() {
        const response = await fetch(`${API_BASE}/api/backtest`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
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
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Failed to fetch stats: ${response.statusText}`);
        }
        return await response.json();
    }

    /**
     * Get improvement sequences
     */
    async getImprovementSequences() {
        const response = await fetch(`${API_BASE}/api/sequences`);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Failed to fetch sequences: ${response.statusText}`);
        }
        return await response.json();
    }

}

// Export singleton instance
const apiClient = new APIClient();
