import { describe, expect, it } from "vitest";
import { parsePrometheusMetrics } from "./api";

describe("Prometheus metric parsing", () => {
  it("parses numeric samples, labels, comments and scientific notation", () => {
    const metrics = parsePrometheusMetrics(`# HELP queue_depth Current depth\nqueue_depth{queue=\"telemetry\"} 4\nsentinel_rate 1.25e+2\ninvalid line\nqueue_depth 99`);

    expect(metrics).toEqual({
      queue_depth: 4,
      sentinel_rate: 125
    });
  });
});
