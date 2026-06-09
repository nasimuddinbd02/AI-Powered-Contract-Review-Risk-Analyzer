import { ShieldCheck } from "lucide-react";

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-auto border-t bg-background">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-3 px-4 py-6 text-sm text-muted-foreground sm:flex-row sm:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <span>
            &copy; {year} <span className="font-medium text-foreground">ContractIQ</span>. All rights reserved.
          </span>
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden sm:inline">AI-Powered Contract Review &amp; Risk Analyzer</span>
          <span className="text-xs">v1.0.0</span>
        </div>
      </div>
    </footer>
  );
}
