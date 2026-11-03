from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
DB_URI = "postgresql+psycopg2://postgres@localhost:5432/isp_churn_db"