/**
 * Bounded queue of recently mutated UUIDs. The serializer emits full state
 * only for objects in this window so the agent context stays small.
 */
export const ACTIVE_WINDOW_CAPACITY = 3

export class ActiveWindow {
  private uuids: string[] = []

  push(uuid: string): void {
    const without = this.uuids.filter((u) => u !== uuid)
    without.push(uuid)
    this.uuids =
      without.length > ACTIVE_WINDOW_CAPACITY
        ? without.slice(without.length - ACTIVE_WINDOW_CAPACITY)
        : without
  }

  contains(uuid: string): boolean {
    return this.uuids.includes(uuid)
  }

  toArray(): string[] {
    return [...this.uuids]
  }
}
