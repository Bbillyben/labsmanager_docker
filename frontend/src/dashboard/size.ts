export type DashboardSize = 'compact' | 'standard' | 'expanded'
export function dashboardSize(width: number, height: number): DashboardSize {
  if (width <= 3 || height <= 2) return 'compact'
  if (width >= 7 && height >= 4) return 'expanded'
  return 'standard'
}
