from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notice_docs", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentschedule",
            name="payment_type",
            field=models.CharField(
                choices=[
                    ("application", "Application"),
                    ("winner", "Winner"),
                    ("down_payment", "Down payment"),
                    ("middle_payment", "Middle payment"),
                    ("final_payment", "Final payment"),
                    ("installment_payment", "Installment payment"),
                    ("move_in_balance", "Move-in balance"),
                    ("loan", "Loan"),
                    ("other", "Other"),
                ],
                default="other",
                max_length=24,
            ),
        ),
    ]
