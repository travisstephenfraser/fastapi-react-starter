import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

describe("cn", () => {
  it("joins class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("drops falsy values", () => {
    expect(cn("a", false, null, undefined, "b")).toBe("a b");
  });

  it("merges conflicting tailwind classes with twMerge (last wins)", () => {
    // twMerge collapses conflicting utilities so the last one wins.
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
});
