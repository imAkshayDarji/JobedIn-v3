This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

### Clerk auth and deployment

Install the [Clerk CLI](https://clerk.com/cli) (for example `brew install clerk/stable/clerk`). From this directory:

1. `npm run clerk:link` — attach the app to a Clerk instance (or `clerk link --app app_...`).
2. `npm run clerk:env:dev` — write Development keys to `.env.local`.
3. For production: create a **Production** instance in the [Clerk Dashboard](https://dashboard.clerk.com), then `npm run clerk:env:prod` and mirror those variables on your host (e.g. Vercel → Environment Variables).
4. Backend: set `CLERK_JWKS_URL` and the same instance’s Clerk keys on your API service, and set `CORS_ORIGINS` to your deployed frontend origin. See the repository root `.env.example` comments.
5. `npm run clerk:doctor` — verify the integration locally.

Follow [Deploy to production](https://clerk.com/docs/deployments/overview) for domains, OAuth credentials, and CSP on your live URL.

Monorepo production checklist (Railway API, Vercel app, env vars): [docs/DEPLOY.md](../docs/DEPLOY.md).

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
