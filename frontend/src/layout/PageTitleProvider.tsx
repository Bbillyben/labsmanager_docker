import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { PageTitleContext } from './PageTitleContext';

/** Scope dynamic page titles to the active route so old names never leak across navigation. */
export function PageTitleProvider({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const [current, setCurrent] = useState<{
    pathname: string;
    title: string;
    parent?: { href: string; label: string };
  } | null>(null);
  const setTitle = useCallback(
    (title: string, route: string, parent?: { href: string; label: string }) => {
      setCurrent((previous) =>
        previous?.pathname === route &&
        previous.title === title &&
        previous.parent?.href === parent?.href &&
        previous.parent?.label === parent?.label
          ? previous
          : { pathname: route, title, parent },
      );
    },
    [],
  );
  const value = useMemo(
    () => ({
      title: current?.pathname === pathname ? current.title : null,
      parent: current?.pathname === pathname ? (current.parent ?? null) : null,
      setTitle,
    }),
    [current, pathname, setTitle],
  );
  return <PageTitleContext.Provider value={value}>{children}</PageTitleContext.Provider>;
}
