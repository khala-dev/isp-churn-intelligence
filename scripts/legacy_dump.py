import os
import numpy as np
import pandas as pd


def _run_dump():
    rng = np.random.default_rng(42)
    os.makedirs("data/raw", exist_ok=True)
    n = 1500

    w_map = {
        "Oran": (["Oran", "31 - Oran", "ORAN ", "oran"], "041"),
        "Algiers": (["Algiers", "16 - Alger", "Alger", "ALGIERS"], "021"),
        "Constantine": (["Constantine", "25 - Constantine", "CONSTANTINE"], "031"),
        "Mascara": (["Mascara", "29 - Mascara", "mascara ", "MASCARA"], "045"),
    }
    w_keys = list(w_map.keys())
    w_probs = [0.32, 0.35, 0.20, 0.13]

    plans = [
        ("Idoom_Fibre", 15, 2000),
        ("Idoom_Fibre", 20, 2200),
        ("Idoom_Fibre", 50, 2600),
        ("Idoom_Fibre", 100, 3000),
        ("Idoom_Fibre", 300, 4200),
        ("Idoom_ADSL", 15, 2000),
        ("Idoom_ADSL", 20, 2200),
    ]
    p_probs = [0.22, 0.25, 0.20, 0.12, 0.05, 0.10, 0.06]
    modems = ["Huawei_HG8245H", "ZTE_F660", "Nokia_G240W", "DLink_DSL2750U"]
    channels = ["Commercial_Agency", "Online_Portal", "Door_to_Door"]

    crm_rows, _meta = [], []
    used_phones = set()

    for i in range(n):
        sid = f"SUB-{10000 + i}"
        w_clean = rng.choice(w_keys, p=w_probs)
        w_dirty = rng.choice(w_map[w_clean][0])
        prefix = w_map[w_clean][1]

        while True:
            ph = f"{prefix}{rng.integers(100000, 999999)}"
            if ph not in used_phones:
                used_phones.add(ph)
                break

        p_idx = rng.choice(len(plans), p=p_probs)
        p_type, spd, prc = plans[p_idx]

        spd_val = str(spd)
        r_spd = rng.random()
        if r_spd < 0.04:
            spd_val = f"{spd} Mbps"
        elif r_spd < 0.06:
            spd_val = np.nan

        inst_days = int(rng.integers(365, 1400))
        inst_dt = pd.Timestamp("2025-01-01") - pd.Timedelta(days=inst_days)
        mdm = modems[3] if p_type == "Idoom_ADSL" else rng.choice(modems[:3])
        chn = rng.choice(channels, p=[0.65, 0.25, 0.10])

        pref_online = rng.random() < (0.62 if w_clean in ["Algiers", "Oran"] else 0.42)
        base_risk = 0.08 + (0.18 if p_type == "Idoom_ADSL" else 0.0) + (0.12 if not pref_online else 0.0)
        is_bad_line = rng.random() < 0.22
        if is_bad_line:
            base_risk += 0.38
        will_churn = rng.random() < min(base_risk, 0.85)

        crm_rows.append(
            {
                "subscriber_id": sid,
                "landline_number": ph,
                "wilaya": w_dirty,
                "plan_type": p_type,
                "speed_mbps": spd_val,
                "monthly_price_dzd": prc,
                "install_date": inst_dt.strftime("%Y-%m-%d"),
                "modem_model": mdm,
                "acquisition_channel": chn,
            }
        )
        _meta.append((sid, ph, prc, pref_online, is_bad_line, will_churn))

    df_crm = pd.DataFrame(crm_rows)
    dups = df_crm.sample(n=23, random_state=7)
    df_crm = pd.concat([df_crm, dups], ignore_index=True).sample(frac=1.0, random_state=42).reset_index(drop=True)
    df_crm.to_csv("data/raw/crm_subscribers.csv", index=False)

    rech_rows, tkt_rows, fixe_rows = [], [], []
    tx_counter, tkt_counter, inv_counter = 500000, 90000, 700000

    for sid, ph, prc, pref_online, is_bad_line, will_churn in _meta:
        cur_dt = pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(rng.integers(0, 28)))
        cutoff_dt = (
            pd.Timestamp("2025-12-31")
            if not will_churn
            else pd.Timestamp("2025-07-15") + pd.Timedelta(days=int(rng.integers(0, 105)))
        )

        cycle_num = 0
        while cur_dt <= cutoff_dt:
            cycle_num += 1
            use_online = rng.random() < (0.85 if pref_online else 0.15)
            pmethod = rng.choice(["Edahabia_Online", "CIB_Online"]) if use_online else "Agency_Cash"

            hr = int(rng.integers(8, 23)) if use_online else int(rng.integers(8, 16))
            mn = int(rng.integers(0, 59))
            ts = cur_dt + pd.Timedelta(hours=hr, minutes=mn)

            if use_online and rng.random() < 0.09:
                tx_counter += 1
                rech_rows.append(
                    {
                        "tx_id": f"TX-{tx_counter}",
                        "subscriber_id": sid,
                        "timestamp": (ts - pd.Timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S"),
                        "amount_dzd": prc,
                        "payment_method": pmethod,
                        "tx_status": rng.choice(["FAILED", "TIMEOUT"]),
                        "days_granted": 0,
                    }
                )

            tx_counter += 1
            rech_rows.append(
                {
                    "tx_id": f"TX-{tx_counter}",
                    "subscriber_id": sid,
                    "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "amount_dzd": prc,
                    "payment_method": pmethod,
                    "tx_status": "SUCCESS",
                    "days_granted": 30,
                }
            )

            exp_dt = cur_dt + pd.Timedelta(days=30)
            if will_churn:
                gap = int(rng.integers(2, 6) * cycle_num) + (3 if not use_online else 0)
            else:
                if use_online:
                    gap = int(rng.choice([0, 0, 0, 1, 2]))
                else:
                    is_wknd = exp_dt.dayofweek in [3, 4]
                    gap = int(rng.integers(2, 5)) if is_wknd else int(rng.choice([0, 1, 2, 3]))

            cur_dt = exp_dt + pd.Timedelta(days=gap)

        n_tkts = int(rng.poisson(3.2 if is_bad_line else (1.8 if will_churn else 0.45)))
        for _ in range(n_tkts):
            tkt_counter += 1
            o_dt = pd.Timestamp("2025-01-05") + pd.Timedelta(
                days=int(rng.integers(0, 340)), hours=int(rng.integers(8, 20))
            )
            res_hrs = float(rng.uniform(24, 140) if (is_bad_line or will_churn) else rng.uniform(2, 36))
            c_dt = o_dt + pd.Timedelta(hours=res_hrs)

            r_bug = rng.random()
            if r_bug < 0.03:
                c_str = (o_dt - pd.Timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S")
            elif r_bug < 0.08:
                c_str = np.nan
            else:
                c_str = c_dt.strftime("%Y-%m-%d %H:%M:%S")

            cat = rng.choice(
                ["Fibre_Cut", "High_Attenuation", "Fixe_No_Dialtone", "Modem_Sync", "Billing_Dispute"],
                p=[0.30, 0.28, 0.20, 0.14, 0.08] if is_bad_line else [0.12, 0.15, 0.15, 0.38, 0.20],
            )
            att = round(float(rng.normal(29.5 if is_bad_line else 18.2, 3.1)), 1)

            tkt_rows.append(
                {
                    "ticket_id": f"TKT-{tkt_counter}",
                    "subscriber_id": sid,
                    "opened_at": o_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "closed_at": c_str,
                    "issue_category": cat,
                    "line_attenuation_db": att,
                }
            )

        for b_idx in range(1, 7):
            inv_counter += 1
            calls_dzd = int(rng.choice([0, 0, 150, 320, 680, 1200]))
            fixe_fee = 500
            tot = fixe_fee + calls_dzd
            due_month = b_idx * 2
            due_dt = pd.Timestamp(f"2025-{due_month:02d}-15")

            if will_churn and b_idx >= 5:
                st_fixe = "UNPAID"
                p_dt = np.nan
            else:
                st_fixe = rng.choice(["PAID", "LATE", "UNPAID"], p=[0.82, 0.13, 0.05])
                if st_fixe == "UNPAID":
                    p_dt = np.nan
                elif st_fixe == "PAID":
                    p_dt = (due_dt - pd.Timedelta(days=int(rng.integers(0, 10)))).strftime("%Y-%m-%d")
                else:
                    p_dt = (due_dt + pd.Timedelta(days=int(rng.integers(5, 25)))).strftime("%Y-%m-%d")

            fixe_rows.append(
                {
                    "invoice_id": f"INV-{inv_counter}",
                    "landline_number": ph,
                    "billing_cycle": f"2025-B{b_idx}",
                    "fixe_fee_dzd": fixe_fee,
                    "voice_calls_dzd": calls_dzd,
                    "total_due_dzd": tot,
                    "payment_status": st_fixe,
                    "paid_date": p_dt,
                }
            )

    pd.DataFrame(rech_rows).to_csv("data/raw/internet_recharges.csv", index=False)
    pd.DataFrame(tkt_rows).to_csv("data/raw/technical_tickets.csv", index=False)
    pd.DataFrame(fixe_rows).to_csv("data/raw/fixe_billing.csv", index=False)
    print("[INFO] Raw system dump completed into data/raw/ (4 files generated).")


if __name__ == "__main__":
    _run_dump()