export function DiscographySection() {
  const albums = [
    {
      title: "Solo Debut",
      year: "2025",
      description: "The first chapter of the Casanova journey - raw, authentic blues with a modern edge.",
      image: "/placeholder-kaqco.png",
      tracks: ["Midnight Blues", "Lonely Highway", "Soul Revival", "Electric Dreams", "Delta Sunrise"],
    },
    {
      title: "WAR (Stone Avenue Legacy)",
      year: "2020",
      description: "The powerful debut from The Stone Avenue - the foundation that led to this evolution.",
      image: "/placeholder-4rw8t.png",
      tracks: ["Harley", "Backwood", "Hotshot", "Machiavellian", "Hey Lady", "WAR"],
    },
  ]

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 text-foreground bg-foreground">
      <div className="max-w-6xl mx-auto">
        <h2
          className="text-4xl md:text-5xl font-bold text-center mb-12 text-primary"
          style={{ fontFamily: "var(--font-playfair)" }}
        >
          Discography
        </h2>

        <div className="flex justify-center">
          <div className="w-full max-w-lg backdrop-blur-sm border border-border rounded-lg p-4 sm:p-6 hover:shadow-lg transition-shadow bg-foreground">
            <h3 className="text-xl sm:text-2xl font-bold mb-4 text-center text-foreground">
              WAR (Stone Avenue Legacy) - 2020
            </h3>
            <div className="w-full flex justify-center">
              <iframe
                data-testid="embed-iframe"
                style={{ borderRadius: "12px" }}
                src="https://open.spotify.com/embed/album/7L68NHmd6FQ1IWdWbAc3yr?utm_source=generator"
                width="100%"
                height="352"
                frameBorder="0"
                allowFullScreen
                allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                loading="lazy"
                className="max-w-full"
              />
            </div>
            <p className="text-muted-foreground mt-4 text-center leading-relaxed text-sm sm:text-base">
              The powerful debut from The Stone Avenue - the foundation that led to this evolution.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
