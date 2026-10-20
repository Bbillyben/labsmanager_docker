from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("data_consistency", "0003_more_issue_identities")]

    operations = [
        migrations.AddField("dataconsistencyexception", "teammate_id",
                            models.BigIntegerField(blank=True, null=True)),
        migrations.AddField("dataconsistencyexception", "participant_id",
                            models.BigIntegerField(blank=True, null=True)),
        migrations.AddField("dataconsistencyexception", "team_id",
                            models.BigIntegerField(blank=True, null=True)),
        migrations.AlterField("dataconsistencyexception", "project_id",
                              models.BigIntegerField(blank=True, null=True)),
        migrations.RemoveConstraint("dataconsistencyexception", "unique_open_project_consistency_exception"),
        migrations.AddConstraint("dataconsistencyexception", models.UniqueConstraint(
            fields=("rule_key", "project_id"),
            condition=models.Q(closed_at__isnull=True, contract_id__isnull=True,
                               fund_id__isnull=True, milestone_id__isnull=True,
                               expense_id__isnull=True, participant_id__isnull=True,
                               teammate_id__isnull=True, employee_id__isnull=True),
            name="unique_open_project_consistency_exception")),
        migrations.AddConstraint("dataconsistencyexception", models.UniqueConstraint(
            fields=("rule_key", "employee_id"),
            condition=models.Q(closed_at__isnull=True, employee_id__isnull=False,
                               contract_id__isnull=True, participant_id__isnull=True,
                               teammate_id__isnull=True),
            name="unique_open_employee_consistency_exception")),
        migrations.AddConstraint("dataconsistencyexception", models.UniqueConstraint(
            fields=("rule_key", "teammate_id"),
            condition=models.Q(closed_at__isnull=True, teammate_id__isnull=False),
            name="unique_open_teammate_consistency_exception")),
        migrations.AddConstraint("dataconsistencyexception", models.UniqueConstraint(
            fields=("rule_key", "participant_id"),
            condition=models.Q(closed_at__isnull=True, participant_id__isnull=False),
            name="unique_open_participant_consistency_exception")),
    ]
