import { render, type RenderOptions } from "@testing-library/react";
import React from "react";

type WrapperProps = { children: React.ReactNode };

function AllProviders({ children }: WrapperProps) {
  return <>{children}</>;
}

function customRender(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

export * from "@testing-library/react";
export { customRender as render };
