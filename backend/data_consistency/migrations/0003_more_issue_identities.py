from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("data_consistency", "0002_fund_exceptions")]

    operations = [
        migrations.AddField(
            model_name="dataconsistencyexception", name="milestone_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="dataconsistencyexception", name="expense_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="dataconsistencyexception",
            constraint=models.UniqueConstraint(
                condition=models.Q(closed_at__isnull=True, milestone_id__isnull=False),
                fields=("rule_key", "milestone_id", "project_id"),
                name="unique_open_milestone_consistency_exception",
            ),
        ),
        migrations.AddConstraint(
            model_name="dataconsistencyexception",
            constraint=models.UniqueConstraint(
                condition=models.Q(closed_at__isnull=True, expense_id__isnull=False),
                fields=("rule_key", "expense_id", "project_id"),
                name="unique_open_expense_consistency_exception",
            ),
        ),
        migrations.AddConstraint(
            model_name="dataconsistencyexception",
            constraint=models.UniqueConstraint(
                condition=models.Q(closed_at__isnull=True, contract_id__isnull=True,
                                   fund_id__isnull=True, milestone_id__isnull=True,
                                   expense_id__isnull=True),
                fields=("rule_key", "project_id"),
                name="unique_open_project_consistency_exception",
            ),
        ),
    ]
