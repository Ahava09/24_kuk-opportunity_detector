CREATE TABLE mail_type (
    id SERIAL PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL UNIQUE
);

INSERT INTO mail_type (type_name) VALUES 
('All'),
('Type negoce industries'),
('Maintenance'),
('Support'),
('Personal'),
('Spam');



CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    subject VARCHAR(255) NOT NULL,
    sender VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    receive_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    path VARCHAR,
    percentage DOUBLE PRECISION DEFAULT 0,
    mail_type_id INTEGER REFERENCES mail_type(id) ON DELETE SET NULL
);

create table state (
    id SERIAL PRIMARY KEY,
    name_state VARCHAR(255) NOT NULL UNIQUE
);

-- Insérer des états dans la table state
INSERT INTO state (name_state) VALUES 
('Nouveau Client'),
('Accepté'),
('Refusé'),
('En Attente'),
('Archivé');


create table emails_state (
    id SERIAL PRIMARY KEY,
    emails_id INTEGER REFERENCES emails(id) ON DELETE CASCADE,
    state_id INTEGER REFERENCES state(id) ON DELETE SET NULL
);

-- Création de la table res_country (nécessaire pour les relations)
CREATE TABLE res_country (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    code VARCHAR(10) UNIQUE NOT NULL
);

-- Création de la table res_currency (nécessaire pour les relations)
CREATE TABLE res_currency (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    symbol VARCHAR(5) NOT NULL
);

CREATE TABLE res_company (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    street VARCHAR(255),
    city VARCHAR(100),
    zip VARCHAR(20),
    -- country_id INTEGER REFERENCES res_country(id) ON DELETE SET NULL,
    phone VARCHAR(50),
    email VARCHAR(255) UNIQUE,
    website VARCHAR(255),
    logo BYTEA,
    -- currency_id INTEGER REFERENCES res_currency(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO res_company (name, street, city, zip, phone, email, website, created_at) VALUES
('Tech Solutions', '123 Rue de la Paix', 'Paris', '75001', '+33123456789', 'contact@techsolutions.com', 'https://www.techsolutions.com', NOW()),
('Green Energy', '45 Boulevard Haussmann', 'Paris', '75008', '+33987654321', 'info@greenenergy.com', 'https://www.greenenergy.com', NOW()),
('NextGen Innovations', '99 Avenue des Champs', 'Lyon', '69002', '+33412345678', 'hello@nextgen.com', 'https://www.nextgen.com', NOW()),
('Global Finance', '200 Wall Street', 'New York', '10005', '+12125559999', 'support@globalfinance.com', 'https://www.globalfinance.com', NOW()),
('Creative Agency', '77 Rue Saint-Honoré', 'Marseille', '13001', '+33611223344', 'contact@creativeagency.com', 'https://www.creativeagency.com', NOW());

-- INSERT INTO res_country (id, name, code) VALUES
-- (1, 'France', 'FR'),
-- (2, 'United States', 'US'),
-- (3, 'United Kingdom', 'GB');

-- INSERT INTO res_currency (id, name, symbol) VALUES
-- (1, 'Euro', '€'),
-- (2, 'US Dollar', '$'),
-- (3, 'British Pound', '£');

CREATE TABLE res_partner (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    is_company BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


INSERT INTO res_partner (name, email, phone, is_company, created_at) VALUES
('John Doe', 1, 'john.doe@techsolutions.com', '+33678901234', FALSE, NOW()),
('Jane Smith', 1, 'jane.smith@techsolutions.com', '+33678905678', FALSE, NOW()),
('Global Investors', 2, 'info@globalinvestors.com', '+12125558888', TRUE, NOW());

CREATE TABLE emails_partner (
    id SERIAL PRIMARY KEY,
    partner_id INTEGER REFERENCES res_partner(id) ON DELETE CASCADE,
    emails_id INTEGER REFERENCES emails(id) ON DELETE CASCADE
);

create table partner_company (
    id  SERIAL PRIMARY KEY,
    partner_id INTEGER REFERENCES res_partner(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES res_company(id) ON DELETE CASCADE
);

delete from emails_state;
delete from res_company;
delete from partner_company;
delete from emails_state;
delete from res_partner;
delete from emails;
