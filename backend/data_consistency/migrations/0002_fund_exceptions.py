from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data_consistency", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="dataconsistencyexception",
            name="unique_open_consistency_exception",
        ),
        migrations.AlterField(
            model_name="dataconsistencyexception",
            name="contract_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="dataconsistencyexception",
            name="employee_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="dataconsistencyexception",
            name="fund_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="dataconsistencyexception",
            constraint=models.UniqueConstraint(
                condition=models.Q(closed_at__isnull=True, contract_id__isnull=False),
                fields=("rule_key", "contract_id", "employee_id", "project_id"),
                name="unique_open_contract_consistency_exception",
            ),
        ),
        migrations.AddConstraint(
            model_name="dataconsistencyexception",
            constraint=models.UniqueConstraint(
                condition=models.Q(closed_at__isnull=True, fund_id__isnull=False),
                fields=("rule_key", "fund_id", "project_id"),
                name="unique_open_fund_consistency_exception",
            ),
        ),
    ]
