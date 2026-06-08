"""Contract validation."""

from __future__ import annotations

import pandas as pd
import pytest

from module_c_forecasting_scenarios.data.contract_validate import validate_dataframe_contract
from module_c_forecasting_scenarios.data.exceptions import QAGateFailure


def test_validate_polls_clean_tracking_requires_columns() -> None:
    df = pd.DataFrame({"poll_wave_id": ["a"]})
    with pytest.raises(QAGateFailure):
        validate_dataframe_contract(df, "polls_clean_tracking_wave")
