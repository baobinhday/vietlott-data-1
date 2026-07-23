"""Data loader: reads product NDJSON into a pandas DataFrame."""

import pandas as pd
import polars as pl

from vietlott.config.products import get_config


def load_product_dataframe(name: str) -> pd.DataFrame:
    """
    Load the NDJSON history for a product into a pandas DataFrame
    compatible with `PredictModel(df=...)`.

    Parameters
    ----------
    name : Product name key (e.g. "power_655", "power_645", "power_535").

    Returns
    -------
    pd.DataFrame with at least these columns:
      - "date": datetime64[ns]
      - "result": object (each row is a list[int] of main+special numbers)
      - "id": object (draw id string)

    The DataFrame is sorted ascending by date and has a fresh
    0..N-1 integer index.

    Raises
    ------
    ValueError
        If `name` is not a registered product.
    FileNotFoundError
        If the data file does not exist.
    """
    config = get_config(name)
    if not config.raw_path.exists():
        raise FileNotFoundError(f"Data file not found: {config.raw_path}")

    pdf = pl.read_ndjson(config.raw_path)
    df = pdf.to_pandas()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    if df["result"].dtype != object:
        df["result"] = df["result"].astype(object)

    return df
