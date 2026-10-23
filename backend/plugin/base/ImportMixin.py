"""File import methods supplied by active LabsManager plugins."""

import tablib


class ImportMixin:
    import_method = []
    # Declare a list of dictionaries, for example:
    # import_method = [{"id": "expenses", 
    #                       "label": "Import expenses",
    #                   "resource": "ExpenseResource", 
    #                   "handler": "transform_expenses",
    #                   "columns": {
        #                       "Invoice Date": ["Date Facture", "Fact Date"],
    #                           "Amount": ["Total TTC"], 
    #                           "Financial Center": []
    #                   }
    #                 }]
    # Each id (non-empty string) is unique within its plugin; two plugins may use
    # the same id. label, resource (an allowed Resource class name), and handler
    # (a method name on this plugin) are non-empty strings. columns maps every
    # required canonical header to a list of alternate header strings. Matching
    # ignores case and collapses surrounding/repeated whitespace. Every declared
    # column must occur exactly once; missing columns and duplicate matches make
    # the file ineligible. Extra source columns are reported and ignored. An
    # alias shared by two canonical columns is a conflict, never a choice made
    # by column order. check_eligibility(dataset, method, option_data=None) returns
    # a structured report and may be overridden with super() to retain these
    # checks. option_data carries already-selected sheet/header options; the
    # dataset has already been parsed and must not be read from disk again.
    # Before eligibility and normalization, prepare_dataset(dataset, method,
    # option_data=None) may optionally adjust the parsed dataset's structure.
    # Its default returns the dataset unchanged; override it to move headers or
    # remove leading rows. option_data contains selected file options, if any.
    # Do not read the file again: eligibility and normalization use this prepared
    # dataset. Preparation must not write to the database or perform the final
    # business transformation; the handler receives canonical columns instead.
    # normalize_columns passes the handler a tablib.Dataset containing only the
    # canonical headers in declaration order, with the original cell values.
    # Implement handler as transform_expenses(self, dataset, current_import_methode)
    # and return a tablib.Dataset whose headers match the declared Resource.
    # Handlers transform data only; the existing Import-Export preview/commit
    # pipeline validates and writes database rows. Do not write in a handler.

    class MixinMeta:
        """Meta options for this mixin."""
        MIXIN_NAME = "ImportMixin"

    def __init__(self):
        super().__init__()
        self.add_mixin("importmixin", True, __class__)

    def get_import_methods(self):
        return self.import_method

    def get_import_template(self, current_import_methode):
        return tablib.Dataset(headers=list(current_import_methode["columns"]))

    def prepare_dataset(self, dataset, current_import_methode, option_data=None):
        """Prepare a parsed dataset before eligibility checks and normalization.

        Plugins may override this to adjust headers or remove leading rows.
        The default leaves the dataset unchanged.
        """
        return dataset

    @staticmethod
    def _header(value):
        return " ".join(str(value or "").split()).casefold()

    def check_eligibility(self, dataset, current_import_methode, option_data=None):
        columns = current_import_methode["columns"]
        owners = {}
        conflicts = []
        for canonical, aliases in columns.items():
            for name in (canonical, *aliases):
                key = self._header(name)
                previous = owners.setdefault(key, canonical)
                if previous != canonical:
                    conflicts.append(f"{name}: {previous} / {canonical}")
        matches = {canonical: [] for canonical in columns}
        extra = []
        ambiguous = list(conflicts)
        for source in dataset.headers or ():
            canonical = owners.get(self._header(source))
            if canonical:
                matches[canonical].append(str(source))
            else:
                extra.append(str(source))
        for canonical, sources in matches.items():
            if len(sources) > 1:
                ambiguous.append(f"{canonical}: {', '.join(sources)}")
        missing = [name for name, sources in matches.items() if not sources]
        recognized = {name: sources[0] for name, sources in matches.items() if len(sources) == 1}
        aliases_used = {name: source for name, source in recognized.items() if source != name}
        rows = sum(any(value is not None and str(value).strip() for value in row) for row in dataset)
        errors = ([f"Missing columns: {', '.join(missing)}"] if missing else []) + ambiguous
        if not rows:
            errors.append("No usable rows")
        warnings = [f"Extra columns ignored: {', '.join(extra)}"] if extra else []
        return {"eligible": not errors, "rows": rows, "columns": len(dataset.headers or ()),
                "expected": list(columns), "recognized": recognized, "aliases_used": aliases_used,
                "missing": missing, "extra": extra, "ambiguities": ambiguous,
                "errors": errors, "warnings": warnings}

    def normalize_columns(self, dataset, current_import_methode):
        # The plugin's eligibility hook already ran with option_data in preview.
        # Here only the base column mapping is needed for canonical projection.
        report = ImportMixin.check_eligibility(self, dataset, current_import_methode)
        if not report["eligible"]:
            raise ValueError("; ".join(report["errors"]))
        source_positions = {name: index for index, name in enumerate(dataset.headers)}
        names = list(current_import_methode["columns"])
        positions = [source_positions[report["recognized"][name]] for name in names]
        return tablib.Dataset(*([row[index] for index in positions] for row in dataset), headers=names)
