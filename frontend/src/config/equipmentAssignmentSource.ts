import { getEquipment, listEquipment } from '../api/equipment';
import type { EntitySearchSource } from '../filters/types';

/** Search visible Equipment on demand for one Expense business assignment. */
export const equipmentAssignmentSource: EntitySearchSource = {
  async search(search, signal) {
    const data = await listEquipment(
      new URLSearchParams({ search, offset: '0' }).toString(),
      signal,
    );
    return {
      options: data.results.map((item) => ({
        value: String(item.id),
        label: `${item.name} · ${item.internal_reference}`,
      })),
      hasMore: Boolean(data.next),
    };
  },
  async resolve(id, signal) {
    const item = await getEquipment(id, signal);
    return { value: String(item.id), label: `${item.name} · ${item.internal_reference}` };
  },
};
