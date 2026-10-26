"""Pydantic schemas for public Model Evaluation and Architecture metrics."""

from typing import Any
from pydantic import BaseModel, Field


class ConfusionMatrixData(BaseModel):
    """Confusion matrix counts."""

    true_negatives: int = Field(..., description="True negative count")
    false_positives: int = Field(..., description="False positive count")
    false_negatives: int = Field(..., description="False negative count")
    true_positives: int = Field(..., description="True positive count")


class ModelMetricsData(BaseModel):
    """Model performance metrics on validation or test split."""

    threshold: float = Field(..., description="Decision threshold applied")
    precision: float = Field(..., description="Precision score")
    recall: float = Field(..., description="Recall score")
    f1_score: float = Field(..., description="F1 harmonic score")
    pr_auc: float = Field(..., description="Area under Precision-Recall Curve")
    roc_auc: float = Field(..., description="Area under Receiver Operating Characteristic Curve")
    confusion_matrix: ConfusionMatrixData = Field(..., description="Confusion matrix values")
    cost_index: float | None = Field(None, description="Weighted asymmetric cost index")


class EvaluatedModelItem(BaseModel):
    """Evaluation summary for a specific verified model."""

    model_name: str = Field(..., description="Model identifier (e.g. RandomForest, LogisticRegression)")
    model_version: str = Field(..., description="Artifact version tag")
    model_type: str = Field(..., description="Classifier algorithm family")
    is_deployed: bool = Field(..., description="Whether this model is currently serving live inference")
    status_label: str = Field(..., description="Human-readable deployment state")
    optimal_threshold: float = Field(..., description="Threshold chosen through cost/F1 optimization")
    selected_threshold: float = Field(..., description="Operational decision threshold")
    validation_metrics: ModelMetricsData = Field(..., description="Metrics on held-out validation split")
    test_metrics: ModelMetricsData | None = Field(
        None, description="Metrics on final test set (None if not evaluated on test set)"
    )
    hyperparameters: dict[str, Any] = Field(..., description="Trained model hyperparameters")
    preprocessing: str = Field(..., description="Input transformation and feature scaling method")
    training_dataset_description: str = Field(..., description="Description of training sample distribution")


class ModelEvaluationResponse(BaseModel):
    """Complete response payload for model evaluation governance dashboard."""

    deployed_model: EvaluatedModelItem = Field(..., description="Currently active production model")
    baseline_model: EvaluatedModelItem = Field(..., description="Benchmark non-deployed baseline model")
    candidate_models: list[EvaluatedModelItem] = Field(
        default_factory=list,
        description="Comprehensive list of evaluated candidate models (RF, XGBoost, DecisionTree, KNN, LR, Clustering, NaiveBayes)",
    )
    evaluation_timestamp: str = Field(..., description="Timestamp of model comparison benchmark run")
    comparison_summary: str = Field(..., description="High-level reasoning for production model selection")
