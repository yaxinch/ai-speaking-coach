import { describe, expect, it } from "vitest";
import { parseHistoryTimestamp } from "./HistoryList";

describe("parseHistoryTimestamp", () => {
  it("treats legacy timestamps without an offset as UTC", () => {
    expect(parseHistoryTimestamp("2026-07-03T06:14:20").toISOString()).toBe("2026-07-03T06:14:20.000Z");
  });

  it("preserves timestamps that already include an offset", () => {
    expect(parseHistoryTimestamp("2026-07-03T14:14:20+08:00").toISOString()).toBe("2026-07-03T06:14:20.000Z");
  });
});
