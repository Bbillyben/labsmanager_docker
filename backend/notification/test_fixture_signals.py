"""Fixture-loading guards for signals with business side effects."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.test import SimpleTestCase

from data_consistency import signals as consistency_signals
from expense import signals as expense_signals
from fund import signals as fund_signals
from notification import signals as notification_signals
from staff.models import Employee


class FixtureSignalTests(SimpleTestCase):
    def test_raw_save_handlers_do_not_read_relations_or_write(self):
        instance = SimpleNamespace(pk=1)

        fund_signals.save_Fund_Item_handler(sender=None, instance=instance, raw=True)
        fund_signals.save_Fund_handler(sender=None, instance=instance, raw=True)
        expense_signals.save_Expense_point_handler(sender=None, instance=instance, raw=True)
        notification_signals.track_status_change(sender=None, instance=instance, raw=True)
        notification_signals.track_participant_add(sender=None, instance=instance, created=True, raw=True)


    def test_consistency_save_handlers_ignore_raw(self):
        handlers = (
            consistency_signals.remember_contract_relation,
            consistency_signals.close_changed_contract,
            consistency_signals.remember_fund_project,
            consistency_signals.close_changed_fund_project,
            consistency_signals.remember_project_dates,
            consistency_signals.close_changed_project_dates,
            consistency_signals.remember_employee_dates,
            consistency_signals.close_changed_employee_dates,
            consistency_signals.remember_milestone_relation,
            consistency_signals.close_changed_milestone,
            consistency_signals.remember_expense_relation,
            consistency_signals.close_changed_expense,
            consistency_signals.remember_participant_relation,
            consistency_signals.close_resolved_participant,
        )
        for handler in handlers:
            with self.subTest(handler=handler.__name__):
                sender = Mock()
                instance = SimpleNamespace(pk=1)
                handler(sender=sender, instance=instance, using="default", raw=True)
                sender.objects.using.assert_not_called()
                self.assertEqual(vars(instance), {"pk": 1})

    def test_normal_financial_signals_still_recalculate(self):
        fund = Mock()
        project = Mock()
        fund_signals.save_Fund_Item_handler(sender=None, instance=SimpleNamespace(fund=fund), raw=False)
        expense_signals.save_Expense_point_handler(sender=None, instance=SimpleNamespace(fund=fund), raw=False)
        fund_signals.save_Fund_handler(sender=None, instance=SimpleNamespace(project=project), raw=False)
        self.assertEqual(fund.calculate.call_count, 2)
        project.calculate.assert_called_once_with()

    def test_normal_participant_notification_still_runs(self):
        user = object()
        participant = SimpleNamespace(employee=SimpleNamespace(user=user))
        with patch.object(notification_signals.UserNotification, "add_notification") as notify:
            notification_signals.track_participant_add(
                sender=None, instance=participant, created=True, raw=False,
            )
        notify.assert_called_once_with(user=user, instance=participant, action="add")

    def test_normal_consistency_handler_still_records_prior_state(self):
        instance = SimpleNamespace(pk=None)
        sender = Mock()
        consistency_signals.remember_contract_relation(
            sender=sender, instance=instance, using="default", raw=False,
        )
        self.assertIsNone(instance._consistency_old_relation)
        sender.objects.using.assert_not_called()

    def test_milestone_m2m_is_quiet_during_cli_import(self):
        with patch.object(notification_signals, "isImportingData", return_value=True), patch.object(
            notification_signals.Employee.objects, "get"
        ) as get_employee, patch.object(notification_signals.UserNotification, "add_notification") as notify:
            notification_signals.employee_milestones_changed(
                sender=None, instance=object(), action="post_add", reverse=False,
                model=None, pk_set={1},
            )
        get_employee.assert_not_called()
        notify.assert_not_called()

    def test_normal_milestone_m2m_still_notifies(self):
        user = object()
        employee = SimpleNamespace(user=user)
        milestone = object()
        with patch.object(notification_signals, "isImportingData", return_value=False), patch.object(
            notification_signals.Employee.objects, "get", return_value=employee
        ) as get_employee, patch.object(notification_signals.UserNotification, "add_notification") as notify:
            notification_signals.employee_milestones_changed(
                sender=None, instance=milestone, action="post_add", reverse=False,
                model=None, pk_set={1},
            )
        get_employee.assert_called_once_with(pk=1)
        notify.assert_called_once_with(user=user, instance=milestone, action="add")

    def test_calendar_m2m_skips_validation_during_cli_import(self):
        Event, EventOccurrenceException = self.calendar_models()
        with patch("sys.argv", ["manage.py", "loaddata", "fixture.json"]):
            for sender in (Event.employees.through, EventOccurrenceException.employees.through):
                with self.subTest(sender=sender):
                    m2m_changed.send(
                        sender=sender, instance=SimpleNamespace(), action="pre_add",
                        reverse=False, model=Employee, pk_set={1}, using="default",
                    )

    def test_calendar_m2m_keeps_normal_validation(self):
        Event, EventOccurrenceException = self.calendar_models()
        with patch("sys.argv", ["manage.py", "test"]):
            for sender, instance in (
                (Event.employees.through, SimpleNamespace(calendar=SimpleNamespace(calendar_type="events"))),
                (EventOccurrenceException.employees.through,
                 SimpleNamespace(event=SimpleNamespace(calendar=SimpleNamespace(calendar_type="events")))),
            ):
                with self.subTest(sender=sender), self.assertRaises(ValidationError):
                    m2m_changed.send(
                        sender=sender, instance=instance, action="pre_add",
                        reverse=False, model=Employee, pk_set={1}, using="default",
                    )

    def calendar_models(self):
        if not apps.is_installed("plugins.Calendars"):
            self.skipTest("External Calendars plugin is not installed")
        from plugins.Calendars.models import Event, EventOccurrenceException
        return Event, EventOccurrenceException
