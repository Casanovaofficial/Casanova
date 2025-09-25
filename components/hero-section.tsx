import { Button } from "@/components/ui/button"

export function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background Image */}
      <div
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{
          backgroundImage: `url('https://hebbkx1anhila5yf.public.blob.vercel-storage.com/287703870_3105532863095145_8169722531221663463_n.jpg-s06J92DwGLXeeodKyMrsdVLsDQmOuE.jpeg')`,
        }}
      >
        <div className="absolute inset-0 bg-black/60" />
      </div>

      {/* Content */}
      <div className="relative z-10 text-center px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto">
        <h1
          className="text-4xl sm:text-6xl md:text-7xl lg:text-8xl xl:text-9xl font-bold text-primary mb-6 tracking-tight"
          style={{ fontFamily: "var(--font-playfair)" }}
        >
          C A S A N O V A
        </h1>
        <p className="text-lg sm:text-xl md:text-2xl mb-8 max-w-2xl mx-auto leading-relaxed text-card">
          From the depths of Stone Avenue to new horizons.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-8">
          <Button size="lg" className="bg-primary hover:bg-primary/90 text-primary-foreground w-full sm:w-auto">
            ▶ Listen Now
          </Button>
          <Button
            variant="outline"
            size="lg"
            className="border-primary text-primary hover:bg-primary hover:text-primary-foreground bg-transparent w-full sm:w-auto"
          >
            ♪ View Discography
          </Button>
        </div>

        <div className="w-full max-w-sm sm:max-w-md mx-auto"></div>
      </div>
    </section>
  )
}
