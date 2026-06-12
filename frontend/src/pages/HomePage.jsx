import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ItemCard from "@/components/ItemCard";
import DonationThermometer from "@/components/DonationThermometer";
import ImpactCounter from "@/components/ImpactCounter";
import DonorOfMonth from "@/components/DonorOfMonth";
import { Button } from "@/components/ui/button";
import { Camera, ShieldCheck, HandHeart, Clock, Sparkles, ArrowRight } from "lucide-react";

const HERO_IMG = "https://images.unsplash.com/photo-1721180672597-beddd124205a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjAzOTB8MHwxfHNlYXJjaHwxfHxjb21tdW5pdHklMjBzaGFyaW5nJTIwZm9vZHxlbnwwfHx8fDE3ODEyMjcxMTl8MA&ixlib=rb-4.1.0&q=85";
const FOUNDER_IMG = "https://images.pexels.com/photos/771317/pexels-photo-771317.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

export default function HomePage() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    api.get("/items").then((r) => setItems(r.data.items.slice(0, 6))).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 pb-16 grid lg:grid-cols-12 gap-10 items-center">
        <div className="lg:col-span-7">
          <div className="inline-flex items-center gap-2 rounded-full bg-em-secondary/10 text-em-secondary px-3 py-1.5 text-xs font-semibold tracking-wider uppercase mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Hyperlocal · Verified · Free</span>
          </div>
          <h1 className="font-heading text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.02] mb-5">
            Food expires.<br />
            Your <span className="text-em-primary italic">kindness</span> doesn't.
          </h1>
          <p className="text-lg text-em-textSoft max-w-xl mb-8 leading-relaxed">
            Give unexpired food, sealed medicine, and household items to verified neighbors before they spoil.
            No money. No waste. Every gift helps send a high school student to college.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/browse">
              <Button
                data-testid="hero-browse-button"
                className="rounded-full bg-em-primary hover:bg-em-primaryHover text-white h-12 px-7 text-base font-semibold"
              >
                Browse items near me <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
            <Link to="/register">
              <Button
                data-testid="hero-signup-button"
                variant="outline"
                className="rounded-full border-em-text text-em-text hover:bg-em-text hover:text-white h-12 px-7 text-base font-semibold"
              >
                Start giving
              </Button>
            </Link>
          </div>
          <p className="text-xs text-em-textSoft mt-5">
            $2 one-time ID verification keeps the community safe → 100% goes to the college fund.
          </p>
        </div>

        <div className="lg:col-span-5 space-y-5">
          <div className="relative rounded-3xl overflow-hidden border border-em-border bg-em-surface h-64">
            <img src={HERO_IMG} alt="Community sharing food" className="w-full h-full object-cover" />
            <div className="absolute bottom-3 left-3 right-3 bg-white/95 backdrop-blur rounded-2xl p-3 flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-em-primary/10 flex items-center justify-center">
                <Clock className="w-5 h-5 text-em-primary" />
              </div>
              <div className="text-sm">
                <div className="font-semibold">Avg pickup time</div>
                <div className="text-em-textSoft">Under 4 hours</div>
              </div>
            </div>
          </div>
          <DonationThermometer />
          <DonorOfMonth />
        </div>
      </section>

      {/* Impact counter strip */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-6">
        <ImpactCounter />
      </section>

      {/* How it works */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 border-y border-em-border">
        <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-3">How it works</div>
        <h2 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mb-10 max-w-2xl">
          Three steps. Real food. Real neighbors.
        </h2>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { icon: Camera, title: "Snap a photo", body: "Found Tylenol expiring next month? Milk in 2 days? Photograph it, add the expiration date, post it." },
            { icon: ShieldCheck, title: "A verified neighbor claims", body: "Only ID-verified members can claim. They get a 4-digit code — yours to give in person." },
            { icon: HandHeart, title: "Meet in public, share the code", body: "Pick a grocery store parking lot. Trade the code. The item lives. The donation banner appears." },
          ].map((s, i) => (
            <div key={i} className="em-card p-6 flex flex-col gap-3">
              <div className="w-12 h-12 rounded-2xl bg-em-secondary text-white flex items-center justify-center">
                <s.icon className="w-6 h-6" />
              </div>
              <div className="font-heading text-xl font-semibold">{s.title}</div>
              <div className="text-em-textSoft text-sm leading-relaxed">{s.body}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Recent items */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="flex items-end justify-between gap-4 mb-8">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-2">Available now</div>
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight">Recently posted</h2>
          </div>
          <Link to="/browse" data-testid="see-all-link" className="text-sm font-semibold text-em-primary hover:underline whitespace-nowrap">
            See all →
          </Link>
        </div>

        {items.length === 0 ? (
          <div className="em-card p-10 text-center text-em-textSoft">
            <p className="mb-2 font-semibold text-em-text">No items yet — be the first</p>
            <p className="text-sm">Sign up, verify your ID, and start saving food from the landfill today.</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((i) => <ItemCard key={i.id} item={i} />)}
          </div>
        )}
      </section>

      {/* Founder strip */}
      <section className="bg-em-secondary text-white em-grain relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 grid md:grid-cols-12 gap-10 items-center">
          <div className="md:col-span-5">
            <div className="rounded-3xl overflow-hidden border border-white/10 h-72">
              <img src={FOUNDER_IMG} alt="Founder studying" className="w-full h-full object-cover" />
            </div>
          </div>
          <div className="md:col-span-7">
            <div className="text-xs uppercase tracking-[0.2em] opacity-80 mb-3">Built by a high schooler</div>
            <h2 className="font-heading text-3xl sm:text-4xl font-semibold tracking-tight mb-4 leading-tight">
              Every $3 donation = one closer step to a dorm room, books, a future.
            </h2>
            <p className="text-white/85 mb-6 max-w-2xl leading-relaxed">
              ExpireMate is 100% free. There's no paywall, no premium tier, no ads. The platform is funded by neighbors
              who saved food on it and wanted to say "thanks" with a few bucks.
            </p>
            <Link to="/donate">
              <Button
                data-testid="founder-donate-button"
                className="rounded-full bg-em-yellow hover:bg-em-yellow/90 text-em-text font-semibold h-11 px-6"
              >
                Help me get to college
              </Button>
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
