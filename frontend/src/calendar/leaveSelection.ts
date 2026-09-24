/** FullCalendar all-day selections use an exclusive end; Leave uses an inclusive date. */
export function leaveDatesFromSelection(start: string, endExclusive: string) {
  const end = new Date(`${endExclusive.slice(0, 10)}T00:00:00Z`)
  end.setUTCDate(end.getUTCDate() - 1)
  return { start_date: start.slice(0, 10), end_date: end.toISOString().slice(0, 10) }
}
