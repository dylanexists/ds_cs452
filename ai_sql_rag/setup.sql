CREATE TABLE tenant (
    tenant_id BIGINT PRIMARY KEY,
    first_name VARCHAR(30) NOT NULL,
    last_name VARCHAR(40) NOT NULL,
    phone_number VARCHAR(20)
);

CREATE TABLE unitaddress (
    unitaddress_id BIGINT PRIMARY KEY,
    street_address VARCHAR(255) NOT NULL,
    apt_number VARCHAR(10),
    city VARCHAR(50) NOT NULL,
    region VARCHAR(20) NOT NULL,
    zip CHAR(5) NOT NULL
);

CREATE TABLE rentalunit (
    rentalunit_id BIGINT PRIMARY KEY,
    unitaddress_id BIGINT NOT NULL,
    room_count DECIMAL(3,1),
    bath_count DECIMAL(3,1),
    square_footage SMALLINT,
    FOREIGN KEY (unitaddress_id) REFERENCES unitaddress (unitaddress_id)
);

CREATE TABLE leasingperiod (
    leasingperiod_id BIGINT PRIMARY KEY,
    rentalunit_id BIGINT NOT NULL,
    FOREIGN KEY (rentalunit_id) REFERENCES rentalunit (rentalunit_id)
);

CREATE TABLE lease (
    lease_id BIGINT PRIMARY KEY,
    leasingperiod_id BIGINT NOT NULL,
    begin_date DATE NOT NULL,
    original_end_date DATE NOT NULL,
    updated_end_date DATE,
    rent_amount_dollars INT NOT NULL,
    FOREIGN KEY (leasingperiod_id) REFERENCES leasingperiod (leasingperiod_id)
);

CREATE TABLE portal (
    portal_id BIGINT PRIMARY KEY,
    leasingperiod_id BIGINT NOT NULL,
    is_autopay_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (leasingperiod_id) REFERENCES leasingperiod (leasingperiod_id)
);

CREATE TABLE payment (
    payment_id BIGINT PRIMARY KEY,
    portal_id BIGINT NOT NULL,
    payment_amount_dollars INT NOT NULL,
    payment_date DATE NOT NULL,
    FOREIGN KEY (portal_id) REFERENCES portal (portal_id)
);

CREATE TABLE charge (
    charge_id BIGINT PRIMARY KEY,
    portal_id BIGINT NOT NULL,
    charge_type VARCHAR(20) NOT NULL,
    charge_amount_dollars INT NOT NULL,
    due_date DATE NOT NULL,
    payment_id BIGINT,
    FOREIGN KEY (portal_id) REFERENCES portal (portal_id),
    FOREIGN KEY (payment_id) REFERENCES payment (payment_id)
);

CREATE TABLE leasingperiod_tenant (
    leasingperiod_id BIGINT NOT NULL,
    tenant_id BIGINT NOT NULL,
    is_primary_contact BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (leasingperiod_id, tenant_id),
    FOREIGN KEY (leasingperiod_id) REFERENCES leasingperiod (leasingperiod_id),
    FOREIGN KEY (tenant_id) REFERENCES tenant (tenant_id)
);