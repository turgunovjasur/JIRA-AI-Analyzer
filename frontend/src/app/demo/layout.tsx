import { DemoShell } from "@/components/demo/demo-shell";

export default function DemoLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <DemoShell>{children}</DemoShell>;
}
