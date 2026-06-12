import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import ItemCard from "@/components/ItemCard";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search } from "lucide-react";

const CATS = ["All", "Food", "Sealed Medicine", "Pet", "Cleaning", "Other"];

export default function BrowsePage() {
  const [items, setItems] = useState([]);
  const [zip, setZip] = useState("");
  const [category, setCategory] = useState("All");
  const [loading, setLoading] = useState(true);

  const fetchItems = async () => {
    setLoading(true);
    try {
      const params = {};
      if (zip) params.zip_code = zip;
      if (category && category !== "All") params.category = category;
      const { data } = await api.get("/items", { params });
      setItems(data.items);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchItems(); /* eslint-disable-next-line */ }, [category]);

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="mb-8">
          <div className="text-xs uppercase tracking-[0.2em] font-semibold text-em-textSoft mb-2">Browse</div>
          <h1 className="font-heading text-4xl sm:text-5xl font-bold tracking-tight">Items expiring near you</h1>
        </div>

        <div className="em-card p-4 mb-8 flex flex-col sm:flex-row gap-3">
          <div className="flex-1 flex items-center gap-2 border border-em-border rounded-xl px-3 bg-white">
            <Search className="w-4 h-4 text-em-textSoft" />
            <Input
              data-testid="browse-zip-input"
              placeholder="ZIP code"
              value={zip}
              onChange={(e) => setZip(e.target.value)}
              className="border-0 focus-visible:ring-0 px-0"
            />
          </div>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger data-testid="browse-category-select" className="w-full sm:w-52 rounded-xl border-em-border">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              {CATS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button
            data-testid="browse-search-button"
            onClick={fetchItems}
            className="rounded-full bg-em-primary hover:bg-em-primaryHover h-11 px-6 font-semibold"
          >
            Search
          </Button>
        </div>

        {loading ? (
          <div className="text-center text-em-textSoft py-12">Loading items…</div>
        ) : items.length === 0 ? (
          <div className="em-card p-12 text-center">
            <p className="font-semibold mb-1">No items match those filters yet.</p>
            <p className="text-sm text-em-textSoft">Try widening your search or be the first to post.</p>
          </div>
        ) : (
          <div data-testid="items-grid" className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {items.map((i) => <ItemCard key={i.id} item={i} />)}
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}
