"""
PolicyEngine: Global monthly adaptive three-factor recommendation blend.

Selects one global policy per prediction month from prior completed outcomes, combining
similarity, sequence, and time-aware popularity evidence. This is the single source of
truth for the blend so the web API, the CLI, and the backtest cannot drift apart - all
three call into the same PolicyEngine instance built from the same recommender.

See docs/PROJECT_DOCUMENTATION.md for the specification this
implements, and scripts/research_three_factor_blend.py / research_popularity_strategies.py /
research_full_per_team_optimization.py for the research prototypes this ports.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product

TOP_N = 2

# Fixed component windows - never vary by team or prediction month (spec section
# "Fixed Component Windows").
FIXED_LOOKAHEAD_SNAPSHOTS = 2  # similarity: peer's observed snapshots after it looked similar
FIXED_RECENCY_SNAPSHOTS = 2  # sequence: target team's own preceding observed snapshots
OUTCOME_WINDOW_SNAPSHOTS = 3  # evaluation: baseline -> next 3 observed snapshots

PEER_COUNTS = (5, 10, 19)
SIMILARITY_THRESHOLDS = (0.0, 0.5, 0.75)
RECENCY_WEIGHTS = (0.0, 0.25, 0.5, 0.75, 1.0)


def _weight_triples() -> tuple[tuple[float, float, float], ...]:
    """Return the 15 (similarity, sequence, popularity) triples that sum to exactly 1.0."""
    step = 0.25
    units = round(1.0 / step)
    return tuple(
        (similarity / units, sequence / units, (units - similarity - sequence) / units)
        for similarity in range(units + 1)
        for sequence in range(units - similarity + 1)
    )


WEIGHT_TRIPLES = _weight_triples()  # 15 combinations


@dataclass(frozen=True)
class Policy:
    """One candidate global policy: component config + factor weights + recency weight."""

    peer_count: int
    min_similarity: float
    similarity_weight: float
    sequence_weight: float
    popularity_weight: float
    recency_weight: float


# The full candidate grid: 3 peer counts x 3 thresholds x 15 weight triples x 5 recency
# weights = 675 combinations (spec: "Global Monthly Policy Selection").
POLICY_GRID: tuple[Policy, ...] = tuple(
    Policy(
        peer_count=peer_count,
        min_similarity=min_similarity,
        similarity_weight=weights[0],
        sequence_weight=weights[1],
        popularity_weight=weights[2],
        recency_weight=recency_weight,
    )
    for peer_count, min_similarity, weights, recency_weight in product(
        PEER_COUNTS, SIMILARITY_THRESHOLDS, WEIGHT_TRIPLES, RECENCY_WEIGHTS
    )
)

# Bootstrap policy used before any prior prediction month has a completed outcome window.
BOOTSTRAP_POLICY = Policy(
    peer_count=PEER_COUNTS[0],
    min_similarity=SIMILARITY_THRESHOLDS[0],
    similarity_weight=0.0,
    sequence_weight=0.0,
    popularity_weight=1.0,
    recency_weight=0.5,
)

# The subset of the grid used for the backtest's independent time-aware-popularity
# comparison arm: pure popularity (0% similarity, 0% sequence), one per recency weight.
# peer_count/min_similarity are irrelevant when similarity_weight is 0, so any fixed
# choice reproduces the same hit rate; PEER_COUNTS[0]/SIMILARITY_THRESHOLDS[0] is used
# for consistency with BOOTSTRAP_POLICY.
POPULARITY_ARM_POLICIES: tuple[Policy, ...] = tuple(
    Policy(
        peer_count=PEER_COUNTS[0],
        min_similarity=SIMILARITY_THRESHOLDS[0],
        similarity_weight=0.0,
        sequence_weight=0.0,
        popularity_weight=1.0,
        recency_weight=recency_weight,
    )
    for recency_weight in RECENCY_WEIGHTS
)


def _preference_key(policy: Policy) -> tuple[float, float, float, float, float, float]:
    """Deterministic tie-break: prefer more popularity-heavy, then lower recency, then
    lower similarity weight, lower sequence weight, lower peer count, lower threshold.

    Ported from scripts/research_full_per_team_optimization.py's `prefer()`. Combined with
    the mean-hit-rate primary key, this is a strict total order over the 675-policy grid:
    (popularity_weight, recency_weight, similarity_weight, sequence_weight, peer_count,
    min_similarity) uniquely determines a Policy.
    """
    k_idx = PEER_COUNTS.index(policy.peer_count)
    thr_idx = SIMILARITY_THRESHOLDS.index(policy.min_similarity)
    return (
        policy.popularity_weight,
        -policy.recency_weight,
        -policy.similarity_weight,
        -policy.sequence_weight,
        -k_idx,
        -thr_idx,
    )


def policy_summary(selected: SelectedPolicy) -> dict:
    """Serializable audit record for a selected policy, shared by the backtest and the
    live recommendation response so both present identical policy information (spec:
    "User-Visible Explanation and Audit Record"). Peer count and threshold are reported
    as None (not a default value) when the bootstrap policy is in effect, since
    similarity carries 0% weight in that case."""
    policy = selected.policy
    return {
        "is_bootstrap": selected.is_bootstrap,
        "peer_count": None if selected.is_bootstrap else policy.peer_count,
        "min_similarity": None if selected.is_bootstrap else policy.min_similarity,
        "similarity_weight": policy.similarity_weight,
        "sequence_weight": policy.sequence_weight,
        "popularity_weight": policy.popularity_weight,
        "popularity_recency_weight": policy.recency_weight,
        "completed_prior_months": list(selected.completed_prior_months),
        "mean_prior_hit_rate": selected.mean_prior_hit_rate,
    }


def _normalize(scores: dict) -> dict:
    """Normalize non-negative scores to [0, 1] by dividing by their max; empty/all-zero -> 0.0
    for every entry. Matches scripts/research_popularity_strategies.py:normalized_scores.
    """
    maximum = max(scores.values()) if scores else 0.0
    return {practice: (value / maximum if maximum else 0.0) for practice, value in scores.items()}


def _baseline_month_for(team_months: list, prediction_month: int) -> int | None:
    """The team's own most recent observed snapshot strictly before prediction_month."""
    prior = [m for m in team_months if m < prediction_month]
    return prior[-1] if prior else None


