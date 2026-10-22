"""Pydantic V2 schemas for incoming transaction inference payloads.

Enforces strict input validation: rejects missing, non-finite, extra, or invalid features,
and explicitly forbids the target field 'Class'.
"""

import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionInput(BaseModel):
    """Single credit card transaction feature vector.

    Strictly forbids unexpected fields (such as 'Class') and validates that
    all values are finite numbers (rejecting NaN, inf, and -inf).
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject any extra fields (including 'Class')
        json_schema_extra={
            "example": {
                "Time": 406.0,
                "V1": -2.312226542,
                "V2": 1.951992011,
                "V3": -1.609850732,
                "V4": 3.997905588,
                "V5": -0.522187865,
                "V6": -1.426545319,
                "V7": -2.537387306,
                "V8": 1.391657248,
                "V9": -2.770089277,
                "V10": -2.772272145,
                "V11": 3.202033207,
                "V12": -2.899907388,
                "V13": -0.595221881,
                "V14": -4.289253782,
                "V15": 0.38972412,
                "V16": -1.14074718,
                "V17": -2.830055675,
                "V18": -0.016822468,
                "V19": 0.416955705,
                "V20": 0.126910559,
                "V21": 0.517232371,
                "V22": -0.035049369,
                "V23": -0.465211076,
                "V24": 0.320198198,
                "V25": 0.044519167,
                "V26": 0.177839798,
                "V27": 0.261145003,
                "V28": -0.143275875,
                "Amount": 0.0,
            }
        },
    )

    Time: float = Field(..., description="Seconds elapsed since the first transaction in dataset")
    V1: float = Field(..., description="PCA transformed feature 1")
    V2: float = Field(..., description="PCA transformed feature 2")
    V3: float = Field(..., description="PCA transformed feature 3")
    V4: float = Field(..., description="PCA transformed feature 4")
    V5: float = Field(..., description="PCA transformed feature 5")
    V6: float = Field(..., description="PCA transformed feature 6")
    V7: float = Field(..., description="PCA transformed feature 7")
    V8: float = Field(..., description="PCA transformed feature 8")
    V9: float = Field(..., description="PCA transformed feature 9")
    V10: float = Field(..., description="PCA transformed feature 10")
    V11: float = Field(..., description="PCA transformed feature 11")
    V12: float = Field(..., description="PCA transformed feature 12")
    V13: float = Field(..., description="PCA transformed feature 13")
    V14: float = Field(..., description="PCA transformed feature 14")
    V15: float = Field(..., description="PCA transformed feature 15")
    V16: float = Field(..., description="PCA transformed feature 16")
    V17: float = Field(..., description="PCA transformed feature 17")
    V18: float = Field(..., description="PCA transformed feature 18")
    V19: float = Field(..., description="PCA transformed feature 19")
    V20: float = Field(..., description="PCA transformed feature 20")
    V21: float = Field(..., description="PCA transformed feature 21")
    V22: float = Field(..., description="PCA transformed feature 22")
    V23: float = Field(..., description="PCA transformed feature 23")
    V24: float = Field(..., description="PCA transformed feature 24")
    V25: float = Field(..., description="PCA transformed feature 25")
    V26: float = Field(..., description="PCA transformed feature 26")
    V27: float = Field(..., description="PCA transformed feature 27")
    V28: float = Field(..., description="PCA transformed feature 28")
    Amount: float = Field(..., description="Transaction amount in currency units", ge=0.0)

    @field_validator("*", mode="after")
    @classmethod
    def check_finite(cls, v: Any) -> Any:
        """Reject NaN, inf, and -inf values."""
        if isinstance(v, (int, float)):
            if not math.isfinite(v):
                raise ValueError("Values must be finite numbers (NaN, inf, and -inf are rejected)")
        return v


class BatchTransactionInput(BaseModel):
    """Batch input schema with bounded payload size."""

    model_config = ConfigDict(extra="forbid")

    transactions: list[TransactionInput] = Field(
        ...,
        description="List of transaction records for batch prediction",
        min_length=1,
    )
