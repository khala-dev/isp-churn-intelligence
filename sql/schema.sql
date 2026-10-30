DROP TABLE IF EXISTS fixe_billing CASCADE;
DROP TABLE IF EXISTS technical_tickets CASCADE;
DROP TABLE IF EXISTS internet_recharges CASCADE;
DROP TABLE IF EXISTS crm_subscribers CASCADE;

CREATE TABLE crm_subscribers (
    subscriber_id VARCHAR(20) PRIMARY KEY,
    landline_number VARCHAR(15) UNIQUE NOT NULL,
    wilaya VARCHAR(30) NOT NULL,
    plan_type VARCHAR(20) NOT NULL,
    speed_mbps INTEGER NOT NULL,
    monthly_price_dzd INTEGER NOT NULL,
    install_date DATE NOT NULL,
    modem_model VARCHAR(30) NOT NULL,
    acquisition_channel VARCHAR(30) NOT NULL,

    CHECK (wilaya IN ('Oran', 'Algiers', 'Constantine', 'Mascara')),
    CHECK (plan_type IN ('Idoom_ADSL', 'Idoom_Fibre')),
    CHECK (speed_mbps IN (15, 20, 50, 100, 300)),
    CHECK (monthly_price_dzd > 0)
);

CREATE TABLE internet_recharges (
    tx_id VARCHAR(20) PRIMARY KEY,
    subscriber_id VARCHAR(20) NOT NULL REFERENCES crm_subscribers(subscriber_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    amount_dzd INTEGER NOT NULL,
    payment_method VARCHAR(30) NOT NULL,
    tx_status VARCHAR(20) NOT NULL,
    days_granted INTEGER NOT NULL,

    CHECK (amount_dzd > 0),
    CHECK (tx_status IN ('SUCCESS', 'FAILED', 'TIMEOUT')),
    CHECK (days_granted IN (0, 30))
);

CREATE TABLE technical_tickets (
    ticket_id VARCHAR(20) PRIMARY KEY,
    subscriber_id VARCHAR(20) NOT NULL REFERENCES crm_subscribers(subscriber_id) ON DELETE CASCADE,
    opened_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    issue_category VARCHAR(30) NOT NULL,
    line_attenuation_db NUMERIC(5, 2) NOT NULL,

    CHECK (line_attenuation_db > 0),
    CHECK (closed_at IS NULL OR closed_at >= opened_at)
);

CREATE TABLE fixe_billing (
    invoice_id VARCHAR(20) PRIMARY KEY,
    landline_number VARCHAR(15) NOT NULL REFERENCES crm_subscribers(landline_number) ON DELETE CASCADE,
    billing_cycle VARCHAR(10) NOT NULL,
    fixe_fee_dzd INTEGER NOT NULL DEFAULT 500,
    voice_calls_dzd INTEGER NOT NULL CHECK (voice_calls_dzd >= 0),
    total_due_dzd INTEGER NOT NULL CHECK (total_due_dzd = fixe_fee_dzd + voice_calls_dzd),
    payment_status VARCHAR(15) NOT NULL CHECK (payment_status IN ('PAID', 'UNPAID', 'LATE')),
    paid_date DATE,

    CHECK (total_due_dzd >= 0)
);