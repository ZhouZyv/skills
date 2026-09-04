import { resolve } from "node:path";

export const vitestShared = {
  resolve: {
    alias: {
      "@taskman/core": resolve(__dirname, "../core/src/index.ts"),
      "@taskman/notify": resolve(__dirname, "../notify/src/index.ts"),
    },
  },
  test: {
    include: ["tests/**/*.test.ts"],
  },
};
