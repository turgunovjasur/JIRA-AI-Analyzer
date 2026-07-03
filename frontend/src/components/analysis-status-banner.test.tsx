import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AnalysisStatusBannerView } from "@/components/analysis-status-banner";

describe("AnalysisStatusBannerView", () => {
  it("banner bo'lmasa hech narsa chizmaydi", () => {
    const { container } = render(<AnalysisStatusBannerView banner={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("title, message va code qatorlarini chiqaradi", () => {
    render(
      <AnalysisStatusBannerView
        banner={{
          level: "warning",
          title: "TZ juda qisqa",
          message: "Kamida 100 belgi kerak.",
          code: "WARN_MIN_TZ",
        }}
      />,
    );

    const notice = screen.getByText(/TZ juda qisqa/);
    expect(notice.textContent).toContain("Kamida 100 belgi kerak.");
    expect(notice.textContent).toContain("Code: WARN_MIN_TZ");
  });
});
