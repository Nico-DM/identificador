import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SearchResult } from "@/lib/search/types";
import { ResultCard } from "./ResultCard";

const baseResult: SearchResult = {
  url: "https://example.com/post",
  platform: "unknown",
  date: "2024-06-15T12:00:00Z",
  score: 0.8,
  source: "google",
  confidence: "confirmed",
  site_name: "Example Site",
};

describe("ResultCard", () => {
  it("renders site name and formatted date", () => {
    render(<ResultCard result={baseResult} />);
    expect(screen.getByText("Example Site")).toBeInTheDocument();
    expect(screen.getByText(/2024/)).toBeInTheDocument();
  });

  it("shows initials when no thumbnail", () => {
    render(<ResultCard result={baseResult} />);
    expect(screen.getByText("EX")).toBeInTheDocument();
  });

  it("shows provisional date styling", () => {
    const result: SearchResult = {
      ...baseResult,
      confidence: "provisional",
    };
    render(<ResultCard result={result} />);
    expect(screen.getByText(/fecha aproximada/)).toBeInTheDocument();
  });

  it("links to result URL", () => {
    render(<ResultCard result={baseResult} />);
    const links = screen.getAllByRole("link");
    for (const link of links) {
      expect(link).toHaveAttribute("href", "https://example.com/post");
    }
  });
});