def _outcome_snapshots(team_months: list, baseline_month: int) -> list:
    """Up to OUTCOME_WINDOW_SNAPSHOTS observed snapshots after the baseline."""
    after = [m for m in team_months if m > baseline_month]
    return after[:OUTCOME_WINDOW_SNAPSHOTS]


@dataclass(frozen=True)
class CaseComponents:
    """Everything policy-independent needed to score one (team, baseline) case.

    peers / peer_contributions are parallel tuples, sorted descending by similarity
    (min_similarity=0.0, unbounded k), so any (peer_count, min_similarity) variant can be
    reproduced by filtering peers to similarity >= threshold (order-preserving) and
    truncating to peer_count - see PolicyEngine._selected_peer_indices.
    """

    team: str
    baseline_month: int
    candidates: tuple
    current_levels: dict
    peers: tuple
    peer_contributions: tuple
    sequence_raw: dict
    historical_popularity_raw: dict
    recent_popularity_raw: dict
    no_similar_teams_found: bool


@dataclass(frozen=True)
class CohortCase:
    """One evaluable team-month case: its components plus the observed outcome."""

    components: CaseComponents
    actual_improved: frozenset


@dataclass(frozen=True)
class SelectedPolicy:
    """The audit record for a monthly policy selection."""

    policy: Policy
    is_bootstrap: bool
    completed_prior_months: tuple
    mean_prior_hit_rate: float | None


@dataclass(frozen=True)
class RecommendationResult:
    """Result of PolicyEngine.recommend() for one team/prediction-month."""

    team: str
    prediction_month: int
    baseline_month: int | None
    practices: tuple
    scores: dict
    current_levels: dict
    selected_policy: SelectedPolicy
    no_similar_teams_found: bool
    insufficient_practices: bool


