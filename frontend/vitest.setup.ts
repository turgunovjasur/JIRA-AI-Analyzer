// Node'ning experimental webstorage globali (metodlari ishlamaydigan localStorage)
// jsdom muhitidagi Storage'ni yopib qo'yadi — testlar uchun to'liq ishlaydigan
// in-memory Storage bilan almashtiramiz.
class MemoryStorage {
  private store = new Map<string, string>();

  get length() {
    return this.store.size;
  }

  clear() {
    this.store.clear();
  }

  getItem(key: string) {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }

  key(index: number) {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string) {
    this.store.delete(key);
  }

  setItem(key: string, value: string) {
    this.store.set(String(key), String(value));
  }
}

for (const name of ["localStorage", "sessionStorage"] as const) {
  const current = (globalThis as Record<string, unknown>)[name] as Storage | undefined;
  if (typeof current?.setItem !== "function") {
    Object.defineProperty(globalThis, name, {
      configurable: true,
      value: new MemoryStorage() as unknown as Storage,
    });
  }
}
