-- Mock data for the schema in setup.sql.
-- Run setup.sql first, then run this file.
-- Amounts are whole dollars, matching the *_amount_dollars INT columns.
-- The current schema has no payment tenant_id column, so individual payers
-- cannot be distinguished when multiple tenants share a leasing period.

-- Mock Overview:
-- 1. (lp 301, portal 501) 2 tenants, rentalunit (201), 1 lease (401), 4 charges, 3 paid in 2 payments
-- 2. (lp 302, portal 502) 3 tenants, rentalunit (202), 2 lease (402,403), 5 charges, 4 paid in 2 payments
-- 3. (lp 303, portal 503) 1 tenant, rentalunit (203), 1 lease (404), 2 charges, 1 paid in 1 payment

BEGIN;

INSERT INTO tenant (tenant_id, first_name, last_name, phone_number) VALUES
    (1, 'Alex', 'Morgan', "+19095654433"),
    (2, 'Jamie', 'Morgan', NULL),
    (3, 'Taylor', 'Reed', NULL),
    (4, 'Casey', 'Reed', "+15596063202"),
    (5, 'Jordan', 'Reed', NULL),
    (6, 'Riley', 'Chen', "+18014547578");

INSERT INTO unitaddress (unitaddress_id, street_address, apt_number, city, region, zip) VALUES
    (101, '1200 Maple Street', '1A', 'Provo', 'UT', '84601'),
    (102, '45 Canyon Road', NULL, 'Orem', 'UT', '84057'),
    (103, '880 West Center Street', '3B', 'Springville', 'UT', '84663');

INSERT INTO rentalunit (rentalunit_id, unitaddress_id, room_count, bath_count, square_footage) VALUES
    (201, 101, 2.0, 1.0, 850),
    (202, 102, 3.0, 2.0, 1240),
    (203, 103, 1.0, 1.0, 620);

INSERT INTO leasingperiod (leasingperiod_id, rentalunit_id) VALUES
    (301, 201),
    (302, 202),
    (303, 203);

-- Leasing period 302 has two consecutive leases to model a renewal.
INSERT INTO lease (lease_id, leasingperiod_id, begin_date, original_end_date, updated_end_date, rent_amount_dollars) VALUES
    (401, 301, '2025-01-01', '2025-12-31', NULL, 1200),
    (402, 302, '2024-07-01', '2025-06-30', '2025-08-31', 1400),
    (403, 302, '2025-09-01', '2026-08-31', NULL, 1450),
    (404, 303, '2025-04-01', '2026-03-31', NULL, 950);

INSERT INTO leasingperiod_tenant (leasingperiod_id, tenant_id, is_primary_contact) VALUES
    (301, 1, TRUE),
    (301, 2, FALSE),
    (302, 3, TRUE),
    (302, 4, FALSE),
    (302, 5, FALSE),
    (303, 6, TRUE);

INSERT INTO portal (portal_id, leasingperiod_id, is_autopay_enabled) VALUES
    (501, 301, TRUE),
    (502, 302, FALSE),
    (503, 303, TRUE);

-- Each payment amount equals the sum of its linked charges below.
INSERT INTO payment (payment_id, portal_id, payment_amount_dollars, payment_date) VALUES
    (601, 501, 1300, '2025-01-02'), -- 1200 rent + 100 utilities
    (602, 501, 75,   '2025-02-03'), -- 75 late fee, paid after its due date
    (603, 502, 1450, '2025-06-30'), -- 1400 rent + 50 utilities
    (604, 502, 1475, '2025-09-01'), -- 1450 rent + 25 utilities
    (605, 503, 1000, '2025-04-01'); -- 950 rent + 50 utilities

INSERT INTO charge (charge_id, portal_id, charge_type, charge_amount_dollars, due_date, payment_id) VALUES
    (701, 501, 'rent', 1200, '2025-01-01', 601),
    (702, 501, 'utilities', 100, '2025-01-01', 601),
    (703, 501, 'latefee', 75, '2025-02-01', 602),
    (704, 501, 'utilities', 90, '2025-03-01', NULL), -- unpaid charge
    (705, 502, 'rent', 1400, '2025-06-30', 603),
    (706, 502, 'utilities', 50, '2025-06-30', 603),
    (707, 502, 'rent', 1450, '2025-09-01', 604),
    (708, 502, 'utilities', 25, '2025-09-01', 604),
    (709, 502, 'utilities', 60, '2025-10-01', NULL), -- unpaid charge
    (710, 503, 'rent', 950, '2025-04-01', 605),
    (711, 503, 'utilities', 50, '2025-04-01', 605);

COMMIT;
