import { getEquipmentInstitutionOptions } from '../api/equipment';
import type { EntitySearchSource } from '../filters/types';

/** Permission-scoped Institution selector shared by Equipment forms and filters. */
export const equipmentInstitutionSource: EntitySearchSource = {
  async search(search, signal) {
    const data = await getEquipmentInstitutionOptions(new URLSearchParams({ search }), signal);
    return {
      options: data.results.map((item) => ({
        value: String(item.id),
        label: `${item.short_name} · ${item.name}`,
      })),
      hasMore: data.has_more,
    };
  },
  async resolve(id, signal) {
    const data = await getEquipmentInstitutionOptions(new URLSearchParams({ id }), signal);
    const item = data.results[0];
    return item ? { value: String(item.id), label: `${item.short_name} · ${item.name}` } : null;
  },
};
