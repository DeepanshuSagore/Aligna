import { Navbar } from "@/components/Navbar";
import { Hero } from "@/components/Hero";
import { AuroraBackground } from "@/components/ui/AuroraBackground";

export default function Home() {
  return (
    <main className="relative min-h-screen flex flex-col justify-between overflow-x-hidden pt-20">
      <AuroraBackground />
      <Navbar />
      <Hero />
    </main>
  );
}
