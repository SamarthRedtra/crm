# API and System Changes (Properties & Transactions)

## 1. Completion Status Fix
* **Doctype (`Property`)**: Fixed an issue where the `completion_status` field was missing from the schema.
* **Fields**: Re-added `completion_status` to `property.json` with the options: `All`, `Ready`, and `Off-Plan`.
* **Standardization**: Corrected the casing from `Off-plan` to `Off-Plan` across the codebase to ensure filters and logic conditions evaluate correctly.
* **Agencies Link**: Updated the `off_plan_agencies` field to correctly appear when `completion_status` is `Off-Plan`.

## 2. Rent Transaction Support
* **Doctype (`Property Transaction Log`)**: Added a new `rent_type` field with options `Weekly`, `Monthly`, and `Yearly`.
* **Visibility**: Set `rent_type` to only appear when the `transaction_type` is set to `Rent`.
* **API (`transactions.py`)**:
  * **Creation (`create_transaction`)**: Now checks if a transaction is a `Rent` transaction. If true, it automatically checks the `is_rented` flag on the linked Property. It also copies the `rent_type` specified in the transaction over to the Property.
  * **Fetching (`list_transactions`, `get_transaction`)**: Included `rent_type` in the serialized response.
* **API (`properties.py`)**:
  * Added logic to map and copy verified agencies for Off-Plan properties (`verified_agencies`).

## 3. Testing
* **Transactions (`test_transactions.py`)**: Added a new test `test_create_rent_transaction_and_is_rented` to verify the creation of rent transactions perfectly updates the `is_rented` flag and `rent_type` property fields.
* **Agencies (`test_off_plan_agencies.py`)**: Updated the test assertions to match the new `Off-Plan` casing.
