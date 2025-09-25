import { Card, CardContent } from "@/components/ui/card"

export function EvolutionTimeline() {
  const timelineEvents = [
    {
      year: "2018",
      title: "The Stone Avenue Formation",
      description:
        "Born from the collective passion for blues and rock, The Stone Avenue began their journey as a band.",
      image:
        "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/315527545_3231084310539999_106860494818731701_n.jpg-uCNvKyZIKRvlw9g9eVF2PKdkvNxgtf.jpeg",
    },
    {
      year: "2020",
      title: "First Album Release",
      description:
        "Released self-titled debut Stone Avenue - a powerful statement of musical identity and artistic vision.",
      image:
        "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/ab6761610000e5ebbb218c06832a38e5732c903d.jfif-Ifs0tEumQGFScdI9tpZVC4Z97Kl3nl.jpeg",
    },
    {
      year: "2024",
      title: "WAR",
      description: "Last Stone Avenue single.",
      image:
        "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/286678427_3101911636790601_3843196379373469219_n.jpg-2HriYVjg3q5OJMwRoXZhiB5E3O9eFf.jpeg",
    },
    {
      year: "2024",
      title: "Solo Evolution",
      description: "Casanova emerges - the natural evolution from collective harmony to individual blues expression.",
      image: "/placeholder-upr93.png",
    },
  ]

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 text-background bg-foreground">
      <div className="max-w-6xl mx-auto">
        <h2
          className="text-4xl md:text-5xl font-bold text-center mb-16 text-primary"
          style={{ fontFamily: "var(--font-playfair)" }}
        >
          The Evolution
        </h2>

        <div className="relative">
          {/* Timeline Line */}
          <div className="absolute left-1/2 transform -translate-x-px h-full w-0.5 bg-primary/30 hidden lg:block" />

          {timelineEvents.map((event, index) => (
            <div key={index} className="relative mb-8 sm:mb-12 lg:mb-16">
              <div
                className={`flex flex-col lg:flex-row items-center gap-4 sm:gap-6 lg:gap-8 ${
                  index % 2 === 0 ? "lg:flex-row" : "lg:flex-row-reverse"
                }`}
              >
                {/* Content */}
                <div className="flex-1 w-full">
                  <Card className="backdrop-blur-sm border-border bg-foreground">
                    <CardContent className="p-4 sm:p-6">
                      <div className="flex items-center gap-4 mb-4">
                        <div className="bg-primary text-primary-foreground px-3 py-1 rounded-full text-sm font-bold">
                          {event.year}
                        </div>
                        <div className="h-px bg-primary/30 flex-1" />
                      </div>
                      <h3 className="text-lg sm:text-xl font-bold mb-3 text-card">{event.title}</h3>
                      <p className="text-sm sm:text-base leading-relaxed text-card">{event.description}</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Image */}
                <div className="flex-1 w-full">
                  <img
                    src={event.image || "/placeholder.svg"}
                    alt={event.title}
                    className="w-full h-48 sm:h-56 lg:h-64 object-cover rounded-lg shadow-lg"
                  />
                </div>
              </div>

              {/* Timeline Dot */}
              <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 w-3 h-3 sm:w-4 sm:h-4 bg-primary rounded-full border-2 sm:border-4 border-background hidden lg:block" />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
