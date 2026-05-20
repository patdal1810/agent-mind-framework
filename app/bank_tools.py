TRANSACTIONS = {
    "TXN1001": {
        "transaction_id": "TXN1001",
        "customer": "Ada Johnson",
        "amount": 75.50,
        "country": "Nigeria",
        "usual_country": "Nigeria",
        "merchant": "Shoprite",
        "hour": 14,
        "average_spend": 120.00,
    },
    "TXN1002": {
        "transaction_id": "TXN1002",
        "customer": "Ada Johnson",
        "amount": 4500.00,
        "country": "Russia",
        "usual_country": "Nigeria",
        "merchant": "Unknown Crypto Exchange",
        "hour": 2,
        "average_spend": 120.00,
    },
}


LOAN_APPLICATIONS = {
    "LOAN2001": {
        "application_id": "LOAN2001",
        "customer": "Samuel Okoro",
        "monthly_income": 900000,
        "requested_amount": 2000000,
        "credit_score": 720,
        "existing_debt": 150000,
    },
    "LOAN2002": {
        "application_id": "LOAN2002",
        "customer": "Tina Bello",
        "monthly_income": 250000,
        "requested_amount": 5000000,
        "credit_score": 540,
        "existing_debt": 700000,
    },
}


def transaction_lookup_tool(input_data: dict):
    transaction_id = input_data.get("transaction_id")

    if not transaction_id:
        raise ValueError("transaction_id is required.")

    transaction = TRANSACTIONS.get(transaction_id)

    if not transaction:
        raise ValueError("Transaction not found.")

    return {
        "transaction": transaction,
    }


def fraud_checker_tool(input_data: dict):
    transaction = input_data.get("transaction")

    if not transaction:
        raise ValueError("transaction is required.")

    risk_score = 0
    reasons = []

    if transaction["amount"] > transaction["average_spend"] * 10:
        risk_score += 40
        reasons.append("Amount is more than 10x normal spending.")

    if transaction["country"] != transaction["usual_country"]:
        risk_score += 30
        reasons.append("Transaction country differs from usual country.")

    if transaction["hour"] < 5:
        risk_score += 15
        reasons.append("Transaction happened at unusual late-night hour.")

    if "crypto" in transaction["merchant"].lower():
        risk_score += 15
        reasons.append("Merchant is crypto-related and high risk.")

    if risk_score >= 70:
        decision = "high_risk"
    elif risk_score >= 40:
        decision = "medium_risk"
    else:
        decision = "low_risk"

    return {
        "risk_score": risk_score,
        "decision": decision,
        "reasons": reasons or ["No strong fraud signals detected."],
    }


def loan_evaluator_tool(input_data: dict):
    application_id = input_data.get("application_id")

    if not application_id:
        raise ValueError("application_id is required.")

    application = LOAN_APPLICATIONS.get(application_id)

    if not application:
        raise ValueError("Loan application not found.")

    monthly_income = application["monthly_income"]
    requested_amount = application["requested_amount"]
    credit_score = application["credit_score"]
    existing_debt = application["existing_debt"]

    debt_to_income = existing_debt / monthly_income
    loan_to_income = requested_amount / monthly_income

    reasons = []

    if credit_score < 650:
        reasons.append("Credit score is below preferred approval threshold.")

    if debt_to_income > 0.4:
        reasons.append("Debt-to-income ratio is too high.")

    if loan_to_income > 12:
        reasons.append("Requested loan is too large compared to monthly income.")

    approved = (
        credit_score >= 650
        and debt_to_income <= 0.4
        and loan_to_income <= 12
    )

    return {
        "application": application,
        "decision": "approved" if approved else "rejected",
        "debt_to_income": round(debt_to_income, 2),
        "loan_to_income": round(loan_to_income, 2),
        "reasons": reasons or ["Applicant meets basic approval rules."],
    }