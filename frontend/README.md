# Frontend

Bu papka yangi customer-facing `Next.js` frontend uchun.

## Ishga tushirish

```bash
cd frontend
npm run dev
```

Yoki repo root'dan:

```bash
./start.sh
```

Build tekshiruvi:

```bash
npm run typecheck
npm run build
```

## Env

`.env.local` ichiga kamida quyidagini qo'ying:

```bash
BACKEND_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_BACKEND_API_BASE_URL=http://127.0.0.1:8000
```

## Hozirgi Holat

- `Tailwind CSS v4` foundation o'rnatilgan
- `shadcn/ui` bilan mos ishlaydigan `components.json` va utility layer tayyor
- yangi `ui/` primitive'lar Tailwind utility classlari bilan ishlaydi
- eski `globals.css` layout/classlari bosqichma-bosqich Tailwind utilitylariga ko'chiriladi
- login route tayyor
- dashboard route tayyor
- super admin `/admin` route tayyor
- monitoring sahifasi haqiqiy backend snapshot bilan ishlaydi
- TZ-PR Checker sahifasi haqiqiy backend analyze flow bilan ishlaydi
- Test Case Generator sahifasi haqiqiy backend generate flow bilan ishlaydi
- settings sahifasi haqiqiy customer API keys load/save flow bilan ishlaydi
- company admin `Team` sahifasi haqiqiy user management flow bilan ishlaydi
- super admin kompaniya/billing/platform admin/AI default flowlari haqiqiy backend route'lar bilan ishlaydi
- auth backend-managed session token orqali ishlaydi
- `Next.js` faqat session tokenni `httpOnly` cookie ichida saqlaydi
- `./start.sh` bilan repo root'dan ko'tarish mumkin
- backend `queue` rejimida bo'lsa worker alohida process sifatida ishlaydi
- legacy `Streamlit` qatlam olib tashlangan, portal endi yagona UI hisoblanadi

## Deploy Notes

- `docker compose up --build` worker + postgres bilan to'liq stackni ko'taradi
- compose ichida frontend `backend:8000` manziliga ulanadi
- local `./start.sh` esa `.env` dagi `APP_WEBHOOK_EXECUTION_MODE=queue` bo'lsa worker'ni ham avtomatik ko'taradi
- production checklist uchun [DEPLOY_WEB.md](/Users/mac/Documents/projects/JIRA-AI-Analyzer/DEPLOY_WEB.md) ga qarang

## UI Stack

- `Tailwind CSS v4`
- `shadcn/ui`-compatible component setup
- `Lucide React`
- `class-variance-authority`
- `tailwind-merge`

Migratsiya tartibi:

1. Tailwind + shadcn foundation o'rnatiladi
2. reusable `ui/` komponentlar Tailwind utilitylariga o'tkaziladi
3. sahifa-level `globals.css` classlari asta-sekin Tailwind layoutlariga almashtiriladi
