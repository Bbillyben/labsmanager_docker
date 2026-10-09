from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0014_genericinfotype_icon_lucide"),
        ("invitations", "0004_auto_20230328_1430"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="InvitationProvisioning",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="staff.employee")),
                ("invitation", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="labsmanager_provisioning", to="invitations.invitation")),
                ("groups", models.ManyToManyField(blank=True, to="auth.group")),
            ],
        ),
    ]