class PolicyEngine:
    """Select and apply the global monthly adaptive three-factor recommendation blend."""

    def __init__(self, similarity_engine, sequence_mapper, practices: list):
        self.similarity_engine = similarity_engine
        self.sequence_mapper = sequence_mapper
        self.practices = practices
        self.processor = similarity_engine.processor

        self._all_months = sorted(self.processor.get_all_months())
        self._num_teams = len(self.processor.get_all_teams())

        self._components_cache: dict = {}
        self._popularity_cache: dict = {}
        self._cohort_cache: dict = {}
        self._hit_rate_cache: dict = {}
        self._selected_policy_cache: dict = {}
        self._popularity_arm_cache: dict = {}

    # ------------------------------------------------------------------
    # Month bookkeeping
    # ------------------------------------------------------------------

    def prediction_months(self) -> list:
        """All months eligible for prediction: global index 3 onwards."""
        return self._all_months[3:]

    def full_outcome_window(self, prediction_month: int) -> bool:
        """True if this prediction month's 3-snapshot outcome window is fully observed
        globally (i.e. this is a primary month, not a sensitivity-only month)."""
        idx = self._all_months.index(prediction_month)
        return idx + 2 < len(self._all_months)

    def completed_prior_months(self, prediction_month: int) -> list:
        """Earlier prediction months whose full 3-snapshot outcome window has already
        closed before prediction_month (spec: "Global Monthly Policy Selection")."""
        target_idx = self._all_months.index(prediction_month)
        return [
            m
            for m in self.prediction_months()
            if self._all_months.index(m) + 2 < target_idx
        ]

    # ------------------------------------------------------------------
    # Case components (policy-independent evidence)
    # ------------------------------------------------------------------

    def baseline_month_for(self, team: str, prediction_month: int) -> int | None:
        """The team's own most recent observed snapshot strictly before prediction_month,
        or None if the team has no usable baseline."""
        history = self.processor.get_team_history(team)
        team_months = sorted(history.keys())
        return _baseline_month_for(team_months, prediction_month)

    def case_components(self, team: str, baseline_month: int) -> CaseComponents:
        key = (team, baseline_month)
        if key not in self._components_cache:
            self._components_cache[key] = self._compute_components(team, baseline_month)
        return self._components_cache[key]

    def _peer_contribution(self, peer_team: str, historical_month: int, baseline_month: int) -> dict:
        """Best improvement per practice for one peer, over the fixed 2-snapshot look-ahead
        from historical_month, gated so no snapshot after baseline_month is used."""
        peer_history = self.processor.get_team_history(peer_team)
        if historical_month not in peer_history:
            return {}
        hist_state = peer_history[historical_month]
        peer_months = sorted(peer_history.keys())
        hist_idx = peer_months.index(historical_month)

        best: dict = {}
        for ahead in range(1, FIXED_LOOKAHEAD_SNAPSHOTS + 1):
            if hist_idx + ahead >= len(peer_months):
                break
            future_month = peer_months[hist_idx + ahead]
            if future_month > baseline_month:
                break
            future_state = peer_history[future_month]
            for j, (before, after) in enumerate(zip(hist_state, future_state, strict=True)):
                if after > before:
                    practice = self.practices[j]
                    magnitude = after - before
                    if practice not in best or magnitude > best[practice]:
                        best[practice] = magnitude
        return best

    def _month_popularity(self, baseline_month: int) -> tuple:
        """Org-wide (historical, recent) raw improvement-count dicts for one baseline month.
        Historical: learned strictly before baseline_month (learn_sequences_up_to_month).
        Recent: the single immediately preceding observed transition into baseline_month.
        Shared across every team whose baseline is this month - computed once, cached."""
        if baseline_month in self._popularity_cache:
            return self._popularity_cache[baseline_month]

        self.sequence_mapper.learn_sequences_up_to_month(baseline_month)
        historical = dict(self.sequence_mapper.get_practice_popularity())

        idx = self._all_months.index(baseline_month)
        recent: dict = {}
        if idx > 0:
            previous_month = self._all_months[idx - 1]
            counts: Counter = Counter()
            for team in self.processor.get_all_teams():
                history = self.processor.get_team_history(team)
                if previous_month in history and baseline_month in history:
                    for j, (before, after) in enumerate(
                        zip(history[previous_month], history[baseline_month], strict=True)
                    ):
                        if after > before:
                            counts[self.practices[j]] += 1
            recent = dict(counts)

        result = (historical, recent)
        self._popularity_cache[baseline_month] = result
        return result

    def _compute_components(self, team: str, baseline_month: int) -> CaseComponents:
        """Collect a team's baseline state and raw evidence for later policy scoring.

        The baseline is the team's latest snapshot before the prediction month.
        Evidence combines peer improvements, practice transitions, and organizational
        popularity. Normalization, policy weights, and final ranking are applied later
        by score_case() and top_practices().
        """
        # 1. Baseline and candidates
        # Read the baseline maturity levels and identify practices with room to improve.
        # Scores are normalized: 1.0 represents the maximum original maturity level of 3.
        history = self.processor.get_team_history(team)
        current_scores = history[baseline_month]
        current_practice_score_dict = {p: float(v) for p, v in zip(self.practices, current_scores, strict=True)}
        candidate_to_improve_practices = tuple(p for p in self.practices if current_practice_score_dict[p] < 1.0)

        # 2. Similarity evidence
        # Match this baseline against other teams' snapshots strictly before it.
        # Keep each team's best match and the full ranking; the policy later chooses
        # how many peers to use and the minimum similarity required.
        try:
            similar_teams_by_score_month_full = self.similarity_engine.find_similar_teams(
                team, baseline_month, k=self._num_teams, min_similarity=0.0
            )
        except ValueError:
            # Without peers, transition and popularity evidence can still be collected.
            similar_teams_by_score_month_full = []
        no_similar_teams_found = not similar_teams_by_score_month_full

        # For each peer, record its largest improvement per practice relative to the
        # matching snapshot, over its next two recorded snapshots, never past the baseline.
        similar_teams_per_practice_improvement = tuple(
            self._peer_contribution(peer_team, historical_month, baseline_month)
            for peer_team, _similarity, historical_month in similar_teams_by_score_month_full
        )

        # 3. Transitions evidence
        # Learn practice-transition patterns using snapshots strictly before the baseline.
        self.sequence_mapper.learn_sequences_up_to_month(baseline_month)
        team_months = sorted(history.keys())
        baseline_idx = team_months.index(baseline_month)
        recently_improved = set()
        # Compare the team's current scores with its previous two recorded snapshots.
        # Mark a practice as recently improved if its score is higher than in either snapshot.
        for back in range(1, min(FIXED_RECENCY_SNAPSHOTS, baseline_idx) + 1):
            past_scores = history[team_months[baseline_idx - back]]
            for j, (before, after) in enumerate(zip(past_scores, current_scores, strict=True)):
                if after > before:
                    recently_improved.add(self.practices[j])

        # For each recently improved practice, find up to 3 common next practices in past data.
        # Add their scores when the same next practice appears more than once.
        # The total is ranking evidence, not a probability of success.
        sequence_raw: dict = {}
        for practice in [p for p in self.practices if p in recently_improved]:
            for next_practice, probability in self.sequence_mapper.get_typical_next_practices(practice, top_n=3):
                sequence_raw[next_practice] = sequence_raw.get(next_practice, 0.0) + probability

        # 4. Popularity evidence
        # Count how often each practice improved across all teams:
        # historically before the baseline, and recently between the previous snapshot and the baseline.
        # Recent counts use only teams with data in both snapshots.
        historical_popularity_raw, recent_popularity_raw = self._month_popularity(baseline_month)

        # 5. Assemble the components
        # Return the evidence without applying a policy, so different policies can
        # score the same inputs without repeating the evidence-gathering work.
        return CaseComponents(
            team=team,
            baseline_month=baseline_month,
            candidates=candidate_to_improve_practices,
            current_levels=current_practice_score_dict,
            peers=tuple(similar_teams_by_score_month_full),
            peer_contributions=similar_teams_per_practice_improvement,
            sequence_raw=sequence_raw,
            historical_popularity_raw=historical_popularity_raw,
            recent_popularity_raw=recent_popularity_raw,
            no_similar_teams_found=no_similar_teams_found,
        )

    # ------------------------------------------------------------------
    # Recommendable / evaluable
    # ------------------------------------------------------------------

    def is_recommendable(self, team: str, prediction_month: int) -> tuple:
        """Returns (recommendable: bool, components: CaseComponents | None).

        components is None only when the team has no usable baseline at all; otherwise
        it is always returned (even when not recommendable) so callers can build a
        "fewer than two practices left to improve" message.
        """
        baseline = self.baseline_month_for(team, prediction_month)
        if baseline is None:
            return False, None
        components = self.case_components(team, baseline)
        return len(components.candidates) >= 2, components

    def evaluable_cases(self, prediction_month: int) -> list:
        """The fixed evaluable cohort for a prediction month, established before any
        policy scoring and identical for every candidate policy and reported arm."""
        if prediction_month in self._cohort_cache:
            return self._cohort_cache[prediction_month]

        cases = []
        for team in self.processor.get_all_teams():
            recommendable, components = self.is_recommendable(team, prediction_month)
            if not recommendable:
                continue

            history = self.processor.get_team_history(team)
            team_months = sorted(history.keys())
            baseline_vector = history[components.baseline_month]
            outcome_months = _outcome_snapshots(team_months, components.baseline_month)

            improved = set()
            for outcome_month in outcome_months:
                future_vector = history[outcome_month]
                for j, (before, after) in enumerate(zip(baseline_vector, future_vector, strict=True)):
                    if after > before:
                        improved.add(self.practices[j])

            if not improved:
                continue

            cases.append(CohortCase(components=components, actual_improved=frozenset(improved)))

        self._cohort_cache[prediction_month] = cases
        return cases

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _first_improving_month(self, peer_team: str, historical_month: int, baseline_month: int, practice: str):
        """The first snapshot (within the fixed look-ahead window) at which peer_team's
        state shows practice improved relative to historical_month. Used only for
        building the human-readable explanation, not for scoring."""
        peer_history = self.processor.get_team_history(peer_team)
        if historical_month not in peer_history:
            return None
        hist_state = peer_history[historical_month]
        peer_months = sorted(peer_history.keys())
        hist_idx = peer_months.index(historical_month)
        practice_idx = self.practices.index(practice)

        for ahead in range(1, FIXED_LOOKAHEAD_SNAPSHOTS + 1):
            if hist_idx + ahead >= len(peer_months):
                break
            future_month = peer_months[hist_idx + ahead]
            if future_month > baseline_month:
                break
            if peer_history[future_month][practice_idx] > hist_state[practice_idx]:
                return future_month
        return None

    def explain_practice(self, team: str, prediction_month: int, practice: str) -> dict:
        """Human-readable explanation of why `practice` was (or would be) recommended,
        using the prediction month's selected global policy."""
        _recommendable, components = self.is_recommendable(team, prediction_month)
        if components is None:
            raise ValueError(f"Team '{team}' has no data before month {prediction_month}")

        selected = self.select_policy(prediction_month)
        selected_indices = self._selected_peer_indices(components, selected.policy)

        improved_teams = []
        for i in selected_indices:
            peer_team, similarity, historical_month = components.peers[i]
            if practice in components.peer_contributions[i]:
                future_month = self._first_improving_month(
                    peer_team, historical_month, components.baseline_month, practice
                )
                improved_teams.append(
                    {
                        "team": peer_team,
                        "month": future_month,
                        "similarity": float(similarity),
                        "similar_at_month": historical_month,
                    }
                )

        self.sequence_mapper.learn_sequences_up_to_month(components.baseline_month)
        try:
            sequence_info = self.sequence_mapper.get_typical_next_practices(practice, top_n=1)
        except ValueError:
            sequence_info = []

        score_breakdowns: dict = {}
        self.score_case(components, selected.policy, breakdowns=score_breakdowns)
        return {
            "practice": practice,
            "score_breakdown": score_breakdowns.get(practice, []),
            "similar_teams_improved": len(improved_teams),
            "total_similar_teams_checked": len(selected_indices),
            "similar_teams_list": improved_teams,
            "typical_sequence_follows": sequence_info[0][0] if sequence_info else None,
            "has_sequence_boost": practice in components.sequence_raw,
            "no_similar_teams_found": len(selected_indices) == 0,
        }

    def _selected_peer_indices(self, case: CaseComponents, policy: Policy) -> list:
        """Indices into case.peers/peer_contributions selected for this policy's
        (peer_count, min_similarity). case.peers is already sorted descending by
        similarity at min_similarity=0.0, so filter-then-truncate reproduces
        SimilarityEngine.find_similar_teams(k=peer_count, min_similarity=threshold)
        exactly (dedup-by-max-similarity happens before truncation there too)."""
        indices = [i for i, (_team, similarity, _month) in enumerate(case.peers) if similarity >= policy.min_similarity]
        return indices[: policy.peer_count]

    def score_case(self, case: CaseComponents, policy: Policy, *, breakdowns: dict | None = None) -> dict:
        """Final blended score per candidate practice for one case under one policy.

        Normalization scope (research-exact, see plan doc decision 1 and
        docs/PROJECT_DOCUMENTATION.md):
        - similarity, sequence: normalize over all evidence, then mask to candidates.
        - historical popularity: mask to candidates, then normalize.
        - recent popularity: normalize org-wide, then mask to candidates.

        If supplied, breakdowns receives normalized scores, policy weights and weighted
        contributions for each candidate, using the same values as the final score.
        """
        # 1. Similarity evidence
        # Use the peers selected by the policy. Multiply each peer's practice improvements
        # by its similarity score, then add the results for each practice and normalize.
        # Normalization divides scores by the largest value, putting them between 0 and 1.
        similarity_sum_per_practice_dict: dict = {}
        for i in self._selected_peer_indices(case, policy):
            _team, similarity, _month = case.peers[i]
            for practice, magnitude in case.peer_contributions[i].items():
                similarity_sum_per_practice_dict[practice] = (
                    similarity_sum_per_practice_dict.get(practice, 0.0) + similarity * magnitude
                )
        similarity_norm = _normalize(similarity_sum_per_practice_dict)

        # 2. Transitions evidence
        # Normalize the historical transition evidence gathered for this team.
        # Divide each transition score by the largest score to put the values between 0 and 1.
        sequence_norm = _normalize(case.sequence_raw)

        # 3. Popularity evidence
        # Normalize historical counts using only practices eligible for improvement.
        # Normalize recent counts using all practices across the organization.
        historical_popularity_masked = {p: case.historical_popularity_raw.get(p, 0.0) for p in case.candidates}
        historical_popularity_norm = _normalize(historical_popularity_masked)
        recent_popularity_norm = _normalize(case.recent_popularity_raw)

        # 4. Score each candidate practice
        # Read its evidence scores, using zero when a source has no evidence for it.
        scores: dict = {}
        for practice in case.candidates:
            sim = similarity_norm.get(practice, 0.0)
            seq = sequence_norm.get(practice, 0.0)
            recent = recent_popularity_norm.get(practice, 0.0)
            historical = historical_popularity_norm.get(practice, 0.0)
            # Mix recent and historical popularity using the policy's recency weight.
            popularity = policy.recency_weight * recent + (1.0 - policy.recency_weight) * historical
            # Multiply each evidence score by its policy weight and add them together.
            scores[practice] = (
                policy.similarity_weight * sim
                + policy.sequence_weight * seq
                + policy.popularity_weight * popularity
            )
            # 5. Optional explanation
            # Save each source's score, weight, and contribution to explain the final score.
            if breakdowns is not None:
                breakdowns[practice] = [
                    {"component": name, "score": value, "weight": weight, "contribution": value * weight}
                    for name, value, weight in (
                        ("similarity", sim, policy.similarity_weight),
                        ("transitions", seq, policy.sequence_weight),
                        ("popularity", popularity, policy.popularity_weight),
                    )
                ]
        # Return all candidate scores; the caller can use them to select the top practices.
        return scores

    def top_practices(self, case: CaseComponents, policy: Policy) -> tuple:
        """Top TOP_N candidate practices under one policy, deterministically tie-broken
        by (-score, practice_name)."""
        scores = self.score_case(case, policy)
        return tuple(sorted(scores, key=lambda p: (-scores[p], p))[:TOP_N])

    # ------------------------------------------------------------------
    # Monthly policy selection
    # ------------------------------------------------------------------

    def month_hit_rates(self, prediction_month: int) -> dict:
        """Mean HR@2 for every policy in the 675-policy grid, over this month's fixed
        evaluable cohort."""
        if prediction_month in self._hit_rate_cache:
            return self._hit_rate_cache[prediction_month]

        cases = self.evaluable_cases(prediction_month)
        rates: dict = {}
        for policy in POLICY_GRID:
            if not cases:
                rates[policy] = 0.0
                continue
            hits = sum(1 for case in cases if set(self.top_practices(case.components, policy)) & case.actual_improved)
            rates[policy] = hits / len(cases)

        self._hit_rate_cache[prediction_month] = rates
        return rates

    def _mean_rate(self, months: list, policy: Policy) -> float:
        rates = [self.month_hit_rates(m)[policy] for m in months]
        return sum(rates) / len(rates)

    def select_policy(self, prediction_month: int) -> SelectedPolicy:
        if prediction_month in self._selected_policy_cache:
            return self._selected_policy_cache[prediction_month]

        completed = self.completed_prior_months(prediction_month)
        if not completed:
            selected = SelectedPolicy(
                policy=BOOTSTRAP_POLICY, is_bootstrap=True, completed_prior_months=(), mean_prior_hit_rate=None
            )
        else:
            best_policy = max(
                POLICY_GRID,
                key=lambda p: (self._mean_rate(completed, p), *_preference_key(p)),
            )
            selected = SelectedPolicy(
                policy=best_policy,
                is_bootstrap=False,
                completed_prior_months=tuple(completed),
                mean_prior_hit_rate=self._mean_rate(completed, best_policy),
            )

        self._selected_policy_cache[prediction_month] = selected
        return selected

    def select_popularity_arm(self, prediction_month: int) -> SelectedPolicy:
        """The independently-selected pure time-aware-popularity comparison arm used by
        the backtest: 0% similarity, 0% sequence, recency weight chosen to maximize mean
        HR@2 over the same completed prior months (spec: "Backtest Reporting")."""
        if prediction_month in self._popularity_arm_cache:
            return self._popularity_arm_cache[prediction_month]

        completed = self.completed_prior_months(prediction_month)
        if not completed:
            selected = SelectedPolicy(
                policy=BOOTSTRAP_POLICY, is_bootstrap=True, completed_prior_months=(), mean_prior_hit_rate=None
            )
        else:
            best_policy = max(
                POPULARITY_ARM_POLICIES,
                key=lambda p: (self._mean_rate(completed, p), -p.recency_weight),
            )
            selected = SelectedPolicy(
                policy=best_policy,
                is_bootstrap=False,
                completed_prior_months=tuple(completed),
                mean_prior_hit_rate=self._mean_rate(completed, best_policy),
            )

        self._popularity_arm_cache[prediction_month] = selected
        return selected

    # ------------------------------------------------------------------
    # Live recommendation
    # ------------------------------------------------------------------

    def recommend(self, team: str, prediction_month: int) -> RecommendationResult:
        """Generate the live (or backtest baseline-level) recommendation for one
        team/prediction-month, using that month's selected global policy."""
        recommendable, components = self.is_recommendable(team, prediction_month)
        selected = self.select_policy(prediction_month)

        if not recommendable:
            return RecommendationResult(
                team=team,
                prediction_month=prediction_month,
                baseline_month=components.baseline_month if components else None,
                practices=(),
                scores={},
                current_levels=components.current_levels if components else {},
                selected_policy=selected,
                no_similar_teams_found=False,
                insufficient_practices=True,
            )

        scores = self.score_case(components, selected.policy)
        top = tuple(sorted(scores, key=lambda p: (-scores[p], p))[:TOP_N])
        # Whether the *selected policy's* peer subset is empty - not just whether any
        # peer exists unfiltered. A non-zero min_similarity can filter every peer out
        # even when case.peers (fetched at threshold 0.0) is non-empty.
        no_similar_teams_found = len(self._selected_peer_indices(components, selected.policy)) == 0
        return RecommendationResult(
            team=team,
            prediction_month=prediction_month,
            baseline_month=components.baseline_month,
            practices=top,
            scores=scores,
            current_levels=components.current_levels,
            selected_policy=selected,
            no_similar_teams_found=no_similar_teams_found,
            insufficient_practices=False,
        )
