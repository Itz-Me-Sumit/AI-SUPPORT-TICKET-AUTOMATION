"""Labeled questions for the retrieval evaluation.

Each positive case is (question, expected file, acceptable heading fragments).
"""

# Questions written close to the document wording (easy).
EASY = [
    ("How much does the Business plan cost?", "01_plans_and_pricing.md", ["Business plan"]),
    ("What does the Pro plan include?", "01_plans_and_pricing.md", ["Pro plan"]),
    ("Do you have a group plan?", "01_plans_and_pricing.md", ["Group and team plans"]),
    ("Is there a discount for students?", "01_plans_and_pricing.md", ["Student and education discount"]),
    ("Can I try it for free before buying?", "01_plans_and_pricing.md", ["Free trial"]),
    ("How much do I save if I pay yearly?", "01_plans_and_pricing.md", ["Annual plan discount"]),
    ("What payment methods do you accept?", "02_billing_and_payments.md", ["Accepted payment methods"]),
    ("I was charged twice, what should I do?", "02_billing_and_payments.md", ["Charged twice"]),
    ("My invoice has the wrong tax number", "02_billing_and_payments.md", ["Wrong amount on an invoice"]),
    ("What happens if my card payment fails?", "02_billing_and_payments.md", ["Failed payments"]),
    ("Can I get my money back after two weeks?", "03_refunds_and_cancellation.md", ["Refunds after 14 days", "Full refund within 14 days"]),
    ("How long until the refund shows up in my account?", "03_refunds_and_cancellation.md", ["How long refunds take"]),
    ("How do I cancel my subscription?", "03_refunds_and_cancellation.md", ["How to cancel"]),
    ("Can I pause my annual plan instead of cancelling?", "03_refunds_and_cancellation.md", ["Pausing an annual plan"]),
    ("I forgot my password", "04_account_and_security.md", ["Resetting a password"]),
    ("How many wrong passwords before my account locks?", "04_account_and_security.md", ["Locked account"]),
    ("Someone logged into my account from another country", "04_account_and_security.md", ["Suspected unauthorized access"]),
    ("How do I turn on two factor authentication?", "04_account_and_security.md", ["Two factor authentication"]),
    ("The app crashes whenever I open settings", "05_troubleshooting.md", ["App crashes when opening a page"]),
    ("CSV export keeps timing out", "05_troubleshooting.md", ["Export to CSV fails or times out"]),
    ("Everything is down and I see a 503 error", "05_troubleshooting.md", ["Service down or error 503"]),
    ("What are your support hours?", "06_support_and_escalation.md", ["Support hours"]),
    ("How quickly will you reply to an email on the Pro plan?", "06_support_and_escalation.md", ["Response times by plan"]),
    ("Which problems need a human agent?", "06_support_and_escalation.md", ["What needs a human agent"]),
    ("How do I delete my account and data?", "07_privacy_and_data.md", ["Deleting an account and personal data"]),
]

# Paraphrased, spoken-style and slightly noisy questions, like a phone caller.
HARD = [
    ("what is the price of the current group plan", "01_plans_and_pricing.md", ["Group and team plans"]),
    ("so tell me how long does the refund take", "03_refunds_and_cancellation.md", ["How long refunds take"]),
    ("my team has fifteen people which plan should we take", "01_plans_and_pricing.md", ["Business plan"]),
    ("can a student pay less", "01_plans_and_pricing.md", ["Student and education discount"]),
    ("how do i get out of my plan", "03_refunds_and_cancellation.md", ["How to cancel"]),
    ("somebody else is using my login", "04_account_and_security.md", ["Suspected unauthorized access"]),
    ("i cannot sign in even after changing the password twice", "04_account_and_security.md", ["Invalid credentials after a reset"]),
    ("the app keeps closing by itself on my phone", "05_troubleshooting.md", ["App crashes when opening a page"]),
    ("i am not getting alerts on my iphone", "05_troubleshooting.md", ["Push notifications not arriving"]),
    ("my upload stops at ninety nine percent", "05_troubleshooting.md", ["File upload fails"]),
    ("what time does live support open", "06_support_and_escalation.md", ["Support hours"]),
    ("does the assistant give discounts", "06_support_and_escalation.md", ["What needs a human agent"]),
    ("is my data encrypted", "07_privacy_and_data.md", ["How data is protected"]),
    ("do you sell my information to anyone", "07_privacy_and_data.md", ["Data sharing"]),
    ("can i add more storage", "01_plans_and_pricing.md", ["Extra storage"]),
    ("what happens to my account if payment keeps failing", "02_billing_and_payments.md", ["Failed payments"]),
    ("will the price go up without telling me", "02_billing_and_payments.md", ["Price changes"]),
    ("can i use single sign on", "04_account_and_security.md", ["Single sign-on"]),
    ("who can transfer ownership of the account", "04_account_and_security.md", ["Transferring account ownership"]),
    ("which browsers does the web app work on", "05_troubleshooting.md", ["Supported browsers"]),
    ("how much is the enterprise plan", "01_plans_and_pricing.md", ["Enterprise pricing"]),
    ("i want a copy of all my personal data", "07_privacy_and_data.md", ["Requesting a copy of your data"]),
    ("how do i change my email", "04_account_and_security.md", ["Changing your email address"]),
    ("charged two times this month want one payment back", "02_billing_and_payments.md", ["Charged twice or duplicate charge"]),
    ("the website shows five oh three and nobody can work", "05_troubleshooting.md", ["Service down or error 503"]),
]

# Questions about unrelated topics: the system should answer "not found".
NEGATIVE_FAR = [
    "Do you sell airplane tickets?",
    "What is the capital of France?",
    "Can you recommend a good pizza place?",
    "Who won the cricket world cup?",
    "How do I change the oil in my car?",
]

# Questions that sound like the company, but the documents do not answer them.
NEGATIVE_NEAR = [
    "Who is the CEO of TechNova?",
    "What is the stock price of TechNova?",
    "Does TechNova have an office in Germany?",
    "Can I buy a TechNova t-shirt?",
    "How many employees work at TechNova?",
    "Does the app run on Windows XP?",
    "Is TechNova open source?",
    "Do you offer a lifetime deal?",
]
