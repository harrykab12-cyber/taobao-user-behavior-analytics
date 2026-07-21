from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine


def load_cleaned_events(
    frame: pd.DataFrame,
    engine: Engine,
    table_name: str = "raw_user_behavior",
) -> int:
    frame.to_sql(table_name, engine, if_exists="replace", index=False, method="multi")
    return len(frame)
