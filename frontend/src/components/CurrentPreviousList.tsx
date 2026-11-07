import { useId, useState, type ReactNode } from 'react';
import { useTranslation } from '../i18n/i18n';
import { Button } from '../ui/Button';

/** Show current relations first and reveal previous relations on request. */
export function CurrentPreviousList<T extends { id: number }>({
  current,
  previous,
  empty,
  render,
  listClassName,
  emptyClassName,
  previousClassName,
}: {
  current: T[];
  previous: T[];
  empty: string;
  render: (item: T) => ReactNode;
  listClassName?: string;
  emptyClassName?: string;
  previousClassName?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const previousId = useId();
  const { t } = useTranslation();
  return (
    <>
      <div className={listClassName}>
        {current.length ? current.map(render) : <span className={emptyClassName}>{empty}</span>}
        {previous.length > 0 && (
          <div
            id={previousId}
            hidden={!expanded}
            className={expanded ? listClassName : undefined}
          >
            {expanded && previous.map(render)}
          </div>
        )}
      </div>
      {previous.length > 0 && (
        <Button
          className={previousClassName}
          onClick={() => setExpanded((value) => !value)}
          size="xs"
          variant="ghost"
          aria-expanded={expanded}
          aria-controls={previousId}
        >
          {expanded
            ? t('employee.reduceHistory')
            : t(previous.length === 1 ? 'employee.previousOne' : 'employee.previousMany', {
              count: previous.length,
            })}
        </Button>
      )}
    </>
  );
}
