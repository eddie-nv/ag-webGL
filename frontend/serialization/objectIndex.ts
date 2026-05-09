/**
 * Append-only uuid -> label map. The serializer uses this for `fullIndex`
 * so the agent can see every object's identity without paying for full state.
 */
export class ObjectIndex {
  private readonly entries = new Map<string, string>()

  add(uuid: string, label: string): void {
    this.entries.set(uuid, label)
  }

  getAll(): Record<string, string> {
    return Object.fromEntries(this.entries)
  }

  size(): number {
    return this.entries.size
  }
}
