import { createContext, useContext, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { getPageContext } from './pageContext';

export type PageTitleContextValue = {
  title: string | null;
  parent: { href: string; label: string } | null;
  setTitle: (title: string, pathname: string, parent?: { href: string; label: string }) => void;
};

export const PageTitleContext = createContext<PageTitleContextValue | null>(null);

/** Pass a page's already loaded title to the shared application bar. */
export function usePageTitle(title: string | undefined, parent?: { href: string; label: string }) {
  const context = useContext(PageTitleContext);
  const { pathname } = useLocation();
  const dynamic = getPageContext(pathname)?.dynamic;
  const parentHref = parent?.href;
  const parentLabel = parent?.label;
  useEffect(() => {
    if (context && dynamic && title)
      context.setTitle(
        title,
        pathname,
        parentHref && parentLabel ? { href: parentHref, label: parentLabel } : undefined,
      );
  }, [context, dynamic, pathname, title, parentHref, parentLabel]);
}

export function usePageTitleContext() {
  return useContext(PageTitleContext);
}
