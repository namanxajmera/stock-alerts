"""Custom JSON encoder for handling NumPy and pandas data types."""

import json
from typing import Any

import numpy as np
import pandas as pd


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NaN/Infinity values."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super().default(obj)
