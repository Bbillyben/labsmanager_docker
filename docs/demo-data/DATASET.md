# Synthetic Demo Dataset v1 (R3.5)

This dataset is a fictional laboratory for a **dedicated, disposable, non-production database**. It is generated around T0 (`--reference-date`) with independent SHA-256 namespaced random streams (`--seed`). Version 1 includes 33 Employees, three Teams, 20 Projects, 14 Funds, Fund Items, Budgets, Expenses, Contracts, Leaves, milestones and tasks. No person, institution, or funder denotes a real entity. The dataset is operational data; it is not a database fixture and it adds no schema migration.

From `backend/`:

```bash
python3 manage.py generate_demo_data --reference-date 2026-10-04 --seed 42
python3 manage.py generate_demo_data --reference-date 2026-10-04 --seed 42 --reset
```

Without `--reset`, the command refuses a database with existing operational data. `--reset` deletes operational data, then recreates the complete dataset in one transaction; it preserves technical/reference catalogs and permission groups. Reset is refused when Django is not in DEBUG mode and the database is not a test database. **NEVER run `generate_demo_data --reset` on a production database.** Back up a dedicated demo database before replacing it. The generator does not merge its data with existing business data.

| Account | Password | Group | Main use |
| --- | --- | --- | --- |
| `admin` | `DemoAdmin42!` | `Lab_admin` | Full dataset and administrative views |
| `labmanager` | `DemoManager42!` | `Lab_Manager` | Laboratory overview |
| `leader` | `DemoLeader42!` | `Lab_leader` | Team and managed Projects |
| `employee` | `DemoEmployee42!` | `Lab_employee` | Assigned tasks, Projects and own Leaves |

All demo accounts use `@example.invalid` addresses and also join `favorite_notif_perm`. The existing `group-fixture.json` defines their permissions; the generator does not copy permission lists. **These credentials are for demo use only and must never be reused in production.**

Useful scenario anchors relative to T0:

- `ORION — Optical Resilience`: active Project with the Employee account, tasks and milestones due soon, two Funds, and both ongoing and upcoming Leaves.
- `SELENE — Sustainable Signals` and `LYRA — Learning Research Arrays`: recently ended Projects that still have open overdue planning items for the Leader dashboard.
- `NOVA — Novel Validation`: future Project; `ECHO — Experimental Collaboration`: completed Project.
- `DM-ORION-BRIDGE`: nearly consumed Fund ending at T0+25; `DM-HELIX-GRANT`: under-consumed Fund ending at T0+30.
- R3.6 adds four dated Expense instalments per Cost Type to ORION-MAIN, ORION-BRIDGE, HELIX-GRANT and COBALT-MAIN. Ordinary `Expense.save()` updates `Expense_point` and its `AmountHistory`, yielding monthly financial curves with distinct consumption patterns. Other Funds retain one instalment per Cost Type. Rebuild only the dedicated demo database to obtain these extra historical points.
- `Ilan BERIVE`: Contract ending at T0+24 and a Leave spanning T0; `Camille ORREN`: Employee account with an upcoming Leave.
- Personal dashboards are precreated from the existing Employee, Leader and Lab Manager templates. The dashboard providers use ordinary visibility rules, so each account sees its authorized subset.

The structural identities, references, group assignments and relationships remain stable with a fixed seed. Dates shift with T0; semi-random staff entry dates and financial amounts change when the seed changes. Historic model signals may attach wall-clock audit timestamps; these do not define the scenario dates. Test with `python3 manage.py test labsmanager.demo_data.tests --keepdb --noinput` in `backend/`.
