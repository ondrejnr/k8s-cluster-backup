CREATE TABLE IF NOT EXISTS machines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    type VARCHAR(32) NOT NULL,
    location VARCHAR(128),
    zone VARCHAR(32),
    status VARCHAR(16) DEFAULT 'ok',
    thresholds JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    machine_id INTEGER REFERENCES machines(id),
    machine_name VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    metric VARCHAR(32) NOT NULL,
    value DOUBLE PRECISION,
    threshold DOUBLE PRECISION,
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(64),
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS thresholds (
    id SERIAL PRIMARY KEY,
    machine_type VARCHAR(32) NOT NULL,
    metric VARCHAR(32) NOT NULL,
    warning_value DOUBLE PRECISION NOT NULL,
    critical_value DOUBLE PRECISION NOT NULL,
    unit VARCHAR(16),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(machine_type, metric)
);

CREATE TABLE IF NOT EXISTS maintenance_logs (
    id SERIAL PRIMARY KEY,
    machine_id INTEGER REFERENCES machines(id),
    machine_name VARCHAR(64) NOT NULL,
    action VARCHAR(128) NOT NULL,
    performed_by VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS escalation_rules (
    id SERIAL PRIMARY KEY,
    severity VARCHAR(16) NOT NULL,
    notify_after_minutes INTEGER DEFAULT 5,
    channel VARCHAR(32) NOT NULL,
    recipients JSONB DEFAULT '[]',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_machine ON alerts(machine_id);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_machines_type ON machines(type);
CREATE INDEX IF NOT EXISTS idx_machines_status ON machines(status);

INSERT INTO thresholds (machine_type, metric, warning_value, critical_value, unit) VALUES
    ('conveyor', 'temperature', 55, 70, '°C'),
    ('conveyor', 'voltage', 120, 140, 'V'),
    ('conveyor', 'rpm', 1200, 1500, 'RPM'),
    ('generator', 'rpm', 3600, 4100, 'RPM'),
    ('generator', 'temperature', 80, 95, '°C'),
    ('generator', 'voltage', 165, 185, 'V'),
    ('pumpa', 'temperature', 70, 85, '°C'),
    ('pumpa', 'voltage', 155, 175, 'V'),
    ('pumpa', 'rpm', 3500, 4000, 'RPM'),
    ('reaktor', 'temperature', 85, 95, '°C'),
    ('reaktor', 'voltage', 160, 180, 'V'),
    ('reaktor', 'rpm', 3800, 4200, 'RPM'),
    ('valv', 'temperature', 60, 75, '°C'),
    ('valv', 'voltage', 130, 150, 'V'),
    ('valv', 'rpm', 1100, 1400, 'RPM')
ON CONFLICT DO NOTHING;

INSERT INTO machines (name, type, location, zone, status) VALUES
    ('reaktor-01', 'reaktor', 'Hala A', 'zone-1', 'ok'),
    ('reaktor-02', 'reaktor', 'Hala A', 'zone-1', 'ok'),
    ('pumpa-01', 'pumpa', 'Hala B', 'zone-2', 'ok'),
    ('pumpa-02', 'pumpa', 'Hala B', 'zone-2', 'ok'),
    ('generator-01', 'generator', 'Hala C', 'zone-3', 'ok'),
    ('conveyor-01', 'conveyor', 'Hala D', 'zone-4', 'ok'),
    ('conveyor-02', 'conveyor', 'Hala D', 'zone-4', 'ok'),
    ('valv-01', 'valv', 'Hala A', 'zone-1', 'ok'),
    ('valv-02', 'valv', 'Hala B', 'zone-2', 'ok'),
    ('valv-03', 'valv', 'Hala C', 'zone-3', 'ok')
ON CONFLICT (name) DO NOTHING;

INSERT INTO escalation_rules (severity, notify_after_minutes, channel, recipients, enabled) VALUES
    ('warning', 5, 'email', '["technik@aiot.com"]', true),
    ('critical', 1, 'sms', '["manager@aiot.com","technik@aiot.com"]', true),
    ('critical', 10, 'webhook', '["https://hooks.slack.com/aiot"]', true)
ON CONFLICT DO NOTHING;
