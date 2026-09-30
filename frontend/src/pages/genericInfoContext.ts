import type { ProjectCollection, ProjectGenericInfo } from '../api/projects'

export type GenericInfoItem = ProjectGenericInfo
export type GenericInfoCollection = ProjectCollection<GenericInfoItem>
export type GenericInfoType = GenericInfoItem['type']
export type GenericInfoApi = {
  types: (signal: AbortSignal) => Promise<GenericInfoType[]>
  create: (value: { type_id: number; value: string }) => Promise<GenericInfoItem>
  update: (itemId: number, value: string) => Promise<GenericInfoItem>
  delete: (itemId: number) => Promise<void>
}
