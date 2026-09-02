import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SearchProgressBar } from "./SearchProgressBar";

describe("SearchProgressBar", () => {
  it("shows determinate progress with percent", () => {
    render(
      <SearchProgressBar
        progress={{ processed: 3, total: 10 }}
        phase="static"
        secondsRemaining={null}
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
        secondsRemaining={null}
      />,
    );
    expect(
      screen.getByText("Buscando coincidencias en la imagen..."),
    ).toBeInTheDocument();
  });

  it("shows deep search label", () => {
    render(
      <SearchProgressBar
        progress={{ processed: 2, total: 5 }}
        phase="deep"
        secondsRemaining={60}
      />,
    );
    expect(screen.getByText(/Búsqueda profunda/)).toBeInTheDocument();
    expect(screen.getByText(/1 min restantes/)).toBeInTheDocument();
  });

  it("renders stop button when onStop provided", () => {
    const onStop = vi.fn();
    render(
      <SearchProgressBar
        progress={{ processed: 1, total: 5 }}
        phase="static"
        secondsRemaining={null}
        onStop={onStop}
      />,
    );
    expect(
      screen.getByText("Mostrar resultados parciales"),
    ).toBeInTheDocument();
  });
});
