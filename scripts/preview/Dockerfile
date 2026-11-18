FROM mcr.microsoft.com/playwright:v1.56.1-noble
WORKDIR /preview
COPY scripts/preview/package.json .
RUN npm install --ignore-scripts --no-audit --no-fund
COPY scripts/preview/ ./
RUN mkdir -p src/lib src/components/ui /output && printf 'export { clsx as cn } from "clsx";\n' > src/lib/utils.ts
ENV NPM_CONFIG_IGNORE_SCRIPTS=true
CMD ["sleep", "1800"]
