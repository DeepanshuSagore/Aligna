import { Navbar } from "@/components/Navbar";
import { VideoBackground } from "@/components/VideoBackground";
import { Hero } from "@/components/Hero";

export default function Home() {
  return (
    <main className="relative min-h-screen flex flex-col justify-between overflow-x-hidden pt-20">
      <VideoBackground />
      <Navbar />
      <Hero />
    </main>
  );
}
