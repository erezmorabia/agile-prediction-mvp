"""
FastAPI routes for the recommendation API.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

# Thread pool executor for running blocking optimization tasks
_executor = ThreadPoolExecutor(max_workers=1)
from .models import (
    BacktestRequest,
    BacktestResponse,
    ImprovementInfo,
    OptimizationRequest,
    OptimizationResponse,
    RecommendationRequest,
    RecommendationResponse,
    SystemStats,
    TeamInfo,
)
from .service import APIService

router = APIRouter()


def create_routes(service: APIService) -> APIRouter:
    """
    Create and configure FastAPI routes for the recommendation API.

    Sets up all REST API endpoints including:
    - Team management endpoints (list teams, get team months)
    - Recommendation endpoints (get recommendations for teams)
    - Validation endpoints (backtest, optimization)
    - System information endpoints (stats, sequences)

    Args:
        service (APIService): Initialized APIService instance containing
            the recommendation engine, data processor, and related components.
            Must be fully initialized with data loaded and models trained.

    Returns:
        APIRouter: Configured FastAPI router with all endpoints registered.
            The router includes:
            - GET /api/teams - List all teams
            - GET /api/teams/with-improvements - List teams with improvements
            - GET /api/teams/{team_name}/months - Get available months for a team
            - POST /api/recommendations - Get recommendations
            - POST /api/backtest - Run backtest validation
            - POST /api/optimize - Find optimal configuration
            - POST /api/optimize/cancel - Cancel optimization
            - GET /api/optimize/latest - Get latest optimization results
            - GET /api/stats - Get system statistics
            - GET /api/sequences - Get improvement sequences

    Note:
        All endpoints are async and use Pydantic models for request/response
        validation. Error handling is done via HTTPException with appropriate
        status codes.
    """

    @router.get("/api/teams", response_model=list[TeamInfo])
    async def get_teams():
        """Get all teams with metadata."""
        try:
            return service.get_all_teams()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/teams/with-improvements", response_model=list[ImprovementInfo])
    async def get_teams_with_improvements():
        """Get teams and months where improvements occurred."""
        try:
            return service.get_teams_with_improvements()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/teams/{team_name}/months")
    async def get_team_months(team_name: str):
        """Get available months for a team."""
        try:
            months = service.get_team_months(team_name)
            if months is None:
                raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found")
            return {"team": team_name, "months": months}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/recommendations", response_model=RecommendationResponse)
    async def get_recommendations(request: RecommendationRequest):
        """Get recommendations for a team at a specific month."""
        try:
            result = service.get_recommendations(
                request.team, request.month, top_n=request.top_n, k_similar=request.k_similar
            )

            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])

            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/backtest", response_model=BacktestResponse)
    async def run_backtest(request: BacktestRequest):
        """Run backtest validation."""
        try:
            # Convert config Pydantic model to dict if present
            config_dict = None
            if request.config:
                config_dict = request.config.dict()

            result = service.run_backtest(train_ratio=request.train_ratio, config=config_dict)

            if "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])

            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/stats", response_model=SystemStats)
    async def get_system_stats():
        """Get system statistics."""
        try:
            return service.get_system_stats()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/sequences")
    async def get_improvement_sequences():
        """Get all learned improvement sequences."""
        try:
            return service.get_improvement_sequences()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/optimize", response_model=OptimizationResponse)
    async def find_optimal_config(request: OptimizationRequest):
        """Find optimal configuration by testing parameter combinations."""
        logger.info("[CANCELLATION] ===== OPTIMIZE ENDPOINT HIT =====")
        logger.info(
            f"[CANCELLATION] Service instance: {id(service)}, Optimizer instance: {id(service.optimizer_engine)}"
        )
        try:
            # Run optimization in thread pool to avoid blocking the event loop
            # This allows the cancel endpoint to be processed concurrently
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _executor,
                lambda: service.find_optimal_config(
                    min_accuracy=request.min_accuracy,
                    top_n_range=request.top_n_range,
                    similarity_weight_range=request.similarity_weight_range,
                    k_similar_range=request.k_similar_range,
                    similar_teams_lookahead_months_range=request.similar_teams_lookahead_months_range,
                    recent_improvements_months_range=request.recent_improvements_months_range,
                    min_similarity_threshold_range=request.min_similarity_threshold_range,
                    fixed_params=request.fixed_params,
                ),
            )

            # Convert to response model format
            # Only raise error if not cancelled and no config found
            if result["optimal_config"] is None and not result.get("cancelled", False):
                raise HTTPException(
                    status_code=400, detail=f"No configuration found with accuracy >= {request.min_accuracy * 100}%"
                )

            # Format all_results
            formatted_results = []
            for r in result.get("all_results", []):
                formatted_results.append(
                    {
                        "config": r["config"],
                        "model_accuracy": r["model_accuracy"],
                        "random_baseline": r["random_baseline"],
                        "improvement_gap": r["improvement_gap"],
                        "improvement_factor": r["improvement_factor"],
                        "total_predictions": r["total_predictions"],
                        "correct_predictions": r["correct_predictions"],
                    }
                )

            # Return response (even if optimal_config is None, if cancelled we want to show partial results)
            response_data = {
                "optimal_config": result.get("optimal_config"),
                "model_accuracy": result.get("model_accuracy", 0.0),
                "random_baseline": result.get("random_baseline", 0.0),
                "improvement_gap": result.get("improvement_gap", 0.0),
                "improvement_factor": result.get("improvement_factor", 0.0),
                "total_predictions": result.get("total_predictions", 0),
                "correct_predictions": result.get("correct_predictions", 0),
                "total_combinations_tested": result.get("total_combinations_tested", 0),
                "total_combinations_available": result.get(
                    "total_combinations_available", result.get("total_combinations_tested", 0)
                ),
                "valid_combinations": result.get("valid_combinations", 0),
                "all_results": formatted_results,
                "early_stopped": result.get("early_stopped", False),
                "cancelled": result.get("cancelled", False),
                "results_file": result.get("results_file"),  # Include saved file path if available
            }

            return response_data
        except HTTPException:
            raise
        except KeyboardInterrupt:
            # Handle Ctrl-C gracefully
            raise HTTPException(status_code=499, detail="Optimization cancelled by user")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/api/optimize/cancel")
    async def cancel_optimization():
        """Cancel the current optimization."""
        logger.info("[CANCELLATION] ===== CANCEL ENDPOINT HIT =====")
        try:
            logger.info("[CANCELLATION] Cancel endpoint called - requesting cancellation")
            logger.info(
                f"[CANCELLATION] Service instance: {id(service)}, Optimizer instance: {id(service.optimizer_engine)}"
            )
            logger.info(f"[CANCELLATION] Current _cancelled flag before cancel: {service.optimizer_engine._cancelled}")
            service.cancel_optimization()
            logger.info(f"[CANCELLATION] Current _cancelled flag after cancel: {service.optimizer_engine._cancelled}")
            logger.info("[CANCELLATION] Cancel endpoint completed - cancellation flag set")
            return {"status": "cancelled", "message": "Optimization cancellation requested"}
        except Exception as e:
            logger.error(f"[CANCELLATION] Error in cancel endpoint: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/optimize/latest")
    async def get_latest_optimization_results():
        """Get the latest optimization results from saved file."""
        try:
            from src.validation.optimizer import OptimizationEngine

            results = OptimizationEngine.load_latest_results()
            if results is None:
                raise HTTPException(status_code=404, detail="No optimization results found")
            return results
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading latest optimization results: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    return router
