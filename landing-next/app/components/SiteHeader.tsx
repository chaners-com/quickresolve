import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 backdrop-blur supports-[backdrop-filter]:bg-white/10 bg-white/5 border-b border-white/10">
      <div className="mx-auto max-w-7xl px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="font-extrabold text-white">
          QuickResolve
        </Link>
        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-6 text-white/85">
          <Link href="/product" className="hover:text-white">Product</Link>
          <Link href="/solutions" className="hover:text-white">Solutions</Link>
          <Link href="/pricing" className="hover:text-white">Pricing</Link>
          <Link href="/security" className="hover:text-white">Security</Link>
          <Link href="/widget" className="hover:text-white">Widget</Link>
        </nav>
        {/* Auth Buttons */}
        <div className="flex items-center gap-3">
          <Link href="/login" className="btn-secondary"> Log in </Link>
          <Link href="#waitlist" className="btn-secondary">Get Early Access</Link>
        </div>
      </div>
    </header>
  );
}