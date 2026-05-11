import Link from "next/link";
import { redirect } from "next/navigation";
import { ArrowRight, Blocks, BriefcaseBusiness, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonClassName } from "@/components/ui/button";
import { getDefaultRouteForRole } from "@/lib/app-routes";
import { getOptionalSession } from "@/lib/session";

export default async function HomePage() {
  const session = await getOptionalSession();
  if (session?.auth?.logged_in) {
    redirect(getDefaultRouteForRole(session.auth.role));
  }

  return (
    <main className="mx-auto grid min-h-screen max-w-7xl gap-5 px-4 py-6 lg:grid-cols-[minmax(0,1.15fr)_360px] lg:px-6">
      <section className="rounded-[28px] border border-border bg-card px-8 py-8 shadow-sm">
        <Badge tone="soft">Web Platform</Badge>
        <div className="mt-6 max-w-4xl space-y-5">
          <h1 className="text-4xl font-semibold tracking-tight text-foreground md:text-6xl md:leading-[1]">
            QA Assistant endi jamoalar uchun qulay, yagona ish portaliga aylandi.
          </h1>
          <p className="max-w-3xl text-base leading-8 text-muted-foreground">
            Checkerlar, monitoring, settings va admin boshqaruvi bir joyda ishlaydi.
            Har bir rol o&apos;ziga kerakli modullar bilan toza va tezkor workspace oladi.
          </p>
        </div>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="rounded-[20px] border border-border bg-slate-50/80 p-5">
            <div className="mb-4 inline-flex rounded-full bg-primary/10 p-2 text-primary">
              <Blocks size={18} />
            </div>
            <strong className="block text-lg font-semibold text-foreground">Asosiy modullar tayyor</strong>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Login, settings, monitoring, checkerlar va admin sahifalari ishga tayyor.
            </p>
          </div>
          <div className="rounded-[20px] border border-border bg-slate-50/80 p-5">
            <div className="mb-4 inline-flex rounded-full bg-primary/10 p-2 text-primary">
              <ShieldCheck size={18} />
            </div>
            <strong className="block text-lg font-semibold text-foreground">Har bir rol uchun aniq UX</strong>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Customer, company admin va super admin uchun boshqaruv oqimlari ajratilgan.
            </p>
          </div>
        </div>
      </section>

      <aside className="rounded-[28px] border border-border bg-card px-6 py-6 shadow-sm">
        <Badge tone="soft">Current Scope</Badge>
        <div className="mt-5 grid gap-3">
          {[
            "Customer flows",
            "Company admin flows",
            "Super admin flows",
            "Queue-driven webhook runtime",
          ].map((item) => (
            <div
              className="rounded-[18px] border border-border bg-slate-50/80 px-4 py-4 text-sm font-medium text-foreground"
              key={item}
            >
              {item}
            </div>
          ))}
        </div>
        <div className="mt-6 rounded-[20px] border border-dashed border-primary/20 bg-primary/5 px-4 py-4">
          <div className="mb-3 inline-flex rounded-full bg-white p-2 text-primary shadow-sm">
            <BriefcaseBusiness size={18} />
          </div>
          <p className="text-sm leading-6 text-muted-foreground">
            Portal customer, ops va admin vazifalarini bir xil dizayn tilida birlashtiradi.
          </p>
        </div>
        <div className="mt-6">
          <Link className={buttonClassName({ fullWidth: true })} href="/login">
            Portalni ochish
            <ArrowRight size={16} />
          </Link>
        </div>
      </aside>
    </main>
  );
}
