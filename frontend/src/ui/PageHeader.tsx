import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from '../i18n/i18n';
import { getPageContext } from '../layout/pageContext';
import { usePageTitle, usePageTitleContext } from '../layout/PageTitleContext';
import styles from './PageHeader.module.css';

type PageHeaderProps = {
  title: string;
  registerTitle?: boolean;
  keepTitle?: boolean;
  description?: string;
  meta?: ReactNode;
  actions?: ReactNode;
};

export function PageHeader({
  title,
  registerTitle = true,
  keepTitle = false,
  description,
  meta,
  actions,
}: PageHeaderProps) {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const inAppBar = usePageTitleContext() !== null;
  const route = getPageContext(pathname);
  usePageTitle(registerTitle ? title : undefined);
  const showTitle =
    !inAppBar ||
    keepTitle ||
    (registerTitle &&
      (!!route?.parent || (route?.label === 'page.home' && title !== t('page.home'))));
  if (!showTitle && !description && !meta && !actions) return null;
  return (
    <header className={styles.header}>
      <div className={styles.copy}>
        {showTitle &&
          (inAppBar ? (
            <h2 className={styles.title}>{title}</h2>
          ) : (
            <h1 className={styles.title}>{title}</h1>
          ))}
        {description && <p className={styles.description}>{description}</p>}
        {meta && <div className={styles.meta}>{meta}</div>}
      </div>
      {actions && <div className={styles.actions}>{actions}</div>}
    </header>
  );
}
