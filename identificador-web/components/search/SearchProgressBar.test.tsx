import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SearchProgressBar } from "./SearchProgressBar";

describe("SearchProgressBar", () => {
  it("shows determinate progress with percent", () => {
    render(
      <SearchProgressBar
        progress={{ processed: 3, total: 10 }}
        phase="static"
      />,
    );
    expect(screen.getByText("30%")).toBeInTheDocument();
    expect(screen.getByText(/Analizando publicaciones/)).toBeInTheDocument();
  });

  it("shows indeterminate label when total is 0", () => {
    render(
      <SearchProgressBar
        progress={{ processed: 0, total: 0 }}
        phase="static"
      />,
    );
    expect(
      screen.getByText("Buscando coincidencias en la imagen..."),
    ).toBeInTheDocument();
  });

  it("shows deep search label", () => {
    render(
      <SearchProgressBar progress={{ processed: 2, total: 5 }} phase="deep" />,
    );
    expect(screen.getByText(/Búsqueda profunda/)).toBeInTheDocument();
  });
});
