// orval code-generation config: reads openapi.yaml and emits Zod schemas + TypeScript types.
// Run `orval` from lib/api-spec/ to regenerate lib/api-zod/src/generated/.

import { defineConfig, InputTransformerFn } from "orval";
import path from "path";

const root = path.resolve(__dirname, "..", "..");
const apiClientReactSrc = path.resolve(root, "lib", "api-client-react", "src");
const apiZodSrc = path.resolve(root, "lib", "api-zod", "src");

// Our exports make assumptions about the title of the API being "Api" (i.e. generated output is `api.ts`).
// This transformer enforces the title so the output filename stays stable regardless of openapi.yaml changes.
const titleTransformer: InputTransformerFn = (config) => {
  config.info ??= {};
  config.info.title = "Api";  // normalize title to "Api" to keep output path predictable

  return config;
};

export default defineConfig({
  "api-client-react": {
    input: {
      target: "./openapi.yaml",
      override: {
        transformer: titleTransformer,  // apply the title normalizer before generation
      },
    },
    output: {
      workspace: apiClientReactSrc,
      target: "generated",
      client: "react-query",  // generate TanStack Query hooks for each operation
      mode: "split",          // one file per operation
      baseUrl: "/api",
      clean: true,            // delete stale generated files before writing new ones
      prettier: true,
      override: {
        fetch: {
          includeHttpResponseReturnType: false,
        },
        mutator: {
          path: path.resolve(apiClientReactSrc, "custom-fetch.ts"),  // use a custom fetch wrapper
          name: "customFetch",
        },
      },
    },
  },
  zod: {
    input: {
      target: "./openapi.yaml",
      override: {
        transformer: titleTransformer,
      },
    },
    output: {
      workspace: apiZodSrc,
      client: "zod",              // generate Zod validation schemas instead of a fetch client
      target: "generated",
      schemas: { path: "generated/types", type: "typescript" },  // emit TS interfaces alongside schemas
      mode: "split",
      clean: true,
      prettier: true,
      override: {
        zod: {
          coerce: {
            // Coerce query/param strings to typed values automatically
            query: ['boolean', 'number', 'string'],
            param: ['boolean', 'number', 'string'],
            body: ['bigint', 'date'],
            response: ['bigint', 'date'],
          },
        },
        useDates: true,    // parse ISO date strings into Date objects
        useBigInt: true,   // use BigInt for 64-bit integer fields
      },
    },
  },
});
