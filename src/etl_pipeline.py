from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
DB_URI = "postgresql+psycopg2://postgres@localhost:5432/isp_churn_db"

def clean_crm_subscribers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates(subset=["subscriber_id"]).copy()
    df["landline_number"] = df["landline_number"].astype(str).str.zfill(9)

    conditions = [
        df["wilaya"].str.contains("alg", case=False, na=False),
        df["wilaya"].str.contains("oran", case=False, na=False),
        df["wilaya"].str.contains("const", case=False, na=False),
        df["wilaya"].str.contains("masc", case=False, na=False),
    ]
    choices = ["Algiers", "Oran", "Constantine", "Mascara"]
    df["wilaya"] = np.select(conditions, choices, default="Unknown")

    plan_price_to_speed = {
        ("Idoom_ADSL", 2000): 15,
        ("Idoom_ADSL", 2200): 20,
        ("Idoom_Fibre", 2000): 60,
        ("Idoom_Fibre", 2200): 120,
        ("Idoom_Fibre", 2600): 180,
        ("Idoom_Fibre", 3000): 240,
        ("Idoom_Fibre", 4200): 300,
    }
    df["speed_mbps"] = [
        plan_price_to_speed.get((plan, price))
        for plan, price in zip(df["plan_type"], df["monthly_price_dzd"])
    ]

    df["install_date"] = pd.to_datetime(df["install_date"]).dt.date
    return df


def clean_internet_recharges(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    failed_mask = df["tx_status"] != "SUCCESS"
    df.loc[failed_mask, "amount_dzd"] = 0
    return df


def clean_technical_tickets(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["opened_at"] = pd.to_datetime(df["opened_at"])
    df["closed_at"] = pd.to_datetime(df["closed_at"])
    inverted_mask = df["closed_at"] < df["opened_at"]
    df.loc[inverted_mask, "closed_at"] = pd.NaT
    return df


def clean_fixe_billing(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["landline_number"] = df["landline_number"].astype(str).str.zfill(9)
    df["paid_date"] = pd.to_datetime(df["paid_date"]).dt.date
    return df

def run_pipeline():
    print("[INFO] 1/3 Extracting raw CSV files...")
    df_crm_raw = pd.read_csv(RAW_DATA_DIR / "crm_subscribers.csv")
    df_rech_raw = pd.read_csv(RAW_DATA_DIR / "internet_recharges.csv")
    df_tkt_raw = pd.read_csv(RAW_DATA_DIR / "technical_tickets.csv")
    df_fixe_raw = pd.read_csv(RAW_DATA_DIR / "fixe_billing.csv")

    print("[INFO] 2/3 Transforming and cleaning datasets...")
    df_crm = clean_crm_subscribers(df_crm_raw)
    df_rech = clean_internet_recharges(df_rech_raw)
    df_tkt = clean_technical_tickets(df_tkt_raw)
    df_fixe = clean_fixe_billing(df_fixe_raw)

    print("[INFO] 3/3 Loading clean tables into PostgreSQL...")
    engine = create_engine(DB_URI)

    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE fixe_billing, technical_tickets, "
                "internet_recharges, crm_subscribers CASCADE;"
            )
        )

        df_crm.to_sql("crm_subscribers", con=conn, if_exists="append", index=False)
        df_rech.to_sql("internet_recharges", con=conn, if_exists="append", index=False)
        df_tkt.to_sql("technical_tickets", con=conn, if_exists="append", index=False)
        df_fixe.to_sql("fixe_billing", con=conn, if_exists="append", index=False)

    print("[SUCCESS] ETL Pipeline completed successfully!")


if __name__ == "__main__":
    run_pipeline()