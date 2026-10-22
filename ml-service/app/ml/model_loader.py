"""Secure and Validated Model Artifact Loader for FraudShield AI.

Ensures only trusted, pre-validated model bundles are loaded into memory.
Validates required artifact metadata, schema compliance, and pipeline instances.
"""

import logging
from pathlib import Path
from typing import Any

import joblib
from sklearn.pipeline import Pipeline

logger = logging.getLogger("model_loader")

REQUIRED_ARTIFACT_KEYS = {
    "model_version",
    "model_type",
    "feature_names",
    "expected_feature_order",
    "selected_threshold",
    "pipeline",
}


def load_model_artifact(artifact_path: Path) -> dict[str, Any]:
    """Load and validate serialized model bundle from a trusted path.

    Args:
        artifact_path: Resolved path to the .joblib artifact.

    Returns:
        Validated metadata dictionary including the fitted Pipeline.

    Raises:
        FileNotFoundError: If artifact does not exist at specified path.
        RuntimeError: If artifact is corrupted, missing required keys, or incompatible.
    """
    if not artifact_path.exists():
        logger.error("Model artifact not found at expected location: %s", artifact_path)
        raise FileNotFoundError(
            f"Model artifact not found at: {artifact_path}. "
            f"Please run the model comparison training pipeline first: "
            f"`python training/compare_models.py`"
        )

    logger.info("Loading model artifact from: %s", artifact_path)
    try:
        artifact = joblib.load(artifact_path)
    except Exception as exc:
        logger.critical("Failed to deserialize model artifact at %s: %s", artifact_path, exc)
        raise RuntimeError(
            f"Corrupted or invalid model artifact at {artifact_path}: {exc}"
        ) from exc

    if not isinstance(artifact, dict):
        raise RuntimeError(
            f"Invalid model artifact structure: expected dict bundle, got {type(artifact).__name__}"
        )

    missing_keys = REQUIRED_ARTIFACT_KEYS - set(artifact.keys())
    if missing_keys:
        raise RuntimeError(f"Model artifact missing essential metadata keys: {missing_keys}")

    pipeline = artifact["pipeline"]
    if not isinstance(pipeline, Pipeline):
        raise RuntimeError(
            f"Model artifact 'pipeline' must be an sklearn.pipeline.Pipeline, got {type(pipeline).__name__}"
        )

    # Validate threshold is a valid probability
    threshold = artifact["selected_threshold"]
    if not isinstance(threshold, (int, float)) or not (0.0 <= threshold <= 1.0):
        raise RuntimeError(f"Invalid selected_threshold in artifact: {threshold}")

    logger.info(
        "Successfully loaded model '%s' (type: %s, threshold: %.4f)",
        artifact["model_version"],
        artifact["model_type"],
        artifact["selected_threshold"],
    )
    return artifact
