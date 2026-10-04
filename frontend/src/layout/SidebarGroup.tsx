import { useState, type ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import styles from './Sidebar.module.css';

type SidebarGroupProps = {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
};

function SidebarGroup({
  title,
  children,
  defaultOpen = true,
}: SidebarGroupProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={styles.group}>
      <p>
        <button
          type="button"
          className={styles.sidebarGroupToggle}
          onClick={() => setIsOpen(open => !open)}
          aria-expanded={isOpen}
        >
          <span className={styles.groupTitle}>{title}</span>

          <ChevronDown
            aria-hidden="true"
            size={15}
            className={`${styles.sidebarGroupChevron} ${
              isOpen ? styles.sidebarGroupChevronOpen : ''
            }`}
          />
        </button>
      </p>

      {isOpen && children}
    </div>
  );
}

export { SidebarGroup }
