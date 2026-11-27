# Frontend Docs — LedgerLens

## Stack
- **Next.js 16** (App Router) + TypeScript
- **Tailwind CSS v4** + `Inter` / `JetBrains Mono` (`next/font/google`)
- **lucide-react** for vector icons

## Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Fonts (Inter, JetBrains Mono) + metadata
│   ├── globals.css         # Theme variables + grid utility
│   ├── page.tsx            # Landing — hero, product preview mockup, features
│   ├── auth/
│   │   ├── signup/page.tsx # Account creation → /auth/signin
│   │   └── signin/page.tsx # JWT login → /dashboard
│   ├── dashboard/page.tsx  # Stats, drag-drop upload, skeleton loaders, 3s polling
│   └── chat/page.tsx       # Doc scope sidebar, sample prompts, Q&A + citations
├── components/
│   └── Logo.tsx            # Brand mark + wordmark
└── lib/
    └── api.ts              # Typed fetch wrapper + JWT header injection
```

## API Client (`lib/api.ts`)
- Injects `Authorization: Bearer <token>` from `localStorage`
- Skips `Content-Type: application/json` for `FormData` uploads
- Throws backend `detail` error message on non-2xx responses

## Run Locally

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
# → http://localhost:3000
```

## Deploy (Vercel)
1. Import repo, set **Root Directory** → `frontend`
2. Set `NEXT_PUBLIC_API_URL=https://your-backend.onrender.com`
3. Deploy
