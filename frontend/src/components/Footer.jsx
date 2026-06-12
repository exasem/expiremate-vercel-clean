import React from "react";
import { Link } from "react-router-dom";
import { Sprout } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-24 border-t border-em-border bg-em-bg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 grid md:grid-cols-3 gap-10">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-9 h-9 rounded-xl bg-em-primary flex items-center justify-center text-white">
              <Sprout className="w-5 h-5" />
            </div>
            <div className="font-heading text-xl font-bold">
              Expire<span className="text-em-primary">Mate</span>
            </div>
          </div>
          <p className="text-sm text-em-textSoft max-w-xs">
            Built by a high school student to keep food out of landfills — and send themselves to college.
          </p>
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-3">Platform</div>
          <ul className="space-y-2 text-sm">
            <li><Link to="/browse" className="hover:text-em-primary">Browse items</Link></li>
            <li><Link to="/post" className="hover:text-em-primary">Post an item</Link></li>
            <li><Link to="/donate" className="hover:text-em-primary">Donate</Link></li>
            <li><Link to="/leaderboard" className="hover:text-em-primary">Donor wall</Link></li>
          </ul>
        </div>
        <div>
          <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-3">Trust &amp; Safety</div>
          <ul className="space-y-2 text-sm">
            <li><Link to="/safety" className="hover:text-em-primary">Safety rules</Link></li>
            <li><Link to="/how-it-works" className="hover:text-em-primary">How it works</Link></li>
            <li><a href="mailto:safety@expiremate.com" className="hover:text-em-primary">Report a problem</a></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-em-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 text-xs text-em-textSoft flex flex-col md:flex-row justify-between gap-2">
          <div>© {new Date().getFullYear()} ExpireMate. A student-run platform.</div>
          <div>By using ExpireMate you agree to our <Link to="/safety" className="underline">terms &amp; disclaimer</Link>.</div>
        </div>
      </div>
    </footer>
  );
}
