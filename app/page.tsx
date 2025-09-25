import { HeroSection } from "@/components/hero-section"
import { EvolutionTimeline } from "@/components/evolution-timeline"
import { MusicPlayer } from "@/components/music-player"
import { AboutSection } from "@/components/about-section"
import { DiscographySection } from "@/components/discography-section"
import { LivePerformances } from "@/components/live-performances"
import { ContactSection } from "@/components/contact-section"
import { Navigation } from "@/components/navigation"

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <main>
        <HeroSection />
        <MusicPlayer />
        <EvolutionTimeline />
        <AboutSection />
        <DiscographySection />
        <LivePerformances />
        <ContactSection />
      </main>
    </div>
  )
}
