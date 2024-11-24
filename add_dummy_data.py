from app import create_app, db
from app.models.user import User, Flat, Expense, ExpenseShare
from datetime import datetime, timedelta

def add_dummy_data():
    app = create_app()
    with app.app_context():
        # Clear existing data
        ExpenseShare.query.delete()
        Expense.query.delete()
        User.query.delete()
        Flat.query.delete()
        db.session.commit()

        # Create a flat
        flat = Flat(name="Test Apartment")
        db.session.add(flat)
        db.session.commit()

        # Create users
        users = [
            User(username="john_doe", email="john@example.com", flat_id=flat.id, is_flat_leader=True),
            User(username="jane_smith", email="jane@example.com", flat_id=flat.id),
            User(username="mike_wilson", email="mike@example.com", flat_id=flat.id)
        ]

        # Set passwords
        for user in users:
            user.set_password("password123")
            db.session.add(user)
        db.session.commit()

        # Create expenses with different splitting scenarios
        expenses = [
            # Equal split expense
            {
                "description": "Monthly Rent",
                "amount": 1500.00,
                "category": "Rent",
                "creator_id": users[0].id,
                "flat_id": flat.id,
                "is_shared": True,
                "shares": [
                    {"user_id": users[0].id, "amount": 500.00},
                    {"user_id": users[1].id, "amount": 500.00},
                    {"user_id": users[2].id, "amount": 500.00}
                ]
            },
            # Custom split expense
            {
                "description": "Groceries",
                "amount": 200.00,
                "category": "Food",
                "creator_id": users[1].id,
                "flat_id": flat.id,
                "is_shared": True,
                "shares": [
                    {"user_id": users[0].id, "amount": 80.00},
                    {"user_id": users[1].id, "amount": 70.00},
                    {"user_id": users[2].id, "amount": 50.00}
                ]
            },
            # Non-shared expense
            {
                "description": "Personal Items",
                "amount": 50.00,
                "category": "Others",
                "creator_id": users[2].id,
                "flat_id": flat.id,
                "is_shared": False,
                "shares": [
                    {"user_id": users[2].id, "amount": 50.00}
                ]
            }
        ]

        # Add expenses and their shares
        for expense_data in expenses:
            expense = Expense(
                description=expense_data["description"],
                amount=expense_data["amount"],
                category=expense_data["category"],
                creator_id=expense_data["creator_id"],
                flat_id=expense_data["flat_id"],
                is_shared=expense_data["is_shared"],
                date=datetime.utcnow() - timedelta(days=expenses.index(expense_data))
            )
            db.session.add(expense)
            db.session.commit()

            # Add expense shares
            for share in expense_data["shares"]:
                expense_share = ExpenseShare(
                    expense_id=expense.id,
                    user_id=share["user_id"],
                    share_amount=share["amount"],
                    is_paid=False
                )
                db.session.add(expense_share)
            
            db.session.commit()

        print("Dummy data added successfully!")
        print("\nTest Users:")
        for user in users:
            print(f"Username: {user.username}, Email: {user.email}, Password: password123")

if __name__ == "__main__":
    add_dummy_data()
