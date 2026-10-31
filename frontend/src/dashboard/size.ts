export type DashboardSize = 'compact' | 'standard' | 'expanded'
/** Resolve the display size accepted for a Dashboard widget. */
export function dashboardSize(width: number, height: number): DashboardSize {
  if (width <= 3 || height <= 2) return 'compact'
  if (width >= 4 && height >= 4) return 'expanded'
  return 'standard'
}
