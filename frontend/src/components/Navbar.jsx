import React from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Sprout, ShieldCheck, Menu, X } from "lucide-react";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuSeparator, DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = React.useState(false);

  const links = [
    { to: "/browse", label: "Browse" },
    { to: "/how-it-works", label: "How It Works" },
    { to: "/donate", label: "Donate" },
    { to: "/leaderboard", label: "Donors" },
    { to: "/safety", label: "Safety" },
  ];

  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-[#FAF9F6]/85 border-b border-em-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
        <Link to="/" data-testid="nav-logo-link" className="flex items-center gap-2 group">
          <div className="w-9 h-9 rounded-xl bg-em-primary flex items-center justify-center text-white font-heading font-bold">
            <Sprout className="w-5 h-5" />
          </div>
          <div className="font-heading text-xl font-bold tracking-tight">
            Expire<span className="text-em-primary">Mate</span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-7">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              data-testid={`nav-link-${l.label.toLowerCase().replace(/\s/g, "-")}`}
              className={`text-sm font-medium transition-colors ${
                pathname === l.to ? "text-em-primary" : "text-em-text hover:text-em-primary"
              }`}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button data-testid="nav-user-menu" variant="outline" className="rounded-full border-em-border">
                  {user.verified && <ShieldCheck className="w-4 h-4 text-em-secondary mr-1" />}
                  {user.name.split(" ")[0]}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuLabel className="font-heading">{user.email}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem data-testid="menu-profile" onClick={() => nav(`/users/${user.id}`)}>My profile</DropdownMenuItem>
                <DropdownMenuItem data-testid="menu-dashboard" onClick={() => nav("/dashboard")}>Dashboard</DropdownMenuItem>
                <DropdownMenuItem data-testid="menu-post-item" onClick={() => nav("/post")}>Post an item</DropdownMenuItem>
                {!user.verified && (
                  <DropdownMenuItem data-testid="menu-verify" onClick={() => nav("/verify")}>Verify ID ($2)</DropdownMenuItem>
                )}
                {user.role === "admin" && (
                  <DropdownMenuItem data-testid="menu-admin" onClick={() => nav("/admin")}>Admin panel</DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem data-testid="menu-logout" onClick={async () => { await logout(); nav("/"); }}>
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <>
              <Link to="/login" data-testid="nav-login-link" className="text-sm font-medium text-em-text hover:text-em-primary">
                Log in
              </Link>
              <Button
                data-testid="nav-signup-button"
                onClick={() => nav("/register")}
                className="rounded-full bg-em-primary hover:bg-em-primaryHover text-white px-5"
              >
                Sign up free
              </Button>
            </>
          )}
        </div>

        <button
          data-testid="nav-mobile-toggle"
          className="md:hidden p-2"
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {open && (
        <div className="md:hidden border-t border-em-border bg-em-bg/95 px-4 py-3 space-y-2">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              onClick={() => setOpen(false)}
              data-testid={`mobile-nav-${l.label.toLowerCase().replace(/\s/g, "-")}`}
              className="block py-2 text-em-text"
            >
              {l.label}
            </Link>
          ))}
          {user ? (
            <>
              <Link to="/dashboard" onClick={() => setOpen(false)} className="block py-2">Dashboard</Link>
              <Link to="/post" onClick={() => setOpen(false)} className="block py-2">Post item</Link>
              <button onClick={async () => { await logout(); nav("/"); setOpen(false); }} className="block py-2 text-em-primary">
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" onClick={() => setOpen(false)} className="block py-2">Log in</Link>
              <Link to="/register" onClick={() => setOpen(false)} className="block py-2 text-em-primary font-semibold">Sign up free</Link>
            </>
          )}
        </div>
      )}
    </header>
  );
}
